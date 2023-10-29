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

img_ext_regex = re.compile(r"\.(png|jpeg|jpg|bmp)")

if sys.platform == "win32":
  font_options = ["Comic-Sans-MS-Bold", "Impact", "Times-New-Roman-Bold", "Papyrus"]
else:
  font_options = ["Helvetica-Bold", "Times-New-Roman-Bold", "Comic-Sans-MS-Bold", "Impact", "Papyrus", ]

class DeathGenerator:
  params : dict = {}
  death_map : dict = {}
  total_options = 0
  
  def __init__(self, config : Path):
    with open(config, 'r') as configf:
      self.params = json.load(configf)
      self.map_deaths()
      
  def map_deaths(self):
    for key in self.params.keys():
      self.death_map[key] = len(self.params[key]["reason"]) * max(len(self.params[key]["modifier"]), 1)
      self.total_options += self.death_map[key]
    print("Total death options: ", self.total_options)
      
  def get_death(self, name, pronouns = "they/them"):
    death_num = random.randint(0, self.total_options - 1)
    category = None
    
    for key in sorted(self.death_map.keys()):
      if death_num < self.death_map[key]:
        category = key
        break
      else:
        death_num -= self.death_map[key]
    
    num_modifiers = len(self.params[category]["modifier"])
    
    reason_index = death_num // max(1, num_modifiers)
    modifier_index = death_num - (max(1, num_modifiers) * reason_index)
    
    reason : str = self.params[category]["reason"][reason_index]
    if "modifier" in self.params[category] and len(self.params[category]["modifier"]):
      modifier : str = self.params[category]["modifier"][modifier_index]      
      reason = reason.replace("[[m]]", modifier)
    
    personal_pronoun = "they"
    personal_pronoun_2 = "them"
    possessive_pronoun = "their"
    be_pres = "are"
    be_past = "were"
    be_futu = "will"
    if pronouns == "he/him":
      personal_pronoun = "he"
      personal_pronoun_2 = "him"
      possessive_pronoun = "his"
      be_pres = "is"
      be_past = "was"
      be_futu = "will"
    elif pronouns == "she/her":
      personal_pronoun = "she"
      personal_pronoun_2 = "her"
      possessive_pronoun = "her"
      be_pres = "is"
      be_past = "was"
      be_futu = "will"
      
    reason = reason.replace("[[per]]", personal_pronoun)
    reason = reason.replace("[[Per]]", personal_pronoun.capitalize())
    reason = reason.replace("[[per2]]", personal_pronoun_2)
    reason = reason.replace("[[Per2]]", personal_pronoun_2.capitalize())
    reason = reason.replace("[[pos]]", possessive_pronoun)
    reason = reason.replace("[[Pos]]", possessive_pronoun.capitalize())
    reason = reason.replace("[[wpres]]", be_pres)
    reason = reason.replace("[[wpast]]", be_past)
    reason = reason.replace("[[wfutu]]", be_futu)
    
    return f"{name} {reason}."

class LusciousBot(discord.Client):
  __token__ : str = ""
  
  periodic_msg_channels : typing.List[str] = []
  death_gen : DeathGenerator = None
  image_dir : str = ""
  image_paths : typing.List[str] = []
  
  death_wait_min = (12 * 60 * 60)
  death_wait_max = (36 * 60 * 60)
  
  def __init__(self, channels : typing.List[str], generator_config : str, image_dir : str, *args, **kwargs):
    self.periodic_msg_channels = channels
    
    self.death_gen = DeathGenerator(generator_config)
    self.image_dir = image_dir
    
    self.get_image_paths()
    
    super().__init__(*args, **kwargs)
    
  def get_image_paths(self):
    cwd = os.path.abspath(os.getcwd())
    os.chdir(self.image_dir)
    self.image_paths = sorted([os.path.abspath(f) for f in os.listdir('.') if (os.path.isfile(f) and img_ext_regex.search(f) != None)])
    os.chdir(cwd)
    
  async def setup_hook(self) -> None:
    self.bg_task = self.loop.create_task(self.periodic_message())
    
  async def on_ready(self):
    for guild in self.guilds:
      print(guild.name)
    
  async def periodic_message(self):
    await self.wait_until_ready()
    
    channels = [self.get_channel(int(c)) for c in self.periodic_msg_channels]
    
    while not self.is_closed():
      
      for channel in channels:
        valid_ids = [113416440383610880, 176069643742478336, 209550411252629504, 338071463242498070, 155149108183695360, 1168040719672430662, 83010416610906112]
        mods = list(filter(lambda x: x.id in valid_ids, channel.members))
        
        if len(mods) > 0:
          mentioned : discord.Member = random.choice(mods)
        else:
          mentioned : discord.Member = random.choice(channel.members)
        
        username = mentioned.name
        if mentioned.nick != None:
          username = mentioned.nick
        elif mentioned.global_name != None:
          username = mentioned.global_name
          
        death = self.death_gen.get_death(mentioned.mention)
          
        imgpath = random.choice(self.image_paths)
        
        dtnow = datetime.datetime.now()
        tmp_path = f"./tmp_{dtnow.strftime('%Y%m%d%H%M%S')}.png"
        label_path_1 = f"./label_{dtnow.strftime('%Y%m%d%H%M%S')}-0.png"
        label_path_2 = f"./label_{dtnow.strftime('%Y%m%d%H%M%S')}-1.png"
        
        min_age = 18
        max_age = 250
        ages = [random.randint(min_age, max_age) for i in range(5)]
        age = min(ages)
        current_year = int(dtnow.strftime("%Y"))
        birth_year = current_year - age
        message = f"R.I.P. {username}\n{birth_year} - {current_year}"
        
        subprocess.run(['magick', '-background', 'none', '-gravity', 'South', '-font', random.choice(font_options), '-size', '2048x640', '-fill', 'white', '-stroke', 'black', '-strokewidth', '20', f'Label:{message}', '-write', label_path_1, '+delete', '-stroke', 'none', f'Label:{message}', label_path_2])
        subprocess.run(['magick', 'convert', imgpath, label_path_1, '-gravity', 'South', '-geometry', '512x160+0+10', '-composite', label_path_2, '-gravity', 'South', '-geometry', '512x160+0+10', '-composite', tmp_path])
        
        with open(tmp_path, 'rb') as imgfp:
          imgfile = discord.File(imgfp)
          msg : discord.Message = await channel.send(death, file = imgfile)
          imgfp.close()
          os.remove(tmp_path)
          os.remove(label_path_1)
          os.remove(label_path_2)
          await msg.add_reaction("🪦")
          await msg.add_reaction("🇷")
          await msg.add_reaction("🇮")
          await msg.add_reaction("🇵")
          await msg.add_reaction("🕊️")
        
      await asyncio.sleep(random.randint(self.death_wait_min, self.death_wait_max))

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--gencfg', '-g', default = './generator.json', help = "File containing death generator config.")
  parser.add_argument('--imgdir', '-i', default = './img/', help = "Folder containing images for death generator.")
  parser.add_argument('--secrets', '-s', default = './secrets.json', help = "File containing Discord token.")
  
  args = parser.parse_args()
  
  with open(args.secrets, 'r') as cred_file:
    cred_json = json.load(cred_file)
    
  intents = discord.Intents.default()
  intents.members = True
  bot = LusciousBot(cred_json['CHANNELS'], args.gencfg, args.imgdir, intents = intents)
  
  bot.run(cred_json['TOKEN'])