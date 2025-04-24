from .srs_document_agent import SRSDocumentAgent
from app.services.chat.diagrams import create_diagram_agent
from app.services.chat.utils import get_user_info
from .document_writer_agent import DocumentWriterAgent
from .document_reviewer_agent import DocumentReviewerAgent
from typing import Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

class DocumentCoordinationError(Exception):
    """Base exception for document coordination errors."""
    pass

class DocumentCoordinator:
    def __init__(self, session_id: str, username: str):
        try:
            logger.info(f"Initializing DocumentCoordinator for session {session_id}")
            self.session_id = session_id
            self.username = username
            
            # Initialize agents
            self.srs_agent = SRSDocumentAgent(session_id, username)
            # Diagram and requirements agents are likely initialized by the caller (e.g., ChatManager)
            # We might not need to initialize them here if we receive their results as input.
            # Keep initialization for now, but consider removing if managed elsewhere.
            self.diagram_agent = create_diagram_agent(session_id, username)
            self.writer_agent = DocumentWriterAgent(session_id, username)
            self.reviewer_agent = DocumentReviewerAgent(session_id, username)
            
            logger.info("Document Coordinator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Document Coordinator: {str(e)}")
            raise DocumentCoordinationError(f"Failed to initialize Document Coordinator: {str(e)}") from e

    async def generate_complete_document(self, 
                                         chat_title: str, 
                                         interview_file_path: str, # Keep interview path
                                         diagram_result: Optional[Dict] = None # Add diagram_result back (optional)
                                         ) -> Dict:
        """Coordinate the generation of the complete SRS document, optionally including diagrams."""
        try:
            logger.info("Initiating SRS document generation protocol (with optional diagrams)")
            
            if not chat_title:
                logger.error("No chat title provided")
                raise ValueError("Chat title is required for document generation")
            
            if not interview_file_path or not os.path.exists(interview_file_path):
                error_msg = f"Interview file path missing or file not found: {interview_file_path}"
                logger.error(error_msg)
                raise DocumentCoordinationError(error_msg)

            # --- Read Diagram Content (if provided) ---
            diagram_content_str = None
            if diagram_result and isinstance(diagram_result, dict):
                diagram_file_path = diagram_result.get("diagram_file_path")
                if diagram_file_path and os.path.exists(diagram_file_path):
                    try:
                        with open(diagram_file_path, 'r', encoding='utf-8') as f:
                            diagram_content_str = f.read()
                        logger.info(f"Successfully read diagram content from {diagram_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to read diagram file {diagram_file_path}: {e}. SRS will not include diagrams.")
                        diagram_content_str = "[Error: Could not read diagram content]"
                else:
                    logger.warning(f"Diagram file path missing or file not found in diagram_result: {diagram_file_path}. SRS will not include diagrams.")
            else:
                 logger.info("No diagram result provided, SRS will not include diagrams.")
            
            # Fetch user info to get the correct group name
            try:
                user_info = await get_user_info(self.session_id)
                group_name = user_info.get("group_name", "default") 
                logger.info(f"Using group name '{group_name}' for SRS document.")
            except Exception as e:
                logger.error(f"Failed to get user info for group name: {e}. Using 'default'.")
                group_name = "default"

            # Then, Agent Jones creates the SRS document using the interview transcript and optional diagrams
            logger.info("Agent Jones creating SRS document from interview transcript (with diagrams if available)")
            try:
                document_result = await self.srs_agent.generate_srs_document(
                    chat_title=chat_title,
                    interview_file_path=interview_file_path,
                    group_name=group_name,
                    diagram_content_str=diagram_content_str # Pass diagram content
                )
            except Exception as e:
                logger.error(f"Failed to generate SRS document: {str(e)}", exc_info=True)
                raise DocumentCoordinationError("SRS document generation failed") from e
            
            if not document_result or "file_path" not in document_result:
                logger.error("Invalid SRS document generation result")
                raise DocumentCoordinationError("SRS document was not properly generated")
            
            # Validate the generated file exists
            if not os.path.exists(document_result["file_path"]):
                logger.error(f"Generated file not found: {document_result['file_path']}")
                raise DocumentCoordinationError("Generated document file is missing")
            
            # --- ADD REVIEW STEP --- 
            initial_srs_path = document_result["file_path"]
            review_message = "Review skipped due to error."
            final_srs_path = initial_srs_path # Default to initial path

            logger.info(f"Agent Brown initiating review of SRS document: {initial_srs_path}")
            try:
                # Call the reviewer agent. Pass requirements=None as they aren't directly available.
                # The reviewer should focus on the document's inherent quality.
                review_result = await self.reviewer_agent.review_document(
                    document_path=initial_srs_path,
                    requirements=None # Explicitly pass None
                )
                
                # Check if review was successful and produced an improved path
                if review_result and review_result.get("improved_path"):
                    final_srs_path = review_result["improved_path"]
                    # Optionally check if the improved path exists
                    if os.path.exists(final_srs_path):
                        review_message = f"Document reviewed and improved by Agent Brown: {review_result.get('message', 'Review successful.')}"
                        logger.info(f"Using reviewed SRS document: {final_srs_path}")
                    else:
                        logger.error(f"Reviewer reported improved path {final_srs_path}, but file not found. Using original.")
                        final_srs_path = initial_srs_path # Revert to original path
                        review_message = f"Review attempted, but improved file missing. Using original SRS. Reviewer message: {review_result.get('message', '')}"
                else:
                    # Review might have failed or didn't produce an improved path
                    logger.warning(f"Document review did not result in an improved path. Using original SRS. Reviewer message: {review_result.get('message', 'No improvement path specified.')}")
                    review_message = f"Review attempted by Agent Brown, but no improved version was saved. Reviewer message: {review_result.get('message', 'No improvement path specified.')}"
                    final_srs_path = initial_srs_path # Ensure we use original path
                    
            except Exception as e:
                logger.error(f"Error during SRS document review: {str(e)}", exc_info=True)
                # Keep the original document path and add error message
                review_message = f"An error occurred during Agent Brown's review: {str(e)}. Using the initial SRS document."
                final_srs_path = initial_srs_path # Ensure we use original path
            # --- END REVIEW STEP ---
            
            # Adjust success message based on whether diagrams were included
            diagram_message = "(including diagrams)" if diagram_content_str and "[Error:" not in diagram_content_str else "(diagrams not included or failed)"
            
            # Updated final message construction
            final_message = (
                f"System documentation protocol completed {diagram_message}.\n"
                f"SRS Document generated by Agent Jones: {document_result.get('message', 'Success')}\n"
                f"{review_message}"
            )
                 
            return {
                "message": final_message, # Use the combined message
                "file_path": final_srs_path # Return the path to the potentially reviewed document
            }
            
        except Exception as e:
            logger.error(f"Error in document coordination: {str(e)}", exc_info=True)
            if isinstance(e, (ValueError, DocumentCoordinationError)):
                raise
            raise DocumentCoordinationError(f"Document generation failed: {str(e)}") from e
    
    async def generate_technical_documentation(self, chat_title: str, messages: list, requirements: Optional[Dict] = None) -> Dict:
        """Generate technical documentation based on the conversation."""
        try:
            logger.info("Initiating technical documentation generation")
            
            if not messages:
                logger.error("No messages provided for documentation generation")
                raise ValueError("Cannot generate documentation without conversation history")
            
            if not chat_title:
                logger.error("No chat title provided")
                raise ValueError("Chat title is required for documentation generation")
                
            # Generate requirements if not provided
            if not requirements:
                logger.info("No requirements provided for tech doc generation. Using placeholders.")
                # Directly set placeholder data
                requirements = {
                    "functional": ["Requirements data not available for this document."],
                    "non_functional": ["Requirements data not available for this document."]
                }
            
            # Generate the technical document
            try:
                document_result = await self.writer_agent.generate_technical_document(
                    messages=messages,
                    requirements=requirements,
                    project_name=chat_title,
                    username=self.username
                )
            except Exception as e:
                logger.error(f"Failed to generate technical documentation: {str(e)}")
                raise DocumentCoordinationError("Technical documentation generation failed") from e
            
            if not document_result or "file_path" not in document_result:
                logger.error("Invalid technical documentation generation result")
                raise DocumentCoordinationError("Technical documentation was not properly generated")
            
            # Finally, Agent White reviews and improves the documentation
            logger.info("Agent White reviewing technical documentation")
            try:
                review_result = await self.reviewer_agent.review_document(
                    document_path=document_result["file_path"],
                    requirements=requirements
                )
            except Exception as e:
                logger.error(f"Failed to review technical documentation: {str(e)}")
                # We don't raise an error here because the review is optional
                review_result = {
                    "message": f"Document review failed: {str(e)}",
                    "improved_path": document_result["file_path"]  # Use the original document
                }
            
            # Return the results
            return {
                "message": (
                    "Technical documentation generation completed.\n"
                    f"{document_result['message']}\n"
                    f"{review_result.get('message', 'Document review was skipped.')}"
                ),
                "original_doc_path": document_result["file_path"],
                "reviewed_doc_path": review_result.get("improved_path", document_result["file_path"]),
                "requirements": requirements
            }
            
        except Exception as e:
            logger.error(f"Error in technical documentation coordination: {str(e)}")
            if isinstance(e, (ValueError, DocumentCoordinationError)):
                raise
            raise DocumentCoordinationError(f"Technical documentation generation failed: {str(e)}") from e
    
    async def evaluate_document_quality(self, document_path: str) -> Dict:
        """Evaluate the quality of a document."""
        try:
            logger.info(f"Evaluating document quality: {document_path}")
            
            if not document_path:
                logger.error("No document path provided")
                raise ValueError("Document path is required for evaluation")
            
            # Check if the document exists
            if not os.path.exists(document_path):
                logger.error(f"Document not found: {document_path}")
                raise FileNotFoundError(f"Document not found: {document_path}")
            
            # Use Agent White to evaluate the document
            logger.info("Agent White evaluating document quality")
            try:
                eval_result = await self.reviewer_agent.evaluate_documentation_quality(document_path)
            except Exception as e:
                logger.error(f"Failed to evaluate document quality: {str(e)}")
                raise DocumentCoordinationError("Document quality evaluation failed") from e
            
            return {
                "message": eval_result["message"],
                "document_path": document_path,
                "evaluation": eval_result["evaluation"]
            }
            
        except Exception as e:
            logger.error(f"Error in document quality evaluation: {str(e)}")
            if isinstance(e, (ValueError, FileNotFoundError, DocumentCoordinationError)):
                raise
            raise DocumentCoordinationError(f"Document quality evaluation failed: {str(e)}") from e