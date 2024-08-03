from django.contrib import admin
from django.urls import path, reverse, reverse_lazy
from django.utils.html import format_html
import urllib.parse
import requests

from .models import *
from .views import *

# Register your models here.
  
class TwitchChatInline(admin.TabularInline):
  model = TwitchChat
  extra = 1
  
class TwitchBasicCommandInline(admin.TabularInline):
  model = TwitchBasicCommand
  extra = 1
  
class TwitchCustomCommandInline(admin.TabularInline):
  model = TwitchCustomCommand
  extra = 1
  
class TwitchPeriodicMsgInline(admin.TabularInline):
  model = TwitchPeriodicMsg
  extra = 1
  
class TwitchCustomPeriodicMsgInline(admin.TabularInline):
  model = TwitchCustomPeriodicMsg
  extra = 1
  
@admin.register(TwitchConfig)
class TwitchConfigAdmin(admin.ModelAdmin):
  inlines = (TwitchChatInline, TwitchBasicCommandInline, TwitchCustomCommandInline, TwitchPeriodicMsgInline, TwitchCustomPeriodicMsgInline, )
  
class TwitchConfigInline(admin.TabularInline):
  model = TwitchConfig
  fields = ("client_id", "client_secret", "access_token", "active", )
  show_change_link = True
  
class DiscordChannelInline(admin.TabularInline):
  model = DiscordChannel
  extra = 1
  
class DiscordBasicCommandInline(admin.TabularInline):
  model = DiscordBasicCommand
  extra = 1
  
class DiscordCustomCommandInline(admin.TabularInline):
  model = DiscordCustomCommand
  extra = 1
  
class DiscordPeriodicMsgInline(admin.TabularInline):
  model = DiscordPeriodicMsg
  extra = 1
  
class DiscordCustomPeriodicMsgInline(admin.TabularInline):
  model = DiscordCustomPeriodicMsg
  extra = 1
  
@admin.register(DiscordConfig)
class DiscordConfigAdmin(admin.ModelAdmin):
  inlines = (DiscordChannelInline, DiscordBasicCommandInline, DiscordCustomCommandInline, DiscordPeriodicMsgInline, DiscordCustomPeriodicMsgInline, )
  
class DiscordConfigInline(admin.TabularInline):
  model = DiscordConfig
  fields = ("access_token", "active", )
  show_change_link = True
  
@admin.register(ChatBot)
class ChatBotAdmin(admin.ModelAdmin):
  search_fields = [ 'name' ]
  form = ChatBotForm
  inlines = ( TwitchConfigInline, DiscordConfigInline, )
  ordering = ( 'name', )
  
  def get_urls(self):
    return [
      path(
        "<pk>/detail/",
        self.admin_site.admin_view(ChatBotListView.as_view()),
        name="botmanager_chatbot_detail",
      ),
      path(
        "authcallback/",
        self.admin_site.admin_view(chatbot_twitch_access_token_callback),
        name="botmanager_chatbot_access_token_callback",
      ),
      *super().get_urls(),
    ]
    
  def get_list_display(self, request):
    def detail(obj : ChatBot) -> str:
      url = reverse("admin:botmanager_chatbot_detail", args=[obj.pk])
      return format_html(f'<a href="{url}">Detail</a>')
    
    def get_access_token(obj : ChatBot) -> str:
      auth_params = {
        'client_id': obj.twitchconfig.client_id,
        'redirect_uri': request.build_absolute_uri(reverse("admin:botmanager_chatbot_access_token_callback")),
        'scope': 'chat:edit chat:read bits:read clips:edit',
        'response_type': 'token'
      }
      
      url = f'https://id.twitch.tv/oauth2/authorize?{urllib.parse.urlencode(auth_params)}'
      return format_html(f'<a href="{url}">Get access token.</a>')
    
    return ('name', detail, get_access_token)