from dotenv import load_dotenv
import os
import telebot

from database.connection import create_db_engine
from handlers.diagram_handler import register_diagram_handlers
from handlers.admin_handler import register_admin_handlers
from handlers.subscriber_handler import register_subscriber_handlers

# Load environment variables
load_dotenv()

# Initialize the bot with the token from environment variables
token = os.environ.get('TG_TOKEN')
bot = telebot.TeleBot(token=token)

def main():
    # Register all handlers
    register_diagram_handlers(bot)
    register_admin_handlers(bot)
    register_subscriber_handlers(bot)
    
    # Start the bot
    print("Bot is running...")
    bot.infinity_polling()

if __name__ == '__main__':
    main()