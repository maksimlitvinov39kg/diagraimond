import os
import subprocess
from PIL import Image
import streamlit as st
from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator
import atexit
from checker import Checker

temporary_files = []

# Дефолтные тексты для каждого типа графиков
default_texts = {
    "Process": """Выбор ресторана и блюд:
Пользователь открывает приложение или сайт.
Пользователь выбирает ресторан из списка доступных.
Формирует заказ, добавляя блюда в корзину.
Оформление заказа:
Пользователь переходит к оформлению заказа.
На этом этапе есть две ветви:
Если пользователь уже зарегистрирован — он входит в личный кабинет.
Если пользователь новый — проходит регистрацию или оформляет заказ как гость.
Выбор способа доставки и оплаты:
Пользователь выбирает способ доставки:
Курьерская доставка на дом/офис.
Самовывоз из ресторана.
Затем выбирается способ оплаты:
Онлайн-оплата (картой, через приложение).
Оплата наличными или картой при получении.
Если выбрана онлайн-оплата, пользователь вводит данные карты и подтверждает транзакцию.
Подтверждение заказа:
Если оплата прошла успешно, заказ подтверждается.
Если возникли проблемы с оплатой, пользователь возвращается к выбору способа оплаты.
Доставка:
Если выбрана курьерская доставка, заказ отправляется в службу доставки.
Пользователь может отслеживать статус заказа (например, "готовится", "в пути", "доставлен").
Если выбран самовывоз, пользователь получает уведомление о готовности заказа.
Завершение процесса:
После доставки или получения блюда пользователь может оставить отзыв о заказе.
""",
    "PieChart": """Итальянская кухня: 35%
Японская кухня (суши, роллы): 25%
Фастфуд (бургеры, картофель фри): 20%
Вегетарианская кухня: 10%
Другие категории: 10%   
    """,
    "BarChart": """Понедельник: 120 заказов
Вторник: 150 заказов
Среда: 180 заказов
Четверг: 200 заказов
Пятница: 300 заказов
Суббота: 400 заказов
Воскресенье: 350 заказов
    """,
    "LineGraph": """"00:00 - 06:00: 50 заказов
06:00 - 09:00: 80 заказов
09:00 - 12:00: 150 заказов
12:00 - 15:00: 300 заказов
15:00 - 18:00: 250 заказов
18:00 - 21:00: 400 заказов
21:00 - 00:00: 200 заказов
    """
}

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
            return True, None  # Успех
        
        # Если есть ошибка, пытаемся исправить
        error_message = result.stderr
        st.warning(f"В коде ошибка — исправляем (попытка {attempt + 1} из {max_attempts})")
        checker.check_and_fix(output_python_file, error_message)
        attempt += 1
        
        if attempt == max_attempts:
            return False, error_message  # Превышено количество попыток
    
    return False, "Превышено максимальное количество попыток исправления"

atexit.register(cleanup_files)

st.title("Генератор диаграмм")

generator_type = st.radio("Выберите тип диаграммы:", ["Process", "PieChart", "BarChart", "LineGraph"])

# Чекбокс для загрузки дефолтного текста
load_default = st.checkbox("Load Default Text")

# Если чекбокс активен, подгружаем дефолтный текст, иначе позволяем ввести свой
if load_default:
    description = st.text_area("Описание диаграммы:", value=default_texts[generator_type])
else:
    description = st.text_area("Описание диаграммы:")

generator = load_generator(generator_type)

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
                st.image(output_image_file, caption=f"Сгенерированная диаграмма ({generator_type})", width=new_width)
            else:
                st.error(f"Не удалось сгенерировать диаграмму после нескольких попыток. Последняя ошибка: {error}")
    else:
        st.error("Пожалуйста, выберите генератор и введите описание.")