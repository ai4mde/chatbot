from pydantic import BaseModel, Field
from typing import Optional

class QdrantCollectionInfo(BaseModel):
    name: str
    vectors_count: Optional[int] = None
    points_count: Optional[int] = None # points_count is often used by qdrant-client
    status: Optional[str] = None # e.g., 'green', 'yellow', 'red'

class QdrantCollectionList(BaseModel):
    collections: list[QdrantCollectionInfo]

class QdrantCollectionCreate(BaseModel):
    name: str = Field(..., description="Name of the collection to create. Must be unique.")
    # We might add vector_size, distance_metric etc. later, keep it simple for now.
    # vector_size: int = Field(1536, description="Dimension of vectors (e.g., OpenAI's text-embedding-ada-002 is 1536)")
    # distance: str = Field("Cosine", description="Distance metric (e.g., Cosine, Dot, Euclid)")

class QdrantStatus(BaseModel):
    connected: bool
    version: Optional[str] = None
    error: Optional[str] = None 