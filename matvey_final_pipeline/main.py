import os
import subprocess
from PIL import Image
import streamlit as st
from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator
from checker import Checker
import atexit


temporary_files = []

def load_generator(generator_type):
    if generator_type == "Process":
        return ProcessGenerator()
    elif generator_type == "PieChart":
        return PieChartGenerator()
    elif generator_type == "BarChart":
        return BarChartGenerator()
    elif generator_type == "LineGraph":
        return LineGraphGenerator()
    else:
        st.error("Неверный тип диаграммы.")
        return None

def cleanup_files():
    for file in temporary_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Удалён временный файл: {file}")

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
            return True, None  
        
        
        error_message = result.stderr
        checker.check_and_fix(output_python_file, error_message)
        attempt += 1
        
        if attempt == max_attempts:
            return False, error_message
    
    return False, "Превышено максимальное количество попыток исправления"

atexit.register(cleanup_files)

st.title("Генератор диаграмм")

generator_type = st.radio("Выберите тип диаграммы:", ["Process", "PieChart", "BarChart", "LineGraph"])

generator = load_generator(generator_type)

description = st.text_area("Введите описание диаграммы:")

if st.button("Сгенерировать диаграмму"):
    if generator and description:
        output_python_file = f"{generator_type.lower()}_code.py"
        output_image_file = f"output.png"

        temporary_files.append(output_python_file)
        temporary_files.append(output_image_file)

        with st.spinner("Генерация и обработка кода..."):
            success, error = try_generate_and_fix(generator, description, output_python_file, output_image_file)
            
            if success and os.path.exists(output_image_file):
                img = Image.open(output_image_file)
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
                new_width = 512
                new_height = int(new_width / aspect_ratio)
                st.image(output_image_file, width=new_width)
            else:
                st.error(f"Не удалось сгенерировать диаграмму после нескольких попыток. Последняя ошибка: {error}")
    else:
        st.error("Пожалуйста, выберите генератор и введите описание.")