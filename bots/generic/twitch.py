import argparse
import datetime as dt
import json
import re
import sys
import django

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
  
  channels = []
  commands = []
  
  def __init__(self, bot_name : str, verbose = False, ):
    self.bot_name = bot_name
    self.verbose = verbose
    
    try:
      bot_model = django_models.ChatBot.objects.get(name = bot_name)
    except django_models.ChatBot.DoesNotExist:
      raise(f"Bot with name \"{bot_name}\" does not exist.")
    
    self.__token__ = bot_model.twitch_access_token
    
    twitchchat : django_models.TwitchChat
    for twitchchat in bot_model.twitchchat_set.all():
      self.channels.append(twitchchat.channel_name)
      
    command : django_models.BotCommand
    for command in bot_model.botcommand_set.all():
      self.commands.append(BotCommand(command.command, command.output, command.per_user_cooldown, command.cooldown))
    
    if self.verbose:
      print(self.channels, self.commands)
    
    super().__init__(token = self.__token__, prefix = '\0', initial_channels = self.channels)

  async def event_ready(self):
    print(f'Logged in as {self.nick}')
    print(f'User ID is {self.user_id}')
    
    self.replace_nickname_regex = re.compile(f"{re.escape('@')}?{re.escape(self.nick)}", re.IGNORECASE)
    
  async def event_message(self, message : twitchio.Message):
    if message.echo:
      return
    
    command : BotCommand
    for command in self.commands:
      if str(message.content).startswith(command.command):
        ctx = await self.get_context(message)
        
        if self.verbose:
          print(str(message.content))
          
        if not command.is_on_cooldown():
          await ctx.send(command.generate_output(message.content))
          command.sent()
        elif self.verbose:
          print(f"Command {command.command} skipped due to cooldown.")
          