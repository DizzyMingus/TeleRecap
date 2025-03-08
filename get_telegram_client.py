import os
from dotenv import load_dotenv
from telethon import TelegramClient

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID')) if os.getenv('API_ID') else None
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

class TelegramClientSingleton:
    _bot_instance = None
    _user_instance = None
    
    @classmethod
    def get_bot_client(cls):
        if cls._bot_instance is None:
            if not all([API_ID, API_HASH, BOT_TOKEN]):
                raise ValueError("Bot credentials not found in environment variables")
            cls._bot_instance = TelegramClient('bot_session', API_ID, API_HASH)
        return cls._bot_instance
    
    @classmethod
    def get_user_client(cls):
        if cls._user_instance is None:
            if not all([API_ID, API_HASH]):
                raise ValueError("User client credentials not found in environment variables")
            cls._user_instance = TelegramClient('user_session', API_ID, API_HASH)
        return cls._user_instance

# Convenient function to get bot client
def get_bot():
    return TelegramClientSingleton.get_bot_client()

# Convenient function to get user client
def get_user_client():
    return TelegramClientSingleton.get_user_client()