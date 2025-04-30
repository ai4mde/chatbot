#!/usr/bin/env python
"""
Script to test the introduction message in a new chat session.
"""

import os
import sys
import asyncio
import logging
import uuid
from termcolor import colored

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"
os.environ["CHATBOT_DATA_PATH"] = "data"

from app.services.chat.interview import create_interview_agent
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_introduction():
    """Test the introduction message in a new chat session."""
    try:
        # Generate a unique session ID to ensure we get a fresh session
        session_id = f"test-intro-{uuid.uuid4()}"
        print(colored(f"Creating new chat session with ID: {session_id}", "blue"))

        # Create the agent
        agent = create_interview_agent(session_id, "test-user")

        # Send the first message
        print(colored("\nSending first message...", "blue"))
        response = await agent.process_message("Hello")

        # Print the response
        print(colored("Response:", "green"))
        print(colored(response, "green"))

        # Check if the response contains the introduction text
        # Look for patterns in the new format with time-based greeting
        has_greeting = any(
            greeting in response
            for greeting in ["Good morning", "Good afternoon", "Good evening"]
        )
        has_agent_name = settings.AGENT_SMITH_NAME in response
        has_capitalized_username = "Test-user" in response
        has_question_prompt = "Let's begin with our first question" in response

        if has_greeting and has_agent_name and has_question_prompt:
            print(
                colored(
                    "\n✅ Success: Introduction message is displayed correctly", "green"
                )
            )
            if has_capitalized_username:
                print(colored("✅ Username is properly capitalized", "green"))
            else:
                print(
                    colored(
                        "❌ Username capitalization may not be working correctly",
                        "yellow",
                    )
                )
        else:
            print(
                colored(
                    "\n❌ Error: Introduction message is not displayed correctly", "red"
                )
            )
            if not has_greeting:
                print(colored("  - Missing time-based greeting", "red"))
            if not has_agent_name:
                print(
                    colored(
                        f"  - Missing agent name ({settings.AGENT_SMITH_NAME})", "red"
                    )
                )
            if not has_question_prompt:
                print(colored("  - Missing question prompt", "red"))

    except Exception as e:
        logger.error(f"Error testing introduction: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))


if __name__ == "__main__":
    print(colored("Testing introduction message...", "blue"))
    asyncio.run(test_introduction())
