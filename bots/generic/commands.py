import re
import datetime
import requests
import re

URLFETCH_REGEX = re.compile(r'\|\|(.*)\|\|')
INPUT_REGEX = re.compile(r'\{\{(-?[0-9]+)\}\}')
USERID_REGEX = re.compile(r'\{\{(userid)\}\}', re.IGNORECASE)

class BotCommand:
  command : str = ""
  output : str = ""
  as_reply : bool = False
  cooldown : int = 60
  cooldown_while_offline : int = 60
  last_sent = datetime.datetime(1970, 1, 1, 0, 0, 0, 1)
  restrict_to_channels : bool = False
  
  def __init__(self, command : str, 
                     output : str, 
                     as_reply : bool = False, 
                     cooldown : int = 60, 
                     cooldown_while_offline : int = None, 
                     restrict_to_channels : bool = False):
    self.command = command
    self.output = output
    self.as_reply = as_reply
    self.cooldown = cooldown
    self.cooldown_while_offline = cooldown_while_offline
    self.restrict_to_channels = restrict_to_channels
    
  def is_on_cooldown(self, user = None, is_live = False) -> bool:
    time_since = (datetime.datetime.now() - self.last_sent).total_seconds()
    if is_live or (self.cooldown_while_offline is None):
      return time_since < self.cooldown
    else:
      return time_since < self.cooldown_while_offline
  
  def match(self, message : str) -> bool:
    return message.lower().startswith(self.command.lower())
  
  def generate_output(self, message : str, user_id : str = None) -> str:
    message_parts = message.split(" ")
    
    output = self.output
    
    def replace_with_userid(match_obj):
      if match_obj.group() is not None:
        return user_id
  
    output = re.sub(USERID_REGEX, replace_with_userid, output)
      
    def replace_with_input(match_obj):
      if match_obj.group() is not None:
        message_index = int(match_obj.group(1))
        if message_index < 0:
          return message
        elif message_index < len(message_parts):
          return message_parts[message_index]
        else:
          return ""
      
    output = re.sub(INPUT_REGEX, replace_with_input, output)
    
    def replace_with_resp(match_obj):
      if match_obj.group() is not None:
        url = match_obj.group(1)
        try:
          resp = requests.get(url, timeout = 30)
          
          if resp.status_code >= 200 and resp.status_code < 300:
            resp.encoding = 'UTF-8'
            return resp.text
          else:
            return f"Error. Status {resp.status_code}"
        except requests.exceptions.ConnectionError:
          return "Could not connect to remote server."
        except requests.exceptions.HTTPError:
          return "HTTP Error."
        except TimeoutError:
          return "Request timed out."
        except:
          return "Unknown error."
      
    output = re.sub(URLFETCH_REGEX, replace_with_resp, output)
    
    return output
  
  def sent(self) -> None:
    self.last_sent = datetime.datetime.now()
    
  def __repr__(self):
    return f"{self.command} ({self.cooldown}s / {self.cooldown_while_offline}s, {self.restrict_to_channels}): {self.output}"
  
  def __eq__(self, other):
    if type(other) != BotCommand:
      return False
    
    return other.command == self.command and \
      other.output == self.output and \
        other.cooldown == self.cooldown and \
          other.cooldown_while_offline == self.cooldown_while_offline and \
            other.as_reply == self.as_reply and \
              other.restrict_to_channels == self.restrict_to_channels
              
  def __ne__(self, other):
    return not self == other