import os
import re
from typing import Optional, Dict, List
import logging
from pathlib import Path
from termcolor import colored

logger = logging.getLogger(__name__)

def sanitize_path_component(component: str) -> str:
    """
    Sanitize a path component (username, filename, etc).
    
    Args:
        component: String to sanitize
        
    Returns:
        Sanitized string safe for filesystem use
    """
    # Remove any non-alphanumeric chars except dash and underscore
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '_', component.lower())
    # Remove consecutive underscores/dashes
    sanitized = re.sub(r'[_\-]{2,}', '_', sanitized)
    # Remove leading/trailing underscores/dashes
    return sanitized.strip('_-')

def validate_path(path: str, base_path: str) -> Optional[str]:
    """
    Validate a path is safe and within allowed base path.
    
    Args:
        path: Path to validate
        base_path: Base path that should contain the path
        
    Returns:
        Validated absolute path or None if invalid
    """
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_path)
        
        # Check if path is within base path
        if not abs_path.startswith(abs_base):
            logger.error(f"Path {path} is outside base path {base_path}")
            return None
            
        return abs_path
        
    except Exception as e:
        logger.error(f"Path validation error: {str(e)}")
        return None

def ensure_path(path: str) -> bool:
    """
    Ensure a path exists, creating it if necessary.
    
    Args:
        path: Path to ensure exists
        
    Returns:
        True if path exists/created, False on error
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create path {path}: {str(e)}")
        return False

def ensure_data_directories(group_name: str, base_path: str = "/chatback/data", verbose: bool = False) -> Dict[str, str]:
    """
    Ensure all required data directories exist for a given group.
    Creates the directories if they don't exist.
    
    Args:
        group_name: The name of the group
        base_path: Base data path (defaults to "/chatback/data")
        verbose: Whether to print status messages
        
    Returns:
        Dictionary with paths to all created directories
    """
    try:
        # Sanitize group name for safety
        safe_group_name = sanitize_path_component(group_name)
        
        # Define the required subdirectories
        subdirs = ["interviews", "requirements", "diagrams", "srsdocuments"]
        
        # Base group directory
        group_dir = os.path.join(base_path, safe_group_name)
        
        # Ensure the group directory exists
        if not os.path.exists(group_dir):
            if verbose:
                print(colored(f"Creating group directory: {group_dir}", "blue"))
            Path(group_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created group directory: {group_dir}")
        
        # Dictionary to store all paths
        paths = {"group_dir": group_dir}
        
        # Create each subdirectory
        for subdir in subdirs:
            subdir_path = os.path.join(group_dir, subdir)
            if not os.path.exists(subdir_path):
                if verbose:
                    print(colored(f"Creating {subdir} directory: {subdir_path}", "blue"))
                Path(subdir_path).mkdir(parents=True, exist_ok=True)
                logger.info(f"Created {subdir} directory: {subdir_path}")
            paths[f"{subdir}_dir"] = subdir_path
        
        if verbose:
            print(colored("All required directories are in place.", "green"))
        
        return paths
    except Exception as e:
        error_msg = f"Error ensuring data directories: {str(e)}"
        logger.error(error_msg)
        if verbose:
            print(colored(error_msg, "red"))
        return {"error": error_msg} 