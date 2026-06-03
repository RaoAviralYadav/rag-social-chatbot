from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import rag_service

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await rag_service.query(
        message=request.message,
        session_id=request.session_id,
        history=request.history,
    )
    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        rag_service.stream_query(
            message=request.message,
            session_id=request.session_id,
            history=request.history,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables Nginx response buffering
        },
    )