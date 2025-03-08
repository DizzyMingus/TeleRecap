from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Your API credentials
API_ID = 24907137
API_HASH = "1778d8f3be4a6961acd6016e81aec514"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    # This will request phone number and confirmation code
    print("Please log in to Telegram to generate a session string.")
    client.start()
    
    # Save the session string
    session_string = client.session.save()
    print("\nYour session string is:\n")
    print(session_string)
    print("\nAdd this to your .env file as TELEGRAM_SESSION_STRING") 