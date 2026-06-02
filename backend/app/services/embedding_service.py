from typing import List
from app.config import settings


class EmbeddingService:
    """
    Chunks transcripts and generates embeddings.

    Chunking  → LangChain RecursiveCharacterTextSplitter
    Embeddings → OpenAI text-embedding-3-small
    """

    def __init__(self):
        self.chunk_size = 500
        self.chunk_overlap = 50
        # TODO: self.embeddings = OpenAIEmbeddings(model=settings.embedding_model)

    def chunk_transcript(self, text: str, video_id: str) -> List[dict]:
        """
        Split transcript into overlapping chunks tagged with video_id.
        Returns: [{"text": str, "video_id": str, "chunk_index": int}, ...]
        TODO: from langchain.text_splitter import RecursiveCharacterTextSplitter
        """
        raise NotImplementedError("Text chunking not implemented")

    async def embed_chunks(self, chunks: List[dict]) -> List[dict]:
        """
        Add 'embedding' vector to each chunk dict.
        TODO: call self.embeddings.aembed_documents([c["text"] for c in chunks])
        """
        raise NotImplementedError("Embedding generation not implemented")


embedding_service = EmbeddingService()