from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import RedisChatMessageHistory
from app.core.config import settings
from typing import Dict, List, Any, Optional
import logging
import os
import time
import json
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


class DocumentReviewerAgent:
    """
    Agent responsible for reviewing and improving technical documentation.
    This agent (Agent White) specializes in quality assurance for documentation.
    """

    def __init__(self, session_id: str, username: str):
        try:
            logger.info(f"Initializing DocumentReviewerAgent for session {session_id}")
            self.session_id = session_id
            self.username = username

            # Get agent name from settings
            self.agent_name = settings.AGENT_WHITE_NAME

            # Initialize LLM for document review
            self.llm = ChatOpenAI(
                model_name=settings.AGENT_WHITE_MODEL,
                temperature=settings.AGENT_WHITE_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
                # Increase timeout significantly for potentially long review task
                request_timeout=settings.OPENAI_TIMEOUT
                or 300,  # Use setting or default to 300s
                max_retries=settings.OPENAI_MAX_RETRIES,
            )

            # Setup Redis memory
            redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            self.message_history = RedisChatMessageHistory(
                session_id=f"docreviewer_{session_id}", url=redis_url
            )

            # Create user-specific documentation directory
            self.docs_dir = os.path.join(
                settings.get_user_data_path(username), "documentation"
            )
            if not os.path.exists(self.docs_dir):
                logger.info(f"Creating documentation directory: {self.docs_dir}")
            os.makedirs(self.docs_dir, exist_ok=True)

            # Load prompts from YAML
            prompts_path = os.path.join(
                os.path.dirname(__file__), "..", "prompts", "review_agent_prompt.yaml"
            )
            try:
                with open(prompts_path, "r") as f:
                    self.prompts = yaml.safe_load(f)
                logger.info(f"Successfully loaded reviewer prompts from {prompts_path}")
            except FileNotFoundError:
                logger.error(
                    f"Document Reviewer Prompt file not found at {prompts_path}. Please create it."
                )
                raise
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML prompt file {prompts_path}: {e}")
                raise

            logger.info(
                f"DocumentReviewerAgent initialized successfully for session {session_id}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize DocumentReviewerAgent: {str(e)}")
            raise

    def _create_prompt_from_config(self, prompt_config: Dict) -> ChatPromptTemplate:
        """Creates a ChatPromptTemplate from a loaded YAML config dictionary."""
        messages = []
        for key, value in prompt_config.items():
            if key == "system":
                messages.append(("system", value))
            elif key == "human":
                messages.append(("human", value))
            elif key == "ai":
                messages.append(("ai", value))
            elif key == "history":  # Handle the messages placeholder
                messages.append(
                    MessagesPlaceholder(variable_name=value["variable_name"])
                )
            else:
                logger.warning(f"Unknown prompt component type '{key}' in config")
        return ChatPromptTemplate.from_messages(messages)

    async def review_document(
        self,
        document_path: str,
        requirements: Optional[Dict[str, List[Dict[str, str]]]] = None,
    ) -> Dict[str, Any]:
        """
        Review a technical document and provide feedback and improvements.

        Args:
            document_path: Path to the document to review
            requirements: Dictionary containing functional and non-functional requirements (optional)

        Returns:
            Dictionary containing the review results and improved document
        """
        try:
            logger.info(f"Reviewing document: {document_path}")

            # Clear previous messages
            self.message_history.clear()

            # Check if the document exists
            if not os.path.exists(document_path):
                logger.error(f"Document not found: {document_path}")
                raise FileNotFoundError(f"Document not found: {document_path}")

            # Read the document content
            with open(document_path, "r") as f:
                document_content = f.read()

            # Prepare requirements for the prompt if provided
            requirements_text = ""
            if requirements:
                functional_reqs = requirements.get("functional_requirements", [])
                non_functional_reqs = requirements.get(
                    "non_functional_requirements", []
                )

                requirements_text = "Functional Requirements:\n"
                for req in functional_reqs:
                    requirements_text += f"- {req.get('id', 'FR-X')}: {req.get('name', 'Unnamed')} - {req.get('description', 'No description')}\n"

                requirements_text += "\nNon-Functional Requirements:\n"
                for req in non_functional_reqs:
                    requirements_text += f"- {req.get('id', 'NFR-X')}: {req.get('name', 'Unnamed')} - {req.get('description', 'No description')}\n"

            # Create the prompt for reviewing the document from the loaded YAML config
            review_prompt_config = self.prompts.get("review_document_prompt")
            if not review_prompt_config:
                logger.error(
                    "'review_document_prompt' not found in loaded YAML prompts."
                )
                raise ValueError("Missing review document prompt configuration")
            review_prompt = self._create_prompt_from_config(review_prompt_config)

            # Generate the review / improved document
            review_chain = review_prompt | self.llm
            # Use input variables defined in the YAML prompt ('document', 'diagrams', 'agent_name')
            review_response = await review_chain.ainvoke(
                {
                    "agent_name": self.agent_name,
                    "document": document_content,  # Pass the original document content
                    # If diagrams are needed, they should be read and passed similarly
                    "diagrams": "[Diagram content not currently passed in this review method]",  # Placeholder
                }
            )

            # The LLM is now tasked with returning the *improved* document content directly
            improved_document = review_response.content.strip()
            review_content = (
                improved_document  # The review content *is* the improved doc
            )

            # Create a timestamp for the improved document
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")

            # Get the original filename without extension
            original_filename = os.path.basename(document_path)
            filename_without_ext = os.path.splitext(original_filename)[0]

            # Create the improved document filename
            improved_filename = f"{filename_without_ext}_reviewed_{timestamp}.md"
            improved_path = os.path.join(self.docs_dir, improved_filename)

            # Write the improved document to a file
            with open(improved_path, "w") as f:
                f.write(improved_document)

            logger.info(f"Document review completed successfully: {improved_path}")

            return {
                "message": f"Document review completed successfully by {self.agent_name}.",
                "original_path": document_path,
                "improved_path": improved_path,
                "review": review_content,
            }

        except Exception as e:
            logger.error(f"Error reviewing document: {str(e)}")
            raise

    async def evaluate_documentation_quality(
        self, document_path: str
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of a technical document and provide a score and feedback.

        Args:
            document_path: Path to the document to evaluate

        Returns:
            Dictionary containing the evaluation results
        """
        try:
            logger.info(f"Evaluating document quality: {document_path}")

            # Check if the document exists
            if not os.path.exists(document_path):
                logger.error(f"Document not found: {document_path}")
                raise FileNotFoundError(f"Document not found: {document_path}")

            # Read the document content
            with open(document_path, "r") as f:
                document_content = f.read()

            # Create the prompt for evaluating the document from YAML config
            eval_prompt_config = self.prompts.get("evaluate_quality_prompt")
            if not eval_prompt_config:
                logger.error(
                    "'evaluate_quality_prompt' not found in loaded YAML prompts."
                )
                raise ValueError("Missing evaluate quality prompt configuration")
            eval_prompt = self._create_prompt_from_config(eval_prompt_config)

            # Generate the evaluation
            eval_chain = eval_prompt | self.llm
            eval_response = await eval_chain.ainvoke(
                {"document_content": document_content}
            )

            eval_content = eval_response.content

            # Parse the JSON response
            # In a real implementation, we might want to use a more robust method to extract the JSON
            try:
                # Find the JSON part in the response
                json_start = eval_content.find("{")
                json_end = eval_content.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = eval_content[json_start:json_end]
                    evaluation = json.loads(json_str)
                else:
                    # If JSON parsing fails, return the raw response
                    evaluation = {"raw_response": eval_content}
            except json.JSONDecodeError:
                logger.warning("Failed to parse evaluation response as JSON")
                evaluation = {"raw_response": eval_content}

            logger.info(f"Document quality evaluation completed successfully")

            return {
                "message": f"Document quality evaluation completed successfully by {self.agent_name}.",
                "document_path": document_path,
                "evaluation": evaluation,
            }

        except Exception as e:
            logger.error(f"Error evaluating document quality: {str(e)}")
            raise
