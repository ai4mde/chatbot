import logging
import os
import time
from datetime import datetime
import yaml
from typing import Dict, List, Any, Optional
import jinja2

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import RedisChatMessageHistory

# Local imports
from app.core.config import settings
from ..errors import DocumentGenerationError # Assuming you have custom errors

logger = logging.getLogger(__name__)

class SRSDocumentAgent:
    def __init__(self, session_id: str, username: str):
        try:
            logger.info(f"Initializing SRSDocumentAgent for session {session_id}")
            self.session_id = session_id
            self.username = username
            self.agent_name = settings.AGENT_JONES_NAME

            # Initialize LLM
            self.llm = ChatOpenAI(
                model_name=settings.AGENT_JONES_MODEL,
                temperature=settings.AGENT_JONES_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
                request_timeout=settings.OPENAI_TIMEOUT,
                max_retries=settings.OPENAI_MAX_RETRIES
            )

            # Load SRS section generation prompts from YAML
            prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'srs_agent_prompt.yaml')
            try:
                with open(prompts_path, 'r') as f:
                    self.prompts = yaml.safe_load(f)
                logger.info(f"Successfully loaded SRS section prompts from {prompts_path}")
            except FileNotFoundError:
                logger.error(f"SRS Agent Prompt file not found at {prompts_path}. Please create it.")
                raise
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML prompt file {prompts_path}: {e}")
                raise
            
            # Define the order of sections and corresponding prompt keys
            self.srs_sections = [
                ("Introduction", "generate_introduction_section"),
                ("Overall Description", "generate_overall_description_section"),
                ("System Features", "generate_system_features_section"),
                ("External Interface Requirements", "generate_external_interface_reqs_section"),
                ("Non-functional Requirements", "generate_non_functional_reqs_section"),
                ("Other Requirements", "generate_other_reqs_section"),
                # Add Appendices section generation if needed later
            ]

            logger.info(f"{self.agent_name} initialized successfully")

            # --- Initialize Jinja2 Environment ---
            template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), '..', 'templates'))
            self.jinja_env = jinja2.Environment(loader=template_loader, autoescape=False) # autoescape=False for markdown
            logger.info(f"Jinja2 Environment initialized loading templates from {template_loader.searchpath}")
            # --- END Jinja2 Initialization ---

        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_name}: {str(e)}", exc_info=True)
            raise DocumentGenerationError(f"Failed to initialize SRS document agent: {str(e)}") from e

    def _create_prompt_from_config(self, prompt_config: Dict) -> ChatPromptTemplate:
        """Creates a ChatPromptTemplate from a loaded YAML config dictionary."""
        messages = []
        for key, value in prompt_config.items():
            if key == 'system':
                messages.append(("system", value))
            elif key == 'human':
                messages.append(("human", value))
            # Removed AI and History placeholders as they are not used in these prompts
            else:
                logger.warning(f"Unknown prompt component type '{key}' in config for SRS section generation")
        return ChatPromptTemplate.from_messages(messages)

    async def _generate_srs_section(self, section_name: str, prompt_key: str, interview_content: str) -> str:
        """Generates content for a specific SRS section using the LLM."""
        logger.info(f"Generating SRS Section: {section_name}")
        prompt_config = self.prompts.get(prompt_key)
        if not prompt_config:
            logger.error(f"Prompt configuration '{prompt_key}' not found.")
            return f"## {section_name}\n\n[Error: Prompt configuration missing]\n"

        try:
            prompt = self._create_prompt_from_config(prompt_config)
            chain = prompt | self.llm
            response = await chain.ainvoke({"interview_transcript": interview_content})
            logger.info(f"Successfully generated content for section: {section_name}")
            # Basic validation/cleanup - ensure it starts with the expected header
            generated_content = response.content.strip()
            expected_header = f"## {section_name}"
            # A more robust check might be needed depending on LLM consistency
            if not generated_content.startswith(expected_header):
                 logger.warning(f"Generated content for {section_name} did not start with expected header. Prepending header.")
                 # Attempt to prepend if missing, or return as is with a warning
                 generated_content = f"{expected_header}\n\n{generated_content}"

            return generated_content
        except Exception as e:
            logger.error(f"Error generating SRS section '{section_name}': {e}", exc_info=True)
            return f"## {section_name}\n\n[Error: Failed to generate content for this section due to: {e}]\n"

    async def generate_srs_document(self, chat_title: str, interview_file_path: str, group_name: str, diagram_content_str: Optional[str] = None) -> Dict:
        """Generate an SRS document from interview transcript, optionally appending diagrams."""
        try:
            logger.info(f"Generating SRS document for chat '{chat_title}' using interview: {interview_file_path}")
            
            # Define version 
            version = "1.1-direct+diagrams"

            # --- Read Interview Content ---
            try:
                with open(interview_file_path, 'r', encoding='utf-8') as f:
                    interview_content = f.read()
                logger.info(f"Successfully read interview content. Length: {len(interview_content)}")
            except FileNotFoundError:
                logger.error(f"Interview file not found at {interview_file_path}")
                raise DocumentGenerationError(f"Interview file not found: {interview_file_path}")
            except Exception as e:
                logger.error(f"Error reading interview file {interview_file_path}: {e}", exc_info=True)
                raise DocumentGenerationError(f"Error reading interview file: {e}") from e

            # --- Generate Sections Sequentially ---
            generated_sections_data = []
            # Sequential execution (safer for potential rate limits / easier debugging)
            for section_name, prompt_key in self.srs_sections:
                section_content = await self._generate_srs_section(section_name, prompt_key, interview_content)
                # Store as dict for Jinja loop
                generated_sections_data.append({"content": section_content})

            # --- Prepare Context for Jinja2 Template ---
            current_date = datetime.now().strftime("%Y-%m-%d")
            description = f"Software Requirements Specification for project '{chat_title}'"
            safe_chat_title = chat_title.replace(" ", "_").replace("/", "_").replace("\\", "_")
            if safe_chat_title.endswith('.md'):
                safe_chat_title = safe_chat_title[:-3]
                
            # Handle diagram content for the template variable
            template_diagram_content = None
            if diagram_content_str and "[Error:" not in diagram_content_str:
                template_diagram_content = diagram_content_str
            elif diagram_content_str: # Contains error message
                template_diagram_content = diagram_content_str # Pass error through
                logger.warning("Diagram content string contains an error message, passing to template.")
            else:
                 logger.info("No diagram content provided for template.")
                 
            context = {
                "id": safe_chat_title,
                "title": chat_title,
                "description": description,
                "date": current_date,
                "version": version,
                "sections": generated_sections_data, # Pass list of section dicts
                "diagram_content": template_diagram_content # Pass diagram content or None
            }
            # --- END Context Preparation ---

            # --- Render Template ---
            try:
                template = self.jinja_env.get_template("srs_document.md.j2")
                final_srs_content = template.render(context)
                logger.info("Successfully rendered SRS document using Jinja2 template.")
            except jinja2.TemplateNotFound:
                logger.error(f"Jinja2 template 'srs_document.md.j2' not found.")
                raise DocumentGenerationError("SRS template file not found")
            except Exception as e:
                logger.error(f"Error rendering Jinja2 template: {e}", exc_info=True)
                raise DocumentGenerationError(f"Failed to render SRS template: {e}") from e
            # --- END Render Template ---

            # --- Save Document ---
            # Directory and filename logic remains largely the same
            srsdocs_dir = os.path.join(settings.CHATBOT_DATA_PATH, group_name, "srsdocs")
            os.makedirs(srsdocs_dir, exist_ok=True)
            logger.info(f"Ensured SRS documents directory exists: {srsdocs_dir}")

            # Create the output filename and path (using timestamp for uniqueness)
            timestamp = int(time.time())
            filename = f"{safe_chat_title}_{version}_{timestamp}.md"
            filepath = os.path.join(srsdocs_dir, filename)
            logger.info(f"Target SRS file path: {filepath}")

            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(final_srs_content)
                logger.info(f"SRS document saved successfully to {filepath}")
            except Exception as e:
                logger.error(f"Error writing SRS document to file {filepath}: {e}", exc_info=True)
                raise DocumentGenerationError(f"Error writing SRS document to file: {e}") from e

            return {
                "success": True,
                "message": f"SRS document (with Appendix) generated from interview and saved successfully.",
                "file_path": filepath
            }

        except Exception as e:
            logger.error(f"Error generating SRS document: {str(e)}", exc_info=True)
            # Ensure specific exceptions are caught if needed, otherwise raise a generic one
            if isinstance(e, DocumentGenerationError):
                 raise
            raise DocumentGenerationError(f"SRS document generation failed: {str(e)}") from e