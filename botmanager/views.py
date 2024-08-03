from django.shortcuts import render
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic

from .models import *

# Create your views here.
class ChatBotListView(PermissionRequiredMixin, generic.DetailView):
  permission_required = "botmanager.view_chatbot"
  template_name = "botmanager/chat_bot_detail.html"
  model = ChatBot
  
def chatbot_twitch_access_token_callback(request):
  return render(request, "botmanager/twitch_access_token_callback.html")