
import os
import json
import time
import logging
import datetime
import schedule
from dotenv import load_dotenv
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tdlib
from tdlib import Client

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# TDLib client configuration
tdlib_parameters = {
    'api_id': int(os.getenv('TELEGRAM_API_ID')),
    'api_hash': os.getenv('TELEGRAM_API_HASH'),
    'database_directory': 'tdlib_db',
    'files_directory': 'tdlib_files',
    'use_message_database': True,
    'use_secret_chats': False,
    'system_language_code': 'en',
    'device_model': 'Server',
    'application_version': '1.0',
    'enable_storage_optimizer': True
}

# Bot token for the Telegram Bot API
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Store user preferences
user_preferences = {}
# Store channel messages
channel_messages = {}

# Initialize TDLib client
tdlib_client = Client()
tdlib_client.send({'@type': 'setTdlibParameters', 'parameters': tdlib_parameters})

# Function to handle TDLib authentication
async def tdlib_auth():
    while True:
        event = tdlib_client.receive(1.0)
        if not event:
            continue
            
        if event.get('@type') == 'updateAuthorizationState':
            auth_state = event['authorization_state']['@type']
            
            if auth_state == 'authorizationStateWaitPhoneNumber':
                phone = os.getenv('TELEGRAM_PHONE')
                tdlib_client.send({'@type': 'setAuthenticationPhoneNumber', 'phone_number': phone})
            
            elif auth_state == 'authorizationStateWaitCode':
                code = input('Enter verification code: ')
                tdlib_client.send({'@type': 'checkAuthenticationCode', 'code': code})
            
            elif auth_state == 'authorizationStateWaitPassword':
                password = os.getenv('TELEGRAM_PASSWORD')
                tdlib_client.send({'@type': 'checkAuthenticationPassword', 'password': password})
            
            elif auth_state == 'authorizationStateReady':
                logger.info("TDLib client authenticated successfully")
                return True

# Function to join a channel
async def join_channel(channel_username):
    try:
        # Search for the channel
        search_result = tdlib_client.send({
            '@type': 'searchPublicChat',
            'username': channel_username.replace('@', '')
        })
        
        if search_result and search_result.get('id'):
            channel_id = search_result['id']
            
            # Join the channel if not already a member
            tdlib_client.send({
                '@type': 'joinChat',
                'chat_id': channel_id
            })
            
            logger.info(f"Joined channel: {channel_username}")
            return channel_id
        else:
            logger.error(f"Channel not found: {channel_username}")
            return None
    except Exception as e:
        logger.error(f"Error joining channel: {e}")
        return None

# Function to fetch messages from a channel
async def fetch_channel_messages(channel_id):
    today = datetime.datetime.now().date()
    messages = []
    
    try:
        # Get chat history
        history = tdlib_client.send({
            '@type': 'getChatHistory',
            'chat_id': channel_id,
            'limit': 100,  # Fetch last 100 messages
            'from_message_id': 0,
            'offset': 0,
            'only_local': False
        })
        
        if history and 'messages' in history:
            for msg in history['messages']:
                # Check if message is from today
                msg_date = datetime.datetime.fromtimestamp(msg['date']).date()
                if msg_date == today and msg.get('content', {}).get('@type') == 'messageText':
                    messages.append({
                        'date': msg_date,
                        'text': msg['content']['text']['text']
                    })
        
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []

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
    
    # Join the channel
    channel_id = await join_channel(channel_username)
    
    if channel_id:
        user_preferences[user_id]['channel'] = channel_username
        await update.message.reply_text(f"I'll now monitor {channel_username} for messages.")
    else:
        await update.message.reply_text(f"I couldn't join {channel_username}. Please make sure it's a public channel and the username is correct.")

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

# Command to get recap immediately
async def recap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_preferences or not user_preferences[user_id]['channel']:
        await update.message.reply_text("Please set a channel first using /setchannel @channelname")
        return
    
    channel = user_preferences[user_id]['channel']
    topic = user_preferences[user_id]['topic']
    
    await update.message.reply_text(f"Generating recap for {channel} on topic '{topic}'...")
    
    # Search for the channel
    search_result = tdlib_client.send({
        '@type': 'searchPublicChat',
        'username': channel.replace('@', '')
    })
    
    if search_result and search_result.get('id'):
        channel_id = search_result['id']
        messages = await fetch_channel_messages(channel_id)
        
        if messages:
            # Filter messages by topic if specified
            if topic:
                filtered_messages = [msg for msg in messages if topic.lower() in msg['text'].lower()]
            else:
                filtered_messages = messages
            
            if filtered_messages:
                recap = "Today's recap:\n\n"
                for i, msg in enumerate(filtered_messages, 1):
                    recap += f"{i}. {msg['text'][:100]}...\n\n"
                
                await update.message.reply_text(recap)
            else:
                await update.message.reply_text(f"No messages related to '{topic}' were found today.")
        else:
            await update.message.reply_text("No messages found for today.")
    else:
        await update.message.reply_text(f"Could not find channel {channel}.")

# Function to send daily recaps to all users
async def send_daily_recaps(context: ContextTypes.DEFAULT_TYPE):
    for user_id, prefs in user_preferences.items():
        if prefs['channel']:
            channel = prefs['channel']
            topic = prefs['topic']
            
            # Search for the channel
            search_result = tdlib_client.send({
                '@type': 'searchPublicChat',
                'username': channel.replace('@', '')
            })
            
            if search_result and search_result.get('id'):
                channel_id = search_result['id']
                messages = await fetch_channel_messages(channel_id)
                
                if messages:
                    # Filter messages by topic if specified
                    if topic:
                        filtered_messages = [msg for msg in messages if topic.lower() in msg['text'].lower()]
                    else:
                        filtered_messages = messages
                    
                    if filtered_messages:
                        recap = f"Daily recap for {channel}:\n\n"
                        for i, msg in enumerate(filtered_messages, 1):
                            recap += f"{i}. {msg['text'][:100]}...\n\n"
                        
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
    # Authenticate TDLib client
    await tdlib_auth()
    
    # Initialize the Telegram Bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
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
