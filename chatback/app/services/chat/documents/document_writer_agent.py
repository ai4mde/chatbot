from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import RedisChatMessageHistory
from app.core.config import settings
from typing import Dict, List, Any
import logging
import os
import time
import json
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)

class DocumentWriterAgent:
    """
    Agent responsible for writing technical documentation based on requirements and diagrams.
    This agent (Agent Thompson) specializes in creating detailed technical documentation.
    """
    
    def __init__(self, session_id: str, username: str):
        try:
            logger.info(f"Initializing DocumentWriterAgent for session {session_id}")
            self.session_id = session_id
            self.username = username
            
            # Get agent name from settings
            # Removed: self.agent_name = settings.AGENT_THOMPSON_NAME
            # Assign a default name or use another setting if needed
            self.agent_name = "Document Writer" # Example: Using a generic name
            
            # Initialize LLM for technical writing
            # Need to decide which model to use now that Thompson is removed
            # Using Agent Jones (SRS writer) model as a placeholder
            self.llm = ChatOpenAI(
                model_name=settings.AGENT_JONES_MODEL, 
                temperature=settings.AGENT_JONES_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
                request_timeout=settings.OPENAI_TIMEOUT,
                max_retries=settings.OPENAI_MAX_RETRIES
            )
            
            # Setup Redis memory
            redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            self.message_history = RedisChatMessageHistory(
                session_id=f"docwriter_{session_id}",
                url=redis_url
            )
            
            # Create user-specific documentation directory
            self.docs_dir = os.path.join(settings.get_user_data_path(username), "documentation")
            if not os.path.exists(self.docs_dir):
                logger.info(f"Creating documentation directory: {self.docs_dir}")
            os.makedirs(self.docs_dir, exist_ok=True)
            
            # Load documentation template
            self.doc_template_path = os.path.join(settings.TEMPLATES_PATH, "technical_doc_template.md")
            
            # Check if template exists
            if not os.path.exists(self.doc_template_path):
                logger.error(f"Documentation template file not found at: {self.doc_template_path}")
                # Create a default template if it doesn't exist
                self._create_default_template()
            
            # Check if template is readable
            if not os.access(self.doc_template_path, os.R_OK):
                logger.error(f"Documentation template file is not readable: {self.doc_template_path}")
                raise PermissionError(
                    f"Cannot read documentation template file. "
                    f"Please check file permissions at {self.doc_template_path}"
                )
            
            # Load the template content
            with open(self.doc_template_path, 'r') as f:
                self.template_content = f.read()
            
            # Load prompts from YAML
            prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'document_writer_prompt.yaml')
            try:
                with open(prompts_path, 'r') as f:
                    self.prompts = yaml.safe_load(f)
                logger.info(f"Successfully loaded writer prompts from {prompts_path}")
            except FileNotFoundError:
                logger.error(f"Document Writer Prompt file not found at {prompts_path}. Please create it.")
                raise
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML prompt file {prompts_path}: {e}")
                raise
            
            logger.info(f"DocumentWriterAgent initialized successfully for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DocumentWriterAgent: {str(e)}")
            raise
    
    def _create_default_template(self):
        """Create a default technical documentation template if none exists."""
        try:
            template_dir = settings.TEMPLATES_PATH
            os.makedirs(template_dir, exist_ok=True)
            
            default_template = """---
id: {project_id}
title: {title}
description: {description}
date: {date}
---
# Technical Documentation
## For {project_name}

Version {version}
Prepared by {agent_name}
Organization: {organization}
Last Updated: {date_updated}

## Revision History
| Name | Date | Reason For Changes | Version |
| ---- | ---- | ----------------- | ------- |
| {agent_name} | {date_updated} | Initial version | {version} |

## 1. Introduction
{introduction}

## 2. System Architecture
{system_architecture}

## 3. Component Design
{component_design}

## 4. API Documentation
{api_documentation}

## 5. Database Schema
{database_schema}

## 6. Deployment Instructions
{deployment_instructions}

## 7. Testing Strategy
{testing_strategy}

## 8. Appendices
{appendices}
"""
            
            with open(self.doc_template_path, 'w') as f:
                f.write(default_template)
            
            logger.info(f"Created default technical documentation template at {self.doc_template_path}")
            self.template_content = default_template
            
        except Exception as e:
            logger.error(f"Failed to create default template: {str(e)}")
            raise
    
    def _create_prompt_from_config(self, prompt_config: Dict) -> ChatPromptTemplate:
        """Creates a ChatPromptTemplate from a loaded YAML config dictionary."""
        messages = []
        for key, value in prompt_config.items():
            if key == 'system':
                messages.append(("system", value))
            elif key == 'human':
                messages.append(("human", value))
            elif key == 'ai':
                messages.append(("ai", value))
            elif key == 'history': # Handle the messages placeholder
                messages.append(MessagesPlaceholder(variable_name=value['variable_name']))
            else:
                logger.warning(f"Unknown prompt component type '{key}' in config")
        return ChatPromptTemplate.from_messages(messages)
    
    async def generate_technical_documentation(self, 
                                              project_name: str, 
                                              requirements: Dict[str, List[Dict[str, str]]], 
                                              uml_diagrams: Dict[str, str] = None, 
                                              messages: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate technical documentation based on requirements and UML diagrams.
        
        Args:
            project_name: Name of the project
            requirements: Dictionary containing functional and non-functional requirements
            uml_diagrams: Dictionary containing UML diagrams (optional)
            messages: List of conversation messages (optional)
            
        Returns:
            Dictionary containing the generated documentation and metadata
        """
        try:
            logger.info(f"Generating technical documentation for project: {project_name}")
            
            # Clear previous messages
            self.message_history.clear()
            
            # Create a timestamp for the document
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            
            # Create a safe filename
            safe_project_name = project_name.replace(" ", "_").lower()
            doc_filename = f"technical_doc_{safe_project_name}_{timestamp}.md"
            doc_path = os.path.join(self.docs_dir, doc_filename)
            
            # Prepare requirements for the prompt
            functional_reqs = json.dumps(requirements.get("functional_requirements", []), indent=2)
            non_functional_reqs = json.dumps(requirements.get("non_functional_requirements", []), indent=2)
            
            # Prepare diagrams for the prompt
            diagrams_text = ""
            if uml_diagrams:
                for diagram_type, diagram_content in uml_diagrams.items():
                    diagrams_text += f"\n### {diagram_type.replace('_', ' ').title()}\n```\n{diagram_content}\n```\n"
            
            # Prepare conversation summary if messages are provided
            conversation_summary = ""
            if messages:
                # Create a prompt for summarizing the conversation from YAML config
                summary_prompt_config = self.prompts.get('conversation_summary_prompt')
                if not summary_prompt_config:
                     logger.error("'conversation_summary_prompt' not found in loaded YAML prompts.")
                     raise ValueError("Missing conversation summary prompt configuration")
                summary_prompt = self._create_prompt_from_config(summary_prompt_config)
                
                # Format the conversation for the prompt
                conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
                
                # Get the summary
                summary_chain = summary_prompt | self.llm
                conversation_summary = await summary_chain.ainvoke({"conversation": conversation_text})
                conversation_summary = conversation_summary.content
            
            # Create the prompt for generating technical documentation from YAML config
            doc_prompt_config = self.prompts.get('tech_doc_generation_prompt')
            if not doc_prompt_config:
                 logger.error("'tech_doc_generation_prompt' not found in loaded YAML prompts.")
                 raise ValueError("Missing tech doc generation prompt configuration")
            doc_prompt = self._create_prompt_from_config(doc_prompt_config)
            
            # Generate the documentation content
            doc_chain = doc_prompt | self.llm
            doc_response = await doc_chain.ainvoke({
                "project_name": project_name,
                "functional_requirements": functional_reqs,
                "non_functional_requirements": non_functional_reqs,
                "diagrams": diagrams_text,
                "conversation_summary": conversation_summary
            })
            
            doc_content = doc_response.content
            
            # Fill in the template
            filled_template = self.template_content.format(
                project_id=safe_project_name,
                title=f"Technical Documentation for {project_name}",
                description=f"Detailed technical documentation for the {project_name} project",
                date=datetime.now().strftime("%Y-%m-%d"),
                project_name=project_name,
                version="1.0",
                agent_name=self.agent_name,
                organization="AI4MDE",
                date_updated=datetime.now().strftime("%Y-%m-%d"),
                introduction=doc_content,  # We'll use the generated content for all sections
                system_architecture="",
                component_design="",
                api_documentation="",
                database_schema="",
                deployment_instructions="",
                testing_strategy="",
                appendices=""
            )
            
            # Write the documentation to a file
            with open(doc_path, 'w') as f:
                f.write(filled_template)
            
            logger.info(f"Technical documentation generated successfully: {doc_path}")
            
            return {
                "message": f"Technical documentation generated successfully by {self.agent_name}.",
                "file_path": doc_path,
                "content": filled_template
            }
            
        except Exception as e:
            logger.error(f"Error generating technical documentation: {str(e)}")
            raise 