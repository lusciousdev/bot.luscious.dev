import os
import asyncio
import discord
from discord.ext import tasks
from discord.utils import MISSING
import sys
import logging
import typing
import django
from asgiref.sync import sync_to_async, async_to_sync

from .commands import BotCommand

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
os.environ['DJANGO_SETTINGS_MODULE'] = "config.settings"

django.setup()

import botmanager.models as django_models

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)

class DiscordBot(discord.Client):
  __token__ : str = ""
  
  bot_name : str = ""
  
  channels = {}
  
  commands : typing.List[BotCommand] = []
  custom_commands : typing.List[BotCommand] = []
  periodic_messages : typing.Dict[str, typing.Dict[str, typing.Union[BotCommand, tasks.Loop, bool, int, None]]] = {}
  custom_periodic_messages : typing.Dict[str, typing.Dict[str, typing.Union[BotCommand, tasks.Loop, bool, int, None]]] = {}
  
  verbose : bool = False
  
  def __init__(self, bot_name : str, verbose = False, *args, **kwargs):
    self.bot_name = bot_name
    self.verbose = verbose
    
    try:
      self.bot_model = django_models.ChatBot.objects.get(name = bot_name)
    except django_models.ChatBot.DoesNotExist:
      raise(f"Bot with name \"{bot_name}\" does not exist.")
    
    discordconfig : django_models.DiscordConfig = self.bot_model.discordconfig
    
    self.__token__ = discordconfig.access_token
    
    discord_channel : django_models.DiscordChannel
    for discord_channel in discordconfig.discordchannel_set.all():
      self.channels[discord_channel.channel_id] = {
        "channel": None,
      }
      
    self.get_commands_and_tasks()
    
    if self.verbose:
      print(self.channels, self.commands)
    
    super().__init__(*args, **kwargs)
    
  async def on_ready(self):
    for guild in self.guilds:
      logger.info(guild.name)
      
    channel : dict
    for channel in self.channels.keys():
      self.channels[channel]["channel"] = self.get_channel(int(channel))
      
    self.aget_commands_and_tasks.start()
  
  @tasks.loop(seconds = 10, reconnect = True)
  async def aget_commands_and_tasks(self):
    await sync_to_async(self.get_commands_and_tasks)()
    
    await self.start_routines()
  
  def get_commands_and_tasks(self):
    try:
      self.bot_model = django_models.ChatBot.objects.get(name = self.bot_name)
    except django_models.ChatBot.DoesNotExist:
      raise(f"Bot with name \"{self.bot_name}\" does not exist.")
    
    discordconfig : django_models.DiscordConfig = self.bot_model.discordconfig
    
    existing_commands = []
    command : django_models.DiscordBasicCommand
    for command in discordconfig.discordbasiccommand_set.all():
      existing_commands.append(command.command)
      newbc = BotCommand(command.command, command.output, command.as_reply, command.match_anywhere, command.regex_command, command.cooldown, None, command.restrict_channels)
      
      command_exists = False
      bc : BotCommand
      for bc in self.commands:
        if bc.command == command.command:
          if newbc != bc:
            print(f"Updating command: {bc.command}")
          bc.output = command.output
          bc.as_reply = command.as_reply
          bc.cooldown = command.cooldown
          command_exists = True
      
      if not command_exists:
        print(f"New command: {command.command}")
        self.commands.append(newbc)
      
    for i in reversed(range(len(self.commands))):
      if self.commands[i].command not in existing_commands:
        print(f"Command deleted: {self.commands[i].command}")
        del self.commands[i]
      
    existing_custom_commands = []
    custom_command : django_models.DiscordCustomCommand
    for custom_command in discordconfig.discordcustomcommand_set.all():
      existing_custom_commands.append(custom_command.command)
      newbc = BotCommand(custom_command.command, custom_command.output, custom_command.as_reply, custom_command.match_anywhere, custom_command.regex_command, custom_command.cooldown, None, custom_command.restrict_channels)
      
      command_exists = False
      bc : BotCommand
      for bc in self.custom_commands:
        if bc.command == custom_command.command:
          if newbc != bc:
            print(f"Updating command: {bc.command}")
          bc.output = custom_command.output
          bc.as_reply = custom_command.as_reply
          bc.cooldown = custom_command.cooldown
          command_exists = True
      
      if not command_exists:
        print(f"New custom command: {custom_command.command}")
        self.custom_commands.append(newbc)
      
    for i in reversed(range(len(self.custom_commands))):
      if self.custom_commands[i].command not in existing_custom_commands:
        print(f"Command deleted: {self.custom_commands[i].command}")
        del self.custom_commands[i]
    
    existing_periodics = []
    periodic_message : django_models.DiscordPeriodicMsg
    for periodic_message in discordconfig.discordperiodicmsg_set.all():
      name = periodic_message.name
      existing_periodics.append(name)
      
      cmd = BotCommand(periodic_message.name, periodic_message.output, False, False, False, periodic_message.period)
      
      if periodic_message.name in self.periodic_messages:
        if self.periodic_messages[name]['cmd'] != cmd:
          print(f"Updating periodic message: {periodic_message.name}")
          
        if self.periodic_messages[name]['cmd'].cooldown != periodic_message.period:
          if self.periodic_messages[name]['loop'] is not None:
            self.periodic_messages[name]['loop'].change_interval(seconds = periodic_message.period)
            
        self.periodic_messages[name]['cmd'].output = periodic_message.output
        self.periodic_messages[name]['cmd'].cooldown = periodic_message.period
        
      else:
        print(f"New periodic message: {periodic_message.name}")
        self.periodic_messages[periodic_message.name] = {
          'cmd': cmd,
          'loop': None,
          "deleted": False,
        }
        
    for name in self.periodic_messages.keys():
      if self.periodic_messages[name]['cmd'].command not in existing_periodics:
        print(f"Periodic message deleted: {self.periodic_messages[name]['cmd'].command}")
        self.periodic_messages[name]['deleted'] = True
      
    existing_custom_periodics = []
    custom_periodic_message : django_models.DiscordCustomPeriodicMsg
    for custom_periodic_message in discordconfig.discordcustomperiodicmsg_set.all():
      name = custom_periodic_message.name
      existing_custom_periodics.append(name)
      
      cmd = BotCommand(custom_periodic_message.name, custom_periodic_message.output, False, False, False, custom_periodic_message.period)
      
      if custom_periodic_message.name in self.custom_periodic_messages:
        if self.custom_periodic_messages[name]['cmd'] != cmd:
          print(f"Updating custom periodic message: {custom_periodic_message.name}")
          
        if self.custom_periodic_messages[name]['cmd'].cooldown != custom_periodic_message.period:
          if self.custom_periodic_messages[name]['loop'] is not None:
            self.custom_periodic_messages[name]['loop'].change_interval(seconds = custom_periodic_message.period)
            
        self.custom_periodic_messages[name]['cmd'].output = custom_periodic_message.output
        self.custom_periodic_messages[name]['cmd'].cooldown = custom_periodic_message.period
      
      else:
        print(f"New custom periodic message: {custom_periodic_message.name}")
        self.custom_periodic_messages[custom_periodic_message.name] = {
          'cmd': cmd,
          'loop': None,
          'deleted' : False,
        }
        
    for name in self.custom_periodic_messages.keys():
      if self.custom_periodic_messages[name]['cmd'].command not in existing_custom_periodics:
        print(f"Periodic message deleted: {self.custom_periodic_messages[name]['cmd'].command}")
        self.custom_periodic_messages[name]['deleted'] = True
    
  async def start_routines(self):
    for name in list(self.periodic_messages.keys()):
      if self.periodic_messages[name]['loop'] is None:
        print(f"Starting periodic message: {name}")
        async def coro():
          await self.send_periodic_message(name)
        self.periodic_messages[name]['loop'] = tasks.Loop(coro = coro, seconds = self.periodic_messages[name]['cmd'].cooldown, hours = 0, minutes = 0, time = MISSING, count = None, reconnect = True)
        self.periodic_messages[name]['loop'].start()
        
      if self.periodic_messages[name]['deleted']:
        self.periodic_messages[name]['loop'].cancel()
        del self.periodic_messages[name]
        
    for name in list(self.custom_periodic_messages.keys()):
      if self.custom_periodic_messages[name]['loop'] is None:
        print(f"Starting custom periodic message: {name}")
        async def coro():
          await self.send_custom_periodic_message(name)
        self.custom_periodic_messages[name]['loop'] = tasks.Loop(coro = coro, seconds = self.custom_periodic_messages[name]['cmd'].period, hours = 0, minutes = 0, time = MISSING, count = None, reconnect = True)
        self.custom_periodic_messages[name]['loop'].start()
        
      if self.custom_periodic_messages[name]['deleted']:
        self.custom_periodic_messages[name]['loop'].cancel()
        del self.custom_periodic_messages[name]
    
  async def on_message(self, message : discord.Message) -> None:
    if message.author.id == self.user.id:
      return
    
    command : BotCommand
    for command in self.commands:
      if command.match(message.content):
        if self.verbose: 
          print(message.content)
        if command.restrict_to_channels and (str(message.channel.id) not in self.channels):
          if self.verbose:
            print(f"Command {command.command} ignored because it was called in an invalid channel.")
          continue
        
        if not command.is_on_cooldown():
          if command.as_reply:
            async with message.channel.typing():
              await message.reply(command.generate_output(message.content))
          else:
            async with message.channel.typing():
              await message.channel.send(command.generate_output(message.content))
          command.sent()
        elif self.verbose:
          print(f"Command {command.command} skipped due to cooldown.")
    
    custom_command : BotCommand  
    for custom_command in self.custom_commands:
      if custom_command.match(message.content):
        if self.verbose:
          print(message.content)
        if custom_command.restrict_to_channels and (str(message.channel.id) not in self.channels):
          if self.verbose:
            print(f"Command {command.command} ignored because it was called in an invalid channel.")
          continue
          
        if not custom_command.is_on_cooldown():
          func = getattr(self, custom_command.output, None)
          if func is not None:
            await eval(f"self.{custom_command.output}(command, message)", { "self": self, "command": custom_command, "message": message })
          else:
            await message.channel.send(f"Function \"{custom_command.output}\" does not exist in the local scope.")
          custom_command.sent()
        elif self.verbose:
          print(f"Command {custom_command.command} skipped due to cooldown.")
      
  async def send_periodic_message(self, command_name : str):
    bc : BotCommand = self.periodic_messages[command_name]['cmd']
    for channel in self.channels.keys():
      await self.channels[channel]["channel"].send(bc.generate_output(""))
      
  async def send_custom_periodic_message(self, command_name : str):
    bc : BotCommand = self.custom_periodic_messages[command_name]['cmd']
    for channel in self.channels.keys():
      func = getattr(self, bc.output, None)
      if func is not None:
        await eval(f"self.{bc.output}(channel)", { "self": self, "channel": channel })
      else:
        await self.channels[channel]["channel"].send(f"Function \"{bc.command}\" does not exist in the local scope.")