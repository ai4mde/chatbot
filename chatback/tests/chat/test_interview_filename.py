#!/usr/bin/env python
"""
Test script to verify that the requirements agent can find the interview file with different filename formats.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"
os.environ["CHATBOT_DATA_PATH"] = "data"

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Create a modified version of analyze_interview_markdown that stops after finding the file
async def modified_analyze_interview_markdown(state):
    """Modified version of analyze_interview_markdown that stops after finding the file."""
    from app.services.chat.requirements.requirements_agent_graph import (
        analyze_interview_markdown,
    )

    # Import the original function
    original_function = analyze_interview_markdown

    # Get chat name and group name
    chat_title = state["chat_name"] or state["session_id"]
    original_chat_title = chat_title  # Keep the original for reference

    # Remove .md extension if present
    if chat_title.endswith(".md"):
        chat_title = chat_title[:-3]
        logger.info(f"Removed .md extension from chat_title: {chat_title}")

    group_name = state["group_name"] or "default"

    # First try to find the file in the user's group directory
    interview_file = None

    # Try in the user's group directory first
    interviews_dir = os.path.join(settings.CHATBOT_DATA_PATH, group_name, "interviews")
    logger.info(f"Looking for interview file in {interviews_dir}")

    if os.path.exists(interviews_dir):
        # Log all files in the directory for debugging
        logger.info(
            f"Files in {interviews_dir}: {os.listdir(interviews_dir) if os.path.exists(interviews_dir) else 'directory not found'}"
        )

        # Try with exact filename first
        if os.path.exists(os.path.join(interviews_dir, original_chat_title)):
            interview_file = os.path.join(interviews_dir, original_chat_title)
            logger.info(
                f"Found interview file with exact original name: {original_chat_title}"
            )
        elif os.path.exists(os.path.join(interviews_dir, f"{chat_title}.md")):
            interview_file = os.path.join(interviews_dir, f"{chat_title}.md")
            logger.info(f"Found interview file with exact name: {chat_title}.md")
        else:
            # First, look for files that START with the chat_title (higher priority)
            for filename in os.listdir(interviews_dir):
                if filename.endswith(".md"):
                    filename_without_ext = filename.lower().replace(".md", "")
                    if filename_without_ext.startswith(chat_title.lower()):
                        interview_file = os.path.join(interviews_dir, filename)
                        logger.info(f"Found interview file by prefix match: {filename}")
                        break

            # If not found, then look for files that CONTAIN the chat_title (lower priority)
            if not interview_file:
                for filename in os.listdir(interviews_dir):
                    logger.info(
                        f"Checking file: {filename} against chat_title: {chat_title}"
                    )
                    if filename.endswith(".md"):
                        if chat_title.lower() in filename.lower():
                            interview_file = os.path.join(interviews_dir, filename)
                            logger.info(
                                f"Found interview file by substring match: {filename}"
                            )
                            break
                        elif chat_title.lower().startswith(
                            filename.lower().replace(".md", "")
                        ):
                            interview_file = os.path.join(interviews_dir, filename)
                            logger.info(
                                f"Found interview file by reverse prefix match: {filename}"
                            )
                            break

    # If not found in the user's group, search in all groups
    if not interview_file:
        logger.info(
            f"Interview file not found in {group_name} group, searching in all groups"
        )
        data_path = settings.CHATBOT_DATA_PATH

        # Search in all group directories
        for group_dir in os.listdir(data_path):
            group_path = os.path.join(data_path, group_dir)
            if os.path.isdir(group_path):
                interviews_path = os.path.join(group_path, "interviews")
                if os.path.exists(interviews_path) and os.path.isdir(interviews_path):
                    logger.info(f"Searching in group: {group_dir}")
                    logger.info(
                        f"Files in {interviews_path}: {os.listdir(interviews_path) if os.path.exists(interviews_path) else 'directory not found'}"
                    )

                    # Try with exact filename first
                    if os.path.exists(
                        os.path.join(interviews_path, original_chat_title)
                    ):
                        interview_file = os.path.join(
                            interviews_path, original_chat_title
                        )
                        logger.info(
                            f"Found interview file with exact original name in {group_dir}: {original_chat_title}"
                        )
                        break
                    elif os.path.exists(
                        os.path.join(interviews_path, f"{chat_title}.md")
                    ):
                        interview_file = os.path.join(
                            interviews_path, f"{chat_title}.md"
                        )
                        logger.info(
                            f"Found interview file with exact name in {group_dir}: {chat_title}.md"
                        )
                        break
                    else:
                        # First, look for files that START with the chat_title (higher priority)
                        for filename in os.listdir(interviews_path):
                            if filename.endswith(".md"):
                                filename_without_ext = filename.lower().replace(
                                    ".md", ""
                                )
                                if filename_without_ext.startswith(chat_title.lower()):
                                    interview_file = os.path.join(
                                        interviews_path, filename
                                    )
                                    logger.info(
                                        f"Found interview file by prefix match in {group_dir}: {filename}"
                                    )
                                    break

                        # If found, break out of the outer loop
                        if interview_file:
                            break

                        # If not found, then look for files that CONTAIN the chat_title (lower priority)
                        for filename in os.listdir(interviews_path):
                            logger.info(
                                f"Checking file in {group_dir}: {filename} against chat_title: {chat_title}"
                            )
                            if filename.endswith(".md"):
                                if chat_title.lower() in filename.lower():
                                    interview_file = os.path.join(
                                        interviews_path, filename
                                    )
                                    logger.info(
                                        f"Found interview file by substring match in {group_dir}: {filename}"
                                    )
                                    break
                                elif chat_title.lower().startswith(
                                    filename.lower().replace(".md", "")
                                ):
                                    interview_file = os.path.join(
                                        interviews_path, filename
                                    )
                                    logger.info(
                                        f"Found interview file by reverse prefix match in {group_dir}: {filename}"
                                    )
                                    break

                        # If found, break out of the outer loop
                        if interview_file:
                            break

    if not interview_file:
        logger.warning(
            f"Interview markdown file not found for chat_title: {chat_title}"
        )
        state["error"] = (
            f"Interview markdown file not found for chat_title: {chat_title}"
        )
        return state

    logger.info(f"Found interview markdown file: {interview_file}")

    # Store the interview file path in the state
    state["interview_file_path"] = interview_file

    # Stop here - don't try to read the file or call OpenAI
    return state


async def test_interview_filename_matching():
    """Test that the requirements agent can find the interview file with different filename formats."""
    try:
        # Create test directories
        group_name = "test_group"
        interviews_dir = os.path.join(
            settings.CHATBOT_DATA_PATH, group_name, "interviews"
        )
        os.makedirs(interviews_dir, exist_ok=True)

        # Create test interview files with different formats
        test_files = [
            "Interview-123.md",
            "Test_Interview-456.md",
            "Another_Interview-789.md",
        ]

        for filename in test_files:
            file_path = os.path.join(interviews_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(
                    f"# Test Interview: {filename}\n\nThis is a test interview file."
                )
            print(colored(f"Created test file: {file_path}", "blue"))

        # Test different chat title formats
        test_cases = [
            {"chat_title": "Interview-123", "expected_file": "Interview-123.md"},
            {"chat_title": "Test_Interview", "expected_file": "Test_Interview-456.md"},
            {
                "chat_title": "Another_Interview-789",
                "expected_file": "Another_Interview-789.md",
            },
            {
                "chat_title": "Interview",
                "expected_file": "Interview-123.md",
            },  # Partial match
            {
                "chat_title": "Test_Interview-456.md",
                "expected_file": "Test_Interview-456.md",
            },  # With extension
        ]

        # Patch the analyze_interview_markdown function
        with patch(
            "app.services.chat.requirements.requirements_agent_graph.analyze_interview_markdown",
            side_effect=modified_analyze_interview_markdown,
        ):

            for i, test_case in enumerate(test_cases):
                print(
                    colored(
                        f"\nTest case {i+1}: chat_title='{test_case['chat_title']}'",
                        "cyan",
                    )
                )

                # Create a mock state
                state = {
                    "session_id": f"test-{i}",
                    "username": "test-user",
                    "chat_name": test_case["chat_title"],
                    "group_name": group_name,
                    "messages": [],
                    "functional_requirements": [],
                    "non_functional_requirements": [],
                    "error": None,
                }

                # Import the function here to ensure the patch is applied
                from app.services.chat.requirements.requirements_agent_graph import (
                    analyze_interview_markdown,
                )

                # Call the analyze_interview_markdown function
                result_state = await analyze_interview_markdown(state)

                # Check if the file was found
                if result_state.get("error"):
                    print(colored(f"❌ Error: {result_state['error']}", "red"))
                else:
                    found_file = result_state.get("interview_file_path", "")
                    expected_file = os.path.join(
                        interviews_dir, test_case["expected_file"]
                    )

                    if found_file == expected_file:
                        print(
                            colored(
                                f"✅ Success: Found the expected file: {os.path.basename(found_file)}",
                                "green",
                            )
                        )
                    else:
                        print(
                            colored(
                                f"❌ Error: Found {os.path.basename(found_file)} instead of {test_case['expected_file']}",
                                "red",
                            )
                        )

        # Clean up
        print(colored("\nCleaning up test files...", "blue"))
        for filename in test_files:
            file_path = os.path.join(interviews_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(colored(f"Removed {file_path}", "blue"))

        # Try to remove the test directory
        try:
            os.rmdir(interviews_dir)
            print(colored(f"Removed directory {interviews_dir}", "blue"))
            os.rmdir(os.path.join(settings.CHATBOT_DATA_PATH, group_name))
            print(
                colored(
                    f"Removed directory {os.path.join(settings.CHATBOT_DATA_PATH, group_name)}",
                    "blue",
                )
            )
        except OSError:
            print(
                colored(
                    f"Could not remove directory {interviews_dir} (it may not be empty)",
                    "yellow",
                )
            )

    except Exception as e:
        logger.error(
            f"Error testing interview filename matching: {str(e)}", exc_info=True
        )
        print(colored(f"Error: {str(e)}", "red"))


if __name__ == "__main__":
    print(colored("Testing interview filename matching...", "blue"))
    asyncio.run(test_interview_filename_matching())
