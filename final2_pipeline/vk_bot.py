import vk_api
from dotenv import load_dotenv
from vk_api import VkUpload
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import subprocess
import os
from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator
from PIL import Image
import time

load_dotenv()
TOKEN = os.getenv("VK_API_KEY")
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

user_states = {}
user_diagram_type = {}


def send_message(user_id, message, keyboard=None):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0,
        keyboard=keyboard.get_keyboard() if keyboard else None,
    )


def create_keyboard(buttons):
    keyboard = VkKeyboard(one_time=True)
    for button in buttons:
        keyboard.add_button(button, color=VkKeyboardColor.PRIMARY)
    return keyboard


def load_generator(generator_type):
    if generator_type == "Process":
        return ProcessGenerator()
    elif generator_type == "PieChart":
        return PieChartGenerator()
    elif generator_type == "BarChart":
        return BarChartGenerator()
    elif generator_type == "LineGraph":
        return LineGraphGenerator()


def try_generate_and_fix(generator, description, output_python_file, output_image_file, max_attempts=3):
    attempt = 0
    while attempt < max_attempts:
        if attempt == 0:
            generator.generate_python_from_text(description, output_file=output_python_file, output_image_file= output_image_file)

        result = subprocess.run(
            ["python", output_python_file],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return True, None  # Успех

        attempt += 1
        if attempt == max_attempts:
            return False, result.stderr

    return False, "Превышено максимальное количество попыток исправления"

upload = VkUpload(vk_session)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        text = event.text.strip()

        # Команда для выбора диаграммы
        if text.lower() == "/diagram":
            keyboard = create_keyboard(["Process", "PieChart", "BarChart", "LineGraph"])
            user_states[user_id] = 'waiting_for_diagram_type'
            send_message(user_id, "Выберите тип диаграммы:", keyboard)

        elif user_states.get(user_id) == 'waiting_for_diagram_type':
            if text in ["Process", "PieChart", "BarChart", "LineGraph"]:
                user_states[user_id] = 'waiting_for_description'
                user_diagram_type[user_id] = text
                send_message(user_id, "Введите описание диаграммы:")
            else:
                send_message(user_id, "Пожалуйста, выберите тип диаграммы из предложенных.")

        elif user_states.get(user_id) == 'waiting_for_description':
            diagram_type = user_diagram_type[user_id]
            generator = load_generator(diagram_type)
            output_python_file = f'diagram_{user_id}.py'
            output_image_file = f'diagram_{user_id}.png'
            success, error = try_generate_and_fix(generator, text, output_python_file, output_image_file)
            if success:

                uploaded_photo = upload.photo_messages(output_image_file)
                attachment = f'photo{uploaded_photo[0]["owner_id"]}_{uploaded_photo[0]["id"]}'

                vk.messages.send(
                    user_id=user_id,
                    random_id=0,
                    attachment=attachment,
                    message = "Вот ваша диаграмма!"
                )
                os.remove(output_python_file)
                os.remove(output_image_file)
            else:
                send_message(user_id, f"Ошибка при генерации диаграммы: {error}")

            del user_states[user_id]
            del user_diagram_type[user_id]

        else:
            send_message(user_id, "Введите /diagram, чтобы начать.")

