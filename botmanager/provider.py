from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.providers.twitch.provider import TwitchProvider, TwitchAccount
from allauth.utils import import_attribute
from django.urls import include, path
from .views import ItswillChatOAuth2Adapter, LusciousBotOAuth2Adapter

chat_bot_scopes = ["user:read:chat", "user:write:chat", "user:bot"]

class ItswillChatProvider(TwitchProvider):
    id = "twitch_itswill_chat"
    name = "Twitch - itswillChat"
    oauth2_adapter_class = ItswillChatOAuth2Adapter

    def get_default_scope(self):
        return ["user:read:chat", "user:write:chat", "user:bot"]

class LusciousBotProvider(TwitchProvider):
    id = "twitch_luscious_bot"
    name = "Twitch - luscious_bot"
    oauth2_adapter_class = LusciousBotOAuth2Adapter

    def get_default_scope(self):
        return [].extend(chat_bot_scopes)

def provider_urlpatterns(provider):
    login_view = import_attribute(provider.get_package() + ".views." + provider.id + "_oauth2_login")
    callback_view = import_attribute(provider.get_package() + ".views." + provider.id + "_oauth2_callback")

    urlpatterns = [
        path("login/", login_view, name = provider.id + "_login"),
        path("login/callback/", callback_view, name = provider.id + "_callback"),
    ]

    return [path(provider.get_slug() + "/", include(urlpatterns))]

provider_classes = [ItswillChatProvider, LusciousBotProvider]
