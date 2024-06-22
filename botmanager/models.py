from django.db import models
from django import forms
import django.contrib.admin as admin
from django.dispatch import receiver

import datetime

# Create your models here.

class ChatBot(models.Model):
  name = models.CharField(max_length = 256, blank = False, null = False, unique = True)
  
  discord_bot = models.BooleanField(default = True)
  discord_token = models.CharField(max_length = 256, blank = True, null = True)
  discord_restrict_channels = models.BooleanField(default = False)
  
  twitch_bot = models.BooleanField(default = True)
  twitch_client_id = models.CharField(max_length = 256, blank = True, null = True)
  twitch_client_secret = models.CharField(max_length = 256, blank = True, null = True)
  twitch_access_token = models.CharField(max_length = 256, blank = True, null = True)
  
class DiscordChannel(models.Model):
  bot = models.ForeignKey(ChatBot, on_delete = models.CASCADE)
  
  channel_id = models.CharField(max_length = 256)
  
class DiscordChannelInline(admin.TabularInline):
  model = DiscordChannel
  extra = 1
  
class TwitchChat(models.Model):
  bot = models.ForeignKey(ChatBot, on_delete = models.CASCADE)
  
  channel_name = models.CharField(max_length = 256)
  channel_id = models.CharField(max_length = 256)
  
class TwitchChatInline(admin.TabularInline):
  model = TwitchChat
  extra = 1

class BotCommand(models.Model):
  bot = models.ForeignKey(ChatBot, on_delete = models.CASCADE)
  
  command = models.CharField(max_length = 256, blank = False, null = False)
  output = models.CharField(max_length = 400, blank = True)
  
  per_user_cooldown = models.BooleanField(default = False)
  cooldown = models.IntegerField(verbose_name = "Cooldown in seconds", default = 60)
  
  
class BotCommandInline(admin.TabularInline):
  model = BotCommand
  extra = 1
  
class ChatBotForm(forms.ModelForm):
  template = "botmanager/chat_bot_form.html"
  
  name = forms.CharField(max_length = 256)
  
  discord_bot = forms.BooleanField()
  discord_token = forms.CharField(max_length = 256)
  discord_restrict_channels = forms.BooleanField(label = "Restrict to specific channels?")
  
  twitch_bot = forms.BooleanField()
  twitch_client_id = forms.CharField(max_length = 256)
  twitch_client_secret = forms.CharField(max_length = 256)
  twitch_access_token = forms.CharField(max_length = 256)
  
  class Meta:
    model = ChatBot
    exclude = []
  
class ChatBotAdmin(admin.ModelAdmin):
  list_display = ('name', )
  search_fields = [ 'name' ]
  form = ChatBotForm
  inlines = ( DiscordChannelInline, TwitchChatInline, BotCommandInline, )
  ordering = ( 'name', )