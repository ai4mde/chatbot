import logging
import json
from redis.exceptions import TimeoutError, ConnectionError
from langchain_community.chat_message_histories import RedisChatMessageHistory
from app.core.config import settings
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def get_user_info(session_id: str) -> Dict[str, Any]:
    """Get user info (including group name) from Redis."""
    # This function was moved from the deleted requirements_agent_graph.py
    try:
        # Setup Redis client
        redis_url = (
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            f"?socket_timeout={settings.REDIS_TIMEOUT}"
            f"&socket_connect_timeout={settings.REDIS_CONNECT_TIMEOUT}"  # Use connect timeout
        )

        # Initialize Redis client using a dummy key prefix for connection setup
        # We are not actually reading chat history here, just using it for the client
        # Consider creating a standalone Redis client utility later if needed.
        message_history = RedisChatMessageHistory(
            session_id=f"utility_lookup_{session_id}",  # Use a distinct session ID
            url=redis_url,
            key_prefix="utility:",  # Use a distinct prefix
            ttl=60,  # Short TTL as we don't need to persist this specific history
        )

        redis_client = message_history.redis_client

        # Try to get user info from the key used by InterviewAgentGraph/ChatManager
        user_info_key = f"user_info:{session_id}"  # Assume this is the key where user info is stored
        user_info_data = redis_client.get(user_info_key)

        if user_info_data:
            try:
                user_info = json.loads(user_info_data.decode("utf-8"))
                logger.info(
                    f"Found user info for session {session_id} in Redis key '{user_info_key}'"
                )
                # Ensure group_name exists, default if not
                if "group_name" not in user_info:
                    user_info["group_name"] = "default"
                    logger.warning(
                        f"'group_name' missing in user_info for session {session_id}, defaulting to 'default'."
                    )
                return user_info
            except json.JSONDecodeError:
                logger.error(
                    f"Failed to decode JSON for user_info key '{user_info_key}'"
                )
                return {"group_name": "default"}  # Default on decode error
            except Exception as e:
                logger.error(
                    f"Error processing user_info data for session {session_id}: {e}"
                )
                return {"group_name": "default"}  # Default on other processing errors

        logger.warning(
            f"No user info found in Redis key '{user_info_key}' for session {session_id}"
        )
        # Fallback: Try getting username if user_info wasn't found (less ideal)
        username_key = f"username:{session_id}"  # This key might not exist
        username_data = redis_client.get(username_key)
        if username_data:
            username = username_data.decode("utf-8")
            logger.warning(
                f"Found username '{username}' but no user_info object for session {session_id}. Returning default group."
            )
            return {"username": username, "group_name": "default"}

        # Final fallback if nothing is found
        logger.error(
            f"Could not retrieve any user info or username from Redis for session {session_id}"
        )
        return {"group_name": "default"}  # Return default group if nothing found

    except ConnectionError:
        logger.error(
            f"Redis connection error while getting user info for session {session_id}"
        )
        return {"group_name": "default"}
    except TimeoutError:
        logger.error(f"Redis timeout while getting user info for session {session_id}")
        return {"group_name": "default"}
    except Exception as e:
        logger.error(
            f"Unexpected error getting user info from Redis for session {session_id}: {str(e)}",
            exc_info=True,
        )
        return {"group_name": "default"}  # Default on any other error
