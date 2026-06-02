from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Single-turn RAG query. Returns answer + source citations.
    TODO: wire up rag_service.query()
    """
    # STUB
    return ChatResponse(
        answer="RAG pipeline not yet implemented.",
        sources=[],
        session_id=request.session_id,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming RAG query via Server-Sent Events.
    TODO: wire up rag_service.stream_query()
    """
    # STUB
    async def generate():
        yield "data: Streaming not yet implemented.\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")