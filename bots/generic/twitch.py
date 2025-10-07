import argparse
import asyncio
import datetime as dt
import json
import logging
import re
import sys
import typing

import django
import twitchio
from asgiref.sync import async_to_sync, sync_to_async
from luscioustwitch import *
from twitchio.ext import commands as twitchio_commands
from twitchio.ext import routines as twitchio_routines

from .commands import BotCommand

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

django.setup()

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings

import botmanager.models as django_models


class TwitchBot(twitchio_commands.Bot):
    __token__: str = ""

    channels = {}
    commands: list[BotCommand] = []
    custom_commands: typing.List[BotCommand] = []

    periodic_messages: typing.Dict[
        str,
        typing.Dict[
            str, typing.Union[BotCommand, twitchio_routines.Routine, bool, int, None]
        ],
    ] = {}
    custom_periodic_messages: typing.Dict[
        str,
        typing.Dict[
            str, typing.Union[BotCommand, twitchio_routines.Routine, bool, int, None]
        ],
    ] = {}

    def __init__(
        self,
        bot_name: str,
        verbose=False,
    ):
        self.bot_name = bot_name
        self.verbose = verbose

    async def create(self):
        try:
            bot_model = await django_models.ChatBot.objects.select_related(
                "twitchconfig"
            ).aget(name=self.bot_name)
        except django_models.ChatBot.DoesNotExist:
            raise (f'Bot with name "{self.bot_name}" does not exist.')

        twitchconfig: django_models.TwitchConfig = bot_model.twitchconfig

        self.provider = twitchconfig.provider

        twitchchat: django_models.TwitchChat
        chats = await sync_to_async(list)(
            django_models.TwitchChat.objects.filter(config=twitchconfig).all()
        )
        for twitchchat in chats:
            self.channels[twitchchat.channel_name.lower()] = {
                "id": twitchchat.channel_id,
                "is_live": False,
            }

        super().__init__(
            client_id=twitchconfig.client_id,
            client_secret=twitchconfig.client_secret,
            bot_id=twitchconfig.user_id,
            owner_id=twitchconfig.owner_id,
            prefix="\0",
        )

    async def close(self, **options: typing.Any) -> None:
        pass

    async def add_token(
        self, token: str, refresh: str
    ) -> twitchio.authentication.ValidateTokenPayload:
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(
            token, refresh
        )

        account = None
        try:
            account = await SocialAccount.objects.aget(
                provider=self.provider, uid=resp.user_id
            )
        except SocialAccount.DoesNotExist:
            LOGGER.debug(f"Token added for unknown user: {resp.user_id}")
            return resp

        if account:
            await SocialToken.objects.aupdate_or_create(
                account=account,
                defaults={
                    "token": token,
                    "token_secret": refresh,
                    "expires_at": datetime.datetime.now(tz=datetime.UTC)
                    + datetime.timedelta(seconds=resp.expires_in),
                },
            )

        print("token added for " + account.uid)
        return resp

    async def load_tokens(self, path: str | None = None) -> None:
        bot_account = await SocialAccount.objects.aget(
            provider=self.provider, uid=self.bot_id
        )
        bot_token = await SocialToken.objects.aget(account=bot_account)

        _ = await self.add_token(bot_token.token, bot_token.token_secret)

    async def event_ready(self):
        print(f"Logged in as {self.bot_id}")
        print(f"User ID is {self.bot_id}")

        self.twitch_api = TwitchAPI(
            credentials={
                "CLIENT_ID": settings.TWITCH_API_CLIENT_ID,
                "CLIENT_SECRET": settings.TWITCH_API_CLIENT_SECRET,
            }
        )

        for channel_name, channel_data in self.channels.items():
            await self.subscribe_to_channel(channel_id=channel_data["id"])

        _ = self.get_commands.start()
        _ = self.start_routines.start()
        _ = self.check_if_live.start()

    async def subscribe_to_channel(self, channel_id: str) -> None:
        subscription = twitchio.eventsub.ChatMessageSubscription(
            broadcaster_user_id=channel_id, user_id=self.bot_id
        )

        _ = await self.subscribe_websocket(payload=subscription)

    @twitchio_routines.routine(delta=datetime.timedelta(seconds=10), wait_first=False)
    @sync_to_async
    def get_commands(self):
        try:
            bot_model = django_models.ChatBot.objects.get(name=self.bot_name)
        except django_models.ChatBot.DoesNotExist:
            raise (f'Bot with name "{self.bot_name}" does not exist.')

        twitchconfig: django_models.TwitchConfig = bot_model.twitchconfig

        existing_commands = []
        command: django_models.TwitchBasicCommand
        for command in twitchconfig.twitchbasiccommand_set.all():
            existing_commands.append(command.command)
            newbc = BotCommand(
                command.command,
                command.output,
                command.as_reply,
                command.match_anywhere,
                command.regex_command,
                command.cooldown,
                command.cooldown_while_offline,
            )

            command_exists = False
            bc: BotCommand
            for bc in self.commands:
                if bc.command == command.command:
                    if newbc != bc:
                        print(f"Updating command: {bc.command}")
                    bc.output = command.output
                    bc.as_reply = command.as_reply
                    bc.cooldown = command.cooldown
                    bc.cooldown_while_offline = command.cooldown_while_offline
                    command_exists = True

            if not command_exists:
                print(f"New command: {command.command}")
                self.commands.append(newbc)

        for i in reversed(range(len(self.commands))):
            if self.commands[i].command not in existing_commands:
                print(f"Command deleted: {self.commands[i].command}")
                del self.commands[i]

        existing_custom_commands = []
        custom_command: django_models.TwitchCustomCommand
        for custom_command in twitchconfig.twitchcustomcommand_set.all():
            existing_custom_commands.append(custom_command.command)
            newbc = BotCommand(
                custom_command.command,
                custom_command.output,
                custom_command.as_reply,
                custom_command.match_anywhere,
                custom_command.regex_command,
                custom_command.cooldown,
                custom_command.cooldown_while_offline,
            )

            command_exists = False
            bc: BotCommand
            for bc in self.custom_commands:
                if bc.command == custom_command.command:
                    if bc != newbc:
                        print(f"Updating custom command: {bc.command}")
                    bc.output = custom_command.output
                    bc.as_reply = custom_command.as_reply
                    bc.cooldown = custom_command.cooldown
                    bc.cooldown_while_offline = custom_command.cooldown_while_offline
                    command_exists = True

            if not command_exists:
                print(f"New custom command: {custom_command.command}")
                self.custom_commands.append(newbc)

        for i in reversed(range(len(self.custom_commands))):
            if self.custom_commands[i].command not in existing_custom_commands:
                print(f"Custom command deleted: {self.custom_commands[i].command}")
                del self.custom_commands[i]

        existing_periodics = []
        periodic_message: django_models.TwitchPeriodicMsg
        for periodic_message in twitchconfig.twitchperiodicmsg_set.all():
            name = periodic_message.name
            existing_periodics.append(name)

            cmd = BotCommand(
                periodic_message.name,
                periodic_message.output,
                False,
                False,
                False,
                periodic_message.period,
            )

            if periodic_message.name in self.periodic_messages:
                if self.periodic_messages[name]["cmd"] != cmd:
                    print(f"Updating periodic message: {periodic_message.name}")

                if (
                    self.periodic_messages[name]["cmd"].cooldown
                    != periodic_message.period
                ):
                    if self.periodic_messages[name]["routine"] is not None:
                        self.periodic_messages[name]["routine"].change_interval(
                            seconds=periodic_message.period
                        )

                self.periodic_messages[name]["cmd"].output = periodic_message.output
                self.periodic_messages[name]["cmd"].cooldown = periodic_message.period
                self.periodic_messages[name][
                    "only_while_live"
                ] = periodic_message.only_while_live

            else:
                print(f"New periodic message: {periodic_message.name}")
                self.periodic_messages[periodic_message.name] = {
                    "cmd": cmd,
                    "only_while_live": periodic_message.only_while_live,
                    "routine": None,
                    "deleted": False,
                }

        for name in self.periodic_messages.keys():
            if self.periodic_messages[name]["cmd"].command not in existing_periodics:
                print(
                    f"Periodic message deleted: {self.periodic_messages[name]['cmd'].command}"
                )
                self.periodic_messages[name]["deleted"] = True

        existing_custom_periodics = []
        custom_periodic_message: django_models.TwitchCustomPeriodicMsg
        for custom_periodic_message in twitchconfig.twitchcustomperiodicmsg_set.all():
            name = custom_periodic_message.name
            existing_custom_periodics.append(name)
            cmd = BotCommand(
                custom_periodic_message.name,
                custom_periodic_message.output,
                False,
                False,
                False,
                custom_periodic_message.period,
            )

            if custom_periodic_message.name in self.custom_periodic_messages:
                if self.custom_periodic_messages[name]["cmd"] != cmd:
                    print(
                        f"Updating custom periodic message: {custom_periodic_message.name}"
                    )

                if (
                    self.custom_periodic_messages[name]["cmd"].cooldown
                    != custom_periodic_message.period
                ):
                    if self.custom_periodic_messages[name]["routine"] is not None:
                        self.custom_periodic_messages[name]["routine"].change_interval(
                            seconds=custom_periodic_message.period
                        )

                self.custom_periodic_messages[name][
                    "cmd"
                ].output = custom_periodic_message.output
                self.custom_periodic_messages[name][
                    "cmd"
                ].cooldown = custom_periodic_message.period
                self.custom_periodic_messages[name][
                    "only_while_live"
                ] = custom_periodic_message.only_while_live

            else:
                print(f"New custom periodic message: {custom_periodic_message.name}")
                self.custom_periodic_messages[custom_periodic_message.name] = {
                    "cmd": cmd,
                    "only_while_live": custom_periodic_message.only_while_live,
                    "routine": None,
                    "deleted": False,
                }

        for name in self.custom_periodic_messages.keys():
            if (
                self.custom_periodic_messages[name]["cmd"].command
                not in existing_custom_periodics
            ):
                print(
                    f"Periodic message deleted: {self.custom_periodic_messages[name]['cmd'].command}"
                )
                self.custom_periodic_messages[name]["deleted"] = True

        if self.verbose:
            print(
                self.channels,
                self.commands,
                self.custom_commands,
                self.periodic_messages,
                self.custom_periodic_messages,
            )

    @twitchio_routines.routine(delta=datetime.timedelta(seconds=10), wait_first=True)
    async def start_routines(self):
        for name in list(self.periodic_messages.keys()):
            if self.periodic_messages[name]["routine"] is None:
                self.periodic_messages[name]["routine"] = twitchio_routines.Routine(
                    coro=lambda: self.send_periodic_message(name),
                    delta=datetime.timedelta(seconds = self.periodic_messages[name]["cmd"].cooldown),
                    wait_first=False,
                    iterations=None,
                    time=None,
                )
                self.periodic_messages[name]["routine"].start()

            if self.periodic_messages[name]["deleted"]:
                self.periodic_messages[name]["routine"].cancel()
                del self.periodic_messages[name]

        for name in list(self.custom_periodic_messages.keys()):
            if self.custom_periodic_messages[name]["routine"] is None:
                self.custom_periodic_messages[name]["routine"] = (
                    twitchio_routines.Routine(
                        coro=lambda: self.send_custom_periodic_message(name),
                        delta=datetime.timedelta(seconds = self.custom_periodic_messages[name]["cmd"].cooldown),
                        wait_first=False,
                        iterations=None,
                        time=None,
                    )
                )
                self.custom_periodic_messages[name]["routine"].start()

            if self.custom_periodic_messages[name]["deleted"]:
                self.custom_periodic_messages[name]["routine"].cancel()
                del self.custom_periodic_messages[name]

    @twitchio_routines.routine(delta=datetime.timedelta(minutes=1), wait_first=False)
    async def check_if_live(self):
        for channel in self.channels.keys():
            self.channels[channel]["is_live"] = self.twitch_api.is_user_live(
                self.channels[channel]["id"]
            )

            if self.verbose:
                print(
                    channel,
                    self.channels[channel]["id"],
                    self.channels[channel]["is_live"],
                )

    async def send_chat_message(self, buid: str, message: str, reply_to_message_id : str|None = None) -> None:
        broadcaster = self.create_partialuser(user_id=buid)
        _ = await broadcaster.send_message(message, sender = self.user, token_for = self.user, reply_to_message_id = reply_to_message_id)

    async def send_periodic_message(self, command_name: str):
        only_while_live = self.periodic_messages[command_name]["only_while_live"]
        for channel in self.channels.keys():
            if only_while_live and not self.channels[channel]["is_live"]:
                continue

            botcommand: BotCommand = self.periodic_messages[command_name]["cmd"]
            output = botcommand.generate_output("")
            output = output if len(output) < 500 else output[:499]
            await self.send_chat_message(self.channels[channel]["id"], output)

    async def send_custom_periodic_message(self, command_name: str):
        only_while_live = self.custom_periodic_messages[command_name]["only_while_live"]
        for channel in self.channels.keys():
            if only_while_live and not self.channels[channel]["is_live"]:
                continue

            botcommand: BotCommand = self.custom_periodic_messages[command_name]["cmd"]

            func = getattr(self, botcommand.output, None)
            if func is not None:
                await eval(
                    f"self.{botcommand.output}(channel)",
                    {"self": self, "channel": channel},
                )
            else:
                await self.send_chat_message(
                    self.channels[channel]["id"],
                    f'Function "{botcommand.output}" does not exist in the local scope.',
                )

    async def event_message(self, payload: twitchio.ChatMessage):
        if payload.chatter.id == self.bot_id:
            return

        command: BotCommand
        for command in self.commands:
            if command.match(str(payload.text)):
                if self.verbose:
                    print(str(payload.text))

                if not command.is_on_cooldown(
                    payload.chatter.id, self.channels[payload.broadcaster.name]["is_live"]
                ):
                    output = command.generate_output(payload.text, payload.chatter.id)
                    output = output if len(output) < 500 else output[:499]
                    if command.as_reply:
                        _ = await self.send_chat_message(payload.broadcaster.id, output, reply_to_message_id = payload.id) # payload.respond(output)
                    else:
                        _ = await self.send_chat_message(payload.broadcaster.id, output)
                    command.sent()
                elif self.verbose:
                    print(f"Command {command.command} skipped due to cooldown.")

        command: BotCommand
        for command in self.custom_commands:
            if command.match(str(payload.text)):
                if self.verbose:
                    print(str(payload.text))

                if not command.is_on_cooldown():
                    func = getattr(self, command.output, None)
                    if func is not None:
                        await eval(
                            f"self.{command.output}(command, message)",
                            {"self": self, "command": command, "message": payload},
                        )
                    else:
                        _ = await payload.respond("Error.")
                        logging.error(
                            f'Function "{command.output}" does not exist in the local scope.'
                        )
                    command.sent()
                elif self.verbose:
                    print(f"Command {command.command} skipped due to cooldown.")
