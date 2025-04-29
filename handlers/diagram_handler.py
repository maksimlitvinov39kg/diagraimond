import os
from io import BytesIO
from services.cache_service import RedisCacheService
from telebot import types
from database.user_repository import get_or_create_user, get_user_id_by_telegram_id
from database.diagram_repository import get_diagram_types, add_diagram_request, add_diagram_image
from services.generate_diagram import Generator

user_states = {}
user_diagram_type = {}
generation_counter = 0
cache_service = RedisCacheService()

def register_diagram_handlers(bot):
    """Register all diagram-related command handlers."""
    
    @bot.message_handler(commands=["diagram"])
    def generate_diagram_for_user(message):
        get_or_create_user(message.from_user.id, message.from_user.username)
        buttons = get_diagram_types()
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*[types.KeyboardButton(btn) for btn in buttons])
        user_states[message.from_user.id] = 'waiting_for_diagram_type'
        bot.send_message(message.chat.id, "Выберите тип диаграммы:", reply_markup=markup)

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_diagram_type')
    def handle_diagram_type(message):
        diagram_type = message.text

        if diagram_type in ["Process", "Pie Chart", "Bar Chart", "Line Graph"]:
            user_states[message.from_user.id] = 'waiting_for_description'
            user_diagram_type[message.from_user.id] = diagram_type
            bot.send_message(message.chat.id, "Пожалуйста, введите описание диаграммы:")
        else:
            bot.send_message(message.chat.id, "Пожалуйста, выберите тип диаграммы из предложенных кнопок.")

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_description')
    def handle_description(message):
        global generation_counter
        
        description = message.text
        diagram_type = user_diagram_type.get(message.from_user.id)
        
        if not diagram_type:
            del user_states[message.from_user.id]
            if message.from_user.id in user_diagram_type:
                del user_diagram_type[message.from_user.id]
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /diagram.")
            return
        
        # cached_image, metadata = cache_service.get_cached_image(diagram_type, description)
        # if (cached_image):
        #     print("нашли в кэше!")
        generator = Generator()
        success, error, output_python_file, output_image_file = generator.generate_diagram(
            diagram_type, 
            description, 
            message.from_user.id, 
            generation_counter
        )
        generation_counter += 1
        
        print(success, error, output_python_file, output_image_file)
        
        
        # user_id = get_user_id_by_telegram_id(message.from_user.id)
        # request_id = add_diagram_request(user_id, description, diagram_type)
        # output_image_file = "test_" + str(user_id) + "_" + str(request_id) + ".png"
        # add_diagram_image(request_id, output_image_file)
        
        del user_states[message.from_user.id]
        del user_diagram_type[message.from_user.id]