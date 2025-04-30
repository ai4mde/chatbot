"""
Factory module for creating diagram agents.
This module now standardizes on the LangGraph-based implementation.
"""

import logging
from typing import Union

# Import the LangGraph implementation
from .diagram_agent_graph import DiagramAgentGraph

logger = logging.getLogger(__name__)


def create_diagram_agent(session_id: str, username: str) -> DiagramAgentGraph:
    """
    Factory function to create the diagram agent implementation.

    Args:
        session_id: The session ID
        username: The username

    Returns:
        An instance of DiagramAgentGraph
    """
    try:
        logger.info(f"Creating LangGraph-based diagram agent for session {session_id}")
        return DiagramAgentGraph(session_id, username)
    except Exception as e:
        logger.error(f"Error creating diagram agent: {str(e)}")
        raise
