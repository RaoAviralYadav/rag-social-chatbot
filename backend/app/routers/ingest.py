import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import IngestResponse, TranscriptResult, VideoIngestRequest
from app.services.embedding_service import embedding_service
from app.services.metadata_service import metadata_service
from app.services.rag_service import rag_service
from app.services.transcript_service import transcript_service
from app.services.vector_store import vector_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=IngestResponse)
async def ingest_videos(request: VideoIngestRequest):
    """
    Full ingestion pipeline:
      1. Detect platforms
      2. Fetch transcripts + metadata in parallel
      3. Chunk + embed transcripts in parallel
      4. Wipe old vectors, upsert new
      5. Push metadata into RAG service prompt context
    """
    try:
        # ── 1. detect ────────────────────────────────────────────────────
        platform_a = metadata_service.detect_platform(request.youtube_url)
        platform_b = metadata_service.detect_platform(request.instagram_url)

        # ── 2. transcripts + metadata — all four in parallel ─────────────
        logger.info("Starting parallel transcript + metadata fetch…")
        (raw_a, raw_b, meta_a, meta_b) = await asyncio.gather(
            transcript_service.get_transcript(request.youtube_url, platform_a),
            transcript_service.get_transcript(request.instagram_url, platform_b),
            metadata_service.get_metadata(request.youtube_url, "A"),
            metadata_service.get_metadata(request.instagram_url, "B"),
        )

        # ── 3. coerce raw dicts → TranscriptResult (Pydantic coerces entries) ──
        result_a = TranscriptResult(**raw_a)
        result_b = TranscriptResult(**raw_b)

        # ── 4. chunk + embed in parallel ─────────────────────────────────
        logger.info("Chunking and embedding transcripts…")
        chunks_a, chunks_b = await asyncio.gather(
            embedding_service.process(result_a, "A"),
            embedding_service.process(result_b, "B"),
        )

        # ── 5. clear stale vectors, upsert fresh ─────────────────────────
        await asyncio.gather(
            vector_store.delete_video("A"),
            vector_store.delete_video("B"),
        )
        await asyncio.gather(
            vector_store.upsert_chunks(chunks_a),
            vector_store.upsert_chunks(chunks_b),
        )

        # ── 6. prime RAG metadata context ────────────────────────────────
        rag_service.set_video_metadata(meta_a, meta_b)

        logger.info(
            "Ingestion complete | A: %s (%d chunks) | B: %s (%d chunks)",
            meta_a.creator, len(chunks_a),
            meta_b.creator, len(chunks_b),
        )

        return IngestResponse(
            status="success",
            video_a=meta_a,
            video_b=meta_b,
            message=(
                f"Ingested {len(chunks_a) + len(chunks_b)} chunks — "
                f"Video A ({meta_a.creator}) and Video B ({meta_b.creator}) ready."
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.delete("") 
async def reset_ingestion():
    """Clear all vectors — useful for a fresh demo run."""
    await vector_store.clear()
    return {"status": "cleared"}