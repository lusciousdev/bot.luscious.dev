from django.db import models
from django import forms

import datetime

# Create your models here.

class ChatBot(models.Model):
  name = models.CharField(max_length = 255, blank = False, null = False, unique = True)
  
  def __str__(self):
    return f"{self.name}"
  
class DiscordConfig(models.Model):
  bot = models.OneToOneField(to = ChatBot, on_delete = models.CASCADE, primary_key = True)
  
  active = models.BooleanField(default = True)
  
  access_token = models.CharField(max_length = 256, blank = True, null = True)
  
  def __str__(self):
    return f"{self.bot.name}'s Discord config"
  
class TwitchConfig(models.Model):
  bot = models.OneToOneField(to = ChatBot, on_delete = models.CASCADE, primary_key = True)
  
  active = models.BooleanField(default = True)
  
  client_id = models.CharField(max_length = 256, blank = True, null = True)
  client_secret = models.CharField(max_length = 256, blank = True, null = True)
  access_token = models.CharField(max_length = 256, blank = True, null = True)
  
  def __str__(self):
    return f"{self.bot.name}'s Twitch config"
  
class DiscordChannel(models.Model):
  config = models.ForeignKey(DiscordConfig, on_delete = models.CASCADE)
  
  channel_id = models.CharField(max_length = 256)
  
class TwitchChat(models.Model):
  config = models.ForeignKey(TwitchConfig, on_delete = models.CASCADE)
  
  channel_name = models.CharField(max_length = 256)
  channel_id = models.CharField(max_length = 256)
  
class Command_A(models.Model):
  command = models.CharField(max_length = 255, blank = False, null = False, unique = True)
  output = models.CharField(max_length = 400, blank = True)
  
  
  as_reply = models.BooleanField(default = False)
  cooldown = models.IntegerField(verbose_name = "Cooldown in seconds", default = 60)
  
  class Meta:
    abstract = True
    
class TwitchCommand_A(Command_A):
  config = models.ForeignKey(TwitchConfig, on_delete = models.CASCADE)
  
  cooldown_while_offline = models.IntegerField(verbose_name = "Cooldown in seconds (offline)", default = 60)
  
  class Meta:
    abstract = True
    
class DiscordCommand_A(Command_A):
  config = models.ForeignKey(DiscordConfig, on_delete = models.CASCADE)
  
  restrict_channels = models.BooleanField(default = False)
  
  class Meta:
    abstract = True

class TwitchBasicCommand(TwitchCommand_A):
  pass

class TwitchCustomCommand(TwitchCommand_A):
  pass

class DiscordBasicCommand(DiscordCommand_A):
  pass

class DiscordCustomCommand(DiscordCommand_A):
  pass

class PeriodicMsg_A(models.Model):
  name = models.CharField(max_length = 255, blank = False, null = False, unique = True)
  output = models.CharField(max_length = 400, blank = True)
  period = models.IntegerField(verbose_name = "Period in seconds", default = 60)
  
  class Meta:
    abstract = True
    
class TwitchPeriodicMsg_A(PeriodicMsg_A):
  config = models.ForeignKey(TwitchConfig, on_delete = models.CASCADE)
  
  only_while_live = models.BooleanField(default = True)
  
  class Meta:
    abstract = True
    
class DiscordPeriodicMsg_A(PeriodicMsg_A):
  config = models.ForeignKey(DiscordConfig, on_delete = models.CASCADE)
  
  class Meta:
    abstract = True

class TwitchPeriodicMsg(TwitchPeriodicMsg_A):
  pass

class TwitchCustomPeriodicMsg(TwitchPeriodicMsg_A):
  pass

class DiscordPeriodicMsg(DiscordPeriodicMsg_A):
  pass

class DiscordCustomPeriodicMsg(DiscordPeriodicMsg_A):
  pass

class ChatBotForm(forms.ModelForm):
  name = forms.CharField(max_length = 256, required = True)
  
  class Meta:
    model = ChatBot
    exclude = []