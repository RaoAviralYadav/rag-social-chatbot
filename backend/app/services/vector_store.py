import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB wrapper.

    Collection schema per document:
      id       → "{video_id}_{chunk_index}"   (deterministic — safe to re-ingest)
      document → chunk text
      metadata → { video_id, chunk_index, start_time }
      embedding→ pre-computed by EmbeddingService
    """

    COLLECTION_NAME = "video_transcripts"

    def __init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    # ------------------------------------------------------------------ #
    # Init (lazy — called on first use or explicitly at startup)          #
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        if self._client is not None:
            return
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},   # cosine similarity for OpenAI embeddings
            embedding_function=None,
        )
        logger.info(
            "ChromaDB ready at %s | collection=%s | docs=%d",
            settings.chroma_persist_dir,
            self.COLLECTION_NAME,
            self._collection.count(),
        )

    @property
    def collection(self):
        if self._collection is None:
            self.initialize()
        return self._collection

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    async def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Insert or overwrite chunks for a video.
        Deterministic IDs mean re-ingesting the same video is idempotent.
        """
        if not chunks:
            return

        ids = [f"{c['video_id']}_{c['chunk_index']}" for c in chunks]
        documents = [c["text"] for c in chunks]
        embeddings = [c["embedding"] for c in chunks]
        metadatas = [
            {
                "video_id": c["video_id"],
                "chunk_index": c["chunk_index"],
                "start_time": c["start_time"],
            }
            for c in chunks
        ]

        # ChromaDB upsert = add or overwrite if id exists
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Upserted %d chunks for Video %s", len(chunks), chunks[0]["video_id"])

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    async def similarity_search(
        self,
        query_embedding: List[float],
        video_ids: Optional[List[str]] = None,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Top-k cosine similarity search.
        Optionally filter to specific video_ids (e.g. ["A"] or ["A","B"]).

        Returns list of:
          { text, video_id, chunk_index, start_time, score }
        """
        where = None
        if video_ids and len(video_ids) == 1:
            where = {"video_id": video_ids[0]}
        elif video_ids and len(video_ids) > 1:
            where = {"video_id": {"$in": video_ids}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, self.collection.count() or 1),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text": doc,
                "video_id": meta["video_id"],
                "chunk_index": meta["chunk_index"],
                "start_time": meta.get("start_time", 0.0),
                "score": round(1 - dist, 4),   # cosine distance → similarity
            })

        return chunks

    # ------------------------------------------------------------------ #
    # Maintenance                                                          #
    # ------------------------------------------------------------------ #

    async def delete_video(self, video_id: str) -> None:
        """Remove all chunks for a single video. Useful for re-ingestion."""
        self.collection.delete(where={"video_id": video_id})
        logger.info("Deleted all chunks for Video %s", video_id)

    async def clear(self) -> None:
        """Drop and recreate the collection (full reset)."""
        self._client.delete_collection(self.COLLECTION_NAME)
        self._collection = None
        self.initialize()
        logger.warning("Collection reset — all vectors deleted")

    def count(self) -> int:
        return self.collection.count()


vector_store = VectorStore()