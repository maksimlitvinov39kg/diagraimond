import os
import subprocess
from PIL import Image
import streamlit as st
from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator
import atexit
import generate_diagram

temporary_files = []

def cleanup_files():
    for file in temporary_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Удалён временный файл: {file}")

atexit.register(cleanup_files)

st.title("Генератор диаграмм")

generator_type = st.radio("Выберите тип диаграммы:", ["Process", "PieChart", "BarChart", "LineGraph"])


description = st.text_area("Введите описание диаграммы:")

if st.button("Сгенерировать диаграмму"):
    output_python_file = f"{generator_type.lower()}_code.py"
    res, output_image_file, error, files = generate_diagram.generate_diagram(generator_type, description, output_python_file)
    
    for file in files:
         temporary_files.append(file)

    st.success(f"Python-код успешно сгенерирован: {output_python_file}")

    if output_image_file != None:
            img = Image.open(output_image_file)
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            new_width = 512
            new_height = int(new_width / aspect_ratio)
            st.image(output_image_file, caption=f"Сгенерированная диаграмма ({generator_type})", width=new_width)
    else:
        st.error(f"Ошибка при выполнении Python-кода: {error}")
