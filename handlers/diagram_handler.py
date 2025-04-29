import os
from io import BytesIO
from services.cache_service import RedisCacheService
from telebot import types
from database.user_repository import get_or_create_user, get_user_id_by_telegram_id
from database.diagram_repository import get_diagram_types, add_diagram_request, add_diagram_image, add_favourite, get_favourites
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
        
        cached_image = cache_service.get_cached_image(diagram_type, description)
        if cached_image:
            with open(cached_image, 'rb') as photo:
                bot.send_photo(message.from_user.id, photo)
            return        

        user_id = get_user_id_by_telegram_id(message.from_user.id)
        request_id = add_diagram_request(user_id, description, diagram_type)
        generator = Generator()
        success, error, output_python_file, output_image_file = generator.generate_diagram(
            diagram_type, 
            description, 
            message.from_user.id, 
            generation_counter
        )
        add_diagram_image(request_id, output_image_file)
        cache_service.cache_image(diagram_type, description, output_image_file)
        
        print(success, error, output_python_file, output_image_file)
        with open(output_image_file, 'rb') as photo:
                bot.send_photo(message.from_user.id, photo)
        
        del user_states[message.from_user.id]
        del user_diagram_type[message.from_user.id]

    @bot.message_handler(commands=["add_to_favorites"])
    def add_to_favorites(message):
        user_states[message.from_user.id] = 'waiting_for_favorite_id'
        bot.send_message(message.chat.id, "Введите ID диаграммы, которую хотите добавить в избранное:")

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_favorite_id')
    def process_favorite_id(message):
        try:
            diagram_id = int(message.text)
            exists = add_favourite(message.from_user.id, diagram_id)
            if exists:
                bot.send_message(message.chat.id, f"Диаграмма #{diagram_id} добавлена в избранное!")
            else:
                bot.send_message(message.chat.id, f"Диаграмма #{diagram_id} отсутствует в БД")

        except ValueError:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректный ID диаграммы (число).")

        user_states[message.from_user.id] = None

    @bot.message_handler(commands=["favorites"])
    def show_favorites(message):
            rows = get_favourites(telegram_id=message.from_user.id)
            if not rows:
                bot.send_message(message.chat.id, "У вас пока нет избранных диаграмм.")
                return

            favorites_text = "Ваши избранные диаграммы:\n\n"
            for row in rows:
                favorites_text += f"⭐ ID: {row.diagram_id}\n"
                favorites_text += f"📝 Запрос: {row.prompt[:50]}...\n"
                favorites_text += f"📅 Добавлено: {row.saved_at.strftime('%Y-%m-%d %H:%M')}\n\n"

            bot.send_message(message.chat.id, favorites_text)