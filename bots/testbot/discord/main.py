import os
import re
import discord
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from bots.generic.discord import DiscordBot

if __name__ == "__main__":
  intents = discord.Intents.default()
  intents.members = True
  intents.guilds = True
  intents.message_content = True
  
  bot = DiscordBot(bot_name = 'testbot', intents = intents)
  
  bot.run(bot.__token__)