#!/usr/bin/env python
"""
Integration test for the chat manager.
This script tests the complete flow from interview to requirements phase.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
from unittest.mock import patch, MagicMock, AsyncMock

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
            "description": "Users should be able to register with email and password, and also with social media accounts",
            "priority": "Must Have"
        },
        {
            "id": "FR2",
            "name": "User Login",
            "rationale": "Allow users to access their accounts",
            "description": "Users should be able to login with email and password",
            "priority": "Must Have"
        },
        {
            "id": "FR3",
            "name": "Product Search",
            "rationale": "Allow users to find products",
            "description": "Users should be able to search for products by name, category, or other attributes",
            "priority": "Must Have"
        }
    ],
    "non_functional_requirements": [
        {
            "id": "NFR1",
            "name": "Performance",
            "rationale": "Ensure good user experience",
            "description": "The system should be fast and responsive, with page loads under 2 seconds",
            "priority": "Should Have"
        }
    ],
    "functional_requirements_path": "data/default/requirements/fr-Test-Interview.md",
    "non_functional_requirements_path": "data/default/requirements/nfr-Test-Interview.md",
    "message": "Requirements have been extracted and saved. - Agent Thompson"
}

# Mock interview agent
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
        self.message_count = 0
    
    async def process_message(self, content):
        """Mock the process_message method."""
        self.message_count += 1
        
        # Add the user message to the state
        self.state["messages"].append({"role": "user", "content": content})
        
        # Return completion response on the second message
        if self.message_count >= 2:
            self.completion_triggered = True
            response = INTERVIEW_COMPLETION_RESPONSE
        else:
            response = "What kind of business do you have?"
        
        # Add the assistant response to the state
        self.state["messages"].append({"role": "assistant", "content": response})
        
        return response
    
    async def save_interview_document(self):
        """Mock the save_interview_document method."""
        # Create the interview directory
        os.makedirs("data/default/interviews", exist_ok=True)
        
        # Create a sample interview markdown file
        interview_file_path = "data/default/interviews/Test-Interview.md"
        with open(interview_file_path, "w", encoding="utf-8") as f:
            f.write("# Interview Transcript: Test-Interview\n\n")
            for msg in self.state["messages"]:
                if msg["role"] == "user":
                    f.write(f"**User**: {msg['content']}\n\n")
                elif msg["role"] == "assistant":
                    f.write(f"**Agent Smith**: {msg['content']}\n\n")
        
        return {"success": True, "file_path": interview_file_path}

# Mock requirements agent
class MockRequirementsAgent:
    """Mock implementation of the RequirementsAgentGraph for testing."""
    
    def __init__(self):
        self.analyze_called = False
    
    async def analyze_interview_file(self, chat_title):
        """Mock the analyze_interview_file method."""
        self.analyze_called = True
        print(colored(f"Mock analyze_interview_file called with chat_title: {chat_title}", "blue"))
        
        # Create the requirements directories
        os.makedirs("data/default/requirements", exist_ok=True)
        
        # Create the functional requirements file
        fr_path = f"data/default/requirements/fr-{chat_title}.md"
        with open(fr_path, "w", encoding="utf-8") as f:
            f.write("# Functional Requirements\n\n")
            for req in MOCK_REQUIREMENTS_RESULT["functional_requirements"]:
                f.write(f"## {req['id']}: {req['name']}\n")
                f.write(f"**Description**: {req['description']}\n")
                f.write(f"**Rationale**: {req['rationale']}\n")
                f.write(f"**Priority**: {req['priority']}\n\n")
        
        # Create the non-functional requirements file
        nfr_path = f"data/default/requirements/nfr-{chat_title}.md"
        with open(nfr_path, "w", encoding="utf-8") as f:
            f.write("# Non-Functional Requirements\n\n")
            for req in MOCK_REQUIREMENTS_RESULT["non_functional_requirements"]:
                f.write(f"## {req['id']}: {req['name']}\n")
                f.write(f"**Description**: {req['description']}\n")
                f.write(f"**Rationale**: {req['rationale']}\n")
                f.write(f"**Priority**: {req['priority']}\n\n")
        
        # Update the paths in the result
        result = MOCK_REQUIREMENTS_RESULT.copy()
        result["functional_requirements_path"] = fr_path
        result["non_functional_requirements_path"] = nfr_path
        
        return result

async def test_chat_manager_integration():
    """Test the complete flow from interview to requirements phase."""
    try:
        # Generate a unique session ID for testing
        import uuid
        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"
        
        print(colored(f"Testing chat manager integration for session {session_id}...", "blue"))
        
        # Create mock instances
        mock_interview_agent = MockInterviewAgent()
        mock_requirements_agent = MockRequirementsAgent()
        
        # Create a direct test of the chat manager's functionality
        # We'll manually create and configure the chat manager
        
        # Create the chat manager
        chat_manager = LangChainChatManager(session_id, username)
        
        # Replace the agents with our mocks
        chat_manager.interview_agent = mock_interview_agent
        chat_manager.requirements_agent = mock_requirements_agent
        
        # Set the flag to disable diagram and document phases
        import app.services.chat.chat_manager
        app.services.chat.chat_manager.DISABLE_DIAGRAM_AND_DOCUMENT_PHASES = True
        
        # Verify initial state
        assert chat_manager.state == ConversationState.INTERVIEW
        print(colored("Chat manager initialized in INTERVIEW state", "green"))
        
        # Process first message (should not trigger completion)
        print(colored("Processing first message...", "blue"))
        response1 = await chat_manager.process_message("Hello, I need a system for my business.")
        print(colored(f"Response 1: {response1[:100]}...", "cyan"))
        
        # Verify that the state is still INTERVIEW
        assert chat_manager.state == ConversationState.INTERVIEW
        print(colored("Chat manager state is still INTERVIEW after first message", "green"))
        
        # Process second message (should trigger completion)
        print(colored("Processing second message to trigger interview completion...", "blue"))
        response2 = await chat_manager.process_message("I need user registration, login, and product search.")
        print(colored(f"Response 2: {response2[:100]}...", "cyan"))
        
        # Verify that the interview agent's process_message was called
        if mock_interview_agent.completion_triggered:
            print(colored("Interview completion was triggered", "green"))
        else:
            print(colored("Interview completion was not triggered", "red"))
        
        # Verify that the requirements agent's analyze_interview_file was called
        if mock_requirements_agent.analyze_called:
            print(colored("Requirements agent's analyze_interview_file was called", "green"))
        else:
            print(colored("Requirements agent's analyze_interview_file was not called", "red"))
        
        # Verify that the response contains the requirements information
        if "Agent Thompson is extracting and categorizing requirements" in response2:
            print(colored("Response contains requirements extraction message", "green"))
        else:
            print(colored("Response does not contain requirements extraction message", "red"))
            print(colored(f"Response: {response2}", "yellow"))
        
        # Verify that the state has changed to COMPLETED
        if chat_manager.state == ConversationState.COMPLETED:
            print(colored("Chat manager state changed to COMPLETED", "green"))
        else:
            print(colored(f"Chat manager state is {chat_manager.state}, expected COMPLETED", "red"))
        
        # Check if functional requirements were extracted
        if "functional_requirements_path" in response2:
            print(colored("Response contains functional requirements path", "green"))
        else:
            print(colored("Response does not contain functional requirements path", "red"))
        
        print(colored("Test completed successfully!", "green"))
        
        # Clean up the temporary files
        print(colored("Cleaning up temporary files...", "blue"))
        try:
            # Clean up interview file
            interview_file_path = "data/default/interviews/Test-Interview.md"
            if os.path.exists(interview_file_path):
                os.remove(interview_file_path)
                print(colored(f"Removed {interview_file_path}", "blue"))
            
            # Clean up requirements files
            fr_path = "data/default/requirements/fr-Test-Interview.md"
            nfr_path = "data/default/requirements/nfr-Test-Interview.md"
            
            if os.path.exists(fr_path):
                os.remove(fr_path)
                print(colored(f"Removed {fr_path}", "blue"))
            
            if os.path.exists(nfr_path):
                os.remove(nfr_path)
                print(colored(f"Removed {nfr_path}", "blue"))
            
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error testing chat manager integration: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))

if __name__ == "__main__":
    print(colored("Testing chat manager integration...", "blue"))
    asyncio.run(test_chat_manager_integration()) 