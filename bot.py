from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator

import telebot
from telebot import types
import subprocess
import networkx as nx
import yaml
import os

import matplotlib.pyplot as plt
from PIL import Image
from checker import Checker
import time

from dotenv import load_dotenv

from sqlalchemy import create_engine, text

load_dotenv()

token = os.environ.get('TG_TOKEN')
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASS = os.environ.get("POSTGRES_PASS")
POSTGRESS_DB = os.environ.get("POSTGRES_DB")
POSTGRES_IP = "176.108.250.9"
POSTGRES_PORT = "5432"

bot = telebot.TeleBot(token=token)
connection_string = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_IP}:{POSTGRES_PORT}/{POSTGRESS_DB}"
engine = create_engine(connection_string)
generation = 0

user_states = {}
user_diagram_type = {}

def load_generator(generator_type):
    if generator_type == "Process":
        return ProcessGenerator()
    elif generator_type == "PieChart":
        return PieChartGenerator()
    elif generator_type == "BarChart":
        return BarChartGenerator()
    elif generator_type == "LineGraph":
        return LineGraphGenerator()


@bot.message_handler(commands=["diagram"])
def generate_diagram_for_user(message): 
    buttons = []
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM diagram_types"))
        rows = result.fetchall()
        for row in rows:
            buttons.append(row[1])

    print(buttons)
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    user_states[message.from_user.id] = 'waiting_for_diagram_type'
    bot.send_message(message.chat.id, "Выберите тип диаграммы:", reply_markup=markup)

if __name__ == '__main__':
    bot.infinity_polling()