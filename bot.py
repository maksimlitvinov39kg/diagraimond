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

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_feedback')
def process_feedback(message):
    user_id = message.from_user.id
    feedback_text = message.text
    
    # Проверяем, содержит ли сообщение оценку (например, число от 1 до 5)
    if any(char.isdigit() for char in feedback_text):
        rating = int(next(char for char in feedback_text if char.isdigit()))
        rating = max(1, min(5, rating))  # Ограничиваем оценку от 1 до 5
    else:
        rating = None
    
    with engine.connect() as connection:
        query = text("""
            INSERT INTO feedback (user_id, rating, comment, submitted_at)
            VALUES (
                (SELECT id FROM users WHERE telegram_id = :telegram_id),
                :rating,
                :comment,
                NOW()
            )
        """)
        connection.execute(query, {
            "telegram_id": user_id,
            "rating": rating,
            "comment": feedback_text
        })
        connection.commit()
    
    bot.send_message(message.chat.id, "Спасибо за ваш отзыв!")
    user_states[message.from_user.id] = None

@bot.message_handler(commands=["history"])
def show_user_history(message):
    with engine.connect() as connection:
        query = text("""
            SELECT dr.id, dr.prompt, dr.created_at, dm.diagram_type
            FROM diagram_requests dr
            LEFT JOIN diagram_metadata dm ON dr.id = dm.diagram_id
            WHERE dr.user_id = (SELECT id FROM users WHERE telegram_id = :telegram_id)
            ORDER BY dr.created_at DESC
            LIMIT 10
        """)
        result = connection.execute(query, {"telegram_id": message.from_user.id})
        rows = result.fetchall()
        
        if not rows:
            bot.send_message(message.chat.id, "У вас пока нет истории запросов.")
            return
        
        history_text = "Ваша история запросов:\n\n"
        for row in rows:
            history_text += f"📅 {row.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            history_text += f"📊 Тип: {row.diagram_type or 'Не указан'}\n"
            history_text += f"📝 Запрос: {row.prompt[:50]}...\n"
            history_text += f"🔗 ID: {row.id}\n\n"
        
        bot.send_message(message.chat.id, history_text)

@bot.message_handler(commands=["add_to_favorites"])
def add_to_favorites(message):
    # Предполагаем, что пользователь вводит ID диаграммы
    user_states[message.from_user.id] = 'waiting_for_favorite_id'
    bot.send_message(message.chat.id, "Введите ID диаграммы, которую хотите добавить в избранное:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_favorite_id')
def process_favorite_id(message):
    try:
        diagram_id = int(message.text)
        with engine.connect() as connection:
            # Проверяем существование диаграммы
            check_query = text("SELECT 1 FROM diagram_requests WHERE id = :diagram_id")
            exists = connection.execute(check_query, {"diagram_id": diagram_id}).scalar()
            
            if not exists:
                bot.send_message(message.chat.id, "Диаграмма с таким ID не найдена.")
                return
            
            # Добавляем в избранное
            insert_query = text("""
                INSERT INTO user_favorites (user_id, diagram_id, saved_at)
                VALUES (
                    (SELECT id FROM users WHERE telegram_id = :telegram_id),
                    :diagram_id,
                    NOW()
                )
            """)
            connection.execute(insert_query, {
                "telegram_id": message.from_user.id,
                "diagram_id": diagram_id
            })
            connection.commit()
            
            bot.send_message(message.chat.id, f"Диаграмма #{diagram_id} добавлена в избранное!")
    
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный ID диаграммы (число).")
    
    user_states[message.from_user.id] = None

@bot.message_handler(commands=["favorites"])
def show_favorites(message):
    with engine.connect() as connection:
        query = text("""
            SELECT uf.diagram_id, dr.prompt, uf.saved_at
            FROM user_favorites uf
            JOIN diagram_requests dr ON uf.diagram_id = dr.id
            WHERE uf.user_id = (SELECT id FROM users WHERE telegram_id = :telegram_id)
            ORDER BY uf.saved_at DESC
        """)
        result = connection.execute(query, {"telegram_id": message.from_user.id})
        rows = result.fetchall()
        
        if not rows:
            bot.send_message(message.chat.id, "У вас пока нет избранных диаграмм.")
            return
        
        favorites_text = "Ваши избранные диаграммы:\n\n"
        for row in rows:
            favorites_text += f"⭐ ID: {row.diagram_id}\n"
            favorites_text += f"📝 Запрос: {row.prompt[:50]}...\n"
            favorites_text += f"📅 Добавлено: {row.saved_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        bot.send_message(message.chat.id, favorites_text)

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
    
def save_diagram_image(request_id, image_path, format_type):
    with engine.connect() as connection:
        query = text("""
            INSERT INTO diagram_images (request_id, image_path, format, created_at)
            VALUES (:request_id, :image_path, :format, NOW())
        """)
        connection.execute(query, {
            "request_id": request_id,
            "image_path": image_path,
            "format": format_type
        })
        connection.commit()

    
if __name__ == '__main__':
    bot.infinity_polling()