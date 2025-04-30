"""
Documents module for generating and managing documentation from user interviews.
"""

from .document_coordinator import DocumentCoordinator
from .document_reviewer_agent import DocumentReviewerAgent
from .document_writer_agent import DocumentWriterAgent
from .srs_document_agent import SRSDocumentAgent
from .modification_agent import ModificationAgent
from .review_agent import ReviewAgent
from .document_agent import (
    SRSDocumentAgent as DocumentAgent,
)  # Alias for backward compatibility

__all__ = [
    "DocumentCoordinator",
    "DocumentReviewerAgent",
    "DocumentWriterAgent",
    "SRSDocumentAgent",
    "ModificationAgent",
    "ReviewAgent",
    "DocumentAgent",
]
