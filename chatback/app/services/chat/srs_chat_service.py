import os
import logging
import frontmatter # For parsing markdown front matter
import yaml # For loading prompts
from typing import List, Dict, Optional, Literal, Tuple
import re # For parsing the suggestion block and PlantUML
import json # For parsing the JSON inside the block
from pydantic import ValidationError # For parsing the JSON inside the block

# LangChain/Redis imports
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage # For converting history format

from app.core.config import settings
from app.services.openai_service import OpenAIService
from app.schemas.srs_chat import Message as ChatMessageSchema, ModificationSuggestion, SrsChatResponse # Import SrsChatResponse
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Regex to find the proposal block
PROPOSAL_REGEX = re.compile(r"\s*\[PROPOSED_CHANGE\]<json>(.*?)</json>\[/PROPOSED_CHANGE\]\s*", re.DOTALL)

class SRSChatService:
    def __init__(self, openai_service: OpenAIService, doc_id: str):
        self.openai_service = openai_service
        self.agent_name = settings.AGENT_BROWN_NAME
        self.prompts = self._load_prompts()
        self.doc_id = doc_id
        self.message_history = self._initialize_redis_history()

    def _initialize_redis_history(self) -> RedisChatMessageHistory:
        """Initialize Redis chat message history."""
        redis_session_id = f"srs_{self.doc_id}" # Use doc_id for unique session
        redis_url = settings.REDIS_URL or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        try:
            history = RedisChatMessageHistory(
                session_id=redis_session_id,
                url=redis_url,
                key_prefix="srs_chat_history:", # Specific prefix
                ttl=settings.REDIS_DATA_TTL
            )
            # Test connection? Optional, RedisChatMessageHistory might do it lazily.
            # history.add_message(HumanMessage(content="History initialized")) # Example test
            # history.clear() 
            logger.info(f"Initialized Redis history for {redis_session_id} at {redis_url}")
            return history
        except Exception as e:
            logger.error(f"Failed to initialize Redis history for {redis_session_id}: {e}", exc_info=True)
            # Decide how to handle this - fail init or proceed without history?
            # For now, let's raise to make the issue visible
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to chat history service."
            ) from e

    def _load_prompts(self) -> Dict:
        prompts_path = os.path.join(os.path.dirname(__file__), 'prompts', 'srs_chat_prompts.yaml')
        try:
            with open(prompts_path, 'r') as f:
                loaded_prompts = yaml.safe_load(f)
            if not loaded_prompts or 'srs_chat_system_prompt' not in loaded_prompts:
                logger.error(f"'srs_chat_system_prompt' not found in {prompts_path}")
                raise ValueError("Invalid prompt file structure")
            logger.info(f"SRS Chat prompts loaded successfully from {prompts_path}")
            return loaded_prompts
        except FileNotFoundError:
            logger.error(f"SRS Chat prompt file not found at {prompts_path}")
            # Depending on strictness, either raise or allow fallback to a default inline prompt
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML prompt file {prompts_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading prompts {prompts_path}: {e}")
            raise

    async def _get_srs_document_details(self, doc_id: str, group_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Fetches the file path and content of an SRS document."""
        if not group_name:
            logger.warning(f"No group_name provided for doc_id: {doc_id}")
            return None, None
        
        docs_dir = os.path.join(settings.CHATBOT_DATA_PATH, group_name, "srsdocs")
        logger.debug(f"Searching for doc_id '{doc_id}' in directory: {docs_dir}")

        if not os.path.isdir(docs_dir):
            logger.warning(f"SRS documents directory not found for group '{group_name}': {docs_dir}")
            return None, None
        
        try:
            for filename in os.listdir(docs_dir):
                if filename.endswith('.md'):
                    file_path = os.path.join(docs_dir, filename)
                    try:
                        post = frontmatter.load(file_path)
                        document_identifier = post.metadata.get('id', filename[:-3])
                        if document_identifier == doc_id:
                            logger.info(f"Found document '{doc_id}' at path: {file_path}")
                            return file_path, post.content
                    except Exception as e:
                        logger.error(f"Error parsing frontmatter for file {file_path}: {e}", exc_info=True)
                        continue
            logger.warning(f"Document with doc_id '{doc_id}' not found in group '{group_name}\\'s srsdocs.")
            return None, None
        except FileNotFoundError: # Should be caught by os.path.isdir, but good to have
            logger.warning(f"Directory not found: {docs_dir}")
            return None, None
        except Exception as e:
            logger.error(f"Error reading documents in {docs_dir}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error accessing document storage for group {group_name}."
            ) from e

    async def _apply_modification(
        self, 
        file_path: str, 
        modification: ModificationSuggestion
    ) -> bool: # Returns True if successful, False otherwise
        """Attempts to apply the modification to the given file content."""
        logger.info(f"Attempting to apply modification to {file_path}: {modification.model_dump()}")
        
        try:
            post = frontmatter.load(file_path) # Re-read the file to ensure we have the latest version
            original_doc_content = post.content
        except Exception as e:
            logger.error(f"Failed to read file {file_path} for modification: {e}")
            return False

        modified_doc_content = original_doc_content
        applied_change = False

        if modification.type == "class_diagram_modification":
            logger.info(f"Handling class_diagram_modification for class: {modification.class_name}")
            class_name = modification.class_name
            attribute_name = modification.attribute_name
            attribute_type = modification.attribute_type # Assuming this is provided, e.g., "String"

            if not attribute_name: # Basic validation
                logger.warning("Attribute name not provided for class diagram modification.")
                return False
            
            # Attempt to find and modify the PlantUML class definition
            # This is a simplified regex approach and might need refinement for complex diagrams
            # It looks for `class ClassName {` or `class ClassName` and inserts the attribute.
            # It assumes attributes are listed one per line, indented.
            # Regex to find class block: 
            # (class\s+Order\s*\{\n            #   (.*?)            <-- existing attributes (non-greedy)
            # \})|(class\s+Order(\n|$))
            class_pattern = re.compile(
                rf"(class\s+{re.escape(class_name)}\s*{{(?:\s*\n)?)(.*?)(\s*\n?}})|(class\s+{re.escape(class_name)}(?:\s*\n|$))", 
                re.DOTALL | re.MULTILINE
            )
            
            # New attribute string - assuming simple string type for now
            new_attribute_line = f"  {attribute_name}{f': {attribute_type}' if attribute_type else ''}\n"

            def replace_class_content(match):
                nonlocal applied_change
                if match.group(1): # Matched class ClassName { ... }
                    class_header = match.group(1)
                    existing_attributes = match.group(2) # Content between {
                    class_footer = match.group(3)
                    
                    # Avoid adding if attribute already exists (simple check)
                    if attribute_name in existing_attributes:
                        logger.info(f"Attribute '{attribute_name}' already exists in class '{class_name}'. No changes made.")
                        return match.group(0) # Return original match

                    applied_change = True
                    return f"{class_header}{existing_attributes.rstrip()}\n{new_attribute_line}{class_footer}"
                
                elif match.group(4): # Matched class ClassName (without explicit braces)
                    applied_change = True
                    # This case is simpler, we append the attribute and assume it implies a start of a block
                    # or that it will be correctly interpreted by PlantUML.
                    # For robustness, ensuring it becomes `class ClassName { attribute }` might be better.
                    # For now, just add the attribute; can be refined.
                    return f"{match.group(4).rstrip()}\n{new_attribute_line}"
                return match.group(0) # Should not happen if pattern matches

            modified_doc_content, num_replacements = class_pattern.subn(replace_class_content, modified_doc_content)

            if num_replacements == 0 and not applied_change:
                 logger.warning(f"Could not find class '{class_name}' in a suitable PlantUML format in {file_path} to add attribute.")
                 return False # Class not found or pattern didn't match as expected
            elif not applied_change and num_replacements > 0:
                 logger.info(f"Class '{class_name}' found, but attribute '{attribute_name}' may already exist or other condition prevented change.")
                 return False # No actual change was made (e.g. attribute existed)

        else:
            logger.warning(f"Unsupported modification type: {modification.type}")
            return False

        if applied_change and modified_doc_content != original_doc_content:
            try:
                post.content = modified_doc_content
                with open(file_path, 'w', encoding='utf-8') as f:
                    frontmatter.dump(post, f)
                logger.info(f"Successfully applied modification and saved file {file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to write modified content to {file_path}: {e}")
                return False
        else:
            logger.info(f"No changes made to the document {file_path} or change was not applied.")
            return False

    async def process_chat(
        self, 
        group_name: str, 
        user_message_text: str 
    ) -> SrsChatResponse:
        """Processes the chat request: loads history, fetches doc, calls LLM, saves history, returns response."""
        
        file_path, doc_content = await self._get_srs_document_details(self.doc_id, group_name) # Get path and content

        if doc_content is None or file_path is None: # Check both
            logger.warning(f"SRS document '{self.doc_id}' (or its path) not found for group '{group_name}'.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SRS document with ID '{self.doc_id}' not found for your group."
            )

        if not self.openai_service.client:
            logger.error("OpenAI client not initialized in OpenAIService.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat service is currently unavailable due to AI backend configuration."
            )

        # --- Load history from Redis --- 
        try:
            redis_messages = await self.message_history.aget_messages()
            logger.debug(f"Loaded {len(redis_messages)} messages from Redis history for {self.message_history.session_id}")
        except Exception as e:
            logger.error(f"Failed to load messages from Redis for {self.message_history.session_id}: {e}", exc_info=True)
            # Fallback to empty history or raise error?
            redis_messages = [] 
            # Potentially raise HTTPException here if history is critical
        # --- End Load History --- 

        # Prepare system prompt
        system_prompt_template = self.prompts['srs_chat_system_prompt']
        formatted_system_prompt = system_prompt_template.format(
            agent_name=self.agent_name, 
            doc_content=doc_content
        )
        llm_messages: List[Dict[str, str]] = []
        llm_messages.append({"role": "system", "content": formatted_system_prompt})

        # Add loaded history (converting LangChain messages to OpenAI format)
        for msg in redis_messages:
            if isinstance(msg, HumanMessage):
                llm_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                llm_messages.append({"role": "assistant", "content": msg.content})
        
        # Add current user message
        llm_messages.append({"role": "user", "content": user_message_text})

        try:
            logger.debug(f"Sending {len(llm_messages)} messages to LLM ({self.agent_name}) for doc_id: {self.doc_id} in group {group_name}")
            raw_agent_response = await self.openai_service.get_chat_completion(messages=llm_messages)
            logger.info(f"Received LLM response for doc_id: {self.doc_id} from {self.agent_name}")

            # --- Parse for Proposed Change --- 
            # Initialize display_ai_response with the full raw response initially.
            # It will be cleaned if a proposal block is found and parsed successfully.
            display_ai_response = raw_agent_response 
            parsed_suggestions: List[ModificationSuggestion] = []
            
            suggestion_match = PROPOSAL_REGEX.search(raw_agent_response)

            if suggestion_match:
                json_string = suggestion_match.group(1).strip()
                # If a block is found, clean the response for display *before* trying to parse JSON
                # This way, if JSON parsing fails, user still sees a cleaned response.
                display_ai_response = PROPOSAL_REGEX.sub("", raw_agent_response).strip()
                try:
                    suggestion_data_raw = json.loads(json_string)
                    
                    if isinstance(suggestion_data_raw, list):
                        if not suggestion_data_raw:
                            logger.warning("LLM sent an empty list for PROPOSED_CHANGE.")
                            suggestion_data_list = []
                        else:
                            suggestion_data_list = [suggestion_data_raw[0]] 
                            if len(suggestion_data_raw) > 1:
                                logger.warning("LLM sent multiple suggestions in PROPOSED_CHANGE, but only the first will be processed.")
                    else: 
                        suggestion_data_list = [suggestion_data_raw]

                    for item_data in suggestion_data_list:
                        try:
                            if 'type' not in item_data:
                                item_data['type'] = 'class_diagram_modification'
                            
                            suggestion = ModificationSuggestion(**item_data)
                            
                            if not suggestion.modification_type:
                                logger.warning(f"Skipping suggestion due to missing modification_type: {item_data}")
                                continue

                            if suggestion.modification_type == "create_class_diagram":
                                if not suggestion.diagram_description:
                                    logger.warning(f"Skipping create_class_diagram suggestion due to missing diagram_description: {item_data}")
                                    continue
                            elif suggestion.modification_type in ["add_attribute", "remove_attribute", "add_method", "remove_method"]:
                                if not suggestion.class_name:
                                    logger.warning(f"Skipping UML modification suggestion due to missing class_name: {item_data}")
                                    continue
                                if suggestion.modification_type == "add_attribute" and (not suggestion.attribute_name or not suggestion.attribute_type):
                                    logger.warning(f"Skipping add_attribute suggestion due to missing attribute_name or attribute_type: {item_data}")
                                    continue
                                if suggestion.modification_type == "remove_attribute" and not suggestion.attribute_name:
                                    logger.warning(f"Skipping remove_attribute suggestion due to missing attribute_name: {item_data}")
                                    continue
                                if suggestion.modification_type == "add_method" and (not suggestion.method_name or suggestion.method_parameters is None or not suggestion.method_return_type):
                                    logger.warning(f"Skipping add_method suggestion due to missing method_name, parameters, or return_type: {item_data}")
                                    continue
                                if suggestion.modification_type == "remove_method" and not suggestion.method_name:
                                    logger.warning(f"Skipping remove_method suggestion due to missing method_name: {item_data}")
                                    continue
                            
                            parsed_suggestions.append(suggestion)
                        except ValidationError as e_val:
                            logger.error(f"Validation error for suggestion item {item_data}: {e_val}", exc_info=True)
                        except Exception as e_parse_item:
                            logger.error(f"Error processing suggestion item {item_data}: {e_parse_item}", exc_info=True)

                except json.JSONDecodeError as e_json:
                    logger.error(f"JSONDecodeError parsing suggestion block: {json_string}. Error: {e_json}", exc_info=True)
                    # display_ai_response is already cleaned, parsed_suggestions remains empty
                except Exception as e_outer: 
                    logger.error(f"Unexpected error parsing suggestion block: {e_outer}", exc_info=True)
                    # display_ai_response is already cleaned, parsed_suggestions remains empty
            # else: display_ai_response remains raw_agent_response, parsed_suggestions is empty

            # --- End Parsing --- 
            
            # --- Save messages to Redis --- 
            try:
                self.message_history.add_user_message(user_message_text)
                self.message_history.add_ai_message(display_ai_response) # Save the (potentially cleaned) AI response
                logger.debug(f"Saved user and AI message to Redis history for {self.message_history.session_id}")
                
                final_redis_messages = await self.message_history.aget_messages()
                full_history_response: List[ChatMessageSchema] = []
                for msg in final_redis_messages:
                    sender: Literal['user', 'agent'] = 'user' if isinstance(msg, HumanMessage) else 'agent'
                    full_history_response.append(ChatMessageSchema(sender=sender, text=msg.content))

            except Exception as e:
                logger.error(f"Error during Redis operations for {self.message_history.session_id}: {e}", exc_info=True)
                full_history_response = None 

            return SrsChatResponse(
                response=display_ai_response, 
                suggestions=parsed_suggestions if parsed_suggestions else None, # Return None if empty
                full_history=full_history_response
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during LLM call for doc '{self.doc_id}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while communicating with the AI assistant."
            ) from e 