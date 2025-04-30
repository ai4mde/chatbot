#!/usr/bin/env python
"""
Test script for the LangGraph-based interview agent.
This script allows testing the LangGraph implementation without affecting the production system.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
import httpx

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

# Create a single event loop for all tests
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


async def run_tests():
    """Run all tests in sequence with proper cleanup."""
    try:
        # Run the simple test first
        simple_success = await test_interview_simple()

        # Only run the full test if the simple test succeeds
        if simple_success:
            full_success = await test_interview_full()

        print(colored("\nAll tests completed.", "blue", attrs=["bold"]))
    finally:
        # Ensure all pending tasks are completed
        pending = asyncio.all_tasks(loop)
        for task in pending:
            if not task.done() and task != asyncio.current_task():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error cancelling task: {str(e)}")


async def test_interview_simple():
    """Test the interview agent with a simple conversation."""
    try:
        print(colored("\n=== SIMPLE TEST ===", "blue", attrs=["bold"]))
        print(colored("Creating interview agent...", "blue"))
        agent = create_interview_agent("test-simple", "test-user")

        print(colored("\nStarting interview...", "blue"))
        # First message to start the interview
        response = await agent.process_message("Hello")
        print(colored(f"Agent: {response}", "green"))

        # Just a couple of exchanges to test basic functionality
        user_responses = [
            "I'm working on a project management system.",
            "next",
            "It's a web-based application.",
            "next",
        ]

        for i, msg in enumerate(user_responses):
            print(colored(f"\nUser: {msg}", "yellow"))
            response = await agent.process_message(msg)
            print(colored(f"Agent: {response}", "green"))

            # Show progress after each exchange
            progress = agent.calculate_progress()
            print(colored(f"Progress: {progress:.1f}%", "blue"))

            # Small delay to make it more readable
            await asyncio.sleep(1)

        print(colored("\nSimple test completed successfully!", "blue", attrs=["bold"]))

        # Allow time for any pending HTTP connections to close
        await asyncio.sleep(1)

        return True

    except Exception as e:
        logger.error(f"Error in simple test: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


async def test_interview_full():
    """Test the interview agent with a full conversation."""
    try:
        print(colored("\n=== FULL TEST ===", "blue", attrs=["bold"]))
        print(colored("Creating interview agent...", "blue"))
        agent = create_interview_agent("test-full", "test-user")

        print(colored("\nStarting interview...", "blue"))
        # First message to start the interview
        response = await agent.process_message("Hello")
        print(colored(f"Agent: {response}", "green"))

        # Simulate user responses
        user_responses = [
            "I'm working on a project management system for a small team.",
            "The main goal is to improve collaboration and task tracking.",
            "next",
            "We need features like task assignment, progress tracking, and file sharing.",
            "next",
            "The target users are small teams of 5-10 people.",
            "next",
            "We're looking to launch in about 3 months.",
            "next",
        ]

        for i, msg in enumerate(user_responses):
            print(colored(f"\nUser: {msg}", "yellow"))
            response = await agent.process_message(msg)
            print(colored(f"Agent: {response}", "green"))

            # Show progress after each exchange
            progress = agent.calculate_progress()
            print(colored(f"Progress: {progress:.1f}%", "blue"))

            # Small delay to make it more readable
            await asyncio.sleep(1)

        print(colored("\nFull test completed successfully!", "blue", attrs=["bold"]))

        # Allow time for any pending HTTP connections to close
        await asyncio.sleep(1)

        return True

    except Exception as e:
        logger.error(f"Error in full test: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


if __name__ == "__main__":
    print(colored("Testing LangGraph-based interview agent...", "blue", attrs=["bold"]))

    try:
        # Run all tests in a single event loop
        loop.run_until_complete(run_tests())
    finally:
        # Clean up resources
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
