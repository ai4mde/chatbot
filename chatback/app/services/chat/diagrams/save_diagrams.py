"""
Utility functions for saving UML diagrams to files.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import uuid
from termcolor import colored
import asyncio
import json
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

def save_diagrams_to_files(
    chat_title: str,
    diagrams: Dict[str, str],
    group_name: str,
    interview_file_path: Optional[str] = None,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save UML diagrams to a single markdown file.
    
    Args:
        chat_title: The title of the chat session
        diagrams: Dictionary of diagram type to PlantUML content
        group_name: The group name to save the diagrams under
        interview_file_path: Path to the interview markdown file (optional)
        username: The username of the user (optional, used to get group from Redis)
        
    Returns:
        A dictionary containing the path to the saved file and a success message
    """
    try:
        logger.info(f"Saving UML diagrams for chat_title: {chat_title} into a single markdown file")
        print(colored(f"Saving UML diagrams for chat_title: {chat_title}", "blue"))
        
        # Remove .md extension if present
        if chat_title.endswith('.md'):
            chat_title = chat_title[:-3]
            logger.info(f"Removed .md extension from chat_title: {chat_title}")
        
        # If the interview file was found in a different group, use that group
        if interview_file_path:
            # Extract group name from the interview file path
            # Path format: data/<group-name>/interviews/...
            path_parts = interview_file_path.split(os.sep)
            if len(path_parts) >= 3 and path_parts[0] == "data":
                found_group = path_parts[1]
                logger.info(f"Using group name from interview file path: {found_group}")
                print(colored(f"Using group name from interview file path: {found_group}", "blue"))
                group_name = found_group
        
        # If username is provided and group_name is not set, try to get it from Redis
        if username and not group_name:
            try:
                # Import Redis
                from redis import Redis
                
                # Connect to Redis
                redis_client = Redis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                    socket_timeout=settings.REDIS_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_TIMEOUT
                )
                
                # Get all keys for interview user info
                keys = redis_client.keys("interview:user_info_*")
                logger.info(f"Found {len(keys)} user info keys in Redis")
                
                # Check each key for the username
                for key in keys:
                    user_info_data = redis_client.get(key)
                    if user_info_data:
                        try:
                            user_info = json.loads(user_info_data)
                            if user_info.get("name") == username and "group_name" in user_info:
                                group_name = user_info["group_name"]
                                logger.info(f"Found group name in Redis for user {username}: {group_name}")
                                print(colored(f"Using group name from Redis: {group_name}", "blue"))
                                break
                        except Exception as e:
                            logger.warning(f"Error parsing Redis data for key {key}: {str(e)}")
                
                if not group_name:
                    logger.warning(f"Group name not found in Redis for user {username}")
                    raise ValueError(f"Group name not found for user {username}")
                    
            except Exception as e:
                logger.error(f"Error getting group name from Redis: {str(e)}")
                print(colored(f"Error getting group name from Redis: {str(e)}", "red"))
                raise ValueError(f"Could not determine group name for user {username}")
        
        # Ensure we have a group name
        if not group_name:
            error_msg = "Group name is required and could not be determined"
            logger.error(error_msg)
            print(colored(error_msg, "red"))
            raise ValueError(error_msg)
        
        # Create directory structure: data/<group-name>/diagrams/
        diagrams_dir = os.path.join(settings.CHATBOT_DATA_PATH, group_name, "diagrams")
        os.makedirs(diagrams_dir, exist_ok=True)
        logger.info(f"Ensured diagrams directory exists: {diagrams_dir}")
        
        # Create filename: <safe_chat_title>-<timestamp>.md
        safe_title = chat_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
        timestamp = int(time.time())
        filename = f"{safe_title}-{timestamp}.md"
        file_path = os.path.join(diagrams_dir, filename)
        
        # Generate Markdown Content
        markdown_content = f"# UML Diagrams for {chat_title}\n\n"
        markdown_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for diagram_type, diagram_content in diagrams.items():
            # Extract PlantUML content
            plantuml_content = extract_plantuml(diagram_content)
            
            if plantuml_content:
                # Add header for the diagram type
                markdown_content += f"## {diagram_type.replace('_', ' ').title()} Diagram\n\n"
                # Add the plantuml code block
                markdown_content += "```plantuml\n"
                markdown_content += f"{plantuml_content}\n"
                markdown_content += "```\n\n"
            else:
                 markdown_content += f"## {diagram_type.replace('_', ' ').title()} Diagram\n\n"
                 markdown_content += "(No PlantUML content found or extracted)\n\n"

        # Write the combined content to the single file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        logger.info(f"Saved all diagrams to {file_path}")
        print(colored(f"Saved all diagrams to {file_path}", "green"))
        
        # Return the result with the single file path
        return {
            "success": True,
            "message": f"UML diagrams saved successfully to {file_path}",
            "diagram_file_path": file_path, # Use a new key for the single path
            "diagrams_dir": diagrams_dir # Keep the directory path for reference
        }
    except Exception as e:
        logger.error(f"Error saving UML diagrams: {str(e)}")
        return {
            "success": False,
            "message": f"Error saving UML diagrams: {str(e)}",
            "error": str(e)
        }

def extract_plantuml(content: str) -> str:
    """
    Extract PlantUML content from a string.
    
    Args:
        content: String containing PlantUML content
        
    Returns:
        Extracted PlantUML content
    """
    # Look for PlantUML content between ```plantuml and ``` markers
    plantuml_pattern = r"```plantuml\s*(.*?)```"
    match = re.search(plantuml_pattern, content, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # If no match, look for content between @startuml and @enduml
    startuml_pattern = r"@startuml\s*(.*?)@enduml"
    match = re.search(startuml_pattern, content, re.DOTALL)
    
    if match:
        return f"@startuml\n{match.group(1).strip()}\n@enduml"
    
    # If still no match, return the original content
    return content

def generate_diagram_filename(diagram_type: str, chat_title: str) -> str:
    """
    Generate a filename for a diagram.
    
    Args:
        diagram_type: Type of diagram (e.g., class, sequence, usecase)
        chat_title: Title of the chat session
        
    Returns:
        A filename for the diagram
    """
    # Create a safe filename
    safe_title = chat_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
    safe_type = diagram_type.lower().replace(' ', '_').replace('-', '_')
    
    # Generate a unique ID
    unique_id = str(uuid.uuid4())[:8]
    
    return f"{safe_type}_{safe_title}_{unique_id}.puml" 