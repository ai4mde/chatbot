#!/usr/bin/env python
"""
Script to safely remove legacy agent implementations.
This script will:
1. Create backup copies of the files to be removed
2. Remove the legacy implementation files
"""

import os
import shutil
import logging
from datetime import datetime
from termcolor import colored

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Files to be removed
LEGACY_FILES = [
    "app/services/chat/interview_agent.py",
    "app/services/chat/diagram_agent.py"
]

def main():
    """Main function to run the cleanup."""
    try:
        print(colored("Starting cleanup of legacy agent implementations...", "blue"))
        
        # Get the current directory (should be the chatback directory)
        current_dir = os.getcwd()
        if not os.path.basename(current_dir) == "chatback":
            print(colored("Error: This script should be run from the chatback directory.", "red"))
            return
        
        # Create a backup directory
        backup_dir = os.path.join(current_dir, "backups", f"legacy_agents_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(backup_dir, exist_ok=True)
        print(colored(f"Created backup directory: {backup_dir}", "green"))
        
        # Process each file
        for file_path in LEGACY_FILES:
            full_path = os.path.join(current_dir, file_path)
            
            # Check if the file exists
            if not os.path.exists(full_path):
                print(colored(f"Warning: File {file_path} does not exist, skipping.", "yellow"))
                continue
            
            # Create the backup directory structure
            backup_file_dir = os.path.join(backup_dir, os.path.dirname(file_path))
            os.makedirs(backup_file_dir, exist_ok=True)
            
            # Copy the file to the backup directory
            backup_file_path = os.path.join(backup_dir, file_path)
            shutil.copy2(full_path, backup_file_path)
            print(colored(f"Backed up {file_path} to {backup_file_path}", "green"))
            
            # Remove the original file
            os.remove(full_path)
            print(colored(f"Removed {file_path}", "green"))
        
        print(colored("Legacy agent cleanup completed successfully!", "blue"))
        print(colored(f"Backup files are stored in: {backup_dir}", "blue"))
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))

if __name__ == "__main__":
    main() 