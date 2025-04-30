#!/usr/bin/env python
"""
Script to test the LangGraph-based agent workflow.
This script simulates running the complete agent workflow.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
import argparse
import uuid
import time

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"
os.environ["CHATBOT_DATA_PATH"] = "data"

from app.services.chat.agent_workflow import AgentWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Sample conversation for testing
SAMPLE_CONVERSATION = [
    {
        "role": "user",
        "content": "I need an online bookstore for Leiden University students.",
    },
    {"role": "assistant", "content": "Could you tell me more about your requirements?"},
    {
        "role": "user",
        "content": "We need a platform where students can buy textbooks, course materials, and academic supplies.",
    },
    {"role": "assistant", "content": "What specific features do you need?"},
    {
        "role": "user",
        "content": "We need user registration, product search with filtering by faculty, shopping cart, checkout with multiple payment methods, and academic bundles for different faculties.",
    },
    {"role": "assistant", "content": "Any specific technical requirements?"},
    {
        "role": "user",
        "content": "It should be a web-based application with mobile support. We also need inventory management for administrators and order tracking for users.",
    },
    {"role": "assistant", "content": "Any other features you'd like to include?"},
    {
        "role": "user",
        "content": "We'd like to have personalized recommendations based on user preferences and multi-language support for international students.",
    },
]


async def test_langgraph_workflow():
    """Test the LangGraph-based agent workflow."""
    try:
        # Generate a unique session ID for testing
        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"

        print(colored(f"Creating agent workflow for session {session_id}...", "blue"))
        workflow = AgentWorkflow(session_id, username)

        print(
            colored(
                "Running LangGraph-based agent workflow with sample conversation...",
                "blue",
            )
        )
        start_time = time.time()
        result = await workflow.run_workflow(SAMPLE_CONVERSATION)
        end_time = time.time()

        print(
            colored(
                f"Agent workflow completed in {end_time - start_time:.2f} seconds!",
                "green",
            )
        )

        # Check for errors
        if result.get("error"):
            print(colored(f"Error: {result['error']}", "red"))
            return False

        # Print completed steps
        if "completed_steps" in result:
            print(colored("\nCompleted Steps:", "blue"))
            print(colored(", ".join(result["completed_steps"]), "cyan"))

        # Print interview result
        if result.get("interview_result"):
            print(colored("\nInterview Result:", "blue"))
            print(
                colored(
                    f"Message: {result['interview_result'].get('message', 'N/A')[:100]}...",
                    "cyan",
                )
            )

        # Print diagram result
        if result.get("diagram_result"):
            print(colored("\nDiagram Result:", "blue"))
            print(
                colored(
                    f"Message: {result['diagram_result'].get('message', 'N/A')}", "cyan"
                )
            )

            if "diagram_files" in result["diagram_result"]:
                print(colored("Diagram Files:", "blue"))
                for diagram_type, file_path in result["diagram_result"][
                    "diagram_files"
                ].items():
                    print(colored(f"  {diagram_type}: {file_path}", "cyan"))

        # Print requirements result
        if result.get("requirements_result"):
            print(colored("\nRequirements Result:", "blue"))
            print(
                colored(
                    f"Message: {result['requirements_result'].get('message', 'N/A')}",
                    "cyan",
                )
            )

            if "functional_requirements_path" in result["requirements_result"]:
                print(
                    colored(
                        f"Functional Requirements: {result['requirements_result']['functional_requirements_path']}",
                        "cyan",
                    )
                )

            if "non_functional_requirements_path" in result["requirements_result"]:
                print(
                    colored(
                        f"Non-Functional Requirements: {result['requirements_result']['non_functional_requirements_path']}",
                        "cyan",
                    )
                )

        return True
    except Exception as e:
        logger.error(f"Error testing LangGraph workflow: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


async def test_parallel_execution():
    """Test direct parallel execution of agents."""
    try:
        # Generate a unique session ID for testing
        session_id = f"parallel-{uuid.uuid4()}"
        username = "test-user"

        print(colored(f"Creating agent workflow for session {session_id}...", "blue"))
        workflow = AgentWorkflow(session_id, username)

        print(
            colored(
                "Running direct parallel execution with sample conversation...", "blue"
            )
        )
        start_time = time.time()
        result = await workflow.run_parallel_workflow(SAMPLE_CONVERSATION)
        end_time = time.time()

        print(
            colored(
                f"Parallel execution completed in {end_time - start_time:.2f} seconds!",
                "green",
            )
        )

        # Check for errors
        if result.get("error"):
            print(colored(f"Error: {result['error']}", "red"))
            return False

        # Print diagram result
        if result.get("diagram_result"):
            print(colored("\nDiagram Result:", "blue"))
            print(
                colored(
                    f"Message: {result['diagram_result'].get('message', 'N/A')}", "cyan"
                )
            )

            if "diagram_files" in result["diagram_result"]:
                print(colored("Diagram Files:", "blue"))
                for diagram_type, file_path in result["diagram_result"][
                    "diagram_files"
                ].items():
                    print(colored(f"  {diagram_type}: {file_path}", "cyan"))

        # Print requirements result
        if result.get("requirements_result"):
            print(colored("\nRequirements Result:", "blue"))
            print(
                colored(
                    f"Message: {result['requirements_result'].get('message', 'N/A')}",
                    "cyan",
                )
            )

            if "functional_requirements_path" in result["requirements_result"]:
                print(
                    colored(
                        f"Functional Requirements: {result['requirements_result']['functional_requirements_path']}",
                        "cyan",
                    )
                )

            if "non_functional_requirements_path" in result["requirements_result"]:
                print(
                    colored(
                        f"Non-Functional Requirements: {result['requirements_result']['non_functional_requirements_path']}",
                        "cyan",
                    )
                )

        return True
    except Exception as e:
        logger.error(f"Error testing parallel execution: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


async def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(
        description="Test the LangGraph-based agent workflow"
    )
    parser.add_argument(
        "--test",
        choices=["langgraph", "parallel", "all"],
        default="all",
        help="Which test to run (default: all)",
    )

    args = parser.parse_args()

    if args.test == "langgraph" or args.test == "all":
        print(
            colored(
                "\n=== Testing LangGraph-based Agent Workflow ===",
                "blue",
                attrs=["bold"],
            )
        )
        await test_langgraph_workflow()

    if args.test == "parallel" or args.test == "all":
        print(
            colored(
                "\n=== Testing Direct Parallel Execution ===", "blue", attrs=["bold"]
            )
        )
        await test_parallel_execution()


if __name__ == "__main__":
    print(colored("Testing Agent Workflow...", "blue", attrs=["bold"]))
    asyncio.run(main())
