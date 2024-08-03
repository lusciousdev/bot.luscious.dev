import os
import sys
import re
import typing
import datetime as dt
import discord
import django
from twitchio.ext import commands, routines
from luscioustwitch import TwitchAPI

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
os.environ['DJANGO_SETTINGS_MODULE'] = "config.settings"

django.setup()

import botmanager.models as django_models

from bots.generic.discord import DiscordBot
from bots.generic.commands import BotCommand
from bots.itswillChat.chat_generator import ChatGenerator

CHAT_ABOUT_REGEX : re.Pattern = re.compile(r"^\?chatabout ", re.IGNORECASE)

class itswillChatDiscordBot(DiscordBot):
  chat_generator : ChatGenerator = None
  
  replace_nickname_regex : re.Pattern = None
  
  def __init__(self, bot_name : str, verbose = False, *args, **kwargs):
    super().__init__(bot_name, verbose, *args, **kwargs)
    
    self.chat_generator = ChatGenerator()
      
  async def send_response(self, command : BotCommand, message : discord.Message):
    cleanmsg = message.content
    if cleanmsg.startswith(command.command):
      cleanmsg = cleanmsg[len(command.command):]
    cleanmsg = cleanmsg.strip()
    
    response = self.chat_generator.gen_response(str(cleanmsg))
    await message.reply(response)
    
  async def send_message_about(self, command : BotCommand, message : discord.Message):
    cleanmsg = message.content
    if cleanmsg.startswith(command.command):
      cleanmsg = cleanmsg[len(command.command):]
    clearmsg = cleanmsg.strip()
    
    response = self.chat_generator.gen_about(str(clearmsg))
    await message.reply(response)

if __name__ == "__main__":
  intents = discord.Intents.default()
  intents.members = True
  intents.guilds = True
  intents.message_content = True
  
  bot = itswillChatDiscordBot(bot_name = 'itswillChat', intents = intents)
  
  bot.run(bot.__token__)
  