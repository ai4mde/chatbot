#!/usr/bin/env python3
"""
Script to ensure all required data directories exist for a given group.
"""

import os
import sys
import argparse
import logging
from termcolor import colored

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our function
from app.core.path_utils import ensure_data_directories
from app.core.config import settings

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Ensure all required data directories exist for a given group")
    parser.add_argument("group_name", help="Name of the group to create directories for")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose output")
    parser.add_argument("--data-path", help="Override the data path (default: from settings)")
    
    args = parser.parse_args()
    
    # Use the provided data path or get it from settings
    data_path = args.data_path or settings.CHATBOT_DATA_PATH
    
    print(colored(f"Ensuring directories for group: {args.group_name}", "blue"))
    print(colored(f"Using data path: {data_path}", "blue"))
    
    # Call our function with the data path
    paths = ensure_data_directories(args.group_name, base_path=data_path, verbose=args.verbose)
    
    # Check if there was an error
    if "error" in paths:
        print(colored(f"Error: {paths['error']}", "red"))
        sys.exit(1)
    
    # Print the paths
    print(colored("\nCreated directories:", "green"))
    for key, path in paths.items():
        print(colored(f"  {key}: {path}", "cyan"))
    
    print(colored("\nAll required directories are in place.", "green"))

if __name__ == "__main__":
    main() 