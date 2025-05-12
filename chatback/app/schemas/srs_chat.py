from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

class Message(BaseModel):
    sender: str # 'user' or 'agent'
    text: str

class ModificationSuggestion(BaseModel):
    type: Literal["class_diagram_modification"] = "class_diagram_modification"
    modification_type: Literal[
        "add_attribute", 
        "remove_attribute", 
        "add_method", 
        "remove_method",
        "create_class_diagram"
    ]
    class_name: Optional[str] = Field(None, description="The name of the class to modify or a name for a new diagram.")
    attribute_name: Optional[str] = Field(None, description="Name of the attribute")
    attribute_type: Optional[str] = Field(None, description="Type of the attribute")
    method_name: Optional[str] = Field(None, description="Name of the method")
    method_parameters: Optional[List[str]] = Field(None, description="List of method parameters, e.g., ['param1: Type1', 'param2: Type2']")
    method_return_type: Optional[str] = Field(None, description="Return type of the method")
    diagram_description: Optional[str] = Field(None, description="Description for a new class diagram, e.g., when modification_type is create_class_diagram")
    
    # Fields for general text changes, now mostly unused but kept for potential future flexibility or if an error occurs
    target_description: Optional[str] = Field(None, description="Description or snippet of text/section to change")
    new_content: Optional[str] = Field(None, description="New text content (null/empty for delete)")

class SrsChatRequest(BaseModel):
    doc_id: str # The ID of the SRS document being discussed
    message: str # The new message from the user
    history: List[Message] = [] # Previous messages in the conversation
    # Optional: Pass entire document content if needed, but ID is usually better
    # doc_content: str | None = None 

class SrsChatResponse(BaseModel):
    response: str # The agent's latest textual response
    suggestions: Optional[List[ModificationSuggestion]] = Field(None, description="List of proposed modifications")
    full_history: Optional[List[Message]] = Field(None, description="The complete updated chat history")
    # Optional: Include suggested changes or other metadata
    # suggestions: List[Dict[str, Any]] = [] 

# Schema for returning only the history
class SrsChatHistoryResponse(BaseModel):
    full_history: List[Message] = Field(default_factory=list, description="The complete chat history") 