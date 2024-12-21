import argparse
import datetime as dt
import json
import re
import sys
import django
import typing
import asyncio
from asgiref.sync import sync_to_async, async_to_sync
import logging

import twitchio
from luscioustwitch import *
from twitchio.ext import commands as twitchio_commands
from twitchio.ext import routines as twitchio_routines

from .commands import BotCommand

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
os.environ['DJANGO_SETTINGS_MODULE'] = "config.settings"

django.setup()

import botmanager.models as django_models

class TwitchBot(twitchio_commands.Bot):
  __token__ : str = ""
  
  channels = {}
  commands : typing.List[BotCommand] = []
  custom_commands : typing.List[BotCommand] = []
  
  periodic_messages : typing.Dict[str, typing.Dict[str, typing.Union[BotCommand, twitchio_routines.Routine, bool, int, None]]] = {}
  custom_periodic_messages : typing.Dict[str, typing.Dict[str, typing.Union[BotCommand, twitchio_routines.Routine, bool, int, None]]] = {}
  
  def __init__(self, bot_name : str, verbose = False, ):
    self.bot_name = bot_name
    self.verbose = verbose
    
    try:
      bot_model = django_models.ChatBot.objects.get(name = self.bot_name)
    except django_models.ChatBot.DoesNotExist:
      raise(f"Bot with name \"{bot_name}\" does not exist.")
    
    twitchconfig : django_models.TwitchConfig = bot_model.twitchconfig
    
    twitchchat : django_models.TwitchChat
    for twitchchat in twitchconfig.twitchchat_set.all():
      self.channels[twitchchat.channel_name.lower()] = {
        "id": twitchchat.channel_id,
        "is_live": False,
        "chat_channel": None,
      }
    
    self.__token__ = twitchconfig.access_token
    
    self.api = TwitchAPI({ "CLIENT_ID": twitchconfig.client_id, "ACCESS_TOKEN": twitchconfig.access_token })
    
    super().__init__(token = self.__token__, prefix = '\0', initial_channels = self.channels)

  async def event_ready(self):
    print(f'Logged in as {self.nick}')
    print(f'User ID is {self.user_id}')
    
    channel : str
    for channel in self.channels.keys():
      self.channels[channel]["chat_channel"] = self.get_channel(channel)
    
    self.get_commands.start(stop_on_error = False)
    self.start_routines.start(stop_on_error = False)
    self.check_if_live.start(stop_on_error = False)
    
  @twitchio_routines.routine(seconds = 10, wait_first = False)
  @sync_to_async
  def get_commands(self):
    try:
      bot_model = django_models.ChatBot.objects.get(name = self.bot_name)
    except django_models.ChatBot.DoesNotExist:
      raise(f"Bot with name \"{self.bot_name}\" does not exist.")
    
    twitchconfig : django_models.TwitchConfig = bot_model.twitchconfig
      
    existing_commands = []
    command : django_models.TwitchBasicCommand
    for command in twitchconfig.twitchbasiccommand_set.all():
      existing_commands.append(command.command)
      newbc = BotCommand(command.command, command.output, command.as_reply, command.match_anywhere, command.regex_command, command.cooldown, command.cooldown_while_offline)
      
      command_exists = False
      bc : BotCommand
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
    custom_command : django_models.TwitchCustomCommand
    for custom_command in twitchconfig.twitchcustomcommand_set.all():
      existing_custom_commands.append(custom_command.command)
      newbc = BotCommand(custom_command.command, custom_command.output, custom_command.as_reply, custom_command.match_anywhere, custom_command.regex_command, custom_command.cooldown, custom_command.cooldown_while_offline)
      
      command_exists = False
      bc : BotCommand
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
    periodic_message : django_models.TwitchPeriodicMsg
    for periodic_message in twitchconfig.twitchperiodicmsg_set.all():
      name = periodic_message.name
      existing_periodics.append(name)
      
      cmd = BotCommand(periodic_message.name, periodic_message.output, False, False, False, periodic_message.period)
      
      if periodic_message.name in self.periodic_messages:
        if self.periodic_messages[name]['cmd'] != cmd:
          print(f"Updating periodic message: {periodic_message.name}")
        
        if self.periodic_messages[name]['cmd'].cooldown != periodic_message.period:
          if self.periodic_messages[name]['routine'] is not None:
            self.periodic_messages[name]['routine'].change_interval(seconds = periodic_message.period)
        
        self.periodic_messages[name]['cmd'].output = periodic_message.output
        self.periodic_messages[name]['cmd'].cooldown = periodic_message.period
        self.periodic_messages[name]['only_while_live'] = periodic_message.only_while_live
        
      else:
        print(f"New periodic message: {periodic_message.name}")
        self.periodic_messages[periodic_message.name] = {
          'cmd': cmd,
          'only_while_live': periodic_message.only_while_live,
          'routine': None,
          'deleted': False,
        }
        
    for name in self.periodic_messages.keys():
      if self.periodic_messages[name]['cmd'].command not in existing_periodics:
        print(f"Periodic message deleted: {self.periodic_messages[name]['cmd'].command}")
        self.periodic_messages[name]['deleted'] = True
      
    existing_custom_periodics = []
    custom_periodic_message : django_models.TwitchCustomPeriodicMsg
    for custom_periodic_message in twitchconfig.twitchcustomperiodicmsg_set.all():
      name = custom_periodic_message.name
      existing_custom_periodics.append(name)
      cmd = BotCommand(custom_periodic_message.name, custom_periodic_message.output, False, False, False, custom_periodic_message.period)
        
      if custom_periodic_message.name in self.custom_periodic_messages:
        if self.custom_periodic_messages[name]['cmd'] != cmd:
          print(f"Updating custom periodic message: {custom_periodic_message.name}")
        
        if self.custom_periodic_messages[name]['cmd'].cooldown != custom_periodic_message.period:
          if self.custom_periodic_messages[name]['routine'] is not None:
            self.custom_periodic_messages[name]['routine'].change_interval(seconds = custom_periodic_message.period)
          
        self.custom_periodic_messages[name]['cmd'].output = custom_periodic_message.output
        self.custom_periodic_messages[name]['cmd'].cooldown = custom_periodic_message.period
        self.custom_periodic_messages[name]['only_while_live'] = custom_periodic_message.only_while_live
        
      else:
        print(f"New custom periodic message: {custom_periodic_message.name}")
        self.custom_periodic_messages[custom_periodic_message.name] = {
          'cmd' : cmd,
          'only_while_live': custom_periodic_message.only_while_live,
          'routine': None,
          'deleted': False,
        }
        
    for name in self.custom_periodic_messages.keys():
      if self.custom_periodic_messages[name]['cmd'].command not in existing_custom_periodics:
        print(f"Periodic message deleted: {self.custom_periodic_messages[name]['cmd'].command}")
        self.custom_periodic_messages[name]['deleted'] = True
    
    if self.verbose:
      print(self.channels, self.commands, self.custom_commands, self.periodic_messages, self.custom_periodic_messages)
    
  @twitchio_routines.routine(seconds = 10, wait_first = True)
  async def start_routines(self):
    for name in list(self.periodic_messages.keys()):
      if self.periodic_messages[name]['routine'] is None:
        self.periodic_messages[name]['routine'] = twitchio_routines.Routine(coro = lambda: self.send_periodic_message(name), delta = self.periodic_messages[name]['cmd'].cooldown, wait_first = False)
        self.periodic_messages[name]['routine'].start(stop_on_error = False)
        
      if self.periodic_messages[name]['deleted']:
        self.periodic_messages[name]['routine'].cancel()
        del self.periodic_messages[name]
        
    for name in list(self.custom_periodic_messages.keys()):
      if self.custom_periodic_messages[name]['routine'] is None:
        self.custom_periodic_messages[name]['routine'] = twitchio_routines.Routine(coro = lambda: self.send_custom_periodic_message(name), delta = self.custom_periodic_messages[name]['cmd'].cooldown, wait_first = False)
        self.custom_periodic_messages[name]['routine'].start(stop_on_error = False)
        
      if self.custom_periodic_messages[name]['deleted']:
        self.custom_periodic_messages[name]['routine'].cancel()
        del self.custom_periodic_messages[name]
        
      
  @twitchio_routines.routine(minutes = 1, wait_first = False)
  async def check_if_live(self):
    for channel in self.channels.keys():
      self.channels[channel]["is_live"] = self.api.is_user_live(self.channels[channel]["id"])
      
      if (self.verbose):
        print(channel, self.channels[channel]["id"], self.channels[channel]["is_live"])
      
  async def send_periodic_message(self, command_name : str):
    only_while_live = self.periodic_messages[command_name]['only_while_live']
    for channel in self.channels.keys():
      if only_while_live and not self.channels[channel]["is_live"]:
        continue
      
      botcommand : BotCommand = self.periodic_messages[command_name]['cmd']
      output = botcommand.generate_output("")
      output = output if len(output) < 500 else output[:499]
      await self.channels[channel]["chat_channel"].send(output)
      
  async def send_custom_periodic_message(self, command_name : str):
    only_while_live = self.custom_periodic_messages[command_name]['only_while_live']
    for channel in self.channels.keys():
      if only_while_live and not self.channels[channel]["is_live"]:
        continue
      
      botcommand : BotCommand = self.custom_periodic_messages[command_name]['cmd']
      
      func = getattr(self, botcommand.output, None)
      if func is not None:
        await eval(f"self.{botcommand.output}(channel)", { "self": self, "channel": channel})
      else:
        await self.channels[channel]["chat_channel"].send(f"Function \"{botcommand.output}\" does not exist in the local scope.")
    
  async def event_message(self, message : twitchio.Message):
    if message.echo:
      return
    
    command : BotCommand
    for command in self.commands:
      if command.match(str(message.content)):
        ctx = await self.get_context(message)
        
        if self.verbose:
          print(str(message.content))
          
        if not command.is_on_cooldown(ctx.author.id, self.channels[ctx.channel.name]["is_live"]):
          output = command.generate_output(message.content, message.author.id)
          output = output if len(output) < 500 else output[:499]
          if command.as_reply:
            await ctx.reply(output)
          else:
            await ctx.send(output)
          command.sent()
        elif self.verbose:
          print(f"Command {command.command} skipped due to cooldown.")
          
    command : BotCommand
    for command in self.custom_commands:
      if command.match(str(message.content)):
        ctx = await self.get_context(message)
        
        if self.verbose:
          print(str(message.content))
          
        if not command.is_on_cooldown():
          func = getattr(self, command.output, None)
          if func is not None:
            await eval(f"self.{command.output}(command, message)", { "self": self, "command": command, "message": message})
          else:
            await ctx.reply("Error.")
            logging.error(f"Function \"{command.output}\" does not exist in the local scope.")
          command.sent()
        elif self.verbose:
          print(f"Command {command.command} skipped due to cooldown.")