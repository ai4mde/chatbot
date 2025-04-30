from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional
from uuid import UUID, uuid4
import logging
from datetime import datetime
import time
from redis import Redis
from redis.exceptions import TimeoutError, ConnectionError
import json
import uuid

# Local imports
from app.api import deps
from app.models.user import User
from app.models.chat import (
    ChatSession,
    ChatMessage,
    ChatRole,
    ChatState,
    ConversationState,
)
from app.schemas.chat import (
    ChatSession as ChatSessionSchema,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatMessage as ChatMessageSchema,
    ChatMessageCreate,
    ChatResponse,
)
from app.services.chat.chat_manager import LangChainChatManager
from openai import OpenAIError
from app.core.config import settings
from app.models.group import Group

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions", response_model=ChatSessionSchema)
async def create_chat_session(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    chat_session: ChatSessionCreate,
) -> Any:
    """Create new chat session"""
    try:
        # Create chat session
        current_time = datetime.utcnow()
        chat_session_data = chat_session.model_dump()
        chat_session_data["user_id"] = current_user.id
        chat_session_data["group_id"] = current_user.group_id
        chat_session_data["state"] = "active"
        chat_session_data["created_at"] = current_time
        chat_session_data["updated_at"] = current_time

        db_chat_session = ChatSession(**chat_session_data)
        db.add(db_chat_session)
        await db.commit()
        await db.refresh(db_chat_session)

        # Create initial chat state
        chat_state = ChatState(
            session_id=db_chat_session.id,
            current_section=0,
            current_question_index=0,
            state=ConversationState.INTERVIEW,
            progress=0.0,
            updated_at=current_time,
        )
        db.add(chat_state)
        await db.commit()

        # Store user info in Redis for the session
        try:
            redis_client = Redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                socket_timeout=settings.REDIS_TIMEOUT,
                socket_connect_timeout=settings.REDIS_TIMEOUT,
            )

            # Get the user's group name (should be eagerly loaded)
            group_name = None
            if hasattr(current_user, "group") and current_user.group:
                group_name = current_user.group.name

            if not group_name:
                await db.rollback()
                raise ValueError(
                    f"User {current_user.username} does not have a group assigned."
                )

            # Add group_name to user_info
            user_info = {
                "name": current_user.username,
                "id": current_user.id,
                "group_name": group_name,
            }

            # Log the user info being saved
            logger.info(
                f"Setting initial user info in Redis for session {db_chat_session.id}: {user_info}"
            )

            # Save to Redis (Redis client itself is synchronous here)
            redis_client.set(
                f"interview:user_info_{db_chat_session.id}",
                json.dumps(user_info),
                ex=settings.REDIS_DATA_TTL,
            )
            redis_client.set(
                f"user_info:{db_chat_session.id}",
                json.dumps(user_info),
                ex=settings.REDIS_DATA_TTL,
            )
        except ValueError as ve:
            # Handle the specific group not found error
            logger.error(
                f"User group configuration error for session {db_chat_session.id}: {str(ve)}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except Exception as e:
            # Rollback the session creation if we can't store user info
            await db.rollback()
            logger.error(
                f"Could not store user info in Redis for session {db_chat_session.id}: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not create chat session due to Redis error: {str(e)}",
            )

        return db_chat_session
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating chat session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create chat session: {str(e)}",
        )


@router.get("/sessions", response_model=List[ChatSessionSchema])
async def get_chat_sessions(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 10,
) -> Any:
    """
    Retrieve user's chat sessions.
    """
    try:
        logger.info(f"Fetching sessions for user {current_user.id}")

        # Use SQLAlchemy 2.0 select syntax
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        # Verify that datetime fields are not None
        for session in sessions:
            if session.created_at is None:
                session.created_at = datetime.utcnow()
            if session.updated_at is None:
                session.updated_at = datetime.utcnow()

        logger.info(f"Successfully fetched {len(sessions)} sessions")
        return sessions

    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat sessions: {str(e)}",
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionSchema)
async def get_chat_session(
    session_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get a specific chat session.
    """
    stmt = select(ChatSession).where(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    )
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def create_message(
    *,
    session_id: int,
    message_in: ChatMessageCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a message in a chat session and get AI response.
    """
    try:
        logger.info(f"Processing message for session {session_id}")

        # Verify session exists and belongs to user
        stmt_session = select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        )
        result_session = await db.execute(stmt_session)
        session = result_session.scalars().first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        # Store user info in Redis for the session
        redis_client = Redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
        )

        # Get the user's group name (should be eagerly loaded)
        group_name = None
        if hasattr(current_user, "group") and current_user.group:
            group_name = current_user.group.name

        if not group_name:
            raise ValueError(
                f"User {current_user.username} does not have a group assigned."
            )

        # Add group_name to user_info
        user_info = {
            "name": current_user.username,
            "id": current_user.id,
            "group_name": group_name,
        }

        # Log the user info being saved
        logger.info(f"Saving user info to Redis for session {session_id}: {user_info}")

        # Save to Redis
        redis_client.set(
            f"interview:user_info_{session_id}",
            json.dumps(user_info),
            ex=settings.REDIS_DATA_TTL,
        )

        # Also save user info with the standard key format used by other agents
        redis_client.set(
            f"user_info:{session_id}", json.dumps(user_info), ex=settings.REDIS_DATA_TTL
        )

        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            role=ChatRole.USER,
            content=message_in.content,
            message_uuid=message_in.message_uuid,
        )
        db.add(user_message)
        await db.commit()

        # Initialize LangChain chat manager
        chat_manager = LangChainChatManager(str(session_id), current_user.username)

        # Get AI response
        ai_response = await chat_manager.process_message(message_in.content)

        # Get interview progress
        progress = None
        if hasattr(chat_manager.interview_agent, "calculate_progress"):
            progress = chat_manager.interview_agent.calculate_progress()

        # Save AI response
        ai_message_uuid = uuid4()
        ai_message = ChatMessage(
            session_id=session_id,
            role=ChatRole.ASSISTANT,
            content=ai_response,
            message_uuid=ai_message_uuid,
        )
        db.add(ai_message)
        await db.commit()

        return ChatResponse(
            message=ai_response,
            session_id=session_id,
            message_uuid=str(ai_message_uuid),
            progress=progress,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Could not process message: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a chat session and its associated Redis data.
    """
    try:
        # Find the session
        stmt_session = select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        )
        result_session = await db.execute(stmt_session)
        session = result_session.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Delete chat messages
        stmt_del_msgs = delete(ChatMessage).where(ChatMessage.session_id == session_id)
        await db.execute(stmt_del_msgs)

        # Delete chat state
        stmt_del_state = delete(ChatState).where(ChatState.session_id == session_id)
        await db.execute(stmt_del_state)

        # Clean up Redis data
        redis_keys = [
            f"interview_state_{session_id}",
            f"interview:interview_{session_id}",
            f"document:document_{session_id}",
            f"interview:user_info_{session_id}",
        ]

        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        redis_client = Redis.from_url(
            redis_url,
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
        )

        # Delete Redis keys with retry logic
        for key in redis_keys:
            for attempt in range(settings.REDIS_RETRY_ATTEMPTS):
                try:
                    redis_client.delete(key)
                    break
                except (TimeoutError, ConnectionError) as e:
                    if attempt == settings.REDIS_RETRY_ATTEMPTS - 1:
                        logger.error(f"Failed to delete Redis key {key}: {str(e)}")
                        raise
                    time.sleep(settings.REDIS_RETRY_DELAY)

        # Delete the session
        await db.delete(session)
        await db.commit()

        return {"message": "Chat session and associated data deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Could not delete chat session: {str(e)}"
        )


@router.put("/sessions/{session_id}", response_model=ChatSessionSchema)
async def update_chat_session(
    *,
    session_id: int,
    session_update: ChatSessionUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a chat session's title.
    """
    try:
        session = select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        )
        result = await db.execute(session)
        session = result.scalars().first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        session.title = session_update.title
        session.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(session)
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Could not update chat session: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageSchema])
async def get_chat_messages(
    session_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    try:
        logger.info(f"Getting messages for session {session_id}")

        # Verify session exists and belongs to user
        stmt_session = select(ChatSession.id).where(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        )
        result_session = await db.execute(stmt_session)
        if not result_session.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        # Update user info in Redis with group name
        redis_client = Redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
        )

        # Get the user's group name (should be eagerly loaded)
        group_name = None
        if hasattr(current_user, "group") and current_user.group:
            group_name = current_user.group.name

        if not group_name:
            raise ValueError(
                f"User {current_user.username} does not have a group assigned"
            )

        # Add group_name to user_info
        user_info = {
            "name": current_user.username,
            "id": current_user.id,
            "group_name": group_name,
        }

        # Log the user info being saved
        logger.info(
            f"Updating user info in Redis for session {session_id}: {user_info}"
        )

        # Save to Redis with both key formats
        redis_client.set(
            f"interview:user_info_{session_id}",
            json.dumps(user_info),
            ex=settings.REDIS_DATA_TTL,
        )
        redis_client.set(
            f"user_info:{session_id}", json.dumps(user_info), ex=settings.REDIS_DATA_TTL
        )

        # Initialize chat manager and get current progress
        chat_manager = LangChainChatManager(str(session_id), current_user.username)
        current_progress = chat_manager.interview_agent.calculate_progress()
        logger.info(f"Current progress: {current_progress}%")

        messages = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result_msgs = await db.execute(messages)
        messages = result_msgs.scalars().all()

        # Find last assistant message
        last_assistant_msg = next(
            (msg for msg in reversed(messages) if msg.role == ChatRole.ASSISTANT), None
        )

        # Convert to response format
        message_list = []
        for message in messages:
            message_dict = message.__dict__.copy()
            message_dict["message_uuid"] = str(message.message_uuid)

            # Add progress to last assistant message
            if message == last_assistant_msg:
                message_dict["progress"] = current_progress
                logger.info(
                    f"Adding progress {current_progress}% to message {message.id}"
                )

            message_list.append(message_dict)

        return message_list

    except Exception as e:
        logger.error(f"Error retrieving chat messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_message(
    session_id: int,
    message_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a specific message from a chat session.
    """
    try:
        # Verify session exists and belongs to user
        stmt_session = select(ChatSession.id).where(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        )
        result_session = await db.execute(stmt_session)
        if not result_session.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        # Find and delete the message
        stmt_del = delete(ChatMessage).where(
            ChatMessage.id == message_id, ChatMessage.session_id == session_id
        )
        result = await db.execute(stmt_del)

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Message not found")

        await db.commit()
        return {"message": "Message deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Could not delete message: {str(e)}"
        )


@router.get("/search", response_model=List[ChatMessageSchema])
async def search_messages(
    query: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """
    Search through all messages in user's chat sessions.
    """
    try:
        messages = (
            select(ChatMessage)
            .join(ChatSession)
            .filter(
                ChatSession.user_id == current_user.id,
                or_(
                    ChatMessage.content.ilike(f"%{query}%"),
                    ChatSession.title.ilike(f"%{query}%"),
                ),
            )
            .order_by(ChatMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(messages)
        messages = result.scalars().all()
        return messages
    except Exception as e:
        logger.error(f"Error searching messages: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Could not search messages: {str(e)}"
        )


async def get_ai_response(content: str) -> str:
    """
    Get AI response for a message.
    This is a simplified version used by the /send endpoint.

    Args:
        content: The message content

    Returns:
        The AI response
    """
    try:
        # Use OpenAI API directly for simple responses
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.AGENT_SMITH_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": content},
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error getting AI response: {str(e)}")
        raise


@router.post("/send", response_model=ChatResponse)
async def send_message(
    *,
    db: AsyncSession = Depends(deps.get_db),
    message_in: ChatMessageCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a message and get AI response.
    """
    try:
        logger.info(f"Processing message for session {message_in.session_id}")

        # Save user message
        user_message = ChatMessage(
            content=message_in.content,
            session_id=message_in.session_id,
            role="user",
            message_uuid=message_in.message_uuid,
        )
        db.add(user_message)
        await db.commit()

        # Get AI response
        try:
            ai_response = await get_ai_response(message_in.content)
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting AI response: {str(e)}",
            )

        # Save AI response
        ai_message = ChatMessage(
            content=ai_response,
            session_id=message_in.session_id,
            role="assistant",
            message_uuid=str(uuid.uuid4()),
        )
        db.add(ai_message)
        await db.commit()

        return {
            "message": ai_response,
            "session_id": message_in.session_id,
            "message_uuid": ai_message.message_uuid,
        }

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
