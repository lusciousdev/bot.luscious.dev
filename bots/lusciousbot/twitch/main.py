import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from bots.generic.twitch import TwitchBot

if __name__ == "__main__":
  bot = TwitchBot(bot_name = 'bot.luscious.dev')
  
  bot.run()