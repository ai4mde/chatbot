"""
LangGraph-based implementation of the Diagram Agent.
This implementation uses LangGraph concepts for better state management
while maintaining the same API interface as the original DiagramAgent.
"""

from typing import Dict, List, Any, TypedDict, Optional, Annotated, Literal
import logging
import json
import os
from datetime import datetime
import httpx
import time
import asyncio
import yaml

# SQLAlchemy imports
from sqlalchemy import select, desc

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage

# FastAPI imports
from fastapi import HTTPException

# Redis imports
from redis.exceptions import TimeoutError, ConnectionError

# Tenacity for retries
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# Local imports
from app.core.config import settings
from app.services.chat.interview.save_interview import get_chat_title_from_db

logger = logging.getLogger(__name__)

# --- Helper Function for Prompt Loading (similar to other agents) ---
def _create_prompt_from_config(prompt_config: Dict) -> ChatPromptTemplate:
    """Creates a ChatPromptTemplate from a loaded YAML config dictionary."""
    messages = []
    for key, value in prompt_config.items():
        if key == 'system':
            messages.append(("system", value))
        elif key == 'human':
            messages.append(("human", value))
        elif key == 'ai':
            messages.append(("ai", value))
        elif key == 'history': # Handle the messages placeholder
            messages.append(MessagesPlaceholder(variable_name=value['variable_name']))
        else:
            logger.warning(f"Unknown prompt component type '{key}' in config")
    return ChatPromptTemplate.from_messages(messages)

# --- Prompt Loading Function ---
def load_diagram_prompts() -> Dict:
    """Loads diagram agent prompts from the YAML file."""
    prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'diagram_agent_prompt.yaml')
    try:
        with open(prompts_path, 'r') as f:
            prompts = yaml.safe_load(f)
        logger.info(f"Successfully loaded diagram prompts from {prompts_path}")
        return prompts
    except FileNotFoundError:
        logger.error(f"Diagram Agent Prompt file not found at {prompts_path}. Please create it.")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML prompt file {prompts_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading diagram prompts: {e}")
        raise

# Define the state schema
class DiagramState(TypedDict):
    """State for the diagram generation process."""
    session_id: str  # Session ID
    username: str  # Username
    group_name: str  # Group name
    messages: List[Dict[str, Any]]  # Input messages
    conversation_summary: Optional[str]  # Summarized conversation
    uml_content: Optional[str]  # Generated UML content
    diagram_files: Dict[str, str]  # Paths to saved diagram files
    missing_sections: List[str]  # Missing diagram sections
    error: Optional[str]  # Error message if any
    result: Optional[Dict[str, Any]]  # Final result
    chat_name: Optional[str]  # Name of the chat session
    user_info: Optional[Dict[str, Any]]  # User information

async def initialize_state(state: DiagramState) -> DiagramState:
    """Initialize the diagram state."""
    logger.info(f"Initializing diagram state for session {state['session_id']}")
    
    try:
        # Get user's group info from Redis
        user_info = await get_user_info(state['session_id'])
        state['group_name'] = user_info.get('group_name', 'default')
        
        # Initialize empty values
        state['conversation_summary'] = None
        state['uml_content'] = None
        state['diagram_files'] = {}
        state['missing_sections'] = []
        state['error'] = None
        state['result'] = None
        state['user_info'] = user_info
        
        logger.info(f"Initialized diagram state for session {state['session_id']}")
        return state
    except Exception as e:
        logger.error(f"Error initializing diagram state: {str(e)}")
        state['error'] = f"Failed to initialize diagram state: {str(e)}"
        return state

async def get_user_info(session_id: str) -> Dict[str, Any]:
    """Get user info from Redis."""
    try:
        # Setup Redis client
        redis_url = (
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            f"?socket_timeout={settings.REDIS_TIMEOUT}"
            f"&socket_connect_timeout={settings.REDIS_TIMEOUT}"
        )
        
        # Initialize Redis client
        message_history = RedisChatMessageHistory(
            session_id=f"diagram_{session_id}",
            url=redis_url,
            key_prefix="diagram:",
            ttl=settings.REDIS_DATA_TTL
        )
        
        # Get Redis client from message history
        redis_client = message_history.redis_client
        
        # Get user info from Redis
        user_info_key = f"user_info:{session_id}"
        user_info_data = redis_client.get(user_info_key)
        
        if user_info_data:
            return json.loads(user_info_data)
        else:
            logger.warning(f"No user info found for session {session_id}")
            return {'group_name': 'default'}
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return {'group_name': 'default'}

async def summarize_conversation(state: DiagramState) -> DiagramState:
    """Summarize the conversation for diagram generation."""
    logger.info(f"Summarizing conversation for session {state['session_id']}")
    
    try:
        # Load prompts
        prompts = load_diagram_prompts()
        summary_prompt_config = prompts.get('summarize_conversation_prompt')
        if not summary_prompt_config:
             logger.error("'summarize_conversation_prompt' not found in loaded YAML prompts.")
             raise ValueError("Missing conversation summary prompt configuration")
        
        # Create LLM for summarization
        summary_llm = ChatOpenAI(
            model_name=settings.AGENT_SUMMARY_MODEL,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
            request_timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES
        )
        
        # Extract messages
        messages = state['messages']
        
        # Prepare conversation text
        conversation_text = ""
        for msg in messages:
            # Handle both dictionary messages and LangChain message objects
            if isinstance(msg, dict):
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get('content', '')
            elif isinstance(msg, HumanMessage):
                role = "User"
                content = msg.content
            elif isinstance(msg, AIMessage):
                role = "Assistant"
                content = msg.content
            elif isinstance(msg, SystemMessage):
                role = "System"
                content = msg.content
            elif isinstance(msg, BaseMessage):
                role = msg.type
                content = msg.content
            else:
                logger.warning(f"Unknown message type: {type(msg)}")
                continue
                
            conversation_text += f"{role}: {content}\n\n"
        
        # Create prompt for summarization from YAML config
        prompt = _create_prompt_from_config(summary_prompt_config)
        
        # Create and invoke chain
        chain = prompt | summary_llm
        
        response = await chain.ainvoke({
            "conversation": conversation_text
        })
        
        # Update state with summary
        state['conversation_summary'] = response.content
        logger.info(f"Successfully summarized conversation for session {state['session_id']}")
        
        return state
    except Exception as e:
        logger.error(f"Error summarizing conversation: {str(e)}")
        state['error'] = f"Failed to summarize conversation: {str(e)}"
        return state

async def generate_uml_diagrams(state: DiagramState) -> DiagramState:
    """Generate UML diagrams based on the full conversation."""
    logger.info(f"Generating UML diagrams for session {state['session_id']} using full conversation")
    
    try:
        # Load prompts
        prompts = load_diagram_prompts()
        uml_prompt_config = prompts.get('generate_uml_prompt')
        if not uml_prompt_config:
             logger.error("'generate_uml_prompt' not found in loaded YAML prompts.")
             raise ValueError("Missing UML generation prompt configuration")

        # --- Prepare full conversation text --- 
        messages = state['messages']
        conversation_text = ""
        for msg in messages:
            if isinstance(msg, dict):
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get('content', '')
            elif isinstance(msg, HumanMessage):
                role = "User"
                content = msg.content
            elif isinstance(msg, AIMessage):
                role = "Assistant"
                content = msg.content
            elif isinstance(msg, SystemMessage):
                role = "System"
                content = msg.content
            elif isinstance(msg, BaseMessage):
                # Use the explicit type attribute for BaseMessage subclasses if available
                role = getattr(msg, 'type', 'Unknown').capitalize()
                content = getattr(msg, 'content', '')
            else:
                logger.warning(f"Unknown message type: {type(msg)} - skipping")
                continue
                
            conversation_text += f"{role}: {content}\n\n"
            
        if not conversation_text:
             logger.error("No conversation text could be prepared from messages.")
             state['error'] = "Failed to prepare conversation text for diagram generation."
             return state
        # --- END Prepare full conversation text ---
        
        # Create LLM for diagram generation
        llm = ChatOpenAI(
            model_name=settings.AGENT_JACKSON_MODEL,
            temperature=settings.AGENT_JACKSON_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            request_timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES
        )
        
        # Create prompt for UML generation from YAML config
        # Format the system message part with the agent name
        system_template = uml_prompt_config.get('system', '')
        formatted_system_content = system_template.format(agent_name=settings.AGENT_JACKSON_NAME)
        temp_config = uml_prompt_config.copy() # Avoid modifying original dict
        temp_config['system'] = formatted_system_content
        
        prompt = _create_prompt_from_config(temp_config)
        
        # Create and invoke chain
        chain = prompt | llm
        
        # Use full conversation text instead of summary
        response = await chain.ainvoke({
            # "conversation_summary": state['conversation_summary']
            "conversation_summary": conversation_text # Pass full text to the same key
        })
        
        # Update state with UML content
        state['uml_content'] = response.content
        logger.info(f"Successfully generated UML diagrams for session {state['session_id']}")
        
        return state
    except Exception as e:
        logger.error(f"Error generating UML diagrams: {str(e)}")
        state['error'] = f"Failed to generate UML diagrams: {str(e)}"
        return state

async def validate_diagrams(state: DiagramState) -> DiagramState:
    """Validate the generated UML diagrams."""
    logger.info(f"Validating UML diagrams for session {state['session_id']}")
    
    try:
        # Check if we have UML content
        if not state['uml_content'] or not state['uml_content'].strip():
            logger.error("Generated UML content is empty")
            state['error'] = "Failed to generate UML diagrams: empty response"
            return state
        
        # Validate required diagram sections
        required_sections = ["Class Diagram", "Use Case Diagram", "Sequence Diagram", "Activity Diagram"]
        missing_sections = []
        for section in required_sections:
            if section not in state['uml_content']:
                missing_sections.append(section)
        
        state['missing_sections'] = missing_sections
        
        if missing_sections:
            logger.warning(f"Missing required UML sections: {', '.join(missing_sections)}")
        
        # Validate PlantUML syntax
        if not all(marker in state['uml_content'] for marker in ["@startuml", "@enduml"]):
            logger.error("Invalid PlantUML syntax: missing @startuml/@enduml markers")
            state['error'] = "Generated UML diagrams have invalid syntax. Missing required PlantUML markers."
            return state
        
        logger.info(f"UML diagrams validated for session {state['session_id']}")
        return state
    except Exception as e:
        logger.error(f"Error validating UML diagrams: {str(e)}")
        state['error'] = f"Failed to validate UML diagrams: {str(e)}"
        return state

async def apply_fallback_templates(state: DiagramState) -> DiagramState:
    """Apply fallback templates for missing UML sections."""
    logger.info(f"Applying fallback templates for session {state['session_id']}")
    
    try:
        # Check if we have missing sections
        if not state['missing_sections']:
            logger.info("No missing sections, skipping fallback templates")
            return state
        
        # Apply fallback templates
        result = state['uml_content'] or ""
        
        fallback_templates = {
            "Class Diagram": """
## Class Diagram
```
@startuml
' Default Class Diagram
class User {
  +id: String
  +name: String
  +email: String
  +login()
  +logout()
}

class System {
  +id: String
  +name: String
  +version: String
  +initialize()
  +shutdown()
}

User -- System : uses
@enduml
```
""",
            "Use Case Diagram": """
## Use Case Diagram
```
@startuml
' Default Use Case Diagram
left to right direction
actor User
actor Admin

rectangle System {
  User -- (Login)
  User -- (View Dashboard)
  Admin -- (Manage Users)
  Admin -- (Configure System)
  (Login) <.. (Authenticate) : include
}
@enduml
```
""",
            "Sequence Diagram": """
## Sequence Diagram
```
@startuml
' Default Sequence Diagram
actor User
participant "Frontend" as FE
participant "Backend" as BE
database "Database" as DB

User -> FE: Login Request
activate FE
FE -> BE: Authenticate
activate BE
BE -> DB: Validate Credentials
activate DB
DB --> BE: Return User Data
deactivate DB
BE --> FE: Authentication Result
deactivate BE
FE --> User: Login Response
deactivate FE
@enduml
```
""",
            "Activity Diagram": """
## Activity Diagram
```
@startuml
' Default Activity Diagram
start
:Start
:End
@enduml
```
"""
        }
        
        for section in state['missing_sections']:
            if section in fallback_templates:
                result += "\n\n" + fallback_templates[section]
                logger.info(f"Added fallback template for {section}")
        
        # Update state with the enhanced UML content
        state['uml_content'] = result
        logger.info(f"Applied fallback templates for session {state['session_id']}")
        
        return state
    except Exception as e:
        logger.error(f"Error applying fallback templates: {str(e)}")
        state['error'] = f"Failed to apply fallback templates: {str(e)}"
        return state

async def save_diagrams(state: DiagramState) -> DiagramState:
    """Save the UML diagrams to files."""
    logger.info(f"Saving UML diagrams for session {state['session_id']}")
    
    try:
        # Check if we have UML content
        if not state['uml_content'] or not state['uml_content'].strip():
            logger.error("No UML content to save")
            state['error'] = "No UML content to save"
            return state
        
        # Get chat name
        chat_name = state['chat_name'] or state['session_id']  # Use chat_name if available, otherwise session_id
        
        # Try to get a better chat name from Redis if not already set
        if not state['chat_name']:
            try:
                redis_url = (
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                    f"?socket_timeout={settings.REDIS_TIMEOUT}"
                    f"&socket_connect_timeout={settings.REDIS_TIMEOUT}"
                )
                
                message_history = RedisChatMessageHistory(
                    session_id=f"diagram_{state['session_id']}",
                    url=redis_url,
                    key_prefix="diagram:",
                    ttl=settings.REDIS_DATA_TTL
                )
                
                chat_name_key = f"chat_name:{state['session_id']}"
                chat_name_data = message_history.redis_client.get(chat_name_key)
                
                if chat_name_data:
                    chat_name = chat_name_data.decode('utf-8')
            except Exception as e:
                logger.warning(f"Error getting chat name: {str(e)}")
        
        # Extract diagrams from UML content
        diagrams = {}
        current_type = None
        current_content = []
        
        for line in state['uml_content'].split('\n'):
            if '## Class Diagram' in line:
                if current_type and current_content:
                    # Save previous diagram if exists
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Class Diagram'
                current_content = []
            elif '## Use Case Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Use Case Diagram'
                current_content = []
            elif '## Sequence Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Sequence Diagram'
                current_content = []
            elif '## Activity Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Activity Diagram'
                current_content = []
            elif '## Component Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Component Diagram'
                current_content = []
            elif '## State Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'State Diagram'
                current_content = []
            elif current_type:
                current_content.append(line)
        
        # Save the last diagram
        if current_type and current_content:
            diagrams[current_type] = '\n'.join(current_content)
        
        # Use the new save_diagrams_to_files function
        from .save_diagrams import save_diagrams_to_files
        
        # Get group name from user info in state
        group_name = state['group_name'] or None
        
        # Get interview file path if available
        interview_file_path = state.get('interview_file_path')
        
        # Get username from state
        username = state.get('username')
        
        # Save diagrams to files
        result = save_diagrams_to_files(
            chat_title=chat_name,
            diagrams=diagrams,
            group_name=group_name,
            interview_file_path=interview_file_path,
            username=username
        )
        
        # Check for errors
        if not result.get('success', False):
            state['error'] = result.get('error', 'Unknown error saving diagrams')
            return state
        
        # Update state with diagram files
        state['diagram_files'] = result.get('diagram_files', {})
        logger.info(f"UML diagrams saved successfully: {result.get('message', '')}")
        
        return state
    except Exception as e:
        logger.error(f"Error saving UML diagrams: {str(e)}")
        state['error'] = f"Failed to save UML diagrams: {str(e)}"
        return state

async def prepare_result(state: DiagramState) -> DiagramState:
    """Prepare the final result."""
    logger.info(f"Preparing result for session {state['session_id']}")
    
    try:
        # Check if we have an error
        if state['error']:
            state['result'] = {
                "error": state['error'],
                "message": f"Error generating UML diagrams: {state['error']}"
            }
            return state
        
        # Prepare the result, including the new single file path
        state['result'] = {
            "uml_diagrams": state.get('uml_content'), # Raw UML content string
            "diagram_file_path": state.get('diagram_file_path'), # Path to the consolidated MD file
            # Include the old key for potential backward compatibility, but prioritize the new one
            "diagram_files": state.get('diagram_files', {}), 
            "message": f"The system structure has been visualized. - {settings.AGENT_JACKSON_NAME}"
        }
        
        logger.info(f"Result prepared for session {state['session_id']}: {state['result']}")
        return state
    except Exception as e:
        logger.error(f"Error preparing result: {str(e)}")
        state['error'] = f"Failed to prepare result: {str(e)}"
        state['result'] = {
            "error": str(e),
            "message": f"Error generating UML diagrams: {str(e)}"
        }
        return state

# Create a wrapper class that maintains the same interface as the original DiagramAgent
class DiagramAgentGraph:
    """LangGraph-based implementation of the Diagram Agent."""
    
    def __init__(self, session_id: str, username: str):
        """Initialize the diagram agent."""
        try:
            logger.info(f"Initializing DiagramAgentGraph for session {session_id}")
            self.session_id = session_id
            self.username = username
            self.agent_name = settings.AGENT_JACKSON_NAME
            
            # Initialize state
            self.state = {
                "session_id": session_id,
                "username": username,
                "group_name": "default",  # Will be updated during initialization
                "messages": [],
                "conversation_summary": None,
                "uml_content": None,
                "diagram_files": {},
                "missing_sections": [],
                "error": None,
                "result": None,
                "chat_name": None,
                "user_info": None
            }
            
            # Initialize LLM
            self.llm = ChatOpenAI(
                model=settings.AGENT_JACKSON_MODEL,
                temperature=settings.AGENT_JACKSON_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY
            )
            
            logger.info(f"DiagramAgentGraph initialized for session {session_id}")
        except Exception as e:
            logger.error(f"Error initializing DiagramAgentGraph: {str(e)}")
            raise
    
    async def initialize(self) -> None:
        """Initialize the agent state."""
        try:
            logger.info(f"Initializing agent state for session {self.session_id}")
            
            # Get user info
            self.state["user_info"] = await get_user_info(self.session_id)
            self.state["group_name"] = self.state["user_info"].get("group_name", "default")
            
            logger.info(f"Agent state initialized for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error initializing agent state: {str(e)}")
            self.state["error"] = f"Failed to initialize agent state: {str(e)}"
            raise
    
    async def generate_uml_diagrams(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate UML diagrams from the conversation.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            A dictionary containing the generated UML diagrams and their file paths
        """
        try:
            logger.info(f"Generating UML diagrams for session {self.session_id}")
            
            # Store messages in state
            self.state["messages"] = messages
            
            # Initialize state (which also gets user info)
            self.state = await initialize_state(self.state)

            # Get the actual chat title from DB and store in state
            try:
                chat_title_db = await get_chat_title_from_db(self.session_id, self.username)
                self.state["chat_name"] = chat_title_db
                logger.info(f"Retrieved chat title from DB: {chat_title_db}")
            except Exception as e:
                logger.warning(f"Could not retrieve chat title from DB: {e}. Falling back to session ID.")
                self.state["chat_name"] = self.session_id
            
            # --- REMOVED Summarization Step ---
            # self.state = await summarize_conversation(self.state)
            logger.info("Skipping conversation summarization step.")
            # --- END REMOVED Summarization Step ---
            
            # Generate UML diagrams (now uses full conversation)
            self.state = await generate_uml_diagrams(self.state)
            
            # Validate UML diagrams
            self.state = await validate_diagrams(self.state)
            
            # Apply fallback templates if needed
            self.state = await apply_fallback_templates(self.state)
            
            # Extract individual diagrams from UML content
            diagrams = self.extract_diagrams_from_uml(self.state["uml_content"])
            
            # Save diagrams to the specified directory structure using the retrieved chat_name
            file_paths = self.save_diagrams_to_directory(diagrams)
            
            # Update state with diagram files (This key seems incorrect based on save_diagrams_to_directory return)
            # Let's use the key returned by the save function
            self.state["diagram_file_path"] = file_paths.get("diagram_file_path") # Assuming save returns this key now
            # Keep the old key for backward compatibility if needed, but log it
            if isinstance(file_paths, dict) and not self.state["diagram_file_path"]:
                 self.state["diagram_files"] = file_paths # Fallback to old dict structure if single path not found
                 logger.warning("diagram_file_path not found in save_diagrams_to_directory result, using old diagram_files key.")
            elif not isinstance(file_paths, dict):
                 logger.error(f"Unexpected return type from save_diagrams_to_directory: {type(file_paths)}")

            # Prepare result
            self.state = await prepare_result(self.state)
            
            logger.info(f"UML diagrams generated for session {self.session_id}")
            return self.state["result"]
        except Exception as e:
            logger.error(f"Error generating UML diagrams: {str(e)}")
            self.state["error"] = f"Failed to generate UML diagrams: {str(e)}"
            self.state["result"] = {
                "error": str(e),
                "message": f"Error generating UML diagrams: {str(e)}"
            }
            return self.state["result"]
            
    def extract_diagrams_from_uml(self, uml_content: str) -> Dict[str, str]:
        """
        Extract individual diagrams from the UML content.
        
        Args:
            uml_content: The UML content containing multiple diagrams
            
        Returns:
            A dictionary mapping diagram types to their content
        """
        if not uml_content:
            return {}
            
        diagrams = {}
        current_type = None
        current_content = []
        
        for line in uml_content.split('\n'):
            if '## Class Diagram' in line:
                if current_type and current_content:
                    # Save previous diagram if exists
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Class Diagram'
                current_content = []
            elif '## Use Case Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Use Case Diagram'
                current_content = []
            elif '## Sequence Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Sequence Diagram'
                current_content = []
            elif '## Activity Diagram' in line:
                if current_type and current_content:
                    diagrams[current_type] = '\n'.join(current_content)
                current_type = 'Activity Diagram'
                current_content = []
            elif current_type:
                current_content.append(line)
        
        # Save the last diagram
        if current_type and current_content:
            diagrams[current_type] = '\n'.join(current_content)
        
        return diagrams

    async def analyze_last_chat_session(self) -> Dict[str, Any]:
        """
        Analyze the last chat session and generate UML diagrams.
        
        Returns:
            A dictionary containing the generated UML diagrams and their file paths
        """
        try:
            logger.info(f"Analyzing last chat session for user {self.username}")
            
            # Import database models here to avoid circular imports
            from app.models.user import User
            from app.models.chat import ChatSession, ChatMessage
            from app.db.session import async_session
            
            # Get database session
            async for db in async_session():
                # Get user from database
                user_query = select(User).where(User.username == self.username)
                user_result = await db.execute(user_query)
                user = user_result.scalars().first()
                
                if not user:
                    logger.error(f"User not found: {self.username}")
                    raise ValueError(f"User not found: {self.username}")
                
                # Get the last chat session for this user
                chat_session_query = select(ChatSession).where(
                    ChatSession.user_id == user.id
                ).order_by(desc(ChatSession.created_at)).limit(1)
                
                chat_session_result = await db.execute(chat_session_query)
                chat_session = chat_session_result.scalars().first()
                
                if not chat_session:
                    logger.error(f"No chat sessions found for user: {self.username}")
                    raise ValueError(f"No chat sessions found for user: {self.username}")
                
                logger.info(f"Analyzing chat session: {chat_session.title}")
                
                # Get messages for this chat session
                messages_query = select(ChatMessage).where(
                    ChatMessage.session_id == chat_session.id
                ).order_by(ChatMessage.created_at)
                
                messages_result = await db.execute(messages_query)
                db_messages = messages_result.scalars().all()
                
                if not db_messages:
                    logger.error(f"No messages found for chat session: {chat_session.title}")
                    raise ValueError(f"No messages found for chat session '{chat_session.title}'")
                
                logger.info(f"Found {len(db_messages)} messages in chat session")
                
                # Convert database messages to the format expected by generate_uml_diagrams
                messages = []
                for msg in db_messages:
                    messages.append({
                        "role": msg.role.value.lower(),
                        "content": msg.content
                    })
                
                # Set the chat name in the state
                self.state["chat_name"] = chat_session.title
                
                # Generate UML diagrams
                return await self.generate_uml_diagrams(messages)
            
        except Exception as e:
            logger.error(f"Error analyzing last chat session: {str(e)}", exc_info=True)
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Failed to analyze last chat session: {str(e)}") from e

    def save_diagrams_to_directory(self, diagrams: Dict[str, str], group_name: str = None, chat_name: str = None) -> Dict[str, str]:
        """
        Save the generated diagrams to the specified directory structure.
        Passes data to save_diagrams_to_files.
        """
        if not diagrams:
            logger.warning("No diagrams to save")
            return {}
            
        # Get group name from user info in state if not provided
        if not group_name and self.state.get("user_info") and "group_name" in self.state["user_info"]:
            group_name = self.state["user_info"]["group_name"]
        
        # Get chat name - *** Expects state["chat_name"] to be set correctly by the caller ***
        if not chat_name:
            chat_name = self.state.get("chat_name") # Use get to avoid KeyError
            if not chat_name:
                 logger.error("chat_name not found in state for save_diagrams_to_directory. Cannot save diagrams.")
                 # Return an empty dict or raise an error, depending on desired behavior
                 return {"error": "Chat name not available in state"}
        
        # Use the new save_diagrams_to_files function
        from .save_diagrams import save_diagrams_to_files
        
        # Get interview file path if available
        interview_file_path = self.state.get('interview_file_path')
        
        # Save diagrams to files
        result = save_diagrams_to_files(
            chat_title=chat_name, # Pass the correct chat name
            diagrams=diagrams,
            group_name=group_name,
            interview_file_path=interview_file_path,
            username=self.username
        )
        
        # Check for errors
        if not result.get('success', False):
            logger.error(f"Error saving diagrams: {result.get('error', 'Unknown error')}")
            return {"error": result.get('error', 'Unknown error saving diagrams')}
        
        # Return the result dictionary from save_diagrams_to_files
        # which should now contain 'diagram_file_path'
        return result 