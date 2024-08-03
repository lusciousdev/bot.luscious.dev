import os
import re
import discord
import sys
import typing
import requests
import urllib.request
from pathlib import Path
import cgi

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from bots.generic.discord import DiscordBot

TEMP_FILE_PATH = Path(os.path.join(os.path.dirname(__file__), "./tmp/"))

SOCIAL_MEDIA_REGEXES : typing.List[re.Pattern] = [
  re.compile(r"\bhttps?://(www\.)?instagram.com/reel/[A-Za-z0-9_\-]+\b", flags = re.IGNORECASE),
  re.compile(r"\bhttps?://(www\.)?tiktok.com/.*/video/[A-Za-z0-9_\-]+\b", flags = re.IGNORECASE),
  re.compile(r"\bhttps?://(www\.)?tiktok.com/t/[A-Za-z0-9_\-]+\b", flags = re.IGNORECASE),
]

def download_stream(url, filepath):
  h = { 
       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
       "Accepts": "application/json",
       "Content-Type": "application/json"
      }
  r = requests.get(url, headers = h, stream = True)
  with open(filepath, 'wb') as fp:
    for chunk in r.iter_content(chunk_size=1024):
      if chunk:
        fp.write(chunk)
    fp.close()
        
class LusciousDiscordBot(DiscordBot):
  
  def __init__(self, bot_name : str, verbose = False, *args, **kwargs):
    super().__init__(bot_name, verbose, *args, **kwargs)
    
    if not os.path.exists(TEMP_FILE_PATH):
      os.makedirs(TEMP_FILE_PATH, exist_ok = True)
  
  async def on_message(self, message : discord.Message) -> None:
    await super().on_message(message)
    
    if message.author.id == self.user.id:
      return
    
    # if message.channel.id == 634173511186776064 and message.author.id != 113416440383610880:
    #   await message.add_reaction("<a:monkaLib:844313565954703420>")
    
    for social_regex in SOCIAL_MEDIA_REGEXES:
      sitematch = social_regex.search(message.content)
      if sitematch:
        url = sitematch.group()
        print(url)
        
        try:
          rqdata = {
            "url": url,
            "vQuality": "480",
          }
          headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
          }
          fullresp = requests.post("https://api.cobalt.tools/api/json", json = rqdata, headers = headers)
          
          resp_json = fullresp.json()
          if "status" in resp_json and "url" in resp_json and resp_json["status"] != "error":
            filepath = TEMP_FILE_PATH / Path("./temp.mp4")
            if resp_json["status"] == "stream":
              download_stream(resp_json["url"], filepath)
            elif resp_json["status"] == "redirect":
              urllib.request.urlretrieve(resp_json["url"], filepath)
              
            with open(filepath, 'rb') as attachmentfp:
              attachment = discord.File(attachmentfp)
              await message.reply(file = attachment)
              await message.edit(suppress=True)
              
            os.remove(filepath)
          elif resp_json["status"] == "error":
            await message.reply(f"{resp_json['status']}: {resp_json['text']}")
        except:
          print(f"Failed to fetch video at URL: {url}")
          await message.reply("Unknown error occurred.")

if __name__ == "__main__":
  intents = discord.Intents.default()
  intents.members = True
  intents.guilds = True
  intents.message_content = True
  
  bot = LusciousDiscordBot(bot_name = 'bot.luscious.dev', intents = intents)
  
  bot.run(bot.__token__)