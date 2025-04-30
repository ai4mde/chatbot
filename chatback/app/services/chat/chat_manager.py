from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import RedisChatMessageHistory
from app.core.config import settings
from app.services.vector_store import QdrantManager
from app.services.chat.interview import create_interview_agent
from app.services.chat.documents import DocumentCoordinator
from enum import Enum
import logging
import traceback
from fastapi import HTTPException
from datetime import datetime
import time
import os

# Import errors from the new location
from .errors import ChatError, ChatManagerError

logger = logging.getLogger(__name__)

# Flag to disable diagram and document phases for testing
DISABLE_DIAGRAM_AND_DOCUMENT_PHASES = False


class ConversationState(Enum):
    INTERVIEW = "interview"
    DIAGRAM = "diagram"
    REQUIREMENTS = "requirements"
    DOCUMENT = "document"
    COMPLETED = "completed"


class LangChainChatManager:
    def __init__(self, session_id: str, username: str):
        try:
            logger.info(f"Initializing LangChainChatManager for session {session_id}")
            if not session_id:
                raise ChatManagerError("Session ID cannot be empty")

            self.session_id = session_id
            self.username = username

            # The Architect - oversees the system
            self.manager_name = "The Architect"

            # Initialize agents
            try:
                # Use the factory to create the interview agent
                self.interview_agent = create_interview_agent(
                    session_id, username
                )  # Agent Smith
                logger.info("Agent Smith initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Agent Smith: {str(e)}")
                raise ChatManagerError("Failed to initialize interview agent") from e

            try:
                self.document_coordinator = DocumentCoordinator(
                    session_id, username
                )  # Coordinates Jones & Jackson
                logger.info("Documentation team initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Documentation team: {str(e)}")
                raise ChatManagerError("Failed to initialize documentation team") from e

            self.state = ConversationState.INTERVIEW
            self.user_responses = {}

            logger.info(f"{self.manager_name} initialized successfully")

        except ChatManagerError as e:
            logger.error(f"Chat manager initialization error: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error initializing {self.manager_name}: {str(e)}\n{traceback.format_exc()}"
            )
            raise ChatManagerError(
                f"Failed to initialize chat manager: {str(e)}"
            ) from e

    async def _reset_system(self) -> str:
        """Reset the system state and clear message histories."""
        try:
            logger.info(
                f"{self.manager_name} initiating system reset for session {self.session_id}"
            )

            # Clear message histories
            try:
                # For InterviewAgentGraph, clear messages in state
                if (
                    hasattr(self.interview_agent, "state")
                    and "messages" in self.interview_agent.state
                ):
                    self.interview_agent.state["messages"] = []

                # Clear document coordinator message histories
                if hasattr(self.document_coordinator, "srs_agent") and hasattr(
                    self.document_coordinator.srs_agent, "message_history"
                ):
                    self.document_coordinator.srs_agent.message_history.clear()

                if hasattr(self.document_coordinator, "diagram_agent") and hasattr(
                    self.document_coordinator.diagram_agent, "message_history"
                ):
                    self.document_coordinator.diagram_agent.message_history.clear()
            except Exception as e:
                logger.error(f"Error clearing message histories: {str(e)}")
                raise ChatManagerError("Failed to clear message histories") from e

            # Reset state
            self.state = ConversationState.INTERVIEW

            # Initialize new interview
            try:
                initial_response = await self.interview_agent.process_message("hello")
                return f"{self.manager_name}: System reset complete. Initiating new interview protocol...\n\n{initial_response}"
            except Exception as e:
                logger.error(f"Error starting new interview: {str(e)}")
                raise ChatManagerError("Failed to start new interview") from e

        except Exception as e:
            logger.error(f"Error in system reset: {str(e)}")
            raise

    async def process_message(self, content: str) -> str:
        """Process incoming messages and manage conversation flow."""
        try:
            logger.info(
                f"{self.manager_name} processing message for session {self.session_id} in state {self.state}"
            )

            if not content:
                raise ChatManagerError("Message content cannot be empty")

            # Handle system reset
            if content.lower() == "restart":
                return await self._reset_system()

            # Handle completed state
            if self.state == ConversationState.COMPLETED:
                return f"{self.manager_name}: The system specifications are complete. Type 'restart' to begin a new session."

            # Handle interview state
            if self.state == ConversationState.INTERVIEW:
                try:
                    response = await self.interview_agent.process_message(content)

                    # Check for completion phrases in the response
                    completion_indicators = [
                        "Thank you for completing this comprehensive interview",
                        "Please wait while our specialized agents process this information",
                        "Documentation Phase",
                    ]

                    # Add detailed logging for completion detection
                    logger.info(
                        f"Checking for completion indicators in response: {response[:100]}..."
                    )
                    for indicator in completion_indicators:
                        if indicator in response:
                            logger.info(f"Found completion indicator: '{indicator}'")

                    if any(
                        indicator in response for indicator in completion_indicators
                    ):
                        logger.info(
                            "Interview completion detected, showing completion message"
                        )

                        # Save the interview document
                        try:
                            interview_save_result = (
                                await self.interview_agent.save_interview_document()
                            )
                            logger.info(
                                f"Interview document save result: {interview_save_result}"
                            )

                            # Get the chat title from the interview agent
                            chat_title = (
                                self.interview_agent.state.get("chat_name")
                                or f"Interview-{self.session_id}"
                            )

                            # Extract the actual file path from the save result
                            # Handle both dictionary and string return types for backward compatibility
                            if isinstance(interview_save_result, dict):
                                interview_file_path = interview_save_result.get(
                                    "file_path"
                                )
                                save_message = interview_save_result.get(
                                    "message", "Interview document saved successfully."
                                )
                            else:
                                # For backward compatibility with older versions that return a string
                                interview_file_path = None
                                save_message = (
                                    interview_save_result
                                    if isinstance(interview_save_result, str)
                                    else "Interview document saved."
                                )

                            if interview_file_path:
                                # Extract the filename without extension to use as chat_title
                                interview_filename = os.path.basename(
                                    interview_file_path
                                )
                                if interview_filename.endswith(".md"):
                                    interview_filename = interview_filename[
                                        :-3
                                    ]  # Remove .md extension
                                chat_title = interview_filename
                                logger.info(
                                    f"Using interview filename as chat_title: {chat_title}"
                                )

                            # Always proceed with the standard documentation transition now
                            logger.info(
                                "Interview complete, immediately transitioning to documentation."
                            )
                            # Pass the interview response, chat_title, and file path to the transition handler
                            return await self._handle_documentation_transition(
                                interview_response=response,
                                chat_title=chat_title,
                                interview_file_path=interview_file_path,
                            )
                        except Exception as e:
                            logger.error(
                                f"Error saving interview document or triggering next phase: {str(e)}",
                                exc_info=True,
                            )
                            # Return the original interview completion response, but log the error
                            return (
                                f"{response}\n\n{self.manager_name}: There was an error saving the interview document or starting the next phase: {str(e)}\n"
                                f"The interview transcript may not have been saved correctly. Please check or contact support."
                            )

                    return response

                except Exception as e:
                    logger.error(f"Error in interview process: {str(e)}")
                    raise ChatManagerError("Error during interview process") from e

            # Handle documentation transition after interview completion (REMOVED - transition happens immediately now)
            # if self.state == ConversationState.DIAGRAM and not DISABLE_DIAGRAM_AND_DOCUMENT_PHASES:
            #    logger.info("Starting documentation process after interview completion")
            #    return await self._handle_documentation_transition("")
            # elif self.state == ConversationState.DIAGRAM and DISABLE_DIAGRAM_AND_DOCUMENT_PHASES:
            #    logger.info("Diagram and document phases are disabled. Returning to interview state.")
            #    self.state = ConversationState.INTERVIEW
            #    return f"{self.manager_name}: Diagram and document phases are currently disabled for testing. Type 'restart' to begin a new interview."

            # Fallback if state is unexpected
            logger.warning(f"Unexpected state {self.state} reached in process_message")
            return f"{self.manager_name}: Error in the system (unexpected state: {self.state}). Type 'restart' to reinitialize the process."

        except ChatManagerError as e:
            logger.error(f"Chat processing error: {str(e)}")
            return f"{self.manager_name}: An error has occurred: {str(e)}. Type 'restart' to reinitialize the process."
        except Exception as e:
            logger.error(
                f"Unexpected error in message processing: {str(e)}\n{traceback.format_exc()}"
            )
            return f"{self.manager_name}: A system error has occurred. Type 'restart' to reinitialize the process."

    async def _handle_documentation_transition(
        self,
        interview_response: str,
        chat_title: str,
        interview_file_path: Optional[str],
    ) -> str:
        """Handle transition from interview to documentation phase."""
        logger.info(
            f"[TRANSITION] Entering _handle_documentation_transition for session {self.session_id}"
        )
        try:
            logger.info(f"{self.manager_name} transitioning to documentation phase")

            # First transition to DIAGRAM phase
            self.state = ConversationState.DIAGRAM

            # Updated transition message reflecting active agents
            transition_message = (
                f"\n\n{self.manager_name}: Interview completed successfully. Thank you for providing all the necessary information.\n\n"
                f"Initiating documentation process...\n"
                f"[System]: Agent Jackson is analyzing the interview and generating UML diagrams...\n"
                f"[System]: Agent Jones is creating the SRS document using the interview and diagrams...\n"
                f"Please wait while our specialized agents process your information. This typically takes 1-2 minutes..."
            )

            # Ensure the file path exists before proceeding
            if not interview_file_path or not os.path.exists(interview_file_path):
                error_msg = f"Interview file path missing or file not found after save: {interview_file_path}"
                logger.error(error_msg)
                # Return a combined message including the initial transition info and the error
                return (
                    f"{transition_message}\n\n"
                    f"{self.manager_name}: An internal error occurred ({error_msg}). The documentation process cannot continue. Please report this issue."
                )
            logger.info(
                f"Using provided chat_title: {chat_title} and interview_file_path: {interview_file_path}"
            )

            try:
                # Get messages from InterviewAgentGraph state
                messages_data = self.interview_agent.state["messages"]
                # Convert to LangChain message format
                messages = []
                for msg in messages_data:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
                    elif msg["role"] == "system":
                        messages.append(SystemMessage(content=msg["content"]))

                # Process through each phase sequentially
                logger.info(
                    f"{self.manager_name} initiating document generation protocol"
                )

                # --- Requirements Phase Removed ---
                requirements_message = (
                    "[INFO] Requirements extraction skipped in this workflow."
                )
                logger.info(requirements_message)
                # --- END Requirements Phase Removed ---

                # --- RE-ENABLED Diagram Phase ---
                logger.info(f"{self.manager_name} initiating diagram generation")
                self.state = ConversationState.DIAGRAM  # Keep state for now
                diagrams_result = {}  # Initialize in case of error
                diagrams_message = "[INFO] Diagram generation skipped due to an error."
                try:
                    if not hasattr(self, "diagram_agent"):
                        from app.services.chat.diagrams import create_diagram_agent

                        self.diagram_agent = create_diagram_agent(
                            self.session_id, self.username
                        )
                        logger.info("Diagram agent initialized")

                    diagrams_result = await self.diagram_agent.generate_uml_diagrams(
                        messages_data
                    )
                    logger.info(f"Diagram generation completed: {diagrams_result}")

                    if "error" in diagrams_result:
                        logger.error(
                            f"Error generating UML diagrams: {diagrams_result['error']}"
                        )
                        diagrams_message = f"However, there was an error generating UML diagrams: {diagrams_result['error']}\n"
                    else:
                        logger.info(
                            f"UML diagrams generated successfully: {diagrams_result.get('message', 'No message')}"
                        )
                        # Get the number of diagrams (or check for the file path)
                        diagram_file_path = diagrams_result.get("diagram_file_path")
                        diagram_files = diagrams_result.get("diagram_files", {})
                        count = 1 if diagram_file_path else len(diagram_files)
                        diagrams_message = (
                            f"UML diagrams generation completed successfully!\n"
                            f"Generated {count} UML diagram file(s).\n"
                        )
                except Exception as e:
                    logger.error(
                        f"Error during diagram generation: {str(e)}", exc_info=True
                    )
                    diagrams_message = f"However, there was an error generating UML diagrams: {str(e)}\n"
                # --- END RE-ENABLED Diagram Phase ---

                # 3. DOCUMENT phase - Generate SRS document directly
                logger.info(
                    f"{self.manager_name} initiating direct SRS document generation"
                )
                self.state = ConversationState.DOCUMENT

                # Generate the complete document using INTERVIEW FILE PATH and DIAGRAM RESULT
                result = await self.document_coordinator.generate_complete_document(
                    chat_title=chat_title,
                    interview_file_path=interview_file_path,  # Pass the interview file path
                    diagram_result=diagrams_result,  # Pass the diagram result dictionary
                )

                # Check for errors during final document generation
                if not result or "file_path" not in result:
                    error_msg = f"Final document generation failed: {result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    final_message = (
                        f"{transition_message}\n\n"
                        # Include the info messages about skipped phases
                        f"{requirements_message}\n"
                        f"{diagrams_message}\n"
                        f"{self.manager_name}: An error occurred during final document assembly: {error_msg}. Please report this issue."
                    )
                    self.state = (
                        ConversationState.COMPLETED
                    )  # Mark as completed even with error
                    return final_message

                # Construct the final success message (adjusted)
                completion_message = (
                    f"{transition_message}\n\n"
                    f"[System]: Documentation process completed successfully! 🎉\n"
                    # f"{requirements_message}\n" # Still skipped
                    f"{diagrams_message}\n"  # Re-added diagram message
                    f"{result['message']}\n\n"  # Message from document coordinator
                    f"{self.manager_name}: Your SRS documentation (including diagrams) has been generated and saved at: {result['file_path']}\n"
                    f"The interview transcript has also been saved and is accessible to all users in your group.\n\n"
                    f"Thank you for using our requirements gathering system."
                )

                self.state = ConversationState.COMPLETED
                return completion_message
            except Exception as e:
                logger.error(
                    f"Error extracting messages or initiating documentation protocol: {str(e)}",
                    exc_info=True,
                )
                return (
                    f"{transition_message}\n\n"
                    f"{self.manager_name}: An error occurred while preparing for documentation generation: {str(e)}. Please report this issue."
                )

        except Exception as e:
            logger.error(f"Error in documentation transition: {str(e)}")
            self.state = ConversationState.INTERVIEW  # Revert on error
            return (
                f"{self.manager_name}: I apologize, but there was an error generating the documentation: {str(e)}. "
                f"Please try again or contact support for assistance."
            )

    def get_conversation_state(self) -> Dict:
        """Return current conversation state information"""
        # Determine the current agent name
        current_agent = None
        if self.state == ConversationState.INTERVIEW:
            # Handle the case where interview_agent might not have agent_name attribute
            if hasattr(self.interview_agent, "agent_name"):
                current_agent = self.interview_agent.agent_name
            else:
                current_agent = "Agent Smith"  # Default name from settings
        elif self.state == ConversationState.DOCUMENT:
            current_agent = "Documentation Team"
        elif self.state == ConversationState.DIAGRAM:
            current_agent = "Agent Jackson"

        return {
            "manager": self.manager_name,
            "state": self.state.value,
            "current_agent": current_agent,
            "user_responses": (
                self.user_responses if hasattr(self, "user_responses") else {}
            ),
        }
