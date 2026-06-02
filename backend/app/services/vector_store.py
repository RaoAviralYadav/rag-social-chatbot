from typing import List, Optional
from app.config import settings


class VectorStore:
    """
    ChromaDB wrapper for storing and querying transcript chunks.

    Each chunk is stored with metadata: { video_id, chunk_index }
    This allows filtered retrieval (e.g., only Video A chunks).
    """

    COLLECTION_NAME = "video_transcripts"

    def __init__(self):
        self._client = None
        self._collection = None
        # TODO: import chromadb; self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    def initialize(self):
        """Connect to ChromaDB and create/load the collection."""
        # TODO: self._collection = self._client.get_or_create_collection(self.COLLECTION_NAME)
        raise NotImplementedError("Vector store initialization not implemented")

    async def upsert_chunks(self, chunks: List[dict]):
        """
        Insert embedded chunks into ChromaDB.
        Each doc tagged with video_id for filtered retrieval.
        TODO: self._collection.add(ids, embeddings, documents, metadatas)
        """
        raise NotImplementedError("Chunk upsert not implemented")

    async def similarity_search(
        self,
        query_embedding: List[float],
        video_ids: Optional[List[str]] = None,
        k: int = 5,
    ) -> List[dict]:
        """
        Retrieve top-k chunks. Optionally filter by video_id.
        TODO: self._collection.query(query_embeddings, where={"video_id": {"$in": video_ids}})
        """
        raise NotImplementedError("Similarity search not implemented")

    async def clear(self):
        """Drop and recreate collection (for fresh ingestion)."""
        raise NotImplementedError


vector_store = VectorStore()