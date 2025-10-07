from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.socialaccount.providers.twitch.views import TwitchOAuth2Adapter
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render
from django.views import generic

from .models import *


# Create your views here.
class ChatBotListView(PermissionRequiredMixin, generic.DetailView):
    permission_required = "botmanager.view_chatbot"
    template_name = "botmanager/chat_bot_detail.html"
    model = ChatBot


def chatbot_twitch_access_token_callback(request):
    return render(request, "botmanager/twitch_access_token_callback.html")

class ItswillChatOAuth2Adapter(TwitchOAuth2Adapter):
    provider_id = "twitch_itswill_chat"

twitch_itswill_chat_oauth2_login = OAuth2LoginView.adapter_view(ItswillChatOAuth2Adapter)
twitch_itswill_chat_oauth2_callback = OAuth2CallbackView.adapter_view(ItswillChatOAuth2Adapter)

class LusciousBotOAuth2Adapter(TwitchOAuth2Adapter):
    provider_id = "twitch_luscious_bot"

twitch_luscious_bot_oauth2_login = OAuth2LoginView.adapter_view(LusciousBotOAuth2Adapter)
twitch_luscious_bot_oauth2_callback = OAuth2CallbackView.adapter_view(LusciousBotOAuth2Adapter)
