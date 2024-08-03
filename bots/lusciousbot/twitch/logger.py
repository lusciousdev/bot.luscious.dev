from dotenv import load_dotenv
import os
import sys
import twitchio
import typing
import datetime
import MySQLdb
import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.cursor import MySQLCursor
import asyncio
from luscioustwitch import *

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from bots.generic.twitch import TwitchBot
from twitchio.ext import commands as twitchio_commands
from twitchio.ext import routines as twitchio_routines

class TwitchChatLogBot(TwitchBot):
  dbconn : MySQLConnection = None
  cursor : MySQLCursor = None
  
  table_name : str = "itswill_org_chatmessage"
  
  chat_history_lock : asyncio.Lock = asyncio.Lock()
  chat_history : typing.List[twitchio.Message] = []
  
  def __init__(self, bot_name : str, verbose = False, *args, **kwargs):
    super().__init__(bot_name, verbose, *args, **kwargs)
    
    self.dbconn = mysql.connector.connect(host = os.getenv("MARIADB_HOST", "localhost"), 
                                          port = int(os.getenv("MARIADB_PORT", "8006")), 
                                          user = os.getenv("MARIADB_USER", "lusciousdev-test"),
                                          password = os.getenv("MARIADB_PASSWORD", ""),
                                          database = os.getenv("MARIADB_DATABASE", "test_itswill"),
                                          collation = "utf8mb4_general_ci")
    self.cursor = self.dbconn.cursor()
    
    self.table_name = os.getenv("MARIADB_TABLE", "itswill_org_chatmessage")
    
  async def event_ready(self):
    await super().event_ready()
    
    self.archive_chat_history.start(stop_on_error = False)
  
  @twitchio_routines.routine(seconds = 10, wait_first = True)
  async def archive_chat_history(self):
    if not self.dbconn.is_connected():
      self.dbconn.reconnect(attempts = 10, delay = 30)
    
    async with self.chat_history_lock:
      if len(self.chat_history) <= 0:
        return
      
      for message in self.chat_history:
        message_id = message.id
        content_offset = -1
        message_timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")
        message_content = str(message.content)
        if message.author is not None:
          commenter_id = message.author.id
        elif message.echo:
          commenter_id = self.user_id
        else:
          print(f"Message has no author? {message_timestamp}: {message_content}")
        
        self.cursor.execute(f"""INSERT IGNORE INTO {self.table_name} (message_id, content_offset, created_at, message, commenter_id)
                            VALUES (%s, %s, %s, %s, %s)""", 
                            (message_id, 
                            content_offset,
                            message_timestamp,
                            message_content,
                            commenter_id))
        
      self.dbconn.commit()
      self.chat_history = []
  
  async def event_message(self, message : twitchio.Message):
    if message.echo:
      return
    
    if (message.channel.name == "itswill"):
      async with self.chat_history_lock:
        self.chat_history.append(message)
    
if __name__ == "__main__":
  bot = TwitchChatLogBot(bot_name = 'bot.luscious.dev')
  
  bot.run()