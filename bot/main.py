import os
import json
import argparse
import typing
import asyncio
import discord
from pathlib import Path
import random
import re
import datetime
import subprocess
import sys

img_ext_regex = re.compile(r"\.(png|jpeg|jpg|bmp)")

if sys.platform == "win32":
  font_options = ["Comic-Sans-MS-Bold", "Impact", "Times-New-Roman-Bold", "Papyrus"]
else:
  font_options = ["Helvetica-Bold", "Times-New-Roman-Bold", "Comic-Sans-MS-Bold", "Impact"]

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
      
  def get_death(self, name, pronouns = "they/them", override_deathnum = -1):
    death_num = override_deathnum if override_deathnum >= 0 else random.randint(0, self.total_options - 1)
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
  
  death_msg_channels : typing.List[str] = []
  death_gen : DeathGenerator = None
  image_dir : str = ""
  image_paths : typing.List[str] = []
  
  user_lists_path : str = ""
  user_lists : typing.Dict[str, typing.Dict[str, int]] = {}
  
  death_wait_min = (12 * 60) # 12 hours
  death_wait_max = (36 * 60) # 36 hours
  
  def __init__(self, channels : typing.List[str], generator_config : str, image_dir : str, user_lists_path = "./users.json", *args, **kwargs):
    self.death_msg_channels = channels
    
    self.death_gen = DeathGenerator(generator_config)
    self.image_dir = image_dir
    
    self.user_lists_path = user_lists_path
    
    self.get_image_paths()
    
    super().__init__(*args, **kwargs)
    
  def get_image_paths(self):
    cwd = os.path.abspath(os.getcwd())
    os.chdir(self.image_dir)
    self.image_paths = sorted([os.path.abspath(f) for f in os.listdir('.') if (os.path.isfile(f) and img_ext_regex.search(f) != None)])
    os.chdir(cwd)
    
  def add_channel_to_user_lists(self, channel_id : int):
    channel = self.get_channel(channel_id)
    channel_id_str = str(channel_id)
    
    if channel_id_str not in self.user_lists.keys():
      self.user_lists[channel_id_str] = {}
    
    for member in channel.guild.members:
      if str(member.id) not in self.user_lists[channel_id_str].keys():
        self.user_lists[channel_id_str][str(member.id)] = 1
        
  def save_user_lists(self):
    with open(self.user_lists_path, 'w') as userlistsfp:
      json.dump(self.user_lists, userlistsfp, indent = 2)
    
  def generate_user_lists(self):
    if os.path.exists(self.user_lists_path) and os.path.isfile(self.user_lists_path):
      with open(self.user_lists_path, 'r') as userlistsfp:
        self.user_lists = json.load(userlistsfp)
    else:
      self.user_lists = {}
      
    for channelid in self.death_msg_channels:
      self.add_channel_to_user_lists(int(channelid))
        
    self.save_user_lists()
    
  async def setup_hook(self) -> None:
    self.bg_task = self.loop.create_task(self.periodic_events())
    
  def check_message_in_death_server(self, message : discord.Message):
    guild = message.guild
    for channelid in self.death_msg_channels:
      channel = self.get_channel(int(channelid))
      if guild == channel.guild:
        break
      else:
        channel = None
        
    if channel == None:
      print("Message not from server participating in death msgs.")
    
    channelid = str(channel.id)
    userid = str(message.author.id)
    if userid in self.user_lists[channelid]:
      self.user_lists[channelid][userid] += 9 if self.user_lists[channelid][userid] == 1 else 5
    else:
      self.user_lists[channelid][userid] = 10
    
  async def on_message(self, message : discord.Message) -> None:
    if message.author.id == self.user.id:
      return
    
    self.check_message_in_death_server(message)
    
  async def on_ready(self):
    for guild in self.guilds:
      print(guild.name)
      
  def get_users_and_weights(self, channel_id : str) -> typing.Tuple[typing.List[str], typing.List[float]]:
    users = list(self.user_lists[channel_id].keys())
    
    weights = []
    total_weight = 0
    for user in users:
      user_weight = 1 if self.user_lists[channel_id][user] < 0 else self.user_lists[channel_id][user]
      weights.append(user_weight)
      total_weight += user_weight
      
    normalized_weights = [w / total_weight for w in weights]
    return (users, normalized_weights)
      
  async def send_death_msg(self):
    for channel_id in self.death_msg_channels:
      channel = self.get_channel(int(channel_id))
      
      users, weights = self.get_users_and_weights(channel_id)
      
      while True:
        user_id : str = random.choices(users, weights)[0]
        mentioned : discord.Member = next((member for member in channel.members if member.id == int(user_id)), None)
        if mentioned not in channel.members:
          continue
        else:
          break
        
      self.user_lists[channel_id][user_id] = -49
      
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
      subprocess.run(['magick', 'convert', imgpath, '-set', 'colorspace', 'Gray', '-separate', '-average', label_path_1, '-gravity', 'South', '-geometry', '512x160+0+10', '-composite', label_path_2, '-gravity', 'South', '-geometry', '512x160+0+10', '-composite', tmp_path])
      
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
        
    return random.randint(self.death_wait_min, self.death_wait_max)
    
  async def periodic_events(self):
    await self.wait_until_ready()
    
    self.generate_user_lists()
    
    i = 0
    nextdeathmsg = 181
    nextuserlistsave = 10
    while not self.is_closed():
      
      if i >= nextdeathmsg:
        print("Sending death message.")
        nextdeathmsg =  i + await self.send_death_msg()
        print(f"Next death message in {nextdeathmsg - i} minutes.")
        
      if i >= nextuserlistsave:
        print("Saving user msg list.")
        self.save_user_lists()
        nextuserlistsave = i + 2
        print("User lists saved.")
        
      await asyncio.sleep(60) # wait a minute
      i += 1
      
      if i > 10000:
        i -= 10000
        nextdeathmsg -= 10000
        
        print("Reached 10,000 minutes of runtime. Reseting counter.")

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