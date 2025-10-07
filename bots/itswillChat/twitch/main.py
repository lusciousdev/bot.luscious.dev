import asyncio
import os
import sys

import django
import twitchio
from asgiref.sync import async_to_sync, sync_to_async
from luscioustwitch import TwitchAPI
from twitchio.ext import commands, routines

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

django.setup()

import botmanager.models as django_models
from bots.generic.commands import BotCommand
from bots.generic.twitch import TwitchBot

from bots.itswillChat.chat_generator import ChatGenerator


class itswillChatTwitchBot(TwitchBot):
    chat_generator: ChatGenerator = None

    max_history: int = 25
    bot_input_length: int = 3

    channel_history = {}

    def __init__(self, bot_name: str, verbose=False):
        super().__init__(bot_name, verbose)

    async def create(self):
        await super().create()

        self.chat_generator = ChatGenerator()

        try:
            bot_model = await django_models.ChatBot.objects.select_related(
                "twitchconfig"
            ).aget(name=self.bot_name)
        except django_models.ChatBot.DoesNotExist:
            raise (f'Bot with name "{self.bot_name}" does not exist.')

        chats = await sync_to_async(list)(
            django_models.TwitchChat.objects.filter(config=bot_model.twitchconfig).all()
        )
        channel: django_models.TwitchChat
        for channel in chats:
            self.channel_history[channel.channel_name.lower()] = []

    async def event_message(self, payload: twitchio.ChatMessage):
        if payload.chatter.id == self.bot_id:
            return

        ctx = self.get_context(payload)

        self.channel_history[ctx.channel.name].append(str(payload.text))
        if len(self.channel_history[ctx.channel.name]) > self.max_history:
            self.channel_history[ctx.channel.name] = self.channel_history[
                ctx.channel.name
            ][(-1 * self.max_history) :]

        await super().event_message(payload)

    async def send_generated_message(self, channel):
        if len(self.channel_history[channel]) == 0:
            print(f'Somehow we have no chat history for "{channel}", skipping.')
            return

        bot_input = (
            self.channel_history[channel]
            if len(self.channel_history[channel]) <= self.bot_input_length
            else self.channel_history[channel][(-1 * self.bot_input_length) :]
        )
        response = self.chat_generator.generate(bot_input)

        response = response if len(response) < 400 else response[:400]

        await self.send_chat_message(self.channels[channel]["id"], response)

    async def send_response(self, command: BotCommand, message: twitchio.ChatMessage):
        msgcontent = str(message.text)
        cleanmsg = msgcontent
        if cleanmsg.startswith(command.command):
            cleanmsg = cleanmsg[len(command.command) :]
        cleanmsg = cleanmsg.strip()

        response = self.chat_generator.gen_response(str(cleanmsg))
        response = response if len(response) < 400 else response[:400]
        _ = await self.send_chat_message(message.broadcaster.id, response, reply_to_message_id = message.id)

    async def send_message_about(
        self, command: BotCommand, message: twitchio.ChatMessage
    ):
        msgcontent = str(message.text)
        cleanmsg = msgcontent
        if cleanmsg.startswith(command.command):
            cleanmsg = cleanmsg[len(command.command) :]
        clearmsg = cleanmsg.strip()

        response = self.chat_generator.gen_about(str(clearmsg))
        response = response if len(response) < 400 else response[:400]
        _ = await self.send_chat_message(message.broadcaster.id, response, reply_to_message_id = message.id)


def main() -> None:
    async def runner() -> None:
        async with itswillChatTwitchBot(bot_name="itswillChat", verbose=False) as bot:
            await bot.create()
            await bot.start(with_adapter=False)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("Shutting down due to KeyboardInterrupt...")


if __name__ == "__main__":
    main()
