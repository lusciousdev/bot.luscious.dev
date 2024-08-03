import os
import sys
import re
import typing
import datetime as dt
import twitchio
import django
from twitchio.ext import commands, routines
from luscioustwitch import TwitchAPI

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
os.environ['DJANGO_SETTINGS_MODULE'] = "config.settings"

django.setup()

import botmanager.models as django_models

from bots.generic.twitch import TwitchBot
from bots.generic.commands import BotCommand
from bots.itswillChat.chat_generator import ChatGenerator

class itswillChatTwitchBot(TwitchBot):
  chat_generator : ChatGenerator = None
  
  max_history : int = 25
  bot_input_length : int = 3
  
  channel_history = {}
  
  def __init__(self, bot_name : str, verbose = False):
    super().__init__(bot_name, verbose)
    
    self.chat_generator = ChatGenerator()
    
    channel : django_models.TwitchChat
    for channel in self.bot_model.twitchconfig.twitchchat_set.all():
      self.channel_history[channel.channel_name.lower()] = []
    
  async def event_message(self, message : twitchio.Message):
    if message.echo:
      return
    
    ctx = await self.get_context(message)
    
    self.channel_history[ctx.channel.name].append(str(message.content))
    if len(self.channel_history[ctx.channel.name]) > self.max_history:
      self.channel_history[ctx.channel.name] = self.channel_history[ctx.channel.name][(-1 * self.max_history):]
      
    await super().event_message(message)
    
  async def send_generated_message(self, channel):
    if len(self.channel_history[channel]) == 0:
      print(f"Somehow we have no chat history for \"{channel}\", skipping.")
      return
    
    bot_input = self.channel_history[channel] if len(self.channel_history[channel]) <= self.bot_input_length else self.channel_history[channel][(-1 * self.bot_input_length):]
    response = self.chat_generator.generate(bot_input)
    
    response = response if len(response) < 400 else response[:400]
    
    await self.channels[channel]["chat_channel"].send(response)
      
  async def send_response(self, command : BotCommand, message : twitchio.Message):
    ctx = await self.get_context(message)
      
    msgcontent = str(message.content)
    cleanmsg = msgcontent
    if cleanmsg.startswith(command.command):
      cleanmsg = cleanmsg[len(command.command):]
    cleanmsg = cleanmsg.strip()
    
    response = self.chat_generator.gen_response(str(cleanmsg))
    response = response if len(response) < 400 else response[:400]
    await ctx.reply(response)
    
  async def send_message_about(self, command : BotCommand, message : twitchio.Message):
    ctx = await self.get_context(message)
    
    msgcontent = str(message.content)
    cleanmsg = msgcontent
    if cleanmsg.startswith(command.command):
      cleanmsg = cleanmsg[len(command.command):]
    clearmsg = cleanmsg.strip()
    
    response = self.chat_generator.gen_about(str(clearmsg))
    response = response if len(response) < 400 else response[:400]
    await ctx.reply(response)

if __name__ == "__main__":
  bot = itswillChatTwitchBot(bot_name = 'itswillChat')
  
  bot.run()