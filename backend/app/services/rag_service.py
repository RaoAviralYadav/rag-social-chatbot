import json
import logging
from typing import AsyncGenerator, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings, ChatHuggingFace, HuggingFaceEndpoint

from app.config import settings
from app.models.schemas import ChatMessage, SourceChunk, VideoMetadata
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


def _build_llm_chain():
    candidates = []

    if settings.groq_api_key:
        try:
            groq_llm = ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                temperature=0.3,
                streaming=True,
            )
            candidates.append(groq_llm)
            logger.info("LLM chain: Groq (%s) added", settings.groq_model)
        except Exception as e:
            logger.warning("Groq init failed: %s", e)

    if settings.gemini_api_key:
        try:
            gemini_llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.3,
                streaming=True,
                convert_system_message_to_human=True,
            )
            candidates.append(gemini_llm)
            logger.info("LLM chain: Gemini (%s) added", settings.gemini_model)
        except Exception as e:
            logger.warning("Gemini init failed: %s", e)

    if settings.huggingface_api_key:
        try:
            hf_endpoint = HuggingFaceEndpoint(
                repo_id=settings.huggingface_model,
                huggingfacehub_api_token=settings.huggingface_api_key,
                temperature=0.3,
                max_new_tokens=1024,
            )
            hf_llm = ChatHuggingFace(llm=hf_endpoint)
            candidates.append(hf_llm)
            logger.info("LLM chain: HuggingFace (%s) added", settings.huggingface_model)
        except Exception as e:
            logger.warning("HuggingFace init failed: %s", e)

    if not candidates:
        raise RuntimeError(
            "No LLM providers configured. "
            "Add at least one of GROQ_API_KEY, GEMINI_API_KEY, or HUGGINGFACE_API_KEY to your .env"
        )

    primary = candidates[0]
    fallbacks = candidates[1:]
    return primary.with_fallbacks(fallbacks) if fallbacks else primary


class RAGService:
    HISTORY_WINDOW = 6
    TOP_K = 6

    def __init__(self):
        self._llm = _build_llm_chain()
        self._embeddings = None
        self._sessions: Dict[str, List[ChatMessage]] = {}
        self._video_metadata: Dict[str, VideoMetadata] = {}

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
    # State setters                                                        #
    # ------------------------------------------------------------------ #

    def set_video_metadata(self, video_a: VideoMetadata, video_b: VideoMetadata) -> None:
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
        for m in history[-self.HISTORY_WINDOW:]:
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
    # Streaming query                                                      #
    # ------------------------------------------------------------------ #

    async def stream_query(
        self,
        message: str,
        session_id: str,
        history: List[ChatMessage],
    ) -> AsyncGenerator[str, None]:
        # 1. Embed query — uses lazy property
        query_vector = self.embeddings.embed_query(message)

        # 2. Retrieve top-k chunks
        chunks = await vector_store.similarity_search(
            query_embedding=query_vector,
            video_ids=["A", "B"],
            k=self.TOP_K,
        )

        # 3. Build messages
        lc_messages = [
            SystemMessage(content=self._build_system_prompt(chunks)),
            *self._to_lc_history(history),
            HumanMessage(content=message),
        ]

        # 4. Stream with auto-fallback
        full_response: List[str] = []
        try:
            async for chunk_obj in self._llm.astream(lc_messages):
                token = chunk_obj.content
                if token:
                    full_response.append(token)
                    yield f"data: {token}\n\n"
        except Exception as e:
            logger.error("All LLM providers failed during streaming: %s", e)
            yield "data: [ERROR] All AI providers are currently unavailable. Please try again later.\n\n"
            yield "data: [DONE]\n\n"
            return

        # 5. Persist turn
        session = self.get_session(session_id)
        session.append(ChatMessage(role="user", content=message))
        session.append(ChatMessage(role="assistant", content="".join(full_response)))

        # 6. Sources + close
        sources_json = json.dumps(
            [s.model_dump() for s in self._to_source_chunks(chunks)]
        )
        yield f"data: [SOURCES]{sources_json}\n\n"
        yield "data: [DONE]\n\n"

    # ------------------------------------------------------------------ #
    # Non-streaming query                                                  #
    # ------------------------------------------------------------------ #

    async def query(
        self,
        message: str,
        session_id: str,
        history: List[ChatMessage],
    ) -> Dict:
        # Uses lazy property
        query_vector = self.embeddings.embed_query(message)
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