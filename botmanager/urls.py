import datetime

from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from allauth.utils import import_attribute
from django.urls import include, path
from django.views.decorators.cache import cache_page

from .provider import ItswillChatProvider, LusciousBotProvider, provider_urlpatterns

app_name = 'botmanager'
urlpatterns = [
] + provider_urlpatterns(ItswillChatProvider) + provider_urlpatterns(LusciousBotProvider)
