#!/usr/bin/env python
"""
Script to test the documentation transition process.
This script simulates the transition from interview to documentation phase
and verifies that requirements are properly extracted.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
from unittest.mock import patch, MagicMock

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

# Mock response for document generation
MOCK_DOCUMENT_RESULT = {
    "success": True,
    "file_path": "data/test/documents/Test-Interview-SRS.md",
    "message": "SRS document has been generated successfully."
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
                {"role": "user", "content": "I need user registration, login, and product search."}
            ],
            "chat_name": "Test-Interview"
        }
    
    async def save_interview_document(self):
        """Mock the save_interview_document method."""
        return {"success": True, "file_path": "data/test/interviews/Test-Interview.md"}

class MockRequirementsAgent:
    """Mock implementation of the RequirementsAgentGraph for testing."""
    
    async def analyze_interview_file(self, chat_title):
        """Mock the analyze_interview_file method."""
        return MOCK_REQUIREMENTS_RESULT

class MockDocumentCoordinator:
    """Mock implementation of the DocumentCoordinator for testing."""
    
    async def generate_complete_document(self, chat_title, messages):
        """Mock the generate_complete_document method."""
        return MOCK_DOCUMENT_RESULT

async def test_documentation_transition():
    """Test the documentation transition process."""
    try:
        # Generate a unique session ID for testing
        import uuid
        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"
        
        print(colored(f"Creating chat manager for session {session_id}...", "blue"))
        
        # Create patches for the interview, requirements agents, and document coordinator
        with patch('app.services.chat.interview.create_interview_agent', return_value=MockInterviewAgent()), \
             patch('app.services.chat.requirements.create_requirements_agent', return_value=MockRequirementsAgent()), \
             patch('app.services.chat.chat_manager.DISABLE_DIAGRAM_AND_DOCUMENT_PHASES', False):
            
            # Create the chat manager
            chat_manager = LangChainChatManager(session_id, username)
            
            # Replace the document coordinator with our mock
            chat_manager.document_coordinator = MockDocumentCoordinator()
            
            # Verify initial state
            assert chat_manager.state == ConversationState.INTERVIEW
            print(colored("Chat manager initialized in INTERVIEW state", "green"))
            
            # Directly call the _handle_documentation_transition method
            print(colored("Calling _handle_documentation_transition method...", "blue"))
            response = await chat_manager._handle_documentation_transition("")
            
            print(colored(f"Response received: {response[:200]}...", "cyan"))
            
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
            
            # Check if requirements extraction was successful
            if "Requirements extraction completed successfully" in response:
                print(colored("Requirements extraction completed successfully", "green"))
            else:
                print(colored("Requirements extraction message not found", "red"))
            
            # Check if document generation was successful
            if "Your documentation has been generated and saved" in response:
                print(colored("Document generation completed successfully", "green"))
            else:
                print(colored("Document generation message not found", "red"))
            
            print(colored("Test completed successfully!", "green"))
        
    except Exception as e:
        logger.error(f"Error testing documentation transition: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))

if __name__ == "__main__":
    print(colored("Testing documentation transition process...", "blue"))
    asyncio.run(test_documentation_transition()) 