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
from datetime import datetime
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
    get_or_create_user(message)
    buttons = get_diagram_types()
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    user_states[message.from_user.id] = 'waiting_for_diagram_type'
    bot.send_message(message.chat.id, "Выберите тип диаграммы:", reply_markup=markup)


@bot.message_handler(commands=["admin"])
def admin_access(message):
    if(check_is_admin(message.from_user.id)):
        user_states[message.from_user.id] = 'admin_wait_for_actions'
        bot.send_message(message.chat.id, "Вошли в админку")  
    else:
        bot.send_message(message.chat.id, "Вы не имеете доступа.")      

def get_or_create_user(message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    default_role_id = 1
    query = text("SELECT * FROM users WHERE telegram_id = :telegram_id")
    with engine.connect() as connection:
        result = connection.execute(query, {"telegram_id": telegram_id})
        user = result.fetchone()
        if user:
            print(user)
        else:
            current_time = datetime.now()
            insert_query = text("""
                INSERT INTO users (telegram_id, name, registered_at, is_active) 
                VALUES (:telegram_id, :name, :registered_at, :is_active)
                RETURNING *
            """)
        
            result = connection.execute(
                insert_query, 
                {
                    "telegram_id": telegram_id,
                    "name": username,  
                    "registered_at": current_time,
                    "is_active": True
                }
            )
            new_user = result.fetchone()
            user_id = new_user.id

            insert_role_query = text("""
                INSERT INTO user_roles (user_id, role_id, assigned_at)
                VALUES (:user_id, :role_id, :assigned_at)
            """)

            connection.execute(
                insert_role_query,
                {
                    "user_id" : user_id,
                    "role_id" : default_role_id,
                    "assigned_at" : current_time
                }
            )
            connection.commit()
            print(new_user)

def get_diagram_types():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM diagram_types"))
        rows = result.fetchall()
        buttons = []
        for row in rows:
            buttons.append(row[1])
        return buttons

def check_is_admin(telegram_id):
    with engine.connect() as conn:
        query = text("""
            SELECT ur.role_id 
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE u.telegram_id = :telegram_id
        """)
        
        result = conn.execute(query, {"telegram_id": telegram_id}).scalar()
        return result == 3
    
def check_is_subscriber(telegram_id):
    with engine.connect() as conn:
        query = text("""
            SELECT ur.role_id 
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE u.telegram_id = :telegram_id
        """)
        
        result = conn.execute(query, {"telegram_id": telegram_id}).scalar()
        return (result == 3 or result == 2)   
    
if __name__ == '__main__':
    bot.infinity_polling()