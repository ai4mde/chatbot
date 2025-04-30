#!/usr/bin/env python
"""
Test script to verify that the diagram phase works correctly.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
from unittest.mock import patch, MagicMock, AsyncMock
import json

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


async def test_diagram_phase():
    """Test that the diagram phase works correctly."""
    try:
        # Import the diagram agent
        from app.services.chat.diagrams import create_diagram_agent

        # Create a unique session ID for testing
        import uuid

        session_id = f"test-{uuid.uuid4()}"
        username = "test-user"

        # Create the diagram agent
        diagram_agent = create_diagram_agent(session_id, username)
        logger.info(f"Created diagram agent for session {session_id}")

        # Create sample messages for testing
        messages = [
            {"role": "user", "content": "I need a system for managing a library."},
            {
                "role": "assistant",
                "content": "I'll help you design a library management system.",
            },
            {
                "role": "user",
                "content": "The system should allow users to borrow and return books.",
            },
            {
                "role": "assistant",
                "content": "Got it. What other features do you need?",
            },
            {
                "role": "user",
                "content": "It should also track overdue books and send reminders.",
            },
            {"role": "assistant", "content": "Understood. Any other requirements?"},
            {
                "role": "user",
                "content": "The system should generate reports on book usage.",
            },
            {
                "role": "assistant",
                "content": "Great. Let me summarize the requirements for your library management system.",
            },
        ]

        # Mock the OpenAI API calls
        with patch("langchain_openai.ChatOpenAI.ainvoke") as mock_ainvoke:
            # Mock the response for summarize_conversation
            summary_response = MagicMock()
            summary_response.content = "The user needs a library management system that allows users to borrow and return books, tracks overdue books, sends reminders, and generates reports on book usage."

            # Mock the response for generate_uml_diagrams
            uml_response = MagicMock()
            uml_response.content = """
            Here are the UML diagrams for the library management system:
            
            ```plantuml
            @startuml
            class Book {
                +id: int
                +title: string
                +author: string
                +isbn: string
                +status: BookStatus
                +getDueDate(): Date
                +isOverdue(): boolean
            }
            
            class User {
                +id: int
                +name: string
                +email: string
                +borrowBook(book: Book): void
                +returnBook(book: Book): void
                +getOverdueBooks(): List<Book>
            }
            
            class Librarian {
                +id: int
                +name: string
                +email: string
                +addBook(book: Book): void
                +removeBook(book: Book): void
                +generateReport(): Report
            }
            
            class BookStatus {
                AVAILABLE
                BORROWED
                OVERDUE
                LOST
            }
            
            class Report {
                +id: int
                +type: ReportType
                +startDate: Date
                +endDate: Date
                +generate(): void
            }
            
            enum ReportType {
                USAGE
                OVERDUE
                INVENTORY
            }
            
            User --> Book : borrows >
            Librarian --> Book : manages >
            Librarian --> Report : generates >
            @enduml
            ```
            
            ```plantuml
            @startuml
            actor User
            actor Librarian
            
            rectangle "Library Management System" {
                usecase "Borrow Book" as UC1
                usecase "Return Book" as UC2
                usecase "Track Overdue Books" as UC3
                usecase "Send Reminders" as UC4
                usecase "Generate Reports" as UC5
                usecase "Add Book" as UC6
                usecase "Remove Book" as UC7
            }
            
            User --> UC1
            User --> UC2
            Librarian --> UC3
            Librarian --> UC4
            Librarian --> UC5
            Librarian --> UC6
            Librarian --> UC7
            @enduml
            ```
            
            ```plantuml
            @startuml
            participant User
            participant System
            participant Database
            
            User -> System: Borrow Book Request
            System -> Database: Check Book Availability
            Database --> System: Book Status
            alt Book Available
                System -> Database: Update Book Status
                Database --> System: Status Updated
                System --> User: Book Borrowed Successfully
            else Book Not Available
                System --> User: Book Not Available
            end
            @enduml
            ```
            """

            # Set up the mock to return different responses for different calls
            mock_ainvoke.side_effect = [summary_response, uml_response]

            # Generate UML diagrams
            result = await diagram_agent.generate_uml_diagrams(messages)

            # Check the result
            if "error" in result:
                print(colored(f"❌ Error: {result['error']}", "red"))
            else:
                print(colored("✅ UML diagrams generated successfully", "green"))
                print(
                    colored(
                        f"Generated {len(result.get('diagram_files', {}))} UML diagrams",
                        "green",
                    )
                )

                # Print the diagram files
                for diagram_type, file_path in result.get("diagram_files", {}).items():
                    print(colored(f"  - {diagram_type}: {file_path}", "green"))

                # Check if the diagram files exist
                for file_path in result.get("diagram_files", {}).values():
                    if os.path.exists(file_path):
                        print(colored(f"  ✅ File exists: {file_path}", "green"))
                    else:
                        print(colored(f"  ❌ File does not exist: {file_path}", "red"))

    except Exception as e:
        logger.error(f"Error testing diagram phase: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))


if __name__ == "__main__":
    print(colored("Testing diagram phase...", "blue"))
    asyncio.run(test_diagram_phase())
