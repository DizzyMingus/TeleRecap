from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest
import os
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Create two clients - one for bot commands and one for user operations
bot = TelegramClient('bot_session', API_ID, API_HASH)
user_client = TelegramClient('user_session', API_ID, API_HASH)

async def fetch_messages_with_user(channel_username, limit=20):
    """Fetch messages from a specific channel using the user client"""
    try:
        # Make sure the user client is connected
        if not user_client.is_connected():
            await user_client.connect()

        # Get the channel entity@.env move the secret key value pairs to .env file
        chat = await user_client.get_entity(channel_username)

        # Retrieve messages using the user client
        messages = await user_client(GetHistoryRequest(
            peer=chat,
            limit=limit,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))

        # Format messages into a readable string
        result = []
        for message in messages.messages:
            if message.message:  # Only include messages with text
                result.append(f"ID: {message.id}, Date: {message.date}\n{message.message}\n")

        return "\n".join(result) if result else "No messages found."

    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return f"Error fetching messages: {e}"

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handle the /start command"""
    await event.respond("👋 Hello! I can retrieve messages from every Telegram channel.\n\n"
                        "Use /fetch @channel-id [number of messages] to get messages.\n"
                        "Example: /fetch durov 5")

@bot.on(events.NewMessage(pattern='/fetch'))
async def fetch_handler(event):
    """Handle the /fetch command"""
    try:
        # Parse the command arguments
        args = event.message.message.split()

        if len(args) < 2:
            await event.respond("Please provide a channel username.\n"
                               "Example: /fetch channel-id 10")
            return

        channel = args[1]
        if not channel.startswith('@'):
            channel = '@' + channel

        # Get the limit if provided
        limit = 10  # Default limit
        if len(args) >= 3 and args[2].isdigit():
            limit = min(int(args[2]), 100)  # Cap at 100 to avoid large responses

        await event.respond(f"Fetching up to {limit} messages from {channel}...")

        # Fetch the messages using the user client
        messages = await fetch_messages_with_user(channel, limit)

        # Send messages in chunks due to Telegram message size limits
        max_length = 4000
        for i in range(0, len(messages), max_length):
            chunk = messages[i:i+max_length]
            await event.respond(chunk if chunk else "No messages to display.")

    except Exception as e:
        logger.error(f"Error in fetch handler: {e}")
        await event.respond(f"Error: {str(e)}")

async def main():
    # Start both clients
    await bot.start(bot_token=BOT_TOKEN)
    await user_client.start(PHONE_NUMBER)

    logger.info("Bot started")
    logger.info("User client started")

    # Run until disconnected
    await asyncio.gather(
        bot.run_until_disconnected(),
        user_client.disconnected
    )

if __name__ == '__main__':
    asyncio.run(main())
