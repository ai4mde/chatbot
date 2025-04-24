"""
LangGraph-based workflow for connecting multiple agents.
This module implements the complete agent workflow using LangGraph.

Workflow:
(start) --> [interview agent] --+--> [diagram agent] --> [uml converter agent] --+--> [srsdocument writer agent] <--> [document reviewer agent] --> [chat with document agent] --> (end)
                                |                                                ^
                                |--> [requirements agent] -----------------------|
"""

import os
import logging
from typing import Dict, List, Any, TypedDict, Optional, Union, Annotated, Literal
import asyncio
import json

# LangGraph imports
from langgraph.graph import StateGraph, END

# Agent imports
from app.services.chat.interview import create_interview_agent
from app.services.chat.diagrams import create_diagram_agent
from app.services.chat.requirements import create_requirements_agent

# Local imports
from app.core.config import settings

# Flags to control which phases are enabled/disabled
DISABLE_REQUIREMENTS = False  # Set to True to disable requirements generation
DISABLE_DIAGRAM = False       # Set to True to disable diagram generation
DISABLE_SRSDOCUMENT = False   # Set to True to disable SRS document generation

logger = logging.getLogger(__name__)

# Define the workflow state schema
class WorkflowState(TypedDict):
    """State for the agent workflow."""
    session_id: str  # Session ID
    username: str  # Username
    messages: List[Dict[str, Any]]  # Conversation messages
    interview_result: Optional[Dict[str, Any]]  # Result from interview agent
    diagram_result: Optional[Dict[str, Any]]  # Result from diagram agent
    requirements_result: Optional[Dict[str, Any]]  # Result from requirements agent
    uml_converter_result: Optional[Dict[str, Any]]  # Result from UML converter agent
    document_result: Optional[Dict[str, Any]]  # Result from document writer agent
    error: Optional[str]  # Error message if any
    current_step: str  # Current step in the workflow
    next_steps: List[str]  # Next steps to execute
    completed_steps: List[str]  # Steps that have been completed
    interview_file_path: Optional[str]  # File path of the interview document
    chat_title: Optional[str]  # Title of the interview document

class AgentWorkflow:
    """LangGraph-based workflow for connecting multiple agents."""
    
    def __init__(self, session_id: str, username: str):
        """Initialize the agent workflow."""
        try:
            logger.info(f"Initializing AgentWorkflow for session {session_id}")
            self.session_id = session_id
            self.username = username
            
            # Initialize state
            self.state = {
                "session_id": session_id,
                "username": username,
                "messages": [],
                "interview_result": None,
                "diagram_result": None,
                "requirements_result": None,
                "uml_converter_result": None,
                "document_result": None,
                "error": None,
                "current_step": "start",
                "next_steps": ["interview"],
                "completed_steps": [],
                "interview_file_path": None,
                "chat_title": None
            }
            
            # Initialize agents
            self.interview_agent = create_interview_agent(session_id, username)
            self.diagram_agent = create_diagram_agent(session_id, username)
            self.requirements_agent = create_requirements_agent(session_id, username)
            
            # Initialize workflow graph
            self.workflow = self._create_workflow_graph()
            
            logger.info(f"AgentWorkflow initialized for session {session_id}")
        except Exception as e:
            logger.error(f"Error initializing AgentWorkflow: {str(e)}")
            raise
    
    def _create_workflow_graph(self) -> StateGraph:
        """Create the workflow graph."""
        # Define the graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes for different steps
        workflow.add_node("start", self._start_workflow)
        workflow.add_node("interview", self._run_interview_agent)
        workflow.add_node("branch", self._branch_workflow)
        workflow.add_node("diagram", self._run_diagram_agent)
        workflow.add_node("requirements", self._run_requirements_agent)
        workflow.add_node("merge", self._merge_results)
        workflow.add_node("end", self._end_workflow)
        
        # Define edges
        workflow.add_edge("start", "interview")
        workflow.add_edge("interview", "branch")
        workflow.add_edge("branch", "diagram")
        workflow.add_edge("branch", "requirements")
        workflow.add_edge("diagram", "merge")
        workflow.add_edge("requirements", "merge")
        workflow.add_edge("merge", "end")
        workflow.add_edge("end", END)
        
        return workflow.compile()
    
    async def _start_workflow(self, state: WorkflowState) -> WorkflowState:
        """Start the workflow."""
        logger.info(f"Starting workflow for session {state['session_id']}")
        state["current_step"] = "start"
        state["next_steps"] = ["interview"]
        state["completed_steps"] = []
        return state
    
    async def _run_interview_agent(self, state: WorkflowState) -> WorkflowState:
        """Run the interview agent."""
        logger.info(f"Running interview agent for session {state['session_id']}")
        state["current_step"] = "interview"
        try:
            # Process messages with interview agent
            result = await self.interview_agent.process_message("Hello")
            # Save the interview document and get the file path
            save_result = await self.interview_agent.save_interview_document()
            interview_file_path = save_result.get("file_path")
            chat_title = save_result.get("chat_title") or save_result.get("title")
            # Update state with interview result and file path
            state["interview_result"] = {
                "message": result,
                "completed": True,
                "interview_file_path": interview_file_path,
                "chat_title": chat_title
            }
            state["interview_file_path"] = interview_file_path
            state["chat_title"] = chat_title
            # Set next step
            state["next_steps"] = ["branch"]
            state["completed_steps"].append("interview")
            return state
        except Exception as e:
            logger.error(f"Error running interview agent: {str(e)}")
            state["error"] = f"Failed to run interview agent: {str(e)}"
            state["next_steps"] = ["end"]
            return state
    
    async def _branch_workflow(self, state: WorkflowState) -> WorkflowState:
        logger.info(f"[WORKFLOW] Entering _branch_workflow for session {state['session_id']}")
        state["current_step"] = "branch"
        # Initialize next steps as an empty list
        next_steps = []
        # Add steps based on which phases are enabled
        if not DISABLE_DIAGRAM:
            next_steps.append("diagram")
            logger.info("[WORKFLOW] Diagram phase is enabled")
        else:
            logger.info("[WORKFLOW] Diagram phase is disabled")
        if not DISABLE_REQUIREMENTS:
            next_steps.append("requirements")
            logger.info("[WORKFLOW] Requirements phase is enabled")
        else:
            logger.info("[WORKFLOW] Requirements phase is disabled")
        # If all phases are disabled, go directly to end
        if not next_steps:
            logger.warning("[WORKFLOW] All phases are disabled. Proceeding directly to end.")
            next_steps = ["end"]
        state["next_steps"] = next_steps
        state["completed_steps"].append("branch")
        logger.info(f"[WORKFLOW] _branch_workflow set next_steps: {next_steps}")
        return state
    
    async def _run_diagram_agent(self, state: WorkflowState) -> WorkflowState:
        """Run the diagram agent."""
        logger.info(f"Running diagram agent for session {state['session_id']}")
        state["current_step"] = "diagram"
        
        try:
            # Generate UML diagrams
            result = await self.diagram_agent.generate_uml_diagrams(state["messages"])
            
            # Update state with diagram result
            state["diagram_result"] = result
            
            # Set next step
            state["next_steps"] = ["merge"]
            state["completed_steps"].append("diagram")
            
            return state
        except Exception as e:
            logger.error(f"Error running diagram agent: {str(e)}")
            state["error"] = f"Failed to run diagram agent: {str(e)}"
            state["next_steps"] = ["merge"]  # Continue to merge even if there's an error
            return state
    
    async def _run_requirements_agent(self, state: WorkflowState) -> WorkflowState:
        logger.info(f"[WORKFLOW] Entering _run_requirements_agent for session {state['session_id']} with chat_title: {state.get('chat_title')}")
        logger.info(f"[WORKFLOW] State at requirements agent: {json.dumps({k: str(v) for k, v in state.items() if k not in ['messages', 'interview_result', 'diagram_result', 'requirements_result', 'uml_converter_result', 'document_result']}, indent=2)}")
        state["current_step"] = "requirements"
        try:
            # Use the interview markdown file to generate requirements
            chat_title = state.get("chat_title")
            result = await self.requirements_agent.analyze_interview_file(chat_title)
            # Update state with requirements result
            state["requirements_result"] = result
            # Set next step
            state["next_steps"] = ["merge"]
            state["completed_steps"].append("requirements")
            return state
        except Exception as e:
            logger.error(f"Error running requirements agent: {str(e)}")
            state["error"] = f"Failed to run requirements agent: {str(e)}"
            state["next_steps"] = ["merge"]  # Continue to merge even if there's an error
            return state
    
    async def _merge_results(self, state: WorkflowState) -> WorkflowState:
        """Merge results from diagram and requirements agents."""
        logger.info(f"Merging results for session {state['session_id']}")
        state["current_step"] = "merge"
        
        # Check which phases are enabled and which have completed
        diagram_enabled = not DISABLE_DIAGRAM
        requirements_enabled = not DISABLE_REQUIREMENTS
        
        diagram_done = "diagram" in state["completed_steps"] or not diagram_enabled
        requirements_done = "requirements" in state["completed_steps"] or not requirements_enabled
        
        # Log status of each phase
        logger.info(f"Phase status: diagram_enabled={diagram_enabled}, diagram_done={diagram_done}, "
                   f"requirements_enabled={requirements_enabled}, requirements_done={requirements_done}")
        
        # Check if all enabled phases have completed
        all_phases_done = diagram_done and requirements_done
        
        if all_phases_done:
            # All enabled phases have completed, proceed to end or document phase
            if DISABLE_SRSDOCUMENT:
                logger.info("SRS document phase is disabled. Proceeding to end.")
                state["next_steps"] = ["end"]
            else:
                logger.info("All phases completed. Proceeding to document phase.")
                # TODO: Add document phase when implemented
                state["next_steps"] = ["end"]  # For now, go to end
                
            state["completed_steps"].append("merge")
        else:
            # Wait for all enabled phases to complete
            logger.info(f"Waiting for phases to complete")
            # Don't set next_steps, so the workflow will wait for other branches to complete
            state["next_steps"] = []
        
        return state
    
    async def _end_workflow(self, state: WorkflowState) -> WorkflowState:
        """End the workflow."""
        logger.info(f"Ending workflow for session {state['session_id']}")
        state["current_step"] = "end"
        state["next_steps"] = []
        state["completed_steps"].append("end")
        
        # Prepare final result with status of each phase
        final_result = {
            "interview_result": state["interview_result"],
            "requirements_result": state["requirements_result"] if not DISABLE_REQUIREMENTS else None,
            "diagram_result": state["diagram_result"] if not DISABLE_DIAGRAM else None,
            "document_result": state["document_result"] if not DISABLE_SRSDOCUMENT else None,
            "completed": True,
            "phase_status": {
                "requirements_enabled": not DISABLE_REQUIREMENTS,
                "diagram_enabled": not DISABLE_DIAGRAM,
                "srsdocument_enabled": not DISABLE_SRSDOCUMENT
            },
            "error": state["error"]
        }
        
        # Log completion status for each phase
        logger.info(f"Workflow completed with phases: "
                   f"requirements={'enabled' if not DISABLE_REQUIREMENTS else 'disabled'}, "
                   f"diagram={'enabled' if not DISABLE_DIAGRAM else 'disabled'}, "
                   f"srsdocument={'enabled' if not DISABLE_SRSDOCUMENT else 'disabled'}")
        
        # Log any errors
        if state["error"]:
            logger.error(f"Workflow completed with error: {state['error']}")
        else:
            logger.info(f"Workflow completed successfully for session {state['session_id']}")
        
        return state
    
    async def run_workflow(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run the complete agent workflow.
        """
        try:
            logger.info(f"Running workflow for session {self.session_id}")
            # Update state with messages
            self.state["messages"] = messages
            # Run the workflow
            def log_state(state, step_name):
                logger.info(f"[WORKFLOW] After step {step_name}, state: " + json.dumps({k: str(v) for k, v in state.items() if k not in ['messages', 'interview_result', 'diagram_result', 'requirements_result', 'uml_converter_result', 'document_result']}, indent=2))
            # Use a custom callback to log after each step if supported
            # For now, just log before and after the workflow
            logger.info(f"[WORKFLOW] Initial state: " + json.dumps({k: str(v) for k, v in self.state.items() if k not in ['messages', 'interview_result', 'diagram_result', 'requirements_result', 'uml_converter_result', 'document_result']}, indent=2))
            final_state = await self.workflow.ainvoke(self.state)
            logger.info(f"[WORKFLOW] Final state after workflow: " + json.dumps({k: str(v) for k, v in final_state.items() if k not in ['messages', 'interview_result', 'diagram_result', 'requirements_result', 'uml_converter_result', 'document_result']}, indent=2))
            # Return the final state with phase status
            return {
                "interview_result": final_state["interview_result"],
                "requirements_result": final_state["requirements_result"] if not DISABLE_REQUIREMENTS else None,
                "diagram_result": final_state["diagram_result"] if not DISABLE_DIAGRAM else None,
                "document_result": final_state["document_result"] if not DISABLE_SRSDOCUMENT else None,
                "completed": True,
                "phase_status": {
                    "requirements_enabled": not DISABLE_REQUIREMENTS,
                    "diagram_enabled": not DISABLE_DIAGRAM,
                    "srsdocument_enabled": not DISABLE_SRSDOCUMENT
                },
                "error": final_state["error"],
                "completed_steps": final_state["completed_steps"]
            }
        except Exception as e:
            logger.error(f"Error running workflow: {str(e)}")
            return {
                "error": f"Failed to run workflow: {str(e)}",
                "completed": False
            }
    
    async def run_parallel_workflow(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run the diagram and requirements agents in parallel.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            A dictionary containing the results from both agents
        """
        try:
            logger.info(f"Running parallel workflow for session {self.session_id}")
            
            # Create tasks for parallel execution
            diagram_task = asyncio.create_task(
                self.diagram_agent.generate_uml_diagrams(messages)
            )
            requirements_task = asyncio.create_task(
                self.requirements_agent.generate_requirements(messages)
            )
            
            # Wait for both tasks to complete
            results = await asyncio.gather(diagram_task, requirements_task, return_exceptions=True)
            
            # Process results
            diagram_result, requirements_result = results
            
            # Check for exceptions
            if isinstance(diagram_result, Exception):
                logger.error(f"Error in diagram agent: {str(diagram_result)}")
                diagram_result = {"error": str(diagram_result)}
            
            if isinstance(requirements_result, Exception):
                logger.error(f"Error in requirements agent: {str(requirements_result)}")
                requirements_result = {"error": str(requirements_result)}
            
            # Return combined results
            return {
                "diagram_result": diagram_result,
                "requirements_result": requirements_result,
                "completed": True,
                "parallel_execution": True
            }
        except Exception as e:
            logger.error(f"Error running parallel workflow: {str(e)}")
            return {
                "error": f"Failed to run parallel workflow: {str(e)}",
                "completed": False
            } 