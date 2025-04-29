from database.user_repository import check_is_admin, check_is_subscriber

def require_admin(func):
    """
    Decorator for functions that require admin privileges.
    """
    def wrapper(message, *args, **kwargs):
        if not check_is_admin(message.from_user.id):
            # Send message that user doesn't have access
            from telebot import TeleBot
            bot = kwargs.get('bot')
            if isinstance(bot, TeleBot):
                bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return None
        return func(message, *args, **kwargs)
    return wrapper

def require_subscriber(func):
    """
    Decorator for functions that require subscriber privileges.
    """
    def wrapper(message, *args, **kwargs):
        if not check_is_subscriber(message.from_user.id):
            # Send message that user needs to subscribe
            from telebot import TeleBot
            bot = kwargs.get('bot')
            if isinstance(bot, TeleBot):
                bot.send_message(message.chat.id, "У вас нет подписки. Используйте /subscribe для оформления ее")
            return None
        return func(message, *args, **kwargs)
    return wrapper