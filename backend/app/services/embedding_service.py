# import logging
# from typing import Any, Dict, List

# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_openai import OpenAIEmbeddings

# from app.config import settings
# from app.models.schemas import TranscriptResult

# logger = logging.getLogger(__name__)


# class EmbeddingService:
#     """
#     Chunk → embed pipeline.
#     Output: list of dicts ready for vector_store.upsert_chunks().

#     Each chunk:
#       { text, video_id, chunk_index, start_time, embedding }
#     """

#     CHUNK_SIZE = 500        # characters — fast to compute, no tokeniser needed
#     CHUNK_OVERLAP = 50
#     EMBED_BATCH_SIZE = 100  # well under OpenAI's 2048 limit; safe for rate limits

#     def __init__(self):
#         self._embeddings = OpenAIEmbeddings(
#             model=settings.embedding_model,
#             api_key=settings.openai_api_key,
#         )
#         self._splitter = RecursiveCharacterTextSplitter(
#             chunk_size=self.CHUNK_SIZE,
#             chunk_overlap=self.CHUNK_OVERLAP,
#             separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
#             add_start_index=True,   # injects start_index into each doc's metadata
#         )

#     # ------------------------------------------------------------------ #
#     # Timestamp mapping                                                    #
#     # ------------------------------------------------------------------ #

#     def _build_offset_map(self, entries: list) -> List[tuple]:
#         """
#         Walk transcript entries → list of (char_offset, start_time).
#         Used to assign an approximate video timestamp to every chunk.
#         """
#         offset_map = []
#         cursor = 0
#         for entry in entries:
#             offset_map.append((cursor, entry.start))
#             cursor += len(entry.text) + 1  # +1 for the space used in text join
#         return offset_map

#     def _find_start_time(self, char_start: int, offset_map: List[tuple]) -> float:
#         """Return the timestamp of the last entry that begins at or before char_start."""
#         if not offset_map:
#             return 0.0
#         best = offset_map[0][1]
#         for offset, ts in offset_map:
#             if offset <= char_start:
#                 best = ts
#             else:
#                 break
#         return best

#     # ------------------------------------------------------------------ #
#     # Chunking                                                             #
#     # ------------------------------------------------------------------ #

#     def chunk_transcript(
#         self, result: TranscriptResult, video_id: str
#     ) -> List[Dict[str, Any]]:
#         """
#         Split full transcript text into overlapping chunks.
#         add_start_index=True gives us precise char offsets → accurate timestamps.
#         """
#         offset_map = self._build_offset_map(result.entries)

#         docs = self._splitter.create_documents(
#             [result.text],
#             metadatas=[{"video_id": video_id}],
#         )

#         chunks = []
#         for i, doc in enumerate(docs):
#             char_start = doc.metadata.get("start_index", 0)
#             chunks.append({
#                 "text": doc.page_content,
#                 "video_id": video_id,
#                 "chunk_index": i,
#                 "start_time": self._find_start_time(char_start, offset_map),
#             })

#         logger.info("Video %s → %d chunks (size=%d, overlap=%d)",
#                     video_id, len(chunks), self.CHUNK_SIZE, self.CHUNK_OVERLAP)
#         return chunks

#     # ------------------------------------------------------------------ #
#     # Embedding                                                            #
#     # ------------------------------------------------------------------ #

#     async def embed_chunks(
#         self, chunks: List[Dict[str, Any]]
#     ) -> List[Dict[str, Any]]:
#         """
#         Batch-embed all chunks, add 'embedding' key to each.
#         text-embedding-3-small: 1536 dims, $0.02 / 1M tokens.
#         Avg transcript ≈ 2k tokens → ~$0.00004 per video. Negligible at scale.
#         """
#         texts = [c["text"] for c in chunks]

#         for i in range(0, len(texts), self.EMBED_BATCH_SIZE):
#             batch = texts[i : i + self.EMBED_BATCH_SIZE]
#             vectors = await self._embeddings.aembed_documents(batch)
#             for chunk, vector in zip(chunks[i:], vectors):
#                 chunk["embedding"] = vector
#             logger.debug("Embedded %d/%d chunks", min(i + self.EMBED_BATCH_SIZE, len(texts)), len(texts))

#         return chunks

#     # ------------------------------------------------------------------ #
#     # Public API                                                           #
#     # ------------------------------------------------------------------ #

#     async def process(
#         self, result: TranscriptResult, video_id: str
#     ) -> List[Dict[str, Any]]:
#         """
#         Full pipeline: chunk → embed.
#         Called by ingest router after transcript + metadata are fetched.
#         """
#         chunks = self.chunk_transcript(result, video_id)
#         return await self.embed_chunks(chunks)


# embedding_service = EmbeddingService()


import logging
from typing import Any, Dict, List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import settings
from app.models.schemas import TranscriptResult

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Chunk → embed pipeline.
    Uses local HuggingFace sentence-transformers (free, runs on CPU, no API key needed).

    Model: all-MiniLM-L6-v2
      - 384-dim embeddings (vs OpenAI's 1536 — ChromaDB handles any dim)
      - ~80MB download on first run, cached in ~/.cache/huggingface
      - ~50ms per batch on CPU — fast enough for transcripts

    Each output chunk:
      { text, video_id, chunk_index, start_time, embedding }
    """

    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    EMBED_BATCH_SIZE = 64   # sentence-transformers handles batching internally too

    def __init__(self):
        logger.info("Loading HuggingFace embedding model: %s", settings.embedding_model)
        self._embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},  # cosine similarity ready
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
            add_start_index=True,
        )
        logger.info("Embedding model ready.")

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

    def chunk_transcript(
        self, result: TranscriptResult, video_id: str
    ) -> List[Dict[str, Any]]:
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
    # Embedding (sync model wrapped — sentence-transformers is sync)      #
    # ------------------------------------------------------------------ #

    async def embed_chunks(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        HuggingFaceEmbeddings.aembed_documents is available in langchain-huggingface.
        Falls back gracefully to sync embed_documents if async not supported.
        """
        texts = [c["text"] for c in chunks]
        try:
            vectors = await self._embeddings.aembed_documents(texts)
        except (NotImplementedError, AttributeError):
            # sentence-transformers sync path
            vectors = self._embeddings.embed_documents(texts)

        for chunk, vector in zip(chunks, vectors):
            chunk["embedding"] = vector

        logger.info("Embedded %d chunks for Video %s", len(chunks), chunks[0]["video_id"])
        return chunks

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def process(
        self, result: TranscriptResult, video_id: str
    ) -> List[Dict[str, Any]]:
        chunks = self.chunk_transcript(result, video_id)
        return await self.embed_chunks(chunks)


embedding_service = EmbeddingService()