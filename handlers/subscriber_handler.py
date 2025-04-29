from telebot import types
from services.auth_service import require_subscriber
from database.diagram_repository import get_user_recent_prompts, get_available_export_formats, get_available_templates

# State tracking
subscriber_states = {}

def register_subscriber_handlers(bot):
    """Register all subscriber-related command handlers."""
    
    @bot.message_handler(commands=["available_formats"])
    @require_subscriber
    def show_available_export_formats(message):
        formats = get_available_export_formats()
        
        if not formats:
            bot.send_message(message.chat.id, "Нет доступных форматов экспорта.")
            return
            
        formats_text = '\n'.join(formats)
        bot.send_message(message.chat.id, f"Доступные форматы экспорта:\n{formats_text}")

    @bot.message_handler(commands=["my_activity"])
    @require_subscriber
    def show_user_last_activity(message):
        prompts = get_user_recent_prompts(message.from_user.id)
        
        if not prompts:
            bot.send_message(message.chat.id, "У вас пока нет генераций диаграмм.")
            return

        buttons = [prompt[:30] + "..." for prompt in prompts]
        
        markup = types.ReplyKeyboardMarkup(row_width=1)
        markup.add(*[types.KeyboardButton(btn) for btn in buttons])
        subscriber_states[message.from_user.id] = 'waiting_for_last_activity'
        bot.send_message(message.chat.id, "Ваши последние запросы генерации:", reply_markup=markup)

    @bot.message_handler(commands=["my_templates"])
    @require_subscriber
    def show_available_templates(message):
        templates = get_available_templates()
        
        if not templates:
            bot.send_message(message.chat.id, "Нет доступных шаблонов.")
            return

        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*[types.KeyboardButton(template) for template in templates])
        subscriber_states[message.from_user.id] = 'waiting_for_template_selection'
        bot.send_message(message.chat.id, "Выберите шаблон промпта для генерации:", reply_markup=markup)
        
    # Add handlers for template selection and other subscriber functions