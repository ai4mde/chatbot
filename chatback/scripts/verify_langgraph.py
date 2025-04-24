#!/usr/bin/env python
"""
Script to verify that the LangGraph implementation is being used.
"""

import os
import sys
import logging
from termcolor import colored

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Verify that the LangGraph implementation is being used."""
    try:
        # Import the factory
        from app.services.chat.interview import create_interview_agent, InterviewAgentGraph
        
        # Create an agent
        agent = create_interview_agent("test-session", "test-user")
        
        # Check the type of the agent
        agent_type = type(agent).__name__
        print(colored(f"Agent type: {agent_type}", "blue"))
        
        # Verify it's the LangGraph implementation
        is_langgraph = isinstance(agent, InterviewAgentGraph)
        
        if is_langgraph:
            print(colored("✅ Success: LangGraph implementation is being used", "green"))
        else:
            print(colored("❌ Error: LangGraph implementation is NOT being used", "red"))
            
    except Exception as e:
        logger.error(f"Error verifying LangGraph implementation: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))

if __name__ == "__main__":
    print(colored("Verifying LangGraph implementation...", "blue"))
    main() 