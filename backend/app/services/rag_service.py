import json
import logging
from typing import AsyncGenerator, Dict, List

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings
from app.models.schemas import ChatMessage, SourceChunk, VideoMetadata
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGService:
    """
    LangChain RAG pipeline.

    query flow:
      user message
        → embed query
        → similarity_search (ChromaDB)
        → build system prompt (metadata block + context chunks)
        → stream GPT-4o-mini
        → persist to session memory
        → emit [SOURCES] + [DONE] SSE events
    """

    HISTORY_WINDOW = 6      # last 3 turns (6 messages) — keeps context window lean
    TOP_K = 6               # chunks retrieved per query

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            streaming=True,
            temperature=0.3,
        )
        self._embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        # session_id → [ChatMessage]
        self._sessions: Dict[str, List[ChatMessage]] = {}
        # "A" / "B" → VideoMetadata — set after ingestion
        self._video_metadata: Dict[str, VideoMetadata] = {}

    # ------------------------------------------------------------------ #
    # State setters (called by ingest router)                             #
    # ------------------------------------------------------------------ #

    def set_video_metadata(
        self, video_a: VideoMetadata, video_b: VideoMetadata
    ) -> None:
        self._video_metadata["A"] = video_a
        self._video_metadata["B"] = video_b

    def get_session(self, session_id: str) -> List[ChatMessage]:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    # ------------------------------------------------------------------ #
    # Prompt construction                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _fmt_ts(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

    def _metadata_block(self) -> str:
        if not self._video_metadata:
            return "No metadata loaded."
        lines = []
        for vid_id, m in self._video_metadata.items():
            lines.append(
                f"Video {vid_id} | creator: {m.creator} | "
                f"followers: {m.follower_count or 'N/A'} | "
                f"views: {m.views or 'N/A'} | "
                f"likes: {m.likes or 'N/A'} | "
                f"comments: {m.comments or 'N/A'} | "
                f"engagement: {f'{m.engagement_rate:.2f}%' if m.engagement_rate else 'N/A'} | "
                f"duration: {m.duration}s | "
                f"uploaded: {m.upload_date or 'N/A'} | "
                f"hashtags: {', '.join(m.hashtags[:10]) or 'none'}"
            )
        return "\n".join(lines)

    def _context_block(self, chunks: List[Dict]) -> str:
        return "\n\n".join(
            f"[Video {c['video_id']} @ {self._fmt_ts(c.get('start_time', 0))}] {c['text']}"
            for c in chunks
        )

    def _build_system_prompt(self, chunks: List[Dict]) -> str:
        return f"""You are an expert social media analyst helping a creator understand video performance.

METADATA (stats, engagement, follower counts — always accurate):
{self._metadata_block()}

TRANSCRIPT CONTEXT (retrieved chunks — content, hooks, pacing, tone):
{self._context_block(chunks)}

RULES:
- Use ONLY the information above. Do not hallucinate.
- Cite transcript claims as [Video A @ M:SS] or [Video B @ M:SS].
- Cite stats as [Video A metadata] or [Video B metadata].
- If something is missing, say so clearly.
- Be concise and actionable — the user is a content creator."""

    def _to_lc_history(self, history: List[ChatMessage]) -> list:
        messages = []
        for m in history[-self.HISTORY_WINDOW :]:
            if m.role == "user":
                messages.append(HumanMessage(content=m.content))
            else:
                messages.append(AIMessage(content=m.content))
        return messages

    def _to_source_chunks(self, chunks: List[Dict]) -> List[SourceChunk]:
        return [
            SourceChunk(
                video_id=c["video_id"],
                chunk_index=c["chunk_index"],
                text=c["text"][:200],
                score=c.get("score"),
            )
            for c in chunks
        ]

    # ------------------------------------------------------------------ #
    # Streaming query (primary)                                           #
    # ------------------------------------------------------------------ #

    async def stream_query(
        self,
        message: str,
        session_id: str,
        history: List[ChatMessage],
    ) -> AsyncGenerator[str, None]:
        """
        SSE events emitted:
          data: <token>            — one per LLM token
          data: [SOURCES]<json>    — source chunk array after streaming ends
          data: [DONE]             — stream closed
        """
        # 1. Embed query
        query_vector = await self._embeddings.aembed_query(message)

        # 2. Retrieve top-k chunks across both videos
        chunks = await vector_store.similarity_search(
            query_embedding=query_vector,
            video_ids=["A", "B"],
            k=self.TOP_K,
        )

        # 3. Assemble LangChain message list
        lc_messages = [
            SystemMessage(content=self._build_system_prompt(chunks)),
            *self._to_lc_history(history),
            HumanMessage(content=message),
        ]

        # 4. Stream tokens
        full_response: List[str] = []
        async for chunk_obj in self._llm.astream(lc_messages):
            token = chunk_obj.content
            if token:
                full_response.append(token)
                yield f"data: {token}\n\n"

        # 5. Persist turn to session memory
        session = self.get_session(session_id)
        session.append(ChatMessage(role="user", content=message))
        session.append(ChatMessage(role="assistant", content="".join(full_response)))

        # 6. Emit sources then close
        sources_json = json.dumps(
            [s.model_dump() for s in self._to_source_chunks(chunks)]
        )
        yield f"data: [SOURCES]{sources_json}\n\n"
        yield "data: [DONE]\n\n"

    # ------------------------------------------------------------------ #
    # Non-streaming query (used by /api/chat fallback)                   #
    # ------------------------------------------------------------------ #

    async def query(
        self,
        message: str,
        session_id: str,
        history: List[ChatMessage],
    ) -> Dict:
        query_vector = await self._embeddings.aembed_query(message)
        chunks = await vector_store.similarity_search(
            query_embedding=query_vector, video_ids=["A", "B"], k=self.TOP_K
        )
        lc_messages = [
            SystemMessage(content=self._build_system_prompt(chunks)),
            *self._to_lc_history(history),
            HumanMessage(content=message),
        ]
        response = await self._llm.ainvoke(lc_messages)

        session = self.get_session(session_id)
        session.append(ChatMessage(role="user", content=message))
        session.append(ChatMessage(role="assistant", content=response.content))

        return {
            "answer": response.content,
            "sources": self._to_source_chunks(chunks),
            "session_id": session_id,
        }


rag_service = RAGService()