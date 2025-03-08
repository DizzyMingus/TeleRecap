"""
Telegram Username Resolver Tool

This module provides functionality to resolve a Telegram username from a user ID.
"""

import os
from typing import Optional
from telethon import TelegramClient
from dotenv import load_dotenv
from get_telegram_client import get_user_client
# Load environment variables
load_dotenv()

async def get_telegram_username(user_id: int) -> Optional[str]:
    """
    Resolves a Telegram username from a user ID.
    
    Args:
        user_id: The Telegram user ID to resolve
        
    Returns:
        The username as a string (without the @ symbol) if found, or None if not found or user has no username
        
    Raises:
        ValueError: If the user_id is invalid
        ConnectionError: If there's an issue connecting to Telegram
    """
    # Check if user_id is valid
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Invalid user ID provided")

    
    client = get_user_client()
    
    # Connect to Telegram
    await client.get_dialogs()

    # Get user entity
    user_entity = await client.get_entity(int(user_id))

    # Return the username
    return user_entity.username

# Synchronous wrapper for convenience
def get_telegram_username_sync(user_id: int) -> Optional[str]:
    """
    Synchronous wrapper for the get_telegram_username function.
    
    Args:
        user_id: The Telegram user ID to resolve
        
    Returns:
        The username as a string (without the @ symbol) if found, or None if not found or user has no username
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If there's no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(get_telegram_username(user_id)) 