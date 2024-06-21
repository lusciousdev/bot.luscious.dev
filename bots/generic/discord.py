import os
import asyncio
import discord
import sys
import logging
import django

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
  
  channels = []
  commands = []
  
  verbose : bool = False
  
  def __init__(self, bot_name : str, verbose = False, *args, **kwargs):
    self.bot_name = bot_name
    self.verbose = verbose
    
    try:
      bot_model = django_models.ChatBot.objects.get(name = bot_name)
    except django_models.ChatBot.DoesNotExist:
      raise(f"Bot with name \"{bot_name}\" does not exist.")
    
    self.__token__ = bot_model.discord_token
    
    discord_channel : django_models.DiscordChannel
    for discord_channel in bot_model.discordchannel_set.all():
      self.channels.append(discord_channel.channel_id)
      
    command : django_models.BotCommand
    for command in bot_model.botcommand_set.all():
      self.commands.append(BotCommand(command.command, command.output, command.per_user_cooldown, command.cooldown))
    
    if self.verbose:
      print(self.channels, self.commands)
    
    super().__init__(*args, **kwargs)
    
  async def setup_hook(self) -> None:
    self.bg_task = self.loop.create_task(self.periodic_events())
    
  async def on_message(self, message : discord.Message) -> None:
    if message.author.id == self.user.id:
      return
    
    if str(message.channel.id) in self.channels:
      command : BotCommand
      for command in self.commands:
        if message.content.startswith(command.command):
          if self.verbose: 
            print(message.content)
          
          if not command.is_on_cooldown():
            await message.channel.send(command.generate_output(message.content))
            command.sent()
          elif self.verbose:
            print(f"Command {command.command} skipped due to cooldown.")
    
  async def on_ready(self):
    for guild in self.guilds:
      logger.info(guild.name)
    
  async def periodic_events(self):
    await self.wait_until_ready()
    
    while not self.is_closed():
      await asyncio.sleep(60) # wait a minute