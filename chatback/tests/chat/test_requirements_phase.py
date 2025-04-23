#!/usr/bin/env python
"""
Script to test the requirements phase functionality.
This script directly tests the requirements agent's ability to analyze an interview markdown file.
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

from app.services.chat.requirements import create_requirements_agent
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample interview markdown content
SAMPLE_INTERVIEW_MARKDOWN = """
# Interview Transcript: Test-Interview

## Introduction
**Agent Smith**: Hello, I'm Agent Smith. I'll be conducting this interview to gather requirements for your software project.
**User**: Hello, I need a system for my business.

## Business Context
**Agent Smith**: What kind of business do you have?
**User**: I have an e-commerce business.

## Functional Requirements
**Agent Smith**: What features do you need?
**User**: I need user registration, login, and product search.
**Agent Smith**: Any specific requirements for the user registration?
**User**: Yes, users should be able to register with email and password, and also with social media accounts.

## Non-Functional Requirements
**Agent Smith**: What performance expectations do you have?
**User**: The system should be fast and responsive, with page loads under 2 seconds.

## Conclusion
**Agent Smith**: Thank you for completing this comprehensive interview. Your responses have provided valuable insights into your project requirements.
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

# Mock OpenAI API response
MOCK_OPENAI_RESPONSE = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "gpt-4o",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": """
Based on the interview transcript, I've identified the following requirements:

## Functional Requirements:
1. User Registration - Users should be able to register with email and password, and also with social media accounts
2. User Login - Users should be able to login with email and password
3. Product Search - Users should be able to search for products by name, category, or other attributes

## Non-Functional Requirements:
1. Performance - The system should be fast and responsive, with page loads under 2 seconds
"""
            },
            "finish_reason": "stop",
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 200,
        "total_tokens": 300
    }
}

class MockAsyncResponse:
    def __init__(self, data):
        self.data = data
    
    async def json(self):
        return self.data
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

async def mock_acreate(*args, **kwargs):
    """Mock the OpenAI API acreate method."""
    print(colored("Mock OpenAI API called", "blue"))
    return MOCK_OPENAI_RESPONSE

async def mock_analyze_interview_markdown(state):
    """Mock the analyze_interview_markdown function."""
    print(colored("Mock analyze_interview_markdown called", "blue"))
    
    # Update the state with mock requirements
    state["functional_requirements"] = MOCK_REQUIREMENTS_RESULT["functional_requirements"]
    state["non_functional_requirements"] = MOCK_REQUIREMENTS_RESULT["non_functional_requirements"]
    
    return state

async def mock_save_requirements(state):
    """Mock the save_requirements function."""
    print(colored(f"Mock save_requirements called with chat_title: {state.get('chat_name', 'unknown')}", "blue"))
    
    # Create the requirements directories
    os.makedirs("data/default/requirements", exist_ok=True)
    
    # Create the functional requirements file
    chat_title = state.get("chat_name", "Test-Interview")
    fr_path = f"data/default/requirements/fr-{chat_title}.md"
    with open(fr_path, "w", encoding="utf-8") as f:
        f.write("# Functional Requirements\n\n")
        for req in state["functional_requirements"]:
            f.write(f"## {req['id']}: {req['name']}\n")
            f.write(f"**Description**: {req['description']}\n")
            f.write(f"**Rationale**: {req['rationale']}\n")
            f.write(f"**Priority**: {req['priority']}\n\n")
    
    # Create the non-functional requirements file
    nfr_path = f"data/default/requirements/nfr-{chat_title}.md"
    with open(nfr_path, "w", encoding="utf-8") as f:
        f.write("# Non-Functional Requirements\n\n")
        for req in state["non_functional_requirements"]:
            f.write(f"## {req['id']}: {req['name']}\n")
            f.write(f"**Description**: {req['description']}\n")
            f.write(f"**Rationale**: {req['rationale']}\n")
            f.write(f"**Priority**: {req['priority']}\n\n")
    
    # Update the state with file paths
    state["functional_requirements_path"] = fr_path
    state["non_functional_requirements_path"] = nfr_path
    
    return state

async def mock_prepare_result(state):
    """Mock the prepare_result function."""
    print(colored("Mock prepare_result called", "blue"))
    
    # Prepare the result
    state["result"] = {
        "functional_requirements": state["functional_requirements"],
        "non_functional_requirements": state["non_functional_requirements"],
        "functional_requirements_path": state["functional_requirements_path"],
        "non_functional_requirements_path": state["non_functional_requirements_path"],
        "message": "Requirements have been extracted and saved. - Agent Thompson"
    }
    
    return state

async def test_requirements_phase():
    """Test the requirements phase functionality."""
    try:
        # Generate a unique session ID for testing
        import uuid
        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"
        chat_title = "Test-Interview"
        
        print(colored(f"Testing requirements phase for session {session_id}...", "blue"))
        
        # Create a temporary interview markdown file
        os.makedirs("data/default/interviews", exist_ok=True)
        interview_file_path = f"data/default/interviews/{chat_title}.md"
        
        print(colored(f"Creating temporary interview file at {interview_file_path}", "blue"))
        with open(interview_file_path, "w", encoding="utf-8") as f:
            f.write(SAMPLE_INTERVIEW_MARKDOWN)
        
        # Create the requirements directories
        os.makedirs("data/default/requirements", exist_ok=True)
        
        try:
            # Patch the OpenAI API calls and the requirements agent functions
            with patch('openai.resources.chat.completions.AsyncCompletions.create', new=mock_acreate), \
                 patch('app.services.chat.requirements.requirements_agent_graph.analyze_interview_markdown', new=mock_analyze_interview_markdown), \
                 patch('app.services.chat.requirements.requirements_agent_graph.save_requirements', new=mock_save_requirements), \
                 patch('app.services.chat.requirements.requirements_agent_graph.prepare_result', new=mock_prepare_result):
                
                # Create the requirements agent
                print(colored("Creating requirements agent...", "blue"))
                requirements_agent = create_requirements_agent(session_id, username)
                
                # Analyze the interview markdown file
                print(colored(f"Analyzing interview markdown file for chat_title: {chat_title}", "blue"))
                requirements_result = await requirements_agent.analyze_interview_file(chat_title)
                
                # Print the result
                print(colored("Requirements extraction result:", "cyan"))
                print(colored(f"Message: {requirements_result.get('message', 'No message')}", "cyan"))
                
                # Check if requirements were extracted
                functional_reqs = requirements_result.get("functional_requirements", [])
                non_functional_reqs = requirements_result.get("non_functional_requirements", [])
                
                print(colored(f"Extracted {len(functional_reqs)} functional requirements:", "green"))
                for req in functional_reqs:
                    print(colored(f"  - {req.get('id')}: {req.get('name')} - {req.get('description')}", "green"))
                
                print(colored(f"Extracted {len(non_functional_reqs)} non-functional requirements:", "green"))
                for req in non_functional_reqs:
                    print(colored(f"  - {req.get('id')}: {req.get('name')} - {req.get('description')}", "green"))
                
                # Check if the requirements files were created
                fr_path = requirements_result.get("functional_requirements_path", "")
                nfr_path = requirements_result.get("non_functional_requirements_path", "")
                
                if os.path.exists(fr_path):
                    print(colored(f"Functional requirements file created at: {fr_path}", "green"))
                    # Print the content of the file
                    with open(fr_path, "r", encoding="utf-8") as f:
                        print(colored(f"Content of functional requirements file:", "cyan"))
                        print(colored(f.read()[:200] + "...", "cyan"))
                else:
                    print(colored(f"Functional requirements file not created at: {fr_path}", "red"))
                
                if os.path.exists(nfr_path):
                    print(colored(f"Non-functional requirements file created at: {nfr_path}", "green"))
                    # Print the content of the file
                    with open(nfr_path, "r", encoding="utf-8") as f:
                        print(colored(f"Content of non-functional requirements file:", "cyan"))
                        print(colored(f.read()[:200] + "...", "cyan"))
                else:
                    print(colored(f"Non-functional requirements file not created at: {nfr_path}", "red"))
                
                print(colored("Test completed successfully!", "green"))
            
        finally:
            # Clean up the temporary files
            print(colored("Cleaning up temporary files...", "blue"))
            try:
                if os.path.exists(interview_file_path):
                    os.remove(interview_file_path)
                    print(colored(f"Removed {interview_file_path}", "blue"))
                
                # Clean up requirements files if they were created
                fr_path = f"data/default/requirements/fr-{chat_title}.md"
                nfr_path = f"data/default/requirements/nfr-{chat_title}.md"
                
                if os.path.exists(fr_path):
                    os.remove(fr_path)
                    print(colored(f"Removed {fr_path}", "blue"))
                
                if os.path.exists(nfr_path):
                    os.remove(nfr_path)
                    print(colored(f"Removed {nfr_path}", "blue"))
                
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error testing requirements phase: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))

if __name__ == "__main__":
    print(colored("Testing requirements phase functionality...", "blue"))
    asyncio.run(test_requirements_phase()) 