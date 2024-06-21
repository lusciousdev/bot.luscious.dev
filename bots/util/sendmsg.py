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
  
  def __init__(self, channel_id : int, message : str, *args, **kwargs):
    self.channel_id = channel_id
    self.message = message
    super().__init__(*args, **kwargs)
    
  async def on_ready(self):
    for guild in self.guilds:
      print(guild.name)
      
    channel = self.get_channel(self.channel_id)
    await channel.send(self.message)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--secrets', '-s', default = './secrets.json', help = "File containing Discord token.")
  parser.add_argument('--channel', '-c', type = int, help = "Channel to send message in.")
  parser.add_argument('--msg', '-m', type=str, help = "message to send")
  
  args = parser.parse_args()
  
  with open(args.secrets, 'r') as cred_file:
    cred_json = json.load(cred_file)
    
  intents = discord.Intents.default()
  intents.members = True
  bot = LusciousBot(args.channel, args.msg, intents = intents)
  
  bot.run(cred_json['TOKEN'])