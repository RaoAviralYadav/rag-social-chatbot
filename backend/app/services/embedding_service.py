import logging
from typing import Any, Dict, List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import settings
from app.models.schemas import TranscriptResult

logger = logging.getLogger(__name__)


class EmbeddingService:
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    def __init__(self):
        self._embeddings = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
            add_start_index=True,
        )

    @property
    def embeddings(self):
        if self._embeddings is None:
            logger.info("Loading embedding model: %s", settings.embedding_model)
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.embedding_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Embedding model ready.")
        return self._embeddings

    # ------------------------------------------------------------------ #
    # Timestamp mapping                                                    #
    # ------------------------------------------------------------------ #

    def _build_offset_map(self, entries: list) -> List[tuple]:
        offset_map = []
        cursor = 0
        for entry in entries:
            offset_map.append((cursor, entry.start))
            cursor += len(entry.text) + 1
        return offset_map

    def _find_start_time(self, char_start: int, offset_map: List[tuple]) -> float:
        if not offset_map:
            return 0.0
        best = offset_map[0][1]
        for offset, ts in offset_map:
            if offset <= char_start:
                best = ts
            else:
                break
        return best

    # ------------------------------------------------------------------ #
    # Chunking                                                             #
    # ------------------------------------------------------------------ #

    def chunk_transcript(self, result: TranscriptResult, video_id: str) -> List[Dict[str, Any]]:
        offset_map = self._build_offset_map(result.entries)
        docs = self._splitter.create_documents(
            [result.text],
            metadatas=[{"video_id": video_id}],
        )
        chunks = []
        for i, doc in enumerate(docs):
            char_start = doc.metadata.get("start_index", 0)
            chunks.append({
                "text": doc.page_content,
                "video_id": video_id,
                "chunk_index": i,
                "start_time": self._find_start_time(char_start, offset_map),
            })
        logger.info("Video %s → %d chunks", video_id, len(chunks))
        return chunks

    # ------------------------------------------------------------------ #
    # Embedding                                                            #
    # ------------------------------------------------------------------ #

    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        texts = [c["text"] for c in chunks]
        try:
            vectors = await self.embeddings.aembed_documents(texts)
        except (NotImplementedError, AttributeError):
            vectors = self.embeddings.embed_documents(texts)

        for chunk, vector in zip(chunks, vectors):
            chunk["embedding"] = vector

        logger.info("Embedded %d chunks for Video %s", len(chunks), chunks[0]["video_id"])
        return chunks

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def process(self, result: TranscriptResult, video_id: str) -> List[Dict[str, Any]]:
        chunks = self.chunk_transcript(result, video_id)
        return await self.embed_chunks(chunks)


embedding_service = EmbeddingService()