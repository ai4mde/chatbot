"""
Script to save an interview session from Redis to a markdown file.
This is an alternative to get_chat.py that doesn't rely on the database.
"""

import os
import logging
import json
from datetime import datetime
import pytz
from typing import List, Dict, Any, Optional
import time

# Try to import RedisChatMessageHistory, but provide a fallback if it's not available
try:
    from langchain_community.chat_message_histories import RedisChatMessageHistory

    REDIS_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning(
        "langchain_community.chat_message_histories not available. Redis-based chat history will be disabled."
    )
    REDIS_AVAILABLE = False

    # Define a simple fallback class
    class FallbackChatMessageHistory:
        def __init__(self, *args, **kwargs):
            self.messages = []

        def add_message(self, message):
            self.messages.append(message)

        def clear(self):
            self.messages = []


from app.core.config import settings

logger = logging.getLogger(__name__)


async def save_interview_from_redis(
    session_id: str,
    username: str,
    chat_title: str,
    group_name: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Save an interview session from Redis to a markdown file.

    Args:
        session_id: The session ID of the interview
        username: The username of the user
        chat_title: The title of the chat session
        group_name: The name of the user's group (if None, will try to get from Redis)
        state: Optional state dictionary to use if Redis is not available

    Returns:
        A dictionary with the result of the operation
    """
    try:
        logger.info(
            f"Saving interview from Redis for session {session_id} with title {chat_title}"
        )

        # If group_name is not provided, try to get it from Redis
        if not group_name and username:
            try:
                # Import Redis
                from redis import Redis

                # Connect to Redis
                redis_client = Redis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                    socket_timeout=settings.REDIS_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_TIMEOUT,
                )

                # Get all keys for interview user info
                keys = redis_client.keys("interview:user_info_*")
                logger.info(f"Found {len(keys)} user info keys in Redis")

                # Check each key for the username
                for key in keys:
                    user_info_data = redis_client.get(key)
                    if user_info_data:
                        try:
                            user_info = json.loads(user_info_data)
                            if (
                                user_info.get("name") == username
                                and "group_name" in user_info
                            ):
                                group_name = user_info["group_name"]
                                logger.info(
                                    f"Found group name in Redis for user {username}: {group_name}"
                                )
                                break
                        except Exception as e:
                            logger.warning(
                                f"Error parsing Redis data for key {key}: {str(e)}"
                            )

                if not group_name:
                    logger.warning(f"Group name not found in Redis for user {username}")
                    # Fall back to database lookup
                    group_name = await get_user_group(username, redis_client)

            except Exception as e:
                logger.error(f"Error getting group name from Redis: {str(e)}")
                # Fall back to database lookup
                group_name = await get_user_group(username, None)

        # Ensure we have a group name
        if not group_name:
            error_msg = "Group name is required and could not be determined"
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "error": error_msg}

        logger.info(f"Using group name: {group_name} for user {username}")

        # Setup Redis client
        redis_url = (
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            f"?socket_timeout={settings.REDIS_TIMEOUT}"
            f"&socket_connect_timeout={settings.REDIS_TIMEOUT}"
        )

        # Initialize Redis client
        try:
            if not REDIS_AVAILABLE:
                raise ImportError("Redis chat history not available")

            message_history = RedisChatMessageHistory(
                session_id=f"interview_{session_id}",
                url=redis_url,
                key_prefix="interview:",
                ttl=settings.REDIS_DATA_TTL,
            )

            # Get messages from Redis
            messages = []
            for msg in message_history.messages:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    messages.append(
                        {
                            "role": msg.type,
                            "content": msg.content,
                            "timestamp": datetime.now(pytz.UTC).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        }
                    )

            # Get state data
            state_key = f"interview:state:{session_id}"
            state_data = message_history.redis_client.get(state_key)
            if state_data:
                state_data = json.loads(state_data)
                progress = state_data.get("progress", 0.0)
            else:
                progress = 0.0

            logger.info(
                f"Retrieved {len(messages)} messages from Redis with progress {progress:.1f}%"
            )

        except Exception as e:
            logger.warning(f"Error retrieving messages from Redis: {str(e)}")
            logger.info("Falling back to using provided state")

            # Fall back to using the provided state
            if not state:
                logger.error("No state provided for fallback")
                return {
                    "success": False,
                    "message": "Error saving interview document: No Redis connection and no state provided",
                    "error": str(e),
                }

            # Extract messages from state
            messages = []
            for msg in state.get("messages", []):
                messages.append(
                    {
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", ""),
                        "timestamp": datetime.now(pytz.UTC).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            # Get progress from state
            progress = state.get("progress", 0.0)
            logger.info(
                f"Using {len(messages)} messages from state with progress {progress:.1f}%"
            )

        # Create the interviews directory if it doesn't exist
        interviews_dir = os.path.join(
            settings.CHATBOT_DATA_PATH, group_name, "interviews"
        )
        logger.info(f"Creating interviews directory at: {interviews_dir}")
        os.makedirs(interviews_dir, exist_ok=True)

        # Define the output filename with timestamp
        timestamp = int(time.time())
        safe_chat_title = (
            chat_title.replace(" ", "_").replace("/", "_").replace("\\", "_")
        )
        output_filename = f"{safe_chat_title}-{timestamp}.md"
        file_path = os.path.join(interviews_dir, output_filename)
        logger.info(f"Target interview file path: {file_path}")

        # Create markdown content
        markdown_content = f"# Chat Session: {chat_title}\n\n"
        markdown_content += f"- **User**: {username}\n"
        markdown_content += f"- **Group**: {group_name}\n"
        markdown_content += (
            f"- **Created**: {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        markdown_content += f"- **Progress**: {progress:.1f}%\n"
        markdown_content += (
            f"- **Status**: {'Completed' if progress >= 100 else 'In Progress'}\n\n"
        )
        markdown_content += "## Messages\n\n"

        # Add messages to markdown content
        for message in messages:
            # Format the sender name
            if message["role"] in ["human", "user"]:
                sender = f"**{username}**"
            elif message["role"] in ["ai", "assistant"]:
                sender = f"**Assistant**"
            elif message["role"] == "system":
                sender = f"**System**"
            else:
                sender = f"**{message['role']}**"

            # Add the message to the markdown content
            markdown_content += f"### {sender} ({message['timestamp']})\n\n"
            markdown_content += f"{message['content']}\n\n"
            markdown_content += "---\n\n"

        # Write markdown content to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"Interview saved to {file_path}")

        return {
            "success": True,
            "message": f"Interview document saved successfully to {file_path}",
            "file_path": file_path,
        }
    except Exception as e:
        logger.error(f"Error saving interview document: {str(e)}")
        return {
            "success": False,
            "message": f"Error saving interview document: {str(e)}",
            "error": str(e),
        }


async def get_user_group(username: str, redis_client) -> str:
    """
    Get the user's group name from the database only.

    Args:
        username: The username of the user
        redis_client: Unused parameter, kept for backward compatibility

    Returns:
        The name of the user's group or 'default' if not found
    """
    try:
        # Import database models
        from sqlalchemy import select, create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings
        from app.models.user import User
        from app.models.group import Group

        logger.info(f"Querying database for user {username}'s group")

        # Create database engine
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # Query the user with their group relationship
            user_query = select(User).where(User.username == username)
            user = session.execute(user_query).scalar_one_or_none()

            if user:
                if user.group:
                    logger.info(
                        f"Found group for user {username} in database: {user.group.name}"
                    )
                    return user.group.name
                elif user.group_id:
                    # If group relationship not loaded but group_id exists
                    group_query = select(Group).where(Group.id == user.group_id)
                    group = session.execute(group_query).scalar_one_or_none()

                    if group:
                        logger.info(
                            f"Found group for user {username} in database via group_id: {group.name}"
                        )
                        return group.name

            logger.warning(
                f"User {username} not found in database or has no group assigned"
            )
            return "default"
    except Exception as e:
        logger.error(f"Error getting user group from database: {str(e)}")
        return "default"


async def get_chat_title_from_db(session_id: str, username: str) -> str:
    """
    Get the chat title from the database for the given session ID and username.

    Args:
        session_id: The session ID
        username: The username of the user

    Returns:
        The chat title from the database or a default title if not found
    """
    try:
        # Import database models
        from sqlalchemy import select, create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings
        from app.models.user import User
        from app.models.chat import ChatSession

        logger.info(
            f"Querying database for chat title for session {session_id} and user {username}"
        )

        # Create database engine
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # First get the user ID
            user_query = select(User).where(User.username == username)
            user = session.execute(user_query).scalar_one_or_none()

            if not user:
                logger.warning(f"User {username} not found in database")
                return f"Interview-{session_id}"

            # Query the chat session
            chat_query = select(ChatSession).where(ChatSession.id == int(session_id))
            chat = session.execute(chat_query).scalar_one_or_none()

            if chat:
                logger.info(f"Found chat title in database: {chat.title}")
                return chat.title

            logger.warning(f"Chat session {session_id} not found in database")
            return f"Interview-{session_id}"
    except Exception as e:
        logger.error(f"Error getting chat title from database: {str(e)}")
        return f"Interview-{session_id}"
