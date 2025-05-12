import os # Add missing import
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.srs_chat import SrsChatRequest, SrsChatResponse, Message as ChatMessageSchema, SrsChatHistoryResponse # Renamed to avoid conflict with local Message
from app.api import deps # For user authentication
from app.models.user import User # For type hinting current_user
from app.core.config import settings # For CHATBOT_DATA_PATH and OpenAI settings
from app.services.openai_service import OpenAIService # To interact with OpenAI
from app.services.chat.srs_chat_service import SRSChatService # Import the new service
from langchain_community.chat_message_histories import RedisChatMessageHistory 
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Optional, Literal
import logging # <-- Add missing import
import frontmatter # For parsing markdown frontmatter

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_srs_document_content(doc_id: str, group_name: str) -> Optional[str]:
    """Fetches the content of an SRS document based on doc_id and group_name."""
    if not group_name:
        logger.warning(f"No group_name provided for doc_id: {doc_id}")
        return None
    
    docs_dir = os.path.join(settings.CHATBOT_DATA_PATH, group_name, "srsdocs")
    logger.debug(f"Searching for doc_id '{doc_id}' in directory: {docs_dir}")

    if not os.path.isdir(docs_dir):
        logger.warning(f"SRS documents directory not found for group '{group_name}': {docs_dir}")
        return None

    try:
        for filename in os.listdir(docs_dir):
            if filename.endswith('.md'):
                file_path = os.path.join(docs_dir, filename)
                try:
                    post = frontmatter.load(file_path)
                    # Check frontmatter ID or filename (without .md extension)
                    document_identifier = post.metadata.get('id', filename[:-3])
                    
                    if document_identifier == doc_id:
                        logger.info(f"Found document '{doc_id}' at path: {file_path}")
                        return post.content
                except Exception as e:
                    logger.error(f"Error parsing frontmatter for file {file_path}: {e}", exc_info=True)
                    continue # Skip files that can't be parsed
        logger.warning(f"Document with doc_id '{doc_id}' not found in group '{group_name}\'s srsdocs.")
        return None
    except FileNotFoundError:
        logger.warning(f"Directory not found: {docs_dir}")
        return None
    except Exception as e:
        logger.error(f"Error reading documents in {docs_dir}: {e}", exc_info=True)
        return None

# Helper to initialize Redis history (similar to service, maybe refactor later)
def _initialize_redis_history_for_doc(doc_id: str) -> RedisChatMessageHistory:
    redis_session_id = f"srs_{doc_id}" 
    redis_url = settings.REDIS_URL or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
    try:
        history = RedisChatMessageHistory(
            session_id=redis_session_id,
            url=redis_url,
            key_prefix="srs_chat_history:",
            ttl=settings.REDIS_DATA_TTL
        )
        return history
    except Exception as e:
        logger.error(f"Failed to initialize Redis history for {redis_session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to chat history service."
        ) from e

@router.get("/history/{doc_id}", response_model=SrsChatHistoryResponse)
async def get_srs_chat_history(
    *, 
    doc_id: str,
    current_user: User = Depends(deps.get_current_active_user)
) -> SrsChatHistoryResponse:
    """Retrieves the chat history for a specific SRS document."""
    logger.info(f"User '{current_user.username}' requesting history for doc_id: {doc_id}")
    
    # Optional: Validate if the user/group has access to this doc_id if needed
    
    history_store = _initialize_redis_history_for_doc(doc_id)
    
    try:
        redis_messages = await history_store.aget_messages()
        logger.debug(f"Loaded {len(redis_messages)} messages from Redis history for {history_store.session_id}")
        
        # Convert LangChain messages to frontend schema format
        full_history_response: List[ChatMessageSchema] = []
        for msg in redis_messages:
            sender: Literal['user', 'agent'] = 'user' if isinstance(msg, HumanMessage) else 'agent'
            full_history_response.append(ChatMessageSchema(sender=sender, text=msg.content))
            
        return SrsChatHistoryResponse(full_history=full_history_response)
            
    except Exception as e:
        logger.error(f"Failed to load messages from Redis for {history_store.session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history."
        ) from e

@router.delete("/history/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_srs_chat_history(
    *,
    doc_id: str,
    current_user: User = Depends(deps.get_current_active_user)
):
    """Deletes the chat history for a specific SRS document."""
    logger.info(f"User '{current_user.username}' requesting to delete history for doc_id: {doc_id}")

    # Optional: Add validation here if only specific users/groups can delete history
    # for a given doc_id. For example, check if the doc_id belongs to the user's group.

    history_store = _initialize_redis_history_for_doc(doc_id)

    try:
        await history_store.aclear() # Asynchronously clear the history
        logger.info(f"Successfully deleted chat history from Redis for {history_store.session_id}")
        # Return with 204 No Content, which is handled by default if no response body is set
        return
    except Exception as e:
        logger.error(f"Failed to delete messages from Redis for {history_store.session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat history."
        ) from e

@router.post("/", response_model=SrsChatResponse)
async def handle_srs_chat(
    *,
    current_user: User = Depends(deps.get_current_active_user),
    chat_request: SrsChatRequest,
    # openai_service: OpenAIService = Depends(get_openai_service) # Example if using Depends
) -> SrsChatResponse:
    """
    Handles chat messages related to a specific SRS document.
    Requires user authentication.
    """
    logger.info(f"User '{current_user.username}' initiated SRS chat for doc_id: {chat_request.doc_id}")

    if not current_user.group or not current_user.group.name:
        logger.warning(f"User '{current_user.username}' has no group associated.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User group not found. Cannot determine SRS document context."
        )
    
    group_name = current_user.group.name
    doc_content = await get_srs_document_content(chat_request.doc_id, group_name)

    if doc_content is None:
        logger.warning(f"SRS document '{chat_request.doc_id}' not found for user '{current_user.username}' in group '{group_name}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SRS document with ID '{chat_request.doc_id}' not found."
        )

    # Instantiate services, passing doc_id to SRSChatService
    openai_service = OpenAIService()
    # Pass chat_request.doc_id to the service constructor
    srs_chat_service = SRSChatService(openai_service=openai_service, doc_id=chat_request.doc_id)

    try:
        # Call process_chat without history
        agent_response = await srs_chat_service.process_chat(
            # doc_id is now handled internally by the service instance
            group_name=current_user.group.name,
            user_message_text=chat_request.message
            # history is no longer passed
        )
    except HTTPException as e:
        # Log and re-raise HTTPExceptions (e.g., 404 for doc not found, 503 for OpenAI issues from service)
        logger.error(f"HTTPException in SRS chat for user '{current_user.username}', doc '{chat_request.doc_id}': {e.detail}")
        raise e
    except Exception as e:
        # Catch any other unexpected errors from the service layer
        logger.error(f"Unexpected error in SRS chat for user '{current_user.username}', doc '{chat_request.doc_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your chat request."
        )

    # Return the SrsChatResponse object directly from the service
    return agent_response 