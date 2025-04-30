"""
Factory module for creating interview agents.
This module now standardizes on the LangGraph-based implementation.
"""

import logging
import importlib.metadata
import importlib.util
from typing import Union

# Import the LangGraph implementation
from .interview_agent_graph import InterviewAgentGraph

logger = logging.getLogger(__name__)


def create_interview_agent(session_id: str, username: str) -> InterviewAgentGraph:
    """
    Factory function to create the interview agent implementation.

    Args:
        session_id: The session ID
        username: The username

    Returns:
        An instance of InterviewAgentGraph
    """
    try:
        # Log LangGraph version for debugging
        try:
            # Try to get the version from the primary package name first
            # (We know from requirements.txt that it's 'langgraph')
            try:
                langgraph_version = importlib.metadata.version("langgraph")
                logger.info(f"Using LangGraph version: {langgraph_version}")
            except importlib.metadata.PackageNotFoundError:
                # If that fails, try alternative package names
                package_names = ["langchain-langgraph", "langchain_langgraph"]
                langgraph_version = None

                for package_name in package_names:
                    try:
                        langgraph_version = importlib.metadata.version(package_name)
                        logger.info(
                            f"Using LangGraph version: {langgraph_version} (package: {package_name})"
                        )
                        break
                    except importlib.metadata.PackageNotFoundError:
                        continue

                # If we still couldn't get the version, try importing the module directly
                if not langgraph_version:
                    try:
                        import langgraph

                        if hasattr(langgraph, "__version__"):
                            langgraph_version = langgraph.__version__
                            logger.info(
                                f"Using LangGraph version: {langgraph_version} (from module attribute)"
                            )
                        elif hasattr(langgraph, "VERSION"):
                            langgraph_version = langgraph.VERSION
                            logger.info(
                                f"Using LangGraph version: {langgraph_version} (from module constant)"
                            )
                        else:
                            logger.info(
                                "LangGraph module found but version information is not available"
                            )
                    except ImportError:
                        logger.warning(
                            "Could not import LangGraph module. This is not critical but may be useful for debugging."
                        )
        except Exception as e:
            logger.warning(
                f"Error determining LangGraph version: {str(e)}. This is not critical."
            )

        logger.info(
            f"Creating LangGraph-based interview agent for session {session_id}"
        )
        return InterviewAgentGraph(session_id, username)
    except Exception as e:
        logger.error(f"Error creating interview agent: {str(e)}")
        raise
