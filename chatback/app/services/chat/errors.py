"""
Shared exception classes for the chat service.
"""

class ChatError(Exception):
    """Base class for chat-related errors"""
    pass

class ChatManagerError(ChatError):
    """Errors specific to the chat manager or its coordinated agents."""
    pass

class DocumentGenerationError(ChatError):
    """Errors specific to document generation processes (SRS, etc.)."""
    pass 