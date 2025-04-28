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

@bot.message_handler(commands=["get_diagram_components"])
def get_diagram_components(message):
    """Получить компоненты конкретной диаграммы"""
    if not check_is_subscriber(message.from_user.id):
        bot.send_message(message.chat.id, "У вас нет подписки. Используйте /subscribe для оформления.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Использование: /get_diagram_components <ID_диаграммы>")
        return
    
    diagram_id = parts[1]
    
    with engine.connect() as connection:
        components = connection.execute(text("""
            SELECT dc.id, dc.component_type, dcm.metadata
            FROM diagram_components dc
            LEFT JOIN diagram_components_metadata dcm ON dc.id = dcm.component_id
            WHERE dc.diagram_id = :diagram_id
        """), {"diagram_id": diagram_id}).fetchall()
        
        if not components:
            bot.send_message(message.chat.id, "Компоненты не найдены.")
            return
        
        response = "Компоненты диаграммы:\n"
        for comp in components:
            response += f"ID: {comp.id}, Тип: {comp.component_type}\n"
            if comp.metadata:
                response += f"Метаданные: {comp.metadata}\n"
        
        bot.send_message(message.chat.id, response)   
    
@bot.message_handler(commands=["add_label"])
def add_label_to_diagram(message):
    """Добавить метку к диаграмме"""
    if not check_is_subscriber(message.from_user.id):
        bot.send_message(message.chat.id, "У вас нет подписки. Используйте /subscribe для оформления.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Использование: /add_label <ID_диаграммы> <метка>")
        return
    
    diagram_id, label_name = parts[1], parts[2]
    
    with engine.connect() as connection:
        # Проверяем существование метки
        label_id = connection.execute(
            text("SELECT id FROM labels WHERE name = :name"),
            {"name": label_name}
        ).scalar()
        
        # Если метки нет - создаем
        if not label_id:
            label_id = connection.execute(
                text("INSERT INTO labels (name) VALUES (:name) RETURNING id"),
                {"name": label_name}
            ).scalar()
        
        # Связываем метку с диаграммой
        connection.execute(
            text("""
                INSERT INTO diagram_labels (diagram_id, label_id)
                VALUES (:diagram_id, :label_id)
            """),
            {"diagram_id": diagram_id, "label_id": label_id}
        )
        connection.commit()
    
    bot.send_message(message.chat.id, f"Метка '{label_name}' добавлена к диаграмме {diagram_id}")

@bot.message_handler(commands=["export_history"])
def get_export_history(message):
    """История экспорта диаграмм пользователя"""
    with engine.connect() as connection:
        exports = connection.execute(text("""
            SELECT de.diagram_id, ef.name as format, de.created_at
            FROM diagram_exports de
            JOIN export_formats ef ON de.format_id = ef.id
            JOIN diagram_requests dr ON de.diagram_id = dr.id
            JOIN users u ON dr.user_id = u.id
            WHERE u.telegram_id = :telegram_id
            ORDER BY de.created_at DESC
            LIMIT 5
        """), {"telegram_id": message.from_user.id}).fetchall()
        
        if not exports:
            bot.send_message(message.chat.id, "У вас нет истории экспорта.")
            return
        
        response = "Последние экспорты:\n"
        for exp in exports:
            response += f"Диаграмма {exp.diagram_id} в {exp.format} ({exp.created_at})\n"
        
        bot.send_message(message.chat.id, response)

@bot.message_handler(commands=["feedback"])
def leave_feedback(message):
    """Оставить отзыв о диаграмме"""
    if not message.reply_to_message or not message.reply_to_message.photo:
        bot.send_message(message.chat.id, "Ответьте этой командой на сообщение с диаграммой, чтобы оставить отзыв.")
        return
    
    feedback_text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not feedback_text:
        bot.send_message(message.chat.id, "Использование: /feedback <текст отзыва> (в ответ на диаграмму)")
        return
    
    with engine.connect() as connection:
        # Получаем ID последней диаграммы пользователя
        diagram_id = connection.execute(text("""
            SELECT dr.id 
            FROM diagram_requests dr
            JOIN users u ON dr.user_id = u.id
            WHERE u.telegram_id = :telegram_id
            ORDER BY dr.created_at DESC
            LIMIT 1
        """), {"telegram_id": message.from_user.id}).scalar()
        
        if not diagram_id:
            bot.send_message(message.chat.id, "Не найдено последней диаграммы.")
            return
        
        # Сохраняем отзыв
        connection.execute(text("""
            INSERT INTO feedback (user_id, diagram_id, feedback_text, created_at)
            VALUES (
                (SELECT id FROM users WHERE telegram_id = :telegram_id),
                :diagram_id,
                :feedback_text,
                NOW()
            )
        """), {
            "telegram_id": message.from_user.id,
            "diagram_id": diagram_id,
            "feedback_text": feedback_text
        })
        connection.commit()
    
    bot.send_message(message.chat.id, "Спасибо за ваш отзыв!")

if __name__ == '__main__':
    bot.infinity_polling()