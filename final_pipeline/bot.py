import telebot
from telebot import types
import subprocess
import networkx as nx
import yaml
import os
from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator
import matplotlib.pyplot as plt
from PIL import Image
from checker import Checker
import time

bot = telebot.TeleBot()

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
    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = ["Process", "PieChart", "BarChart", "LineGraph"]
    markup.add(*buttons)
    user_states[message.from_user.id] = 'waiting_for_diagram_type'
    bot.send_message(message.chat.id, "Выберите тип диаграммы:", reply_markup=markup)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_diagram_type')
def handle_diagram_type(message):
    diagram_type = message.text

    # Проверяем, что пользователь выбрал один из типов диаграмм
    if diagram_type in ["Process", "PieChart", "BarChart", "LineGraph"]:
        user_states[message.from_user.id] = 'waiting_for_description'
        user_diagram_type[message.from_user.id] = diagram_type
        bot.send_message(message.chat.id, "Пожалуйста, введите описание диаграммы:")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите тип диаграммы из предложенных кнопок.")

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


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_description')
def handle_description(message):
    description = message.text

    # Получаем тип диаграммы из состояния пользователя
    diagram_type = user_diagram_type[message.from_user.id]
    
    if diagram_type:
        generator = load_generator(diagram_type)
        output_python_file = f'{"diagram_" + str(message.from_user.id) + str(generation)}.py'
        output_image_file = f'{"diagram_" + str(message.from_user.id) + str(generation)}.png'
        generation += 1
        success, error = try_generate_and_fix(generator, description, output_python_file, output_image_file)
        os.rename('output.png', output_image_file)
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

if __name__ == '__main__':
    bot.infinity_polling()