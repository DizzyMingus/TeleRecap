import os
import json
import logging
import datetime
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot token for the Telegram Bot API
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Telegram Client API credentials
API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING', '')

# Initialize Telegram Client
client = None

# Store user preferences
user_preferences = {}


# Command handler for /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm a Telegram message retrieval bot. I can fetch messages from public channels based on your criteria.\n\n"
        "To get started, use the /setchannel command to tell me which channel to retrieve messages from.\n"
        "Example: /setchannel @channelname\n\n"
        "Then, use /settopic to specify what topics you're interested in.\n"
        "Example: /settopic technology\n\n"
        "Use /get to retrieve messages whenever you want!")


# Command handler for setting channel
async def set_channel_command(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Please provide a channel username.\nExample: /setchannel @channelname"
        )
        return

    channel_username = context.args[0]

    # Initialize user preferences if not exists
    if user_id not in user_preferences:
        user_preferences[user_id] = {'channel': None, 'topic': None}

    # Store the channel preference
    user_preferences[user_id]['channel'] = channel_username
    await update.message.reply_text(
        f"Channel set to {channel_username}. Use /get to retrieve messages.")


# Command handler for setting topic
async def set_topic_command(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Please provide a topic.\nExample: /settopic technology")
        return

    topic = ' '.join(context.args)

    # Initialize user preferences if not exists
    if user_id not in user_preferences:
        user_preferences[user_id] = {'channel': None, 'topic': None}

    user_preferences[user_id]['topic'] = topic
    await update.message.reply_text(
        f"Topic set to '{topic}'. Use /get to retrieve relevant messages.")


# Function to fetch messages from a channel
async def fetch_channel_messages(bot: Bot, channel_username: str, limit=100):
    try:
        global client

        # Initialize the Telegram client if not already done
        if client is None:
            client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
            await client.connect()

            # Check if we need to sign in
            if not await client.is_user_authorized():
                logger.warning("Telethon client is not authorized. Sessions string might be invalid or missing.")
                # We can't perform authorization here as it's an automated process
                # You would need to run a separate script to generate a session string

                # Return placeholder message
                return [{
                    'date': datetime.datetime.now(),
                    'text': "Error: Telegram client is not authorized. Contact the administrator."
                }]

        # Get entity (channel) information
        entity = await client.get_entity(channel_username)

        # Fetch messages from the channel
        messages = []
        async for message in client.iter_messages(entity, limit=limit):
            if message.text:  # Only include messages with text
                messages.append({
                    'date': message.date,
                    'text': message.text,
                    'id': message.id
                })

        return messages
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return [{
            'date': datetime.datetime.now(),
            'text': f"Error fetching messages: {str(e)}"
        }]


# Command to get messages
async def get_messages_command(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check if channel is set
    if user_id not in user_preferences or not user_preferences[user_id][
            'channel']:
        await update.message.reply_text(
            "Please set a channel first using /setchannel @channelname")
        return

    channel = user_preferences[user_id]['channel']
    topic = user_preferences[user_id]['topic']

    # Parse limit parameter if provided
    limit = 100  # Default limit
    if context.args and context.args[0].isdigit():
        limit = min(int(context.args[0]),
                    100)  # Cap at 100 to avoid overloading

    await update.message.reply_text(f"Retrieving messages from {channel}" + (
        f" related to '{topic}'" if topic else "") + f" (limit: {limit})...")

    try:
        # Fetch messages from the channel
        bot = context.bot
        messages = await fetch_channel_messages(bot, channel, limit)

        if messages:
            # Filter messages by topic if specified
            if topic:
                filtered_messages = [
                    msg for msg in messages
                    if topic.lower() in msg['text'].lower()
                ]
            else:
                filtered_messages = messages

            if filtered_messages:
                result = f"Retrieved {len(filtered_messages)} messages:\n\n"
                for i, msg in enumerate(filtered_messages[:20],
                                        1):  # Limit to 20 in the response
                    # Format date
                    date_str = msg['date'].strftime("%Y-%m-%d %H:%M")
                    # Truncate long messages
                    truncated_text = msg['text'][:100] + ("..." if len(
                        msg['text']) > 100 else "")
                    result += f"{i}. [{date_str}] {truncated_text}\n\n"

                if len(filtered_messages) > 20:
                    result += f"... and {len(filtered_messages) - 20} more messages."

                await update.message.reply_text(result)
            else:
                await update.message.reply_text(
                    f"No messages related to '{topic}' were found.")
        else:
            await update.message.reply_text("No messages found in the channel."
                                            )
    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        await update.message.reply_text(f"Error retrieving messages: {str(e)}")


# Command to help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Here are the commands you can use:\n\n"
        "/start - Start the bot\n"
        "/help - Get help\n"
        "/setchannel @channelname - Set the channel to retrieve messages from\n"
        "/settopic topic - Set your topic of interest\n"
        "/get [limit] - Get messages (optionally specify how many)\n\n"
        "Example workflow:\n"
        "1. /setchannel @channelname\n"
        "2. /settopic technology\n"
        "3. /get 50")
    await update.message.reply_text(help_text)


async def main():
    global client

    # Log bot initialization with masked token
    masked_token = BOT_TOKEN[:4] + '*' * (len(BOT_TOKEN) - 8) + BOT_TOKEN[-4:] if BOT_TOKEN else None
    logger.info(f"Initializing Telegram Bot with token: {masked_token}")

    # Initialize the Telegram Bot
    application = Application.builder().token(BOT_TOKEN).build()
    logger.info("Telegram Bot application built successfully")

    # Add command handlers
    logger.info("Registering command handlers...")
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setchannel", set_channel_command))
    application.add_handler(CommandHandler("settopic", set_topic_command))
    application.add_handler(CommandHandler("get", get_messages_command))
    logger.info("Command handlers registered successfully")

    # Initialize Telethon client
    logger.info("Starting Telethon client authentication")
    try:
        # Log session string existence (masked for security)
        session_exists = "Available" if SESSION_STRING else "Not available"
        logger.info(f"Telethon session string: {session_exists}")

        # Only attempt to initialize if we have valid credentials
        if API_ID != 0 and API_HASH and SESSION_STRING:
            logger.info(f"Initializing Telethon client with API_ID: {API_ID}")
            # Clean the session string (remove quotes if present)
            clean_session = SESSION_STRING.strip().strip('"\'')
            client = TelegramClient(StringSession(clean_session), API_ID, API_HASH)

            logger.info("Connecting to Telegram servers...")
            await client.connect()

            logger.info("Checking authorization status...")
            if not await client.is_user_authorized():
                logger.warning("Telethon client is not authorized. Using a valid SESSION_STRING env variable is recommended.")
            else:
                logger.info("Telethon client successfully authorized")
        else:
            logger.warning("Missing Telegram API credentials. Channel message retrieval will not work.")
    except Exception as e:
        logger.error(f"Error initializing Telethon client: {e}")

    # Start the Bot in webhook mode
    await application.initialize()
    await application.start()

    # Use webhook instead of polling for Cloud Run deployments
    await application.updater.start_webhook(
        listen="0.0.0.0",  # Listen on all network interfaces
        port=8080,         # Standard port for Cloud Run
        webhook_url=None,  # Let Telegram use the URL it receives requests from
        allowed_updates=Update.ALL_TYPES
    )

    logger.info(f"Bot started and listening on port 8080")

    # Keep the application running
    try:
        # In webhook mode, we need to keep the application running
        while True:
            await asyncio.sleep(3600)  # Just keep the bot running
    except (KeyboardInterrupt, SystemExit):
        # Graceful shutdown
        if client:
            await client.disconnect()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())