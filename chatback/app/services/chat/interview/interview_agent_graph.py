"""
LangGraph-based implementation of the Interview Agent.
This implementation uses LangGraph concepts for better state management
while maintaining the same API interface as the original InterviewAgent.
"""

from typing import Dict, List, Any, TypedDict, Optional, Annotated, Literal
import logging
import json
import os
from datetime import datetime
import pytz
from string import Template
import httpx
import time
import asyncio
import yaml

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage

# FastAPI imports
from fastapi import HTTPException

# Redis imports
from redis.exceptions import TimeoutError, ConnectionError
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

# Tenacity for retries
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# Local imports
from app.core.config import settings
from .question_loader import load_interview_questions
from app.services.chat.errors import ChatManagerError

logger = logging.getLogger(__name__)

# Define the state schema
class InterviewState(TypedDict):
    """State for the interview graph."""
    messages: List[Dict[str, Any]]  # Chat messages
    current_section: int  # Current section index
    current_question_index: int  # Current question index in the section
    progress: float  # Interview progress percentage
    sections: Dict[int, str]  # Section names by index
    questions: Dict[int, List[str]]  # Questions by section index
    session_id: str  # Session ID
    username: str  # Username
    is_first_message: bool  # Whether this is the first message
    command: Optional[str]  # Special command like 'next'
    response: Optional[str]  # Response to return to the user
    iteration_count: int  # Counter to track iterations and prevent infinite recursion
    user_info: Dict[str, str]  # User information including group name
    user_info_loaded: bool  # Flag to indicate if user info has been loaded

async def initialize_state(state: InterviewState) -> InterviewState:
    """Initialize the interview state."""
    logger.info(f"Initializing interview state for session {state['session_id']}")
    
    try:
        # Load interview questions
        sections, questions = load_interview_questions()
        
        # Update state with sections and questions
        state["sections"] = sections
        state["questions"] = questions
        state["current_section"] = 1
        state["current_question_index"] = 0
        state["progress"] = 0.0
        state["is_first_message"] = True
        state["iteration_count"] = 0  # Reset iteration count
        
        # Ensure user_info_loaded is set
        if "user_info_loaded" not in state:
            state["user_info_loaded"] = False
        
        logger.info(f"Initialized interview state with {len(sections)} sections")
        return state
    except Exception as e:
        logger.error(f"Error initializing interview state: {str(e)}")
        raise ValueError(f"Failed to initialize interview: {str(e)}")

async def save_state_to_redis(state: InterviewState) -> InterviewState:
    """Save the current state to Redis."""
    try:
        # Skip saving if there's no response yet (prevents saving incomplete state)
        if state.get("response") is None:
            logger.info("Skipping state save - no response generated yet")
            return state
            
        # Setup Redis client
        redis_url = (
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            f"?socket_timeout={settings.REDIS_TIMEOUT}"
            f"&socket_connect_timeout={settings.REDIS_TIMEOUT}"
        )
        retry = Retry(ExponentialBackoff(), settings.REDIS_RETRY_ATTEMPTS)
        
        # Initialize Redis client
        message_history = RedisChatMessageHistory(
            session_id=f"interview_{state['session_id']}",
            url=redis_url,
            key_prefix="interview:",
            ttl=settings.REDIS_DATA_TTL
        )
        
        # Save messages to Redis
        message_history.clear()
        for msg in state["messages"]:
            if msg["role"] == "user":
                message_history.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                message_history.add_ai_message(msg["content"])
        
        # Save state data
        state_key = f"interview:state:{state['session_id']}"
        state_data = {
            'section': state["current_section"],
            'question': state["current_question_index"],
            'progress': state["progress"]
        }
        message_history.redis_client.set(state_key, json.dumps(state_data))
        
        logger.info(f"Saved state with progress {state['progress']:.1f}%")
        return state
    except Exception as e:
        logger.error(f"Error saving state to Redis: {str(e)}")
        # Continue even if saving fails
        return state

# Create a wrapper class that maintains the same interface as the original InterviewAgent
class InterviewAgentGraph:
    """LangGraph-based implementation of the Interview Agent."""
    
    def __init__(self, session_id: str, username: str):
        """Initialize the interview agent."""
        try:
            logger.info(f"Initializing InterviewAgentGraph for session {session_id}")
            self.session_id = session_id
            self.username = username
            self.agent_name = settings.AGENT_SMITH_NAME # Store agent name
            
            # Load prompts from YAML
            prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'interview_prompt.yaml') 
            try:
                with open(prompts_path, 'r') as f:
                    self.prompts = yaml.safe_load(f)
                logger.info(f"Successfully loaded prompts from {prompts_path}")
            except FileNotFoundError:
                logger.error(f"Prompt file not found at {prompts_path}. Please create it.")
                raise
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML prompt file {prompts_path}: {e}")
                raise

            # Initialize LLM
            self.llm = ChatOpenAI(
                model_name=settings.AGENT_SMITH_MODEL,
                temperature=settings.AGENT_SMITH_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
                request_timeout=settings.OPENAI_TIMEOUT,
                max_retries=settings.OPENAI_MAX_RETRIES
            )

            # Initialize state from Redis if available
            self.state = self._load_initial_state()
            
            logger.info(f"InterviewAgentGraph initialized successfully for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize InterviewAgentGraph: {str(e)}")
            raise
    
    def _load_initial_state(self) -> InterviewState:
        """Load the initial state from Redis or create a new one."""
        try:
            # Setup Redis client
            redis_url = (
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                f"?socket_timeout={settings.REDIS_TIMEOUT}"
                f"&socket_connect_timeout={settings.REDIS_TIMEOUT}"
            )
            
            # Initialize Redis client
            message_history = RedisChatMessageHistory(
                session_id=f"interview_{self.session_id}",
                url=redis_url,
                key_prefix="interview:",
                ttl=settings.REDIS_DATA_TTL
            )
            
            # Get messages from Redis
            messages = []
            for msg in message_history.messages:
                if isinstance(msg, HumanMessage):
                    messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    messages.append({"role": "assistant", "content": msg.content})
            
            # Get state data
            state_key = f"interview:state:{self.session_id}"
            state_data = message_history.redis_client.get(state_key)
            
            # Get user info including group name - set default initially
            # We'll retrieve the actual group name later in an async context
            user_info = {"group_name": "default"}
            logger.info(f"Setting default group name for user {self.username}, will be updated later")
            
            # Load interview questions
            try:
                sections, questions = load_interview_questions()
                logger.info(f"Loaded {len(sections)} sections with {sum(len(q) for q in questions.values())} questions")
            except Exception as e:
                logger.error(f"Error loading interview questions: {str(e)}")
                sections = {}
                questions = {}
            
            if state_data:
                state_data = json.loads(state_data)
                logger.info(f"Loaded state from Redis with progress {state_data.get('progress', 0.0):.1f}%")
                
                # Check if there are any assistant messages to determine if this is the first message
                assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
                is_first_message = len(assistant_messages) == 0
                
                return {
                    "messages": messages,
                    "current_section": state_data.get('section', 1),
                    "current_question_index": state_data.get('question', 0),
                    "progress": state_data.get('progress', 0.0),
                    "sections": sections,  # Load sections directly
                    "questions": questions,  # Load questions directly
                    "session_id": self.session_id,
                    "username": self.username,
                    "is_first_message": is_first_message,
                    "command": None,
                    "response": None,
                    "iteration_count": 0,
                    "user_info": user_info,  # Add user info to state
                    "user_info_loaded": False
                }
            
            # Create new state if none exists
            logger.info("No state found in Redis, creating new state")
            return {
                "messages": [],
                "current_section": 1,
                "current_question_index": 0,
                "progress": 0.0,
                "sections": sections,  # Load sections directly
                "questions": questions,  # Load questions directly
                "session_id": self.session_id,
                "username": self.username,
                "is_first_message": True,
                "command": None,
                "response": None,
                "iteration_count": 0,
                "user_info": user_info,  # Add user info to state
                "user_info_loaded": False
            }
        except Exception as e:
            logger.error(f"Error loading initial state: {str(e)}")
            # Return a default state on error
            return {
                "messages": [],
                "current_section": 1,
                "current_question_index": 0,
                "progress": 0.0,
                "sections": {},  # Will be loaded by initialize_state
                "questions": {},  # Will be loaded by initialize_state
                "session_id": self.session_id,
                "username": self.username,
                "is_first_message": True,
                "command": None,
                "response": None,
                "iteration_count": 0,
                "user_info": {"group_name": "default"},  # Add default user info to state
                "user_info_loaded": False
            }
    
    def _create_prompt_from_config(self, prompt_config: Dict) -> ChatPromptTemplate:
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

    async def process_message(self, content: str) -> str:
        """Process a user message and return the response."""
        # llm = None # LLM is now initialized in __init__
        
        try:
            logger.info(f"Processing message for session {self.session_id}")
            
            # If this is the first message, try to get the user's group name from the database
            if not self.state.get("user_info_loaded"):
                try:
                    from .save_interview import get_user_group
                    # Get group name from database
                    group_name = await get_user_group(self.username, None)
                    self.state["user_info"] = {"group_name": group_name}
                    self.state["user_info_loaded"] = True
                    logger.info(f"Retrieved group name for user {self.username} from database: {group_name}")
                except Exception as e:
                    logger.warning(f"Could not retrieve user group from database: {str(e)}")
                    # Keep the default group name
                    self.state["user_info_loaded"] = True
            
            # Check if this is a 'next' command
            is_next_command = content.lower() in ['next', 'continue', 'proceed']
            
            # Add user message to state
            self.state["messages"].append({"role": "user", "content": content})
            
            # Reset the response field and iteration count to ensure we don't immediately end
            self.state["response"] = None
            self.state["iteration_count"] = 0
            
            # Initialize the graph if this is the first run
            if not self.state.get("sections"):
                logger.info("Initializing state with interview questions")
                # We need to initialize the state first before running the graph
                self.state = await initialize_state(self.state)
            
            # Check if this is the first message in a new chat session
            # If there are no assistant messages yet, this is the first interaction
            assistant_messages = [msg for msg in self.state["messages"] if msg["role"] == "assistant"]
            if not assistant_messages:
                logger.info("First message in a new chat session, displaying introduction")
                # Get first question from current section
                first_question = self.state["questions"][self.state["current_section"]][self.state["current_question_index"]]
                
                # Get time-appropriate greeting
                current_hour = datetime.now(pytz.UTC).hour
                if current_hour < 12:
                    greeting = "Good morning"
                elif current_hour < 17:
                    greeting = "Good afternoon"
                else:
                    greeting = "Good evening"
                
                # Get user name
                user_name = self.state["username"]
                # Capitalize the first letter of the username
                if user_name:
                    user_name = user_name[0].upper() + user_name[1:] if len(user_name) > 1 else user_name.upper()
                name_part = f" {user_name}," if user_name else ","
                
                # Create introduction message with personal greeting
                intro = f"""{greeting}{name_part} my name is {settings.AGENT_SMITH_NAME}. I am a senior business analyst specializing in stakeholder interviews and requirements gathering. I'll be conducting a structured interview to help understand your project needs and requirements thoroughly. We'll go through several sections covering different aspects of your project.\n\n### Let's begin with our first question!\n\n**{first_question}**"""
                
                # Update state
                self.state["response"] = intro
                self.state["messages"].append({"role": "assistant", "content": intro})
                
                # Save state to Redis
                await save_state_to_redis(self.state)
                
                return intro
            
            # Handle 'next' command directly
            if is_next_command:
                logger.info("Handling 'next' command")
                current_section = self.state["current_section"]
                current_question_index = self.state["current_question_index"]
                sections = self.state["sections"]
                questions = self.state["questions"]
                
                # Check if there are more questions in current section
                if current_question_index < len(questions[current_section]) - 1:
                    # Move to next question in current section
                    self.state["current_question_index"] += 1
                    next_question = questions[current_section][self.state["current_question_index"]]
                    response = f"\n\n**{next_question}**"
                else:
                    # Move to next section if available
                    if current_section < len(sections):
                        self.state["current_section"] += 1
                        self.state["current_question_index"] = 0
                        next_section = sections[self.state["current_section"]]
                        next_question = questions[self.state["current_section"]][0]
                        response = f"\n\n### Moving on to section: {next_section}\n\n**{next_question}**"
                    else:
                        # Interview completed
                        response = """{name_part}, Thank you for completing this comprehensive interview!

I've gathered all the information needed to proceed with the next steps in our process. Here's what will happen next:

1. **Modeling Phase**: 
   - Agent Jackson will analyze our conversation and generate UML diagrams to visualize the system architecture
   - The UML diagrams will be saved and are accessable in on the Diagrams page

2. **Requirements Gathering Phase**:
    - Agent Thompson will extract and categorize all functional and non-functional requirements
    - The requirements will be saved and are accessable in on the Requirements page

3. **Documentation Phase**:
    - Agent Jackson will analyze our conversation and generate a Software Requirements Specifications Document
    - Agent Brown  will review the SRS Document and suggest improvements where necessary 
    - The requiremenst and the Diagrams will be included in the document
    - The SRS document can be viewed in menu-item SRSDocs

All these information will be accessible to you and your team members. They will serve as a solid foundation for your software development project.

**Please wait while our specialized agents process this information. This may take a few moments...**"""
                
                # Calculate progress
                total_questions = sum(len(q_list) for q_list in questions.values())
                completed = sum(len(questions[s]) for s in range(1, current_section))
                completed += current_question_index + 1
                progress = (completed / total_questions) * 100
                
                # Update state
                self.state["progress"] = progress
                self.state["response"] = response
                self.state["messages"].append({"role": "assistant", "content": response})
                
                # Save state to Redis
                await save_state_to_redis(self.state)
                
                return response
            
            # For regular messages, use the LLM to generate a response
            if not is_next_command:
                logger.info("Processing regular user message using prompt from YAML")
                
                # Get current state details for formatting
                progress = self.state["progress"]
                current_section_index = self.state["current_section"]
                current_question_index = self.state["current_question_index"]
                sections = self.state["sections"]
                questions = self.state["questions"]
                current_section_name = sections[current_section_index]
                current_question = questions[current_section_index][current_question_index]
                
                # Create prompt from loaded config
                prompt_config = self.prompts.get('interview_prompt')
                if not prompt_config:
                     logger.error("'interview_prompt' not found in loaded YAML prompts.")
                     raise ValueError("Missing interview prompt configuration")
                
                prompt = self._create_prompt_from_config(prompt_config)
                
                # Format the system message part (which is now the first message in the template)
                # This assumes the system message is the first tuple in the prompt messages
                if prompt.messages and isinstance(prompt.messages[0], SystemMessagePromptTemplate):
                    system_template = prompt.messages[0].prompt.template
                    formatted_system_content = system_template.format(
                        agent_name=self.agent_name,
                        current_section_name=current_section_name,
                        progress=progress,
                        current_question=current_question
                    )
                    # Update the prompt with formatted system message (LangChain prompts are immutable, create new)
                    updated_messages = list(prompt.messages)
                    updated_messages[0] = ("system", formatted_system_content) 
                    prompt = ChatPromptTemplate.from_messages(updated_messages)
                else:
                    logger.warning("Could not format system message in loaded prompt template.")

                # Convert state messages to LangChain format for history
                history = []
                for msg in self.state["messages"][-7:-1]:
                    if msg["role"] == "user":
                        history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        history.append(AIMessage(content=msg["content"]))
                
                # Create and invoke chain
                chain = prompt | self.llm # Use self.llm initialized in __init__
                
                try:
                    response = await chain.ainvoke({
                        "input": content,
                        "history": history
                    })
                    
                    # Update state
                    self.state["response"] = response.content
                    self.state["messages"].append({"role": "assistant", "content": response.content})
                    
                    # Save state to Redis
                    await save_state_to_redis(self.state)
                    
                    return response.content
                    
                except Exception as e:
                    logger.error(f"Error invoking LLM chain: {str(e)}", exc_info=True)
                    raise ChatManagerError("Error generating interview response") from e

            # If it was a 'next' command handled earlier, return the stored response
            if is_next_command and self.state.get("response"):
                 return self.state["response"]
                 
            # Fallback if somehow no response was generated
            logger.error("Reached end of process_message without generating a response.")
            return "An unexpected error occurred. Please try again."
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Attempt to return a generic error message
            # Avoid raising here if possible to prevent breaking the chat flow entirely
            return "I encountered an error processing your message. Please try again or type 'next' if you were finished."
    
    def calculate_progress(self) -> float:
        """Calculate the current progress of the interview."""
        return self.state["progress"]
    
    async def save_interview_document(self, chat_title: str = None) -> Dict[str, Any]:
        """Save the interview as a document using the save_interview_from_redis function.
        
        Args:
            chat_title: Optional title for the chat session. If not provided, it will be retrieved from the database.
            
        Returns:
            A dictionary containing the result of the operation, including file_path if successful
        """
        try:
            logger.info(f"Saving interview document for session {self.session_id}")
            
            # Import the save_interview_from_redis function and get_user_group
            from .save_interview import save_interview_from_redis, get_user_group, get_chat_title_from_db
            
            # Get the user's group name - first check if it's already in the state
            group_name = None
            if self.state.get("user_info_loaded") and self.state["user_info"].get("group_name"):
                group_name = self.state["user_info"]["group_name"]
                logger.info(f"Using group name from state: {group_name}")
            
            logger.info(f"Group name for user {self.username}: {group_name or 'Not set, will be determined by save_interview_from_redis'}")
            
            # If chat_title is not provided, try to get it from the database
            if not chat_title:
                try:
                    chat_title = await get_chat_title_from_db(self.session_id, self.username)
                    logger.info(f"Retrieved chat title from database: {chat_title}")
                except Exception as e:
                    logger.warning(f"Could not retrieve chat title from database: {str(e)}")
                    # Use a default title if we couldn't get one from the database
                    chat_title = f"Interview-{self.session_id}"
                    logger.info(f"Using default chat title: {chat_title}")
            
            # Setup Redis client (only needed for save_interview_from_redis)
            redis_url = (
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                f"?socket_timeout={settings.REDIS_TIMEOUT}"
                f"&socket_connect_timeout={settings.REDIS_TIMEOUT}"
            )
            
            # Initialize Redis client
            message_history = RedisChatMessageHistory(
                session_id=f"interview_{self.session_id}",
                url=redis_url,
                key_prefix="interview:",
                ttl=settings.REDIS_DATA_TTL
            )
            
            # Call the function to save the interview
            result = await save_interview_from_redis(
                session_id=self.session_id,
                username=self.username,
                chat_title=chat_title,
                group_name=group_name,  # Pass the group name (may be None)
                state=self.state  # Pass the state as a fallback
            )
            
            # Check if the operation was successful and log the result
            if result.get("success", False):
                logger.info(f"Interview document saved successfully: {result.get('file_path')}")
            else:
                logger.error(f"Error saving interview document: {result.get('error')}")
            
            # Return the full result dictionary
            return result
                
        except Exception as e:
            logger.error(f"Error saving interview document: {str(e)}")
            return {
                "success": False,
                "message": f"Error saving interview document: {str(e)}",
                "error": str(e)
            } 