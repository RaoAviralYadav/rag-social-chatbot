from fastapi import APIRouter, HTTPException

from app.models.schemas import VideoIngestRequest, IngestResponse

router = APIRouter()


@router.post("/", response_model=IngestResponse)
async def ingest_videos(request: VideoIngestRequest):
    """
    Accepts one YouTube URL and one Instagram Reel URL.
    Fetches transcripts + metadata, chunks + embeds, stores in vector DB.
    TODO: wire up transcript_service → metadata_service → embedding_service → vector_store
    """
    # STUB
    return IngestResponse(
        status="pending",
        video_a=None,
        video_b=None,
        message="Ingestion pipeline not yet implemented.",
    )