import os
import json
import time
import logging
import datetime
import schedule
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot token for the Telegram Bot API
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Store user preferences
user_preferences = {}
# Store channel messages
channel_messages = {}

# Command handler for /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm a Telegram recap bot. I can provide daily summaries of messages from public channels.\n\n"
        "To get started, use the /setchannel command to tell me which channel to monitor.\n"
        "Example: /setchannel @channelname\n\n"
        "Then, use /settopic to specify what topics you're interested in.\n"
        "Example: /settopic technology"
    )

# Command handler for setting channel
async def set_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Please provide a channel username.\nExample: /setchannel @channelname")
        return

    channel_username = context.args[0]

    # Initialize user preferences if not exists
    if user_id not in user_preferences:
        user_preferences[user_id] = {'channel': None, 'topic': None}

    # Store the channel preference
    user_preferences[user_id]['channel'] = channel_username
    await update.message.reply_text(f"I'll now monitor {channel_username} for messages.")

# Command handler for setting topic
async def set_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Please provide a topic.\nExample: /settopic technology")
        return

    topic = ' '.join(context.args)

    # Initialize user preferences if not exists
    if user_id not in user_preferences:
        user_preferences[user_id] = {'channel': None, 'topic': None}

    user_preferences[user_id]['topic'] = topic
    await update.message.reply_text(f"I'll filter messages related to '{topic}'.")

# Function to fetch messages from a channel
async def fetch_channel_messages(bot: Bot, channel_username: str):
    try:
        # Get chat information
        chat = await bot.get_chat(channel_username)

        # Get last 100 messages from the channel
        messages = []
        today = datetime.datetime.now().date()
        async for message in bot.get_chat_history(chat.id, limit=100):
            message_date = message.date.date()
            if message_date == today and message.text:
                messages.append({
                    'date': message_date,
                    'text': message.text
                })

        return messages
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []

# Command to get recap immediately
async def recap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_preferences or not user_preferences[user_id]['channel']:
        await update.message.reply_text("Please set a channel first using /setchannel @channelname")
        return

    channel = user_preferences[user_id]['channel']
    topic = user_preferences[user_id]['topic']

    await update.message.reply_text(f"Generating recap for {channel} on topic '{topic}'...")

    try:
        # Fetch messages from the channel
        bot = context.bot
        messages = await fetch_channel_messages(bot, channel)

        if messages:
            # Filter messages by topic if specified
            if topic:
                filtered_messages = [msg for msg in messages if topic.lower() in msg['text'].lower()]
            else:
                filtered_messages = messages

            if filtered_messages:
                recap = "Today's recap:\n\n"
                for i, msg in enumerate(filtered_messages, 1):
                    # Truncate long messages
                    truncated_text = msg['text'][:100] + ("..." if len(msg['text']) > 100 else "")
                    recap += f"{i}. {truncated_text}\n\n"

                await update.message.reply_text(recap)
            else:
                await update.message.reply_text(f"No messages related to '{topic}' were found today.")
        else:
            await update.message.reply_text("No messages found for today.")
    except Exception as e:
        logger.error(f"Error in recap: {e}")
        await update.message.reply_text(f"Error generating recap: {str(e)}")

# Function to send daily recaps to all users
async def send_daily_recaps(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    for user_id, prefs in user_preferences.items():
        if prefs['channel']:
            channel = prefs['channel']
            topic = prefs['topic']

            try:
                messages = await fetch_channel_messages(bot, channel)

                if messages:
                    # Filter messages by topic if specified
                    if topic:
                        filtered_messages = [msg for msg in messages if topic.lower() in msg['text'].lower()]
                    else:
                        filtered_messages = messages

                    if filtered_messages:
                        recap = f"Daily recap for {channel}:\n\n"
                        for i, msg in enumerate(filtered_messages, 1):
                            # Truncate long messages
                            truncated_text = msg['text'][:100] + ("..." if len(msg['text']) > 100 else "")
                            recap += f"{i}. {truncated_text}\n\n"

                        await context.bot.send_message(chat_id=user_id, text=recap)
                    else:
                        await context.bot.send_message(
                            chat_id=user_id, 
                            text=f"No messages related to '{topic}' were found today in {channel}."
                        )
                else:
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text=f"No messages found today in {channel}."
                    )
            except Exception as e:
                logger.error(f"Error in daily recap for user {user_id}: {e}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Error generating daily recap: {str(e)}"
                )

# Command to help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Here are the commands you can use:\n\n"
        "/start - Start the bot\n"
        "/help - Get help\n"
        "/setchannel @channelname - Set the channel to monitor\n"
        "/settopic topic - Set your topic of interest\n"
        "/recap - Get an immediate recap\n\n"
        "I'll also send you daily recaps automatically!"
    )
    await update.message.reply_text(help_text)

async def main():
    # Initialize the Telegram Bot
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setchannel", set_channel_command))
    application.add_handler(CommandHandler("settopic", set_topic_command))
    application.add_handler(CommandHandler("recap", recap_command))

    # Schedule daily recap
    job_queue = application.job_queue
    job_queue.run_daily(
        send_daily_recaps, 
        time=datetime.time(hour=20, minute=0, second=0)  # Send recap at 8:00 PM daily
    )

    # Start the Bot
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())