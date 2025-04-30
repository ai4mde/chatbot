#!/usr/bin/env python
"""
Script to test the analyze_interview_file functionality.
This script analyzes an interview markdown file and generates requirements.
"""

import os
import sys
import asyncio
import logging
import json
from unittest.mock import patch, MagicMock
from termcolor import colored

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"
os.environ["CHATBOT_DATA_PATH"] = "data"

from app.services.chat.requirements import create_requirements_agent
from app.core.config import settings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Mock response for OpenAI API
MOCK_REQUIREMENTS = {
    "functional_requirements": [
        {
            "id": "FR1",
            "name": "User Registration",
            "rationale": "Allow users to create accounts",
            "description": "Users should be able to register with email and password",
            "priority": "Must Have",
        },
        {
            "id": "FR2",
            "name": "User Login",
            "rationale": "Allow users to access their accounts",
            "description": "Users should be able to login with email and password",
            "priority": "Must Have",
        },
        {
            "id": "FR3",
            "name": "Product Search",
            "rationale": "Allow users to find products",
            "description": "Users should be able to search for products by name, category, or keywords",
            "priority": "Must Have",
        },
    ],
    "non_functional_requirements": [
        {
            "id": "NFR1",
            "name": "Performance",
            "rationale": "Ensure good user experience",
            "description": "The system should respond within 2 seconds",
            "priority": "Should Have",
        },
        {
            "id": "NFR2",
            "name": "Security",
            "rationale": "Protect user data",
            "description": "The system should use encryption for sensitive data",
            "priority": "Must Have",
        },
    ],
}


def list_available_interviews():
    """List all available interview files in the data directory."""
    try:
        data_path = settings.CHATBOT_DATA_PATH
        print(colored(f"Looking for interviews in {data_path}", "blue"))

        # Check all subdirectories in the data path
        for group_dir in os.listdir(data_path):
            group_path = os.path.join(data_path, group_dir)
            if os.path.isdir(group_path):
                interviews_path = os.path.join(group_path, "interviews")
                if os.path.exists(interviews_path) and os.path.isdir(interviews_path):
                    print(colored(f"\nGroup: {group_dir}", "cyan"))
                    interviews = os.listdir(interviews_path)
                    if interviews:
                        print(colored("Available interviews:", "green"))
                        for i, interview in enumerate(interviews, 1):
                            if interview.endswith(".md"):
                                print(colored(f"  {i}. {interview}", "green"))
                    else:
                        print(colored("  No interviews found", "yellow"))
    except Exception as e:
        print(colored(f"Error listing interviews: {str(e)}", "red"))


# Create a proper mock for the ChatOpenAI class
class MockChatOpenAI(BaseChatModel):
    """Mock implementation of ChatOpenAI for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Mock the generate method."""
        mock_message = AIMessage(content=json.dumps(MOCK_REQUIREMENTS))
        return {"generations": [[mock_message]]}

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        """Mock the async generate method."""
        mock_message = AIMessage(content=json.dumps(MOCK_REQUIREMENTS))
        return {"generations": [[mock_message]]}

    @property
    def _llm_type(self):
        """Return the type of LLM."""
        return "mock-chat"

    def _identifying_params(self):
        """Return identifying parameters."""
        return {"model": "mock-chat-model"}

    def invoke(self, input, config=None):
        """Mock the invoke method."""
        return AIMessage(content=json.dumps(MOCK_REQUIREMENTS))

    async def ainvoke(self, input, config=None):
        """Mock the async invoke method."""
        return AIMessage(content=json.dumps(MOCK_REQUIREMENTS))


async def test_analyze_interview():
    """Test analyzing an interview markdown file."""
    try:
        # Generate a unique session ID for testing
        import uuid

        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"

        print(
            colored(f"Creating requirements agent for session {session_id}...", "blue")
        )
        agent = create_requirements_agent(session_id, username)

        # List available interviews
        list_available_interviews()

        # Specify the chat title to analyze
        chat_title = input(
            colored("\nEnter the interview filename to analyze: ", "yellow")
        )
        if not chat_title:
            chat_title = "Interview-test"
            print(colored(f"Using default chat title: {chat_title}", "yellow"))

        # Analyze the interview markdown file
        print(colored(f"Analyzing interview markdown file: {chat_title}...", "blue"))

        # Patch the ChatOpenAI class with our mock
        with patch(
            "app.services.chat.requirements.requirements_agent_graph.ChatOpenAI",
            MockChatOpenAI,
        ):
            result = await agent.analyze_interview_file(chat_title)

        # Print the result
        if "error" in result:
            print(colored(f"Error: {result['error']}", "red"))

            # Suggest solutions
            print(colored("\nPossible solutions:", "yellow"))
            print(
                colored(
                    "1. Make sure you entered the correct filename (including .md extension if needed)",
                    "yellow",
                )
            )
            print(
                colored(
                    "2. Check that the file exists in one of the group interview directories",
                    "yellow",
                )
            )
            print(
                colored("3. Verify that the file has the correct permissions", "yellow")
            )
        else:
            print(colored("Analysis completed successfully!", "green"))
            print(colored(f"Message: {result.get('message', 'No message')}", "green"))
            print(
                colored(
                    f"Functional Requirements: {result.get('functional_requirements_path', 'Not available')}",
                    "green",
                )
            )
            print(
                colored(
                    f"Non-Functional Requirements: {result.get('non_functional_requirements_path', 'Not available')}",
                    "green",
                )
            )

            # Print the number of requirements
            functional_reqs = result.get("functional_requirements", [])
            non_functional_reqs = result.get("non_functional_requirements", [])
            print(
                colored(
                    f"Extracted {len(functional_reqs)} functional requirements and {len(non_functional_reqs)} non-functional requirements",
                    "green",
                )
            )

    except Exception as e:
        logger.error(f"Error testing analyze_interview_file: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))


if __name__ == "__main__":
    print(colored("Testing analyze_interview_file functionality...", "blue"))
    asyncio.run(test_analyze_interview())
