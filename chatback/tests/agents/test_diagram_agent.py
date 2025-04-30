#!/usr/bin/env python
"""
Script to test the LangGraph-based Diagram Agent.
This script simulates generating UML diagrams from a conversation.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
import argparse

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"
os.environ["CHATBOT_DATA_PATH"] = "data"

from app.services.chat.diagrams import create_diagram_agent, DiagramAgentGraph

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Sample conversation for testing
SAMPLE_CONVERSATION = [
    {"role": "user", "content": "I need a project management system for a small team."},
    {"role": "assistant", "content": "Could you tell me more about your requirements?"},
    {
        "role": "user",
        "content": "We need to track tasks, assign them to team members, and monitor progress.",
    },
    {"role": "assistant", "content": "What kind of users will be using the system?"},
    {
        "role": "user",
        "content": "We'll have project managers, team members, and administrators.",
    },
    {"role": "assistant", "content": "What specific features do you need?"},
    {
        "role": "user",
        "content": "We need task creation, assignment, status updates, file attachments, and reporting.",
    },
    {"role": "assistant", "content": "Any specific technical requirements?"},
    {
        "role": "user",
        "content": "It should be a web-based application with mobile support.",
    },
]


async def test_generate_diagrams():
    """Test generating UML diagrams from a sample conversation."""
    try:
        # Generate a unique session ID for testing
        import uuid

        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"

        print(colored(f"Creating diagram agent for session {session_id}...", "blue"))
        agent = create_diagram_agent(session_id, username)

        # Verify that we're using the LangGraph implementation
        if isinstance(agent, DiagramAgentGraph):
            print(colored("✅ Using LangGraph-based Diagram Agent", "green"))
        else:
            print(colored("❌ Not using LangGraph-based Diagram Agent", "red"))

        print(colored("Generating UML diagrams from sample conversation...", "blue"))
        result = await agent.generate_uml_diagrams(SAMPLE_CONVERSATION)

        print(colored("UML diagrams generated successfully!", "green"))
        print(colored(f"Message: {result['message']}", "green"))
        print(colored(f"Diagram files: {result['diagram_files']}", "green"))

        # Print a snippet of the UML content
        uml_content = result["uml_diagrams"]
        print(colored("\nUML Content Preview:", "blue"))
        print(colored(uml_content[:500] + "...", "cyan"))

        return True
    except Exception as e:
        logger.error(f"Error testing diagram agent: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


async def test_analyze_last_chat():
    """Test analyzing the last chat session."""
    try:
        # Use a real username for testing
        import uuid

        username = "test-user"
        session_id = f"analyze-{uuid.uuid4()}"

        print(
            colored(
                f"Creating diagram agent for analyzing last chat session...", "blue"
            )
        )
        agent = create_diagram_agent(session_id, username)

        # Initialize the agent
        await agent.initialize()

        print(colored(f"Mocking analyze_last_chat_session method...", "blue"))

        # Mock the analyze_last_chat_session method to avoid database access
        # We'll use the sample conversation instead
        async def mock_analyze_last_chat_session():
            print(colored(f"Using sample conversation for analysis...", "blue"))
            agent.state["chat_name"] = "Sample Project Discussion"
            return await agent.generate_uml_diagrams(SAMPLE_CONVERSATION)

        # Replace the method with our mock
        agent.analyze_last_chat_session = mock_analyze_last_chat_session

        print(colored(f"Analyzing last chat session for user {username}...", "blue"))
        result = await agent.analyze_last_chat_session()

        print(colored("Last chat session analyzed successfully!", "green"))
        print(colored(f"Message: {result['message']}", "green"))
        print(colored(f"Diagram files: {result['diagram_files']}", "green"))

        # Print a snippet of the UML content
        uml_content = result["uml_diagrams"]
        print(colored("\nUML Content Preview:", "blue"))
        print(colored(uml_content[:500] + "...", "cyan"))

        return True
    except Exception as e:
        logger.error(f"Error analyzing last chat session: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


async def test_save_diagrams():
    """Test saving diagrams to the specified directory structure."""
    try:
        # Generate a unique session ID for testing
        import uuid

        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"

        print(
            colored(
                f"Creating diagram agent for testing save_diagrams_to_directory...",
                "blue",
            )
        )
        agent = create_diagram_agent(session_id, username)

        # Create test diagrams
        test_diagrams = {
            "Class Diagram": """@startuml
class User {
  +id: String
  +name: String
  +login()
}
class Task {
  +id: String
  +title: String
  +complete()
}
User -- Task : owns
@enduml""",
            "Use Case Diagram": """@startuml
actor User
rectangle System {
  User -- (Login)
  User -- (Create Task)
}
@enduml""",
            "Sequence Diagram": """@startuml
actor User
participant "System" as S
User -> S: Login
S --> User: Success
@enduml""",
            "Activity Diagram": """@startuml
start
:Login;
if (Credentials Valid?) then (yes)
  :Show Dashboard;
else (no)
  :Show Error;
endif
stop
@enduml""",
        }

        # Set test group and chat name
        test_group = "test-group"
        test_chat = "test-chat-session"

        print(
            colored(
                f"Saving diagrams to directory structure: data/{test_group}/diagrams/{test_chat}/",
                "blue",
            )
        )
        file_paths = agent.save_diagrams_to_directory(
            test_diagrams, test_group, test_chat
        )

        print(colored("Diagrams saved successfully!", "green"))
        for diagram_type, file_path in file_paths.items():
            print(colored(f"{diagram_type}: {file_path}", "green"))

        return True
    except Exception as e:
        logger.error(f"Error saving diagrams: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


async def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(
        description="Test the LangGraph-based Diagram Agent"
    )
    parser.add_argument(
        "--test",
        choices=["generate", "analyze", "save", "all"],
        default="all",
        help="Which test to run (default: all)",
    )

    args = parser.parse_args()

    if args.test == "generate" or args.test == "all":
        print(
            colored("\n=== Testing UML Diagram Generation ===", "blue", attrs=["bold"])
        )
        await test_generate_diagrams()

    if args.test == "analyze" or args.test == "all":
        print(
            colored(
                "\n=== Testing Last Chat Session Analysis ===", "blue", attrs=["bold"]
            )
        )
        await test_analyze_last_chat()

    if args.test == "save" or args.test == "all":
        print(colored("\n=== Testing Diagram Saving ===", "blue", attrs=["bold"]))
        await test_save_diagrams()


if __name__ == "__main__":
    print(
        colored(
            "Testing Enhanced LangGraph-based Diagram Agent...", "blue", attrs=["bold"]
        )
    )
    asyncio.run(main())
