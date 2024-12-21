import os
import re
import discord
import sys
import typing
import django
import requests
from django.utils.http import int_to_base36
import uuid
import urllib.request
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
os.environ['DJANGO_SETTINGS_MODULE'] = "config.settings"

django.setup()

import botmanager.models as django_models
from bots.generic.commands import BotCommand
from bots.generic.discord import DiscordBot

TEMP_FILE_PATH = Path(os.path.join(os.path.dirname(__file__), "./tmp/"))

SOCIAL_MEDIA_REGEXES : typing.List[re.Pattern] = [
  re.compile(r"https?://(www\.)?instagram.com/reel/[A-Za-z0-9_\-]+", flags = re.IGNORECASE),
  re.compile(r"https?://(www\.)?tiktok.com/.*/(video|photo)/[A-Za-z0-9_\-]+", flags = re.IGNORECASE),
  re.compile(r"https?://(www\.)?tiktok.com/t/[A-Za-z0-9_\-]+\b", flags = re.IGNORECASE),
]

OPTIONAL_SOCIAL_MEDIA_REGEXES : typing.List[re.Pattern] = [
  re.compile(r"https?://(www\.)?instagram.com/[A-Za-z0-9_\-]+/p/[A-Za-z0-9_\-]+", flags = re.IGNORECASE),
  re.compile(r"https?://(www\.)?instagram.com/p/[A-Za-z0-9_\-]+", flags = re.IGNORECASE),
  re.compile(r"https?://(www\.)?x.com/[A-Za-z0-9_\-]+/status/[A-Za-z0-9_\-]+", flags = re.IGNORECASE),
  re.compile(r"https?://(www\.)?twitter.com/[A-Za-z0-9_\-]+/status/[A-Za-z0-9_\-]+", flags = re.IGNORECASE),
]

FILE_MIME_TYPE = {
  "video/mp4": "mp4",
  "video/mpeg": "mpg",
  "video/quicktime": "mov",
  "video/webm":"webm",
  "video/x-ms-wmv": "wmv",
  "video/x-msvideo": "avi",
  "video/x-flv": "flv", 
  "image/gif": "gif",
  "image/jpeg": "jpeg",
  "image/png": "png",
  "image/webp": "webp"
}
  

def download_file(url, folderpath : Path) -> typing.Tuple[bool, str]:
  h = { 
        "User-Agent": "lusciousbot/1.0",
      }
  r = requests.get(url, headers = h, stream = True)
  content_type : str = r.headers.get("Content-Type", "")
  content_length : int = int(r.headers.get("Content-Length", 0))
  
  print(content_type, content_length)
  
  if content_length > 50_000_000:
    return (False, "File too large.")
  
  if content_type in FILE_MIME_TYPE:
    filename = folderpath / f"{filename_gen()}.{FILE_MIME_TYPE[content_type]}"
  else:
    print(r.content)
    return (False, "Unsupported file type.")
  
  with open(filename, 'wb') as fp:
    for chunk in r.iter_content(chunk_size=1024):
      if chunk:
        fp.write(chunk)
    fp.close()
  
  return (True, filename)

ID_LENGTH = 8
def filename_gen() -> str:
  return int_to_base36(uuid.uuid4().int)[:ID_LENGTH]
  
class LusciousDiscordBot(DiscordBot):
  cobalt_enabled = False
  cobalt_api_url = "https://cobalt.luscious.dev/"
  
  def __init__(self, bot_name : str, verbose = False, *args, **kwargs):
    super().__init__(bot_name, verbose, *args, **kwargs)
    
    if not os.path.exists(TEMP_FILE_PATH):
      os.makedirs(TEMP_FILE_PATH, exist_ok = True)
      
    try:
      cobaltcred : django_models.ExtraCredential = self.bot_model.extracredential_set.get(credential_name = "cobalt.luscious.dev")
      
      self.cobalt_api_key = cobaltcred.credential
      self.cobalt_enabled = True
    except django_models.ExtraCredential.DoesNotExist:
      print("Unable to find cobalt API key.")
      
  async def find_and_download(self, message : discord.Message, url_list : typing.List[re.Pattern]) -> bool:
    url_found = False
    for social_regex in url_list:
      sitematch = social_regex.search(message.content)
      if sitematch:
        url_found = True
        url = sitematch.group()
        print(url)
        
        try:
          rqdata = {
            "url": url,
            "videoQuality": "144",
            "filenameStyle": "basic",
          }
          headers = {
            "User-Agent": "lusciousbot/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.cobalt_api_key}"
          }
          
          fullresp = requests.post(self.cobalt_api_url, json = rqdata, headers = headers)
          
          try:
            resp_json = fullresp.json()
          except:
            await message.reply("API error.")
            return
            
          if fullresp.status_code < 200 or fullresp.status_code >= 300:
            print(fullresp.status_code, fullresp.reason, resp_json)
            if "text" in resp_json:
              await message.reply(resp_json["text"])
            else:
              await message.reply("API error.")
            return
          
          if "status" in resp_json and resp_json["status"] != "error":
            filepath = ""
            
            if resp_json["status"] == "tunnel" or resp_json["status"] == "redirect":
              success, reason = download_file(resp_json["url"], TEMP_FILE_PATH)
              if not success:
                print(reason)
                await message.reply(reason)
                return url_found
              else:
                filepath = reason
                
                with open(filepath, 'rb') as attachmentfp:
                  filename, ext = os.path.splitext(filepath)
                  attachment = discord.File(attachmentfp, filename=f"{filename_gen()}{ext}")
                  try:
                    await message.reply(file = attachment, mention_author = False)
                    await message.edit(suppress=True)
                  except discord.HTTPException as e:
                    print(f"Failed to upload video from: {url}")
                    print(e)
                    if e.status == 413:
                      await message.reply("File too large.")
                
                os.remove(filepath)

            elif resp_json["status"] == "picker":
              attachmentfps = []
              attachments = []
              for p in resp_json["picker"]:
                success, reason = download_file(p["url"], TEMP_FILE_PATH)
                if not success:
                  print(reason)
                  await message.reply(reason)
                  return url_found
                else:
                  filepath = reason
                  afp = open(filepath, 'rb')
                  attachmentfps.append((filepath, afp))
                  filename, ext = os.path.splitext(filepath)
                  attachments.append(discord.File(afp, filename=f"{filename_gen()}{ext}"))
                  
              try:
                await message.reply(files = attachments, mention_author = False)
                await message.edit(suppress=True)
              except discord.HTTPException as e:
                print(f"Failed to upload video from: {url}")
                print(e)
                if e.status == 413:
                  await message.reply("File too large.")

              for filepath, fp in attachmentfps:
                fp.close()
                os.remove(filepath)
                
          elif resp_json["status"] == "error":
            await message.reply(f"{resp_json['status']}: {resp_json['text']}")
        except Exception as e:
          print(f"Failed to fetch video at URL: {url}")
          print(e)
          
    return url_found
    
  async def move_user(self, command : BotCommand, message : discord.Message):
    is_will = message.author.get_role(511240921288015873) is not None
    is_admin = message.author.get_role(511290086428770324) is not None
    is_mod = message.author.get_role(511290086428770324) is not None
    if not (is_will or is_admin or is_mod):
      print("User is not allowed to use this command.")
      return
    
    if len(message.mentions) == 1:
      target = message.mentions[0]
      
      if target.voice == None or target.voice.channel == None:
        await message.reply(f"{target.nick if target.nick is not None else target.name} is not in a voice channel.")
        return
      
      vc = self.get_channel(511240198244401152)
      await target.move_to(vc)
  
  async def return_user(self, command : BotCommand, message : discord.Message):
    is_will = message.author.get_role(511240921288015873) is not None
    is_admin = message.author.get_role(511290086428770324) is not None
    is_mod = message.author.get_role(511290086428770324) is not None
    if not (is_will or is_admin or is_mod):
      print("User is not allowed to use this command.")
      return
    
    if len(message.mentions) == 1:
      target = message.mentions[0]
      
      if target.voice == None or target.voice.channel == None:
        await message.reply(f"{target.nick if target.nick is not None else target.name} is not in a voice channel.")
        return
      
      vc = self.get_channel(511239539889799182)
      await target.move_to(vc)
  
  async def on_message(self, message : discord.Message) -> None:
    await super().on_message(message)
    
    if message.author.id == self.user.id:
      return
    
    if message.author.id != 113416440383610880 and "lib react" in message.content.lower(): # message.channel.id == 634173511186776064 and 
      await message.add_reaction("<a:monkaLib:844313565954703420>")
    
    found = await self.find_and_download(message, SOCIAL_MEDIA_REGEXES)
        
    if not found and self.user in message.mentions:
      optional_found = await self.find_and_download(message, OPTIONAL_SOCIAL_MEDIA_REGEXES)
      
      if not optional_found and message.reference is not None:
        reference_msg = await message.channel.fetch_message(message.reference.message_id)
        
        if not await self.find_and_download(reference_msg, OPTIONAL_SOCIAL_MEDIA_REGEXES):
          await self.find_and_download(reference_msg, SOCIAL_MEDIA_REGEXES)
        

if __name__ == "__main__":
  intents = discord.Intents.default()
  intents.members = True
  intents.guilds = True
  intents.message_content = True
  
  bot = LusciousDiscordBot(bot_name = 'bot.luscious.dev', intents = intents)
  
  bot.run(bot.__token__)