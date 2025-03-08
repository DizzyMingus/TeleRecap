import re
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest
import os
import logging
import asyncio
from dotenv import load_dotenv
from datetime import datetime, timezone
from rag import create_rag_graph  # Import RAG functionality

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

async def fetch_messages_with_user(channel_username, limit=20, from_date=None, to_date=None, for_rag=False):
    """
    Fetch messages from a specific channel using the user client
    
    Args:
        channel_username: The username of the channel
        limit: Maximum number of messages to fetch (used in count mode)
        from_date: Start date for message filtering (in date mode)
        to_date: End date for message filtering (in date mode)
        for_rag: Whether to return raw messages for RAG processing
    """
    try:
        # Make sure the user client is connected
        if not user_client.is_connected():
            await user_client.connect()

        # Get the channel entity
        chat = await user_client.get_entity(channel_username)
        
        # Initialize variables for message retrieval
        all_messages = []
        offset_id = 0
        limit_per_request = 100  # Telegram API limitation
        total_messages = 0
        date_filter_active = from_date is not None
        
        # If using date filtering, we need to continue fetching until we've covered the date range
        while True:
            # Retrieve messages using the user client
            history = await user_client(GetHistoryRequest(
                peer=chat,
                limit=limit_per_request,
                offset_date=to_date if date_filter_active else None,
                offset_id=offset_id,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            if not history.messages:
                break
                
            messages = history.messages
            
            for message in messages:
                # Apply date filtering if active
                if date_filter_active:
                    message_date = message.date
                    if from_date and message_date < from_date:
                        # We've gone past the from_date, we can stop fetching
                        break
                    if to_date and message_date > to_date:
                        # Skip messages newer than to_date
                        continue
                
                if message.message:  # Only include messages with text
                    all_messages.append(message)
                    total_messages += 1
            
            # Update offset for next iteration
            offset_id = messages[-1].id
            
            # Stop if we've reached the requested limit in count mode
            if not date_filter_active and total_messages >= limit:
                all_messages = all_messages[:limit]  # Trim to exactly the requested limit
                break
                
            # If we're in date mode and we've gone past the from_date, we can stop
            if date_filter_active and from_date and messages[-1].date < from_date:
                break
                
            # Also stop if we got fewer messages than requested (end of history)
            if len(messages) < limit_per_request:
                break

        # Format messages based on whether they're for RAG or display
        if for_rag:
            # Return raw message text for RAG processing
            raw_messages = []
            for message in all_messages:
                if message.message:  # Only include messages with text
                    raw_messages.append(message.message)
            return raw_messages
        else:
            # Format messages into a readable string for display
            result = []
            for message in all_messages:
                if message.message:  # Only include messages with text
                    result.append(f"ID: {message.id}, Date: {message.date}\n{message.message}\n")
            return "\n".join(result) if result else "No messages found."

    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return f"Error fetching messages: {e}" if not for_rag else []

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handle the /start command"""
    await event.respond("👋 Hello! I can retrieve messages from every Telegram channel.\n\n"
                        "Use one of the following commands:\n\n"
                        "1️⃣ Fetch by message count:\n"
                        "/fetch @channel count [number]\n"
                        "Example: /fetch @durov count 5\n\n"
                        "2️⃣ Fetch by date range:\n"
                        "/fetch @channel date [from_date] [to_date]\n"
                        "Example: /fetch @durov date 2023-01-01 2023-01-31\n"
                        "Date format: YYYY-MM-DD\n\n"
                        "3️⃣ Use RAG with fetched messages:\n"
                        "/rag @channel [count/date] [...parameters] [query]\n"
                        "Example for count: /rag @durov count 20 What are Pavel's thoughts on AI?\n"
                        "Example for date: /rag @durov date 2023-01-01 2023-01-31 What topics were discussed?")

@bot.on(events.NewMessage(pattern='/fetch'))
async def fetch_handler(event):
    """Handle the /fetch command"""
    try:
        # Parse the command arguments
        args = event.message.message.split()

        if len(args) < 2:
            await event.respond("Please provide a channel username.\n"
                               "Example: /fetch @channel-id count 10")
            return

        channel = args[1]
        if not channel.startswith('@'):
            channel = '@' + channel
            
        # Check if enough arguments are provided
        if len(args) < 3:
            await event.respond("Please specify fetch mode (count or date).\n"
                              "Examples:\n"
                              "/fetch @channel count 10\n"
                              "/fetch @channel date 2023-01-01 2023-01-31")
            return
            
        fetch_mode = args[2].lower()
        
        if fetch_mode == "count":
            # Count-based fetching
            if len(args) < 4 or not args[3].isdigit():
                await event.respond("Please provide a valid number for count mode.\n"
                                   "Example: /fetch @channel count 10")
                return
                
            limit = min(int(args[3]), 100)  # Cap at 100 to avoid large responses
            await event.respond(f"Fetching up to {limit} messages from {channel}...")
            
            # Fetch the messages using the user client
            messages = await fetch_messages_with_user(channel, limit=limit)
            
        elif fetch_mode == "date":
            # Date-based fetching
            if len(args) < 5:
                await event.respond("Please provide both from_date and to_date for date mode.\n"
                                   "Example: /fetch @channel date 2023-01-01 2023-01-31\n"
                                   "Date format: YYYY-MM-DD")
                return
                
            try:
                from_date = datetime.strptime(args[3], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                to_date = datetime.strptime(args[4], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
                # Ensure to_date is end of day
                to_date = to_date.replace(hour=23, minute=59, second=59)
                
                await event.respond(f"Fetching messages from {channel} between {args[3]} and {args[4]}...")
                
                # Fetch the messages using date range
                messages = await fetch_messages_with_user(channel, from_date=from_date, to_date=to_date)
                
            except ValueError:
                await event.respond("Invalid date format. Please use YYYY-MM-DD format.\n"
                                   "Example: /fetch @channel date 2023-01-01 2023-01-31")
                return
        else:
            await event.respond("Invalid fetch mode. Please use 'count' or 'date'.\n"
                              "Examples:\n"
                              "/fetch @channel count 10\n"
                              "/fetch @channel date 2023-01-01 2023-01-31")
            return

        # Send messages in chunks due to Telegram message size limits
        max_length = 4000
        if len(messages) <= max_length:
            await event.respond(messages if messages else "No messages to display.")
        else:
            for i in range(0, len(messages), max_length):
                chunk = messages[i:i+max_length]
                await event.respond(chunk)

    except Exception as e:
        logger.error(f"Error in fetch handler: {e}")
        await event.respond(f"Error: {str(e)}")

@bot.on(events.NewMessage(pattern=r'^@'))
async def rag_handler(event):
    """Handle messages in the format @<channel_name> [prompt]"""
    try:
        args = event.message.message.split()


        if len(args) < 2:
            await event.respond("Invalid format. Please use: @channel_name [your prompt]")
            return 

        channel_name = args[0]
        prompt = " ".join(args[1:])
    
        limit = 100  # Cap at 100 to avoid large responses
        
        await event.respond(f"Fetching up to {limit} messages from {channel_name} and processing your query: '{prompt}'...")
        
        # Fetch raw messages for RAG
        raw_messages = await fetch_messages_with_user(channel_name, limit=100, for_rag=True)
            
        # Check if we have any messages to process
        if not raw_messages:
            await event.respond("No messages found to process with RAG.")
            return
            
        # Process the messages with RAG
        await event.respond("Processing your query with RAG. Please wait...")

        rag_graph = create_rag_graph()
        rag_response = rag_graph.invoke({"retrieved_documents": raw_messages, "query": prompt})

        output_response = rag_response["response"]

        # Send the RAG response
        await event.respond(f"RAG Response for query '{prompt}':\n\n{output_response}")

    except Exception as e:
        logger.error(f"Error in RAG handler: {e}")
        await event.respond(f"Error processing with RAG: {str(e)}")

@bot.on(events.NewMessage(pattern='/rag'))
async def rag_handler_old(event):
    """Handle the /rag command to fetch messages and process them with RAG"""
    try:
        # Parse the command arguments
        args = event.message.message.split()

        if len(args) < 2:
            await event.respond("Please provide a channel username.\n"
                               "Example: /rag @channel-id count 10 your query here")
            return

        channel = args[1]
        if not channel.startswith('@'):
            channel = '@' + channel
            
        # Check if enough arguments are provided
        if len(args) < 3:
            await event.respond("Please specify fetch mode (count or date).\n"
                              "Examples:\n"
                              "/rag @channel count 10 your query here\n"
                              "/rag @channel date 2023-01-01 2023-01-31 your query here")
            return
            
        fetch_mode = args[2].lower()
        
        # Extract RAG query from the command
        query = ""
        
        if fetch_mode == "count":
            # Count-based fetching
            if len(args) < 4 or not args[3].isdigit():
                await event.respond("Please provide a valid number for count mode.\n"
                                   "Example: /rag @channel count 10 your query here")
                return
                
            limit = min(int(args[3]), 100)  # Cap at 100 to avoid large responses
            
            if len(args) < 5:
                await event.respond("Please provide a query for RAG processing.\n"
                                  "Example: /rag @channel count 10 your query here")
                return
                
            query = " ".join(args[4:])
            await event.respond(f"Fetching up to {limit} messages from {channel} and processing your query: '{query}'...")
            
            # Fetch raw messages for RAG
            raw_messages = await fetch_messages_with_user(channel, limit=limit, for_rag=True)
            
        elif fetch_mode == "date":
            # Date-based fetching
            if len(args) < 5:
                await event.respond("Please provide both from_date and to_date for date mode.\n"
                                   "Example: /rag @channel date 2023-01-01 2023-01-31 your query here")
                return
                
            try:
                from_date = datetime.strptime(args[3], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                to_date = datetime.strptime(args[4], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
                # Ensure to_date is end of day
                to_date = to_date.replace(hour=23, minute=59, second=59)
                
                if len(args) < 6:
                    await event.respond("Please provide a query for RAG processing.\n"
                                      "Example: /rag @channel date 2023-01-01 2023-01-31 your query here")
                    return
                
                query = " ".join(args[5:])
                await event.respond(f"Fetching messages from {channel} between {args[3]} and {args[4]} and processing your query: '{query}'...")
                
                # Fetch raw messages for RAG
                raw_messages = await fetch_messages_with_user(channel, from_date=from_date, to_date=to_date, for_rag=True)
                
            except ValueError:
                await event.respond("Invalid date format. Please use YYYY-MM-DD format.\n"
                                   "Example: /rag @channel date 2023-01-01 2023-01-31 your query here")
                return
        else:
            await event.respond("Invalid fetch mode. Please use 'count' or 'date'.\n"
                              "Examples:\n"
                              "/rag @channel count 10 your query here\n"
                              "/rag @channel date 2023-01-01 2023-01-31 your query here")
            return

        # Check if we have any messages to process
        if not raw_messages:
            await event.respond("No messages found to process with RAG.")
            return
            
        # Process the messages with RAG
        await event.respond("Processing your query with RAG. Please wait...")

        rag_graph = create_rag_graph()
        rag_response = rag_graph.invoke({"retrieved_documents": raw_messages, "query": query})

        output_response = rag_response["response"]

        # Send the RAG response
        await event.respond(f"RAG Response for query '{query}':\n\n{output_response}")

    except Exception as e:
        logger.error(f"Error in RAG handler: {e}")
        await event.respond(f"Error processing with RAG: {str(e)}")

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
