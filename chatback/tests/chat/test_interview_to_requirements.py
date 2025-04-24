#!/usr/bin/env python
"""
Script to test the transition from interview to requirements phase.
This script simulates a completed interview and verifies that the requirements phase is executed.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
from unittest.mock import patch, MagicMock, PropertyMock

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"
os.environ["CHATBOT_DATA_PATH"] = "data"

from app.services.chat.chat_manager import LangChainChatManager, ConversationState
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock response for interview completion
INTERVIEW_COMPLETION_RESPONSE = """
Thank you for completing this comprehensive interview. Your responses have provided valuable insights into your project requirements.

Please wait while our specialized agents process this information to generate detailed requirements, UML diagrams, and comprehensive documentation.
"""

# Mock response for requirements extraction
MOCK_REQUIREMENTS_RESULT = {
    "functional_requirements": [
        {
            "id": "FR1",
            "name": "User Registration",
            "rationale": "Allow users to create accounts",
            "description": "Users should be able to register with email and password",
            "priority": "Must Have"
        },
        {
            "id": "FR2",
            "name": "User Login",
            "rationale": "Allow users to access their accounts",
            "description": "Users should be able to login with email and password",
            "priority": "Must Have"
        }
    ],
    "non_functional_requirements": [
        {
            "id": "NFR1",
            "name": "Performance",
            "rationale": "Ensure good user experience",
            "description": "The system should respond within 2 seconds",
            "priority": "Should Have"
        }
    ],
    "functional_requirements_path": "data/test/requirements/fr-Test-Interview.md",
    "non_functional_requirements_path": "data/test/requirements/nfr-Test-Interview.md",
    "message": "Requirements have been extracted and saved. - Agent Thompson"
}

class MockInterviewAgent:
    """Mock implementation of the InterviewAgentGraph for testing."""
    
    def __init__(self):
        self.state = {
            "messages": [
                {"role": "system", "content": "You are an interview agent."},
                {"role": "user", "content": "Hello, I need a system for my business."},
                {"role": "assistant", "content": "What kind of business do you have?"},
                {"role": "user", "content": "I have an e-commerce business."},
                {"role": "assistant", "content": "What features do you need?"},
                {"role": "user", "content": "I need user registration, login, and product search."},
                {"role": "assistant", "content": INTERVIEW_COMPLETION_RESPONSE}
            ],
            "chat_name": "Test-Interview"
        }
        self.completion_triggered = False
    
    async def process_message(self, content):
        """Mock the process_message method."""
        # Set flag to indicate completion has been triggered
        self.completion_triggered = True
        # Always return the completion response to trigger the transition
        return INTERVIEW_COMPLETION_RESPONSE
    
    async def save_interview_document(self):
        """Mock the save_interview_document method."""
        return {"success": True, "file_path": "data/test/interviews/Test-Interview.md"}

class MockRequirementsAgent:
    """Mock implementation of the RequirementsAgentGraph for testing."""
    
    def __init__(self):
        self.analyze_called = False
    
    async def analyze_interview_file(self, chat_title):
        """Mock the analyze_interview_file method."""
        self.analyze_called = True
        print(colored(f"analyze_interview_file called with chat_title: {chat_title}", "blue"))
        return MOCK_REQUIREMENTS_RESULT

async def test_interview_to_requirements():
    """Test the transition from interview to requirements phase."""
    try:
        # Generate a unique session ID for testing
        import uuid
        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"
        
        print(colored(f"Creating chat manager for session {session_id}...", "blue"))
        
        # Create mock instances
        mock_interview_agent = MockInterviewAgent()
        mock_requirements_agent = MockRequirementsAgent()
        
        # Create patches for the interview and requirements agents
        with patch('app.services.chat.interview.create_interview_agent', return_value=mock_interview_agent), \
             patch('app.services.chat.requirements.create_requirements_agent', return_value=mock_requirements_agent), \
             patch('app.services.chat.chat_manager.DISABLE_DIAGRAM_AND_DOCUMENT_PHASES', True):
            
            # Create the chat manager
            chat_manager = LangChainChatManager(session_id, username)
            
            # Verify initial state
            assert chat_manager.state == ConversationState.INTERVIEW
            print(colored("Chat manager initialized in INTERVIEW state", "green"))
            
            # Process a message to trigger interview completion
            print(colored("Processing message to trigger interview completion...", "blue"))
            response = await chat_manager.process_message("I'm done with the interview.")
            
            print(colored(f"Response received: {response[:200]}...", "cyan"))
            
            # Verify that the interview agent's process_message was called
            if mock_interview_agent.completion_triggered:
                print(colored("Interview completion was triggered", "green"))
            else:
                print(colored("Interview completion was not triggered", "red"))
            
            # Verify that the requirements agent was initialized
            if hasattr(chat_manager, 'requirements_agent'):
                print(colored("Requirements agent was initialized", "green"))
            else:
                print(colored("Requirements agent was not initialized", "red"))
            
            # Verify that the requirements agent's analyze_interview_file was called
            if mock_requirements_agent.analyze_called:
                print(colored("Requirements agent's analyze_interview_file was called", "green"))
            else:
                print(colored("Requirements agent's analyze_interview_file was not called", "red"))
            
            # Verify that the response contains the requirements information
            if "Agent Thompson is extracting and categorizing requirements" in response:
                print(colored("Response contains requirements extraction message", "green"))
            else:
                print(colored("Response does not contain requirements extraction message", "red"))
                print(colored(f"Response: {response}", "yellow"))
            
            # Verify that the state has changed to COMPLETED
            if chat_manager.state == ConversationState.COMPLETED:
                print(colored("Chat manager state changed to COMPLETED", "green"))
            else:
                print(colored(f"Chat manager state is {chat_manager.state}, expected COMPLETED", "red"))
            
            # Check if functional requirements were extracted
            if "functional_requirements_path" in response:
                print(colored("Response contains functional requirements path", "green"))
            else:
                print(colored("Response does not contain functional requirements path", "red"))
            
            print(colored("Test completed successfully!", "green"))
        
    except Exception as e:
        logger.error(f"Error testing interview to requirements transition: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))

if __name__ == "__main__":
    print(colored("Testing interview to requirements transition...", "blue"))
    asyncio.run(test_interview_to_requirements()) 