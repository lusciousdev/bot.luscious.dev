import os
import sys
import requests
import twitchio
import random
import humanize

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from bots.generic.twitch import TwitchBot

class LusciousTwitchBot(TwitchBot):
  pass
      

if __name__ == "__main__":
  bot = LusciousTwitchBot(bot_name = 'bot.luscious.dev', verbose = False)
  
  bot.run()