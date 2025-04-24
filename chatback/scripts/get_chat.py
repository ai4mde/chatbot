#!/usr/bin/env python
"""
Script to retrieve a chat session from the database and save it as a markdown file.
Usage: python get_chat.py <username> <chat_session_title>

The output will be stored in data/<group-name>/interviews/<chat_session_name>.md
This ensures users in the same group can access each other's content.
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from termcolor import colored

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage, ChatRole
from app.models.user import User
from app.models.group import Group

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_chat_session(username: str, chat_title: str):
    """
    Retrieve a chat session from the database and save it as a markdown file.
    
    Args:
        username: The username of the chat session owner
        chat_title: The title of the chat session
    """
    try:
        print(colored(f"Retrieving chat session '{chat_title}' for user '{username}'...", "blue"))
        
        # Create async database engine
        engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        logger.info(f"Connecting to database: {settings.POSTGRES_HOST}")
        print(colored(f"Connecting to database: {settings.POSTGRES_HOST}", "blue"))
        
        async with async_session() as db:
            # Find the user
            user_query = select(User).where(User.username == username)
            user_result = await db.execute(user_query)
            user = user_result.scalars().first()
            
            if not user:
                error_msg = f"User '{username}' not found in the database."
                logger.error(error_msg)
                print(colored(f"Error: {error_msg}", "red"))
                return
            
            print(colored(f"Found user: {username} (ID: {user.id})", "green"))
            
            # Get the user's group
            group_query = select(Group).where(Group.id == user.group_id)
            group_result = await db.execute(group_query)
            group = group_result.scalars().first()
            
            if not group:
                warning_msg = f"User '{username}' is not associated with any group. Using 'default' as group name."
                logger.warning(warning_msg)
                print(colored(f"Warning: {warning_msg}", "yellow"))
                group_name = "default"
            else:
                group_name = group.name
                print(colored(f"Found group: {group_name} (ID: {group.id})", "green"))
            
            # Find the chat session
            chat_query = select(ChatSession).where(
                and_(
                    ChatSession.user_id == user.id,
                    ChatSession.title == chat_title
                )
            )
            chat_result = await db.execute(chat_query)
            chat_session = chat_result.scalars().first()
            
            if not chat_session:
                error_msg = f"Chat session '{chat_title}' not found for user '{username}'."
                logger.error(error_msg)
                print(colored(f"Error: {error_msg}", "red"))
                return
            
            print(colored(f"Found chat session: {chat_session.title} (ID: {chat_session.id})", "green"))
            
            # Get all messages for the chat session
            messages_query = select(ChatMessage).where(
                ChatMessage.session_id == chat_session.id
            ).order_by(ChatMessage.created_at)
            messages_result = await db.execute(messages_query)
            messages = messages_result.scalars().all()
            
            if not messages:
                warning_msg = f"No messages found for chat session: {chat_title}"
                logger.warning(warning_msg)
                print(colored(f"Warning: {warning_msg}", "yellow"))
            else:
                print(colored(f"Found {len(messages)} messages", "green"))
            
            # Create markdown content
            markdown_content = f"# Chat Session: {chat_session.title}\n\n"
            markdown_content += f"- **User**: {username}\n"
            markdown_content += f"- **Group**: {group_name}\n"
            markdown_content += f"- **Created**: {chat_session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            markdown_content += f"- **Updated**: {chat_session.updated_at.strftime('%Y-%m-%d %H:%M:%S') if chat_session.updated_at else 'N/A'}\n"
            markdown_content += f"- **Status**: {chat_session.state}\n\n"
            markdown_content += "## Messages\n\n"
            
            for message in messages:
                # Format the sender name
                if message.role == ChatRole.USER:
                    sender = f"**{username}**"
                elif message.role == ChatRole.ASSISTANT:
                    sender = f"**Assistant**"
                elif message.role == ChatRole.SYSTEM:
                    sender = f"**System**"
                else:
                    sender = f"**{message.role}**"
                
                # Format the timestamp
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                
                # Add the message to the markdown content
                markdown_content += f"### {sender} ({timestamp})\n\n"
                markdown_content += f"{message.content}\n\n"
                markdown_content += "---\n\n"
            
            # Create output directory in the data/<group-name>/interviews/ path
            safe_title = chat_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
            output_dir = os.path.join(settings.CHATBOT_DATA_PATH, group_name, "interviews")
            os.makedirs(output_dir, exist_ok=True)
            
            # Save the markdown file
            output_file = os.path.join(output_dir, f"{safe_title}.md")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            logger.info(f"Chat session saved to: {output_file}")
            print(colored(f"Chat session saved to: {output_file}", "green"))
            print(colored(f"This file is accessible to all users in the '{group_name}' group.", "blue"))
    
    except Exception as e:
        error_msg = f"Error retrieving chat session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        print(colored("Stack trace:", "red"))
        import traceback
        print(colored(traceback.format_exc(), "red"))

def main():
    """Parse command line arguments and run the script."""
    parser = argparse.ArgumentParser(description="Retrieve a chat session and save it as a markdown file.")
    parser.add_argument("username", help="Username of the chat session owner")
    parser.add_argument("chat_title", help="Title of the chat session")
    
    args = parser.parse_args()
    
    # Run the async function
    asyncio.run(get_chat_session(args.username, args.chat_title))

if __name__ == "__main__":
    main() 