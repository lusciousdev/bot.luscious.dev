import re
import datetime
import requests
import re

URLFETCH_REGEX = re.compile(r'\|\|(.*)\|\|')
INPUT_REGEX = re.compile(r'\{\{(-?[0-9]+)\}\}')

class BotCommand:
  command : str = ""
  output : str = ""
  per_user_cooldown : bool = False
  cooldown : int = 60
  last_sent = datetime.datetime(1970, 1, 1, 0, 0, 0, 1)
  
  def __init__(self, command, output, per_user_cooldown = False, cooldown = 60):
    self.command = command
    self.output = output
    self.per_user_cooldown = per_user_cooldown
    self.cooldown = cooldown
    
  def is_on_cooldown(self, user = None) -> bool:
    return (datetime.datetime.now() - self.last_sent).total_seconds() < self.cooldown
  
  def generate_output(self, message : str, user_id : str = None) -> str:
    message_parts = message.split(" ")
    
    output = self.output
      
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
    return f"{self.command} ({self.cooldown}s): {self.output}"