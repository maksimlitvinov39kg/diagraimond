import os
import subprocess
from PIL import Image
import streamlit as st
from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator
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

        generator.generate_python_from_text(description, output_file=output_python_file)
        st.success(f"Python-код успешно сгенерирован: {output_python_file}")

        result = subprocess.run(
            ["python", output_python_file],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and os.path.exists(output_image_file):
            img = Image.open(output_image_file)
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            new_width = 512
            new_height = int(new_width / aspect_ratio)
            st.image(output_image_file, caption=f"Сгенерированная диаграмма ({generator_type})", width=new_width)
        else:
            st.error(f"Ошибка при выполнении Python-кода: {result.stderr}")
    else:
        st.error("Пожалуйста, выберите генератор и введите описание.")
