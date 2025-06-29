import os
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedTokenizer
from transformers.models import gpt2
import torch
import typing
  
class ChatGenerator:
  tokenizer = None
  gen_model = None
  res_model = None
  use_cuda = False
  
  input_max_length = 1024
  
  bad_ids = [[299, 15249], [44873, 4908], [277, 9460, 313], [479, 522], [42964], [34445], [77, 1573]]
  
  def __init__(self, tokenizer_model = "microsoft/DialoGPT-medium", general_model = os.path.join(os.path.dirname(__file__), 'models/itswillchat.2024.09.001'), response_model = os.path.join(os.path.dirname(__file__), 'models/itswillrespond.2024.09.002')):
    self.tokenizer : PreTrainedTokenizer = AutoTokenizer.from_pretrained(tokenizer_model, bad_word_ids = [])
    self.gen_model : gpt2.GPT2LMHeadModel = AutoModelForCausalLM.from_pretrained(general_model)
    self.res_model : gpt2.GPT2LMHeadModel = AutoModelForCausalLM.from_pretrained(response_model)
    
    self.use_cuda = torch.cuda.is_available()
    
    if self.use_cuda:
      self.gen_model.to(torch.device("cuda"))
      self.res_model.to(torch.device("cuda"))
    else:
      self.gen_model.to(torch.device("cpu"))
      self.res_model.to(torch.device("cpu"))
      
    self.input_max_length = int(0.75 * self.tokenizer.model_max_length)
      
    # chatmsgids = self.tokenizer.encode("test" + self.tokenizer.eos_token, truncation = True, max_length = self.input_max_length, return_tensors = 'pt')
    # if self.use_cuda:
    #   chatmsgids = chatmsgids.to(torch.device("cuda"))
    # else:
    #   chatmsgids = chatmsgids.to(torch.device("cpu"))
    #   
    # print(chatmsgids)
      
  def generate(self, chat_history : typing.List[str], top_p = 0.7, temperature = 0.8):
    if len(chat_history) < 1:
      print("Generate needs at least one string for input.")
      return None
    
    temp_input_list = []
    for chatmsg in chat_history:
      chatmsgids = self.tokenizer.encode(chatmsg + self.tokenizer.eos_token, truncation = True, max_length = self.input_max_length, return_tensors='pt')
      if self.use_cuda:
        chatmsgids = chatmsgids.to(torch.device("cuda"))
      else:
        chatmsgids = chatmsgids.to(torch.device("cpu"))
      temp_input_list.append(chatmsgids)
      
    if temp_input_list[-1].shape[-1] <= self.input_max_length:
      bot_input_ids = temp_input_list[-1]
    else:
      bot_input_ids = temp_input_list[-1][:, :self.tokenizer.model_max_length - 1]
    for inp in reversed(temp_input_list[:-1]):
      if (bot_input_ids.shape[-1] + inp.shape[-1]) < self.input_max_length:
        bot_input_ids = torch.cat([inp, bot_input_ids], dim = -1)
      else:
        print('input array exceeded tokenizer max length. skipping some inputs')

    # generated a response while limiting the total chat history to 1000 tokens, 
    chat_history_ids = self.gen_model.generate(
        bot_input_ids, 
        max_length=self.tokenizer.model_max_length,
        pad_token_id=self.tokenizer.eos_token_id,
        no_repeat_ngram_size=3,       
        do_sample=True, 
        top_k=100, 
        top_p=top_p,
        temperature = temperature,
        bad_words_ids = self.bad_ids
    )
    
    bot_response_ids = chat_history_ids[:, bot_input_ids.shape[-1]:]
    return self.tokenizer.decode(bot_response_ids[0], skip_special_tokens=True)
  
  def gen_response(self, prompt : str, top_p = 0.8, temperature = 0.9):
    prompt_msg_ids = self.tokenizer.encode(prompt + self.tokenizer.eos_token, truncation = True, max_length = self.input_max_length, return_tensors='pt')
    if self.use_cuda:
      prompt_msg_ids = prompt_msg_ids.to(torch.device("cuda"))
    else:
      prompt_msg_ids = prompt_msg_ids.to(torch.device("cpu"))
    
    chat_history_ids = self.res_model.generate(
        prompt_msg_ids, 
        max_length=self.tokenizer.model_max_length,
        pad_token_id=self.tokenizer.eos_token_id,
        no_repeat_ngram_size=3,       
        do_sample=True, 
        top_k=350, 
        top_p=top_p,
        temperature = temperature,
        bad_words_ids = self.bad_ids
    )
    
    bot_response_ids = chat_history_ids[:, prompt_msg_ids.shape[-1]:]
    return self.tokenizer.decode(bot_response_ids[0], skip_special_tokens=True)
  
  def gen_about(self, start : str, top_p = 0.8, temperature = 0.9):
    start_msg_ids = self.tokenizer.encode(start, truncation = True, max_length = self.input_max_length, return_tensors = 'pt')
    if self.use_cuda:
      start_msg_ids = start_msg_ids.to(torch.device("cuda"))
    else:
      start_msg_ids = start_msg_ids.to(torch.device("cpu"))
      
    chat_history_ids = self.gen_model.generate(
      start_msg_ids,
      max_length=self.tokenizer.model_max_length,
      pad_token_id=self.tokenizer.eos_token_id,
      no_repeat_ngram_size=3,       
      do_sample=True, 
      top_k=350, 
      top_p=top_p,
      temperature = temperature,
      bad_words_ids = self.bad_ids
    )
    
    bot_response_ids = chat_history_ids[:, :]
    return self.tokenizer.decode(bot_response_ids[0], skip_special_tokens=True)
    
    