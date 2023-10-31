import os
import json
import argparse
import typing
import asyncio
import discord
from pathlib import Path
import random
import logging
import re
import datetime
import subprocess
import sys

class LusciousBot(discord.Client):
  __token__ : str = ""
  
  def __init__(self, channel_id : int, msg_id : int, reaction : str, *args, **kwargs):
    self.channel_id = channel_id
    self.message_id = msg_id
    self.reaction = reaction
    super().__init__(*args, **kwargs)
    
  async def on_ready(self):
    for guild in self.guilds:
      print(guild.name)
      
    channel = self.get_channel(self.channel_id)
    message = channel.get_partial_message(self.message_id)
    await message.add_reaction(self.reaction)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--secrets', '-s', default = './secrets.json', help = "File containing Discord token.")
  parser.add_argument('--channel', '-c', type = int, help = "Channel to send message in.")
  parser.add_argument('--msgid', '-i', type = int, help = "Message to edit.")
  parser.add_argument('--react', '-r', type=str, help = "message to send")
  
  args = parser.parse_args()
  
  with open(args.secrets, 'r') as cred_file:
    cred_json = json.load(cred_file)
    
  intents = discord.Intents.default()
  intents.members = True
  bot = LusciousBot(args.channel, args.msgid, args.react, intents = intents)
  
  bot.run(cred_json['TOKEN'])