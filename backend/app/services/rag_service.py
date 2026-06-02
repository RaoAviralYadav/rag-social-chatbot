from typing import AsyncGenerator, List, Dict
from app.models.schemas import ChatMessage, SourceChunk
from app.config import settings


class RAGService:
    """
    LangChain RAG pipeline.

    Flow: user query → embed query → similarity_search → build prompt
          → LLM (streaming) → parse sources → update session memory
    """

    def __init__(self):
        self._sessions: Dict[str, List[ChatMessage]] = {}
        # TODO: self._llm = ChatOpenAI(model=settings.llm_model, streaming=True)
        # TODO: self._embeddings = OpenAIEmbeddings(model=settings.embedding_model)

    def get_or_create_session(self, session_id: str) -> List[ChatMessage]:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    def build_system_prompt(self, context_chunks: List[dict]) -> str:
        """
        Construct the RAG system prompt injecting retrieved context.
        Each chunk is prefixed with [Video A] or [Video B] for citation.
        TODO: implement
        """
        raise NotImplementedError

    async def query(self, message: str, session_id: str) -> dict:
        """
        Single-turn RAG query.
        Returns: { "answer": str, "sources": List[SourceChunk] }
        TODO: embed message → search → build_system_prompt → LLM → parse
        """
        raise NotImplementedError("RAG query not implemented")

    async def stream_query(
        self, message: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Streaming RAG via SSE. Yields SSE-formatted strings.
        Format: "data: <token>\n\n" for tokens, "data: [DONE]\n\n" to close.
        TODO: LangChain streaming chain with callbacks
        """
        yield "data: Not implemented\n\n"
        yield "data: [DONE]\n\n"


rag_service = RAGService()