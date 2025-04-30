from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from app.core.config import settings
from typing import List, Optional, Dict, Any
import logging
from qdrant_client.models import PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

# Initialize QdrantManager instance (consider using FastAPI dependency injection later)
# This simple global instance works for now but might have issues with async/scoping.
qdrant_manager = None


def get_qdrant_manager():
    global qdrant_manager
    if qdrant_manager is None:
        qdrant_manager = QdrantManager()
    return qdrant_manager


class QdrantManager:
    def __init__(self):
        self.collection_name = "chat_messages"
        self.client: Optional[QdrantClient] = None
        self.is_connected = False
        self.connection_error: Optional[str] = None
        self.qdrant_version: Optional[str] = None

        try:
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=10,
            )
            # Revert to simpler connection check
            self.client.get_collections()  # Check basic collection listing
            self.is_connected = True
            logger.info("Successfully connected to Qdrant")
        except Exception as e:
            self.is_connected = False
            self.connection_error = str(e)
            logger.error(f"Failed to connect to Qdrant: {self.connection_error}")

        if self.is_connected:
            self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
            self._ensure_collection(
                self.collection_name
            )  # Ensure the default chat collection exists

    def get_status(self) -> Dict[str, Any]:
        """Return the connection status and version."""
        return {
            "connected": self.is_connected,
            "version": self.qdrant_version,  # Currently not fetching version, needs client update/different call
            "error": self.connection_error,
        }

    def _ensure_collection(
        self,
        collection_name: str,
        vector_size: int = 1536,
        distance: models.Distance = models.Distance.COSINE,
    ):
        """Ensure a specific collection exists with the correct settings"""
        if not self.client or not self.is_connected:
            logger.warning(
                f"Cannot ensure collection '{collection_name}', Qdrant client not connected."
            )
            return

        try:
            collections_response = self.client.get_collections()
            collections = collections_response.collections
            exists = any(c.name == collection_name for c in collections)

            if not exists:
                logger.info(f"Collection '{collection_name}' not found. Creating...")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size, distance=distance
                    ),
                )
                logger.info(f"Created collection: {collection_name}")
            else:
                logger.debug(f"Collection '{collection_name}' already exists.")

        except Exception as e:
            logger.error(f"Error ensuring collection '{collection_name}': {str(e)}")
            # Don't raise here, maybe log or handle appropriately
            # raise

    def get_all_collections_info(self) -> List[Dict[str, Any]]:
        """Get information about all collections."""
        if not self.client or not self.is_connected:
            logger.warning("Cannot get collections info, Qdrant client not connected.")
            return []

        collections_info = []
        try:
            collections_response = self.client.get_collections()
            for collection_desc in collections_response.collections:
                try:
                    collection_detail = self.client.get_collection(
                        collection_name=collection_desc.name
                    )
                    collections_info.append(
                        {
                            "name": collection_desc.name,
                            "status": collection_detail.status.value,  # Get enum value
                            "points_count": collection_detail.points_count,
                            "vectors_count": collection_detail.vectors_count,
                            # Add more details if needed from collection_detail
                        }
                    )
                except Exception as detail_e:
                    logger.error(
                        f"Error getting details for collection '{collection_desc.name}': {str(detail_e)}"
                    )
                    # Add basic info even if details fail
                    collections_info.append(
                        {
                            "name": collection_desc.name,
                            "status": "error",
                            "points_count": None,
                        }
                    )

            return collections_info
        except Exception as e:
            logger.error(f"Error listing Qdrant collections: {str(e)}")
            return []  # Return empty list on error

    def create_collection(
        self,
        name: str,
        vector_size: int = 1536,
        distance: models.Distance = models.Distance.COSINE,
    ) -> bool:
        """Create a new collection."""
        if not self.client or not self.is_connected:
            logger.error(
                f"Cannot create collection '{name}', Qdrant client not connected."
            )
            return False
        try:
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=vector_size, distance=distance),
            )
            logger.info(f"Successfully created Qdrant collection: {name}")
            return True
        except UnexpectedResponse as e:
            # Qdrant might return 400 if collection already exists
            if e.status_code == 400 and "already exists" in str(e).lower():
                logger.warning(f"Collection '{name}' already exists.")
                # Consider if this should return True or False, or raise a specific exception
                return False  # Indicate it wasn't newly created because it exists
            else:
                logger.error(
                    f"Failed to create Qdrant collection '{name}': {str(e)} - Status: {e.status_code}, Content: {e.content}"
                )
                return False
        except Exception as e:
            logger.error(
                f"Unexpected error creating Qdrant collection '{name}': {str(e)}"
            )
            return False

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if not self.client or not self.is_connected:
            logger.error(
                f"Cannot delete collection '{name}', Qdrant client not connected."
            )
            return False

        # Prevent deleting the main chat collection through this admin interface?
        if name == self.collection_name:
            logger.warning(
                f"Attempted to delete the primary chat collection '{name}' via admin interface. Denied."
            )
            # raise HTTPException(status_code=403, detail="Cannot delete the primary chat collection.")
            return False

        try:
            self.client.delete_collection(collection_name=name)
            logger.info(f"Successfully deleted Qdrant collection: {name}")
            return True
        except UnexpectedResponse as e:
            # Qdrant might return 404 if collection doesn't exist
            if e.status_code == 404:
                logger.warning(f"Collection '{name}' not found for deletion.")
                return False  # Or True depending on desired idempotency behavior
            else:
                logger.error(
                    f"Failed to delete Qdrant collection '{name}': {str(e)} - Status: {e.status_code}, Content: {e.content}"
                )
                return False
        except Exception as e:
            logger.error(
                f"Unexpected error deleting Qdrant collection '{name}': {str(e)}"
            )
            return False

    # Method to get collection info (including count) - KEEPING this specific one for now
    def get_collection_info(
        self, collection_name: Optional[str] = None
    ) -> Optional[models.CollectionInfo]:
        """Get information about a specific collection (defaults to configured chat collection)."""
        target_collection = collection_name or self.collection_name
        if not self.client or not self.is_connected:
            logger.warning(
                f"Cannot get info for collection '{target_collection}', Qdrant client not connected."
            )
            return None

        try:
            collection_info = self.client.get_collection(
                collection_name=target_collection
            )
            return collection_info
        except Exception as e:
            # Handle case where collection might not exist yet or other API errors
            logger.error(
                f"Error getting Qdrant collection info for '{target_collection}': {str(e)}"
            )
            return None

    async def add_texts(
        self, texts: List[str], metadatas: Optional[List[dict]] = None
    ) -> List[str]:
        """Add texts to the vector store"""
        try:
            vector_store = Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )

            ids = await vector_store.aadd_texts(
                texts=texts, metadatas=metadatas or [{}] * len(texts)
            )
            return ids
        except Exception as e:
            logger.error(f"Error adding texts: {str(e)}")
            raise

    async def similarity_search(
        self, query: str, k: int = 4, filter: Optional[Dict[str, Any]] = None
    ):
        """Search for similar texts"""
        try:
            vector_store = Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )

            results = await vector_store.asimilarity_search_with_score(
                query=query, k=k, filter=filter
            )
            return results
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise

    async def delete_by_metadata(self, filter_metadata: Dict[str, Any]):
        """Delete vectors by metadata"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key=key, match=models.MatchValue(value=value)
                            )
                            for key, value in filter_metadata.items()
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            raise

    async def search_similar(self, text: str) -> str:
        try:
            # Get embeddings for the search text
            embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
            vector = await embeddings.aembed_query(text)

            # Search for similar vectors
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=5,  # Return top 5 similar results
            )

            # Format results into a string
            context = " ".join([hit.payload.get("text", "") for hit in search_result])
            return context

        except Exception as e:
            logger.error(f"Error searching similar texts: {str(e)}", exc_info=True)
            return ""  # Return empty context on error


# Initialize the manager when the module loads (can be refined with DI)
try:
    qdrant_manager = QdrantManager()
except Exception as e:
    # Error is logged within __init__ now
    qdrant_manager = None  # Ensure it's None if init fails
