#!/usr/bin/env python
"""
Script to test the save_interview_document functionality.
This script simulates the completion of an interview and tests saving the document.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"
os.environ["CHATBOT_DATA_PATH"] = "data"

from app.services.chat.interview import create_interview_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_save_interview():
    """Test saving an interview document."""
    try:
        # Generate a unique session ID for testing
        import uuid

        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"

        print(colored(f"Creating interview agent for session {session_id}...", "blue"))
        agent = create_interview_agent(session_id, username)

        # Simulate a completed interview by adding some test messages
        print(colored("Simulating a completed interview...", "blue"))

        # First message to start the interview
        await agent.process_message("Hello")

        # Add some test messages
        test_messages = [
            "I'm working on a project management system.",
            "It's for tracking tasks and deadlines.",
            "next",
            "The main features include task assignment and progress tracking.",
            "next",
        ]

        for msg in test_messages:
            print(colored(f"Processing message: {msg}", "blue"))
            response = await agent.process_message(msg)
            print(colored(f"Response: {response[:100]}...", "green"))

        # Test saving the interview document
        print(colored("\nTesting save_interview_document...", "blue"))
        chat_title = f"Test-Interview-{session_id[:8]}"
        result = await agent.save_interview_document(chat_title)

        print(colored(f"Result: {result}", "green"))

    except Exception as e:
        logger.error(f"Error testing save_interview_document: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))


if __name__ == "__main__":
    print(colored("Testing save_interview_document functionality...", "blue"))
    asyncio.run(test_save_interview())
