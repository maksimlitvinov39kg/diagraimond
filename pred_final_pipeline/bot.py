# import telebot
# import networkx as nx
# import yaml
# import os
# from main import generate_yaml
# import matplotlib.pyplot as plt

# bot = telebot.TeleBot(os.getenv("TG_BOT_API"))

# @bot.message_handler(content_types=["text"])
# def repeat_all_messages(message): 
#     generate_yaml(message.text)
#     with open("yaml.png","rb") as file:
#         f=file.read()

#     bot.send_document(message.chat.id, open(r'yaml.png', 'rb'))

# if __name__ == '__main__':
#     bot.infinity_polling()