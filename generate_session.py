from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
import os

load_dotenv()

# Your API credentials from environment variables
API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')

if API_ID == 0 or not API_HASH:
    logger.error("API_ID or API_HASH not found in environment variables")
    print("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file")
    exit(1)

logger.info("Starting Telegram session string generation")
logger.info(f"Using API_ID: {API_ID}")
logger.info("Initializing TelegramClient...")

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    # This will request phone number and confirmation code
    print("Please log in to Telegram to generate a session string.")
    logger.info("Attempting to authenticate with Telegram...")
    client.start()
    logger.info("Authentication successful!")
    
    # Save the session string
    logger.info("Generating session string...")
    session_string = client.session.save()
    logger.info("Session string generated successfully")
    
    print("\nYour session string is:\n")
    # Only print the first and last 5 characters for the logs
    masked_session = session_string[:5] + "..." + session_string[-5:] if len(session_string) > 10 else "..."
    logger.info(f"Session string generated: {masked_session}")
    
    print(session_string)
    print("\nAdd this to your .env file as TELEGRAM_SESSION_STRING")
    logger.info("Session generation process completed") 