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
import math

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
    elif generator_type == "Pie Chart":
        return PieChartGenerator()
    elif generator_type == "Bar Chart":
        return BarChartGenerator()
    elif generator_type == "Line Graph":
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

    print(buttons)
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    user_states[message.from_user.id] = 'waiting_for_diagram_type'
    bot.send_message(message.chat.id, "Выберите тип диаграммы:", reply_markup=markup)


@bot.message_handler(commands=["available_formats"])
def show_available_export_formats(message):
    if (not check_is_subscriber(message.from_user.id)):
        bot.send_message(message.chat.id, "У вас нет подписки. Используйте /subscribe для оформления ее")
        return
    result = ""
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT name
            FROM export_formats
            WHERE is_active = TRUE
        """))
        rows = result.fetchall()
        
        result = '\n'.join(str(row) for row in rows)

    if not result:
        bot.send_message(message.chat.id, "Нет доступных форматов экспорта.")
        return

    bot.send_message(message.chat.id, f"Доступные форматы экспорта:\n{result}")


@bot.message_handler(commands=["my_activity"])
def show_user_last_activity(message):
    if (not check_is_subscriber(message.from_user.id)):
        bot.send_message(message.chat.id, "У вас нет подписки. Используйте /subscribe для оформления ее")
        return
    buttons = []
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT prompt
            FROM diagram_requests dr
            JOIN users u ON dr.user_id = u.id
            WHERE u.telegram_id = :telegram_id
            ORDER BY dr.created_at DESC
            LIMIT 3
        """), {"telegram_id": message.from_user.id})
        rows = result.fetchall()
        
        for row in rows:
            prompt = row[0]
            buttons.append(prompt[:30] + "...")

    if not buttons:
        bot.send_message(message.chat.id, "У вас пока нет генераций диаграмм.")
        return

    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(*buttons)
    user_states[message.from_user.id] = 'waiting_for_last_activity'
    bot.send_message(message.chat.id, "Ваши последние запросы генерации:", reply_markup=markup)


@bot.message_handler(commands=["my_templates"])
def show_available_templates(message):
    if (not check_is_subscriber(message.from_user.id)):
        bot.send_message(message.chat.id, "У вас нет подписки. Используйте /subscribe для оформления ее")
        return
    buttons = []
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT name
            FROM prompt_templates
            WHERE is_public = TRUE
            ORDER BY name ASC
        """))
        rows = result.fetchall()
        
        for row in rows:
            template_name = row[0]
            buttons.append(template_name)

    if not buttons:
        bot.send_message(message.chat.id, "Нет доступных шаблонов.")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    user_states[message.from_user.id] = 'waiting_for_template_selection'
    bot.send_message(message.chat.id, "Выберите шаблон промпта для генерации:", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_diagram_type')
def handle_diagram_type(message):
    print("тута")
    diagram_type = message.text

    if diagram_type in ["Process", "Pie Chart", "Bar Chart", "Line Graph"]:
        user_states[message.from_user.id] = 'waiting_for_description'
        user_diagram_type[message.from_user.id] = diagram_type
        bot.send_message(message.chat.id, "Пожалуйста, введите описание диаграммы:")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите тип диаграммы из предложенных кнопок.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_description')
def handle_description(message):
    description = message.text

    # Получаем тип диаграммы из состояния пользователя
    diagram_type = user_diagram_type[message.from_user.id]
    generation = 0
    if diagram_type:
        generator = load_generator(diagram_type)
        output_python_file = f'{"diagram_" + str(message.from_user.id) + str(generation)}.py'
        output_image_file = f'{"diagram_" + str(message.from_user.id) + str(generation)}.png'
        generation += 1
        success, error = try_generate_and_fix(generator, description, output_python_file, output_image_file)
        os.rename('output.png', output_image_file)
        print("дошли сюда")
        if success and os.path.exists(output_python_file):
            img = Image.open(output_image_file)
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            new_width = 512
            new_height = int(new_width / aspect_ratio)
            with open(output_image_file, 'rb') as file:
                sent_message = bot.send_document(message.chat.id, file)
        attempt = 0
        max_attemp = 5
        while attempt <= max_attemp:
            try:
                if os.path.exists(output_python_file):
                    os.remove(output_python_file)
                if os.path.exists(output_image_file):
                    os.remove(output_image_file)
                break
            except IOError as e:
                attempt += 1
                time.sleep(1)
            # Очищаем состояние пользователя
        del user_states[message.from_user.id]
        del user_diagram_type[message.from_user.id]

    else:
        del user_states[message.from_user.id]
        del user_diagram_type[message.from_user.id]
        bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /diagram.")

def try_generate_and_fix(generator, description, output_python_file, output_image_file, max_attempts=3):
    """
    Попытка сгенерировать и исправить код при необходимости
    """
    checker = Checker(generator)
    attempt = 0
    
    while attempt < max_attempts:
        if attempt == 0:
            generator.generate_python_from_text(description, output_file=output_python_file)
        
        result = subprocess.run(
            ["python", output_python_file],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            return True, None  # Успех
        
        # Если есть ошибка, пытаемся исправить
        error_message = result.stderr
        checker.check_and_fix(output_python_file, error_message)
        attempt += 1
        
        if attempt == max_attempts:
            return False, error_message  # Превышено количество попыток
    
    return False, "Превышено максимальное количество попыток исправления"

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