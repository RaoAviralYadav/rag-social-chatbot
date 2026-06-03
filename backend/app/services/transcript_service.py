import asyncio
import logging
import os
import re
import tempfile
from typing import Any, Dict, List

import yt_dlp
from openai import AsyncOpenAI
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

from app.config import settings

logger = logging.getLogger(__name__)


class TranscriptService:
    """
    YouTube  → youtube-transcript-api (free, no cost, milliseconds)
    Instagram → yt-dlp (audio download) + Whisper API ($0.006/min)

    Both return:
      {
        "text": str,                          # full joined transcript
        "entries": [{text, start, duration}], # timestamped segments for chunking
        "source": str,                        # which extraction method was used
        "raw_video_id": str | None,           # YouTube video ID if applicable
      }

    Sync-heavy calls (YouTubeTranscriptApi, yt-dlp) are offloaded to a
    thread pool via run_in_executor so they never block FastAPI's event loop.
    """

    def __init__(self):
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key)

    # ------------------------------------------------------------------ #
    # YouTube                                                              #
    # ------------------------------------------------------------------ #

    def _parse_youtube_id(self, url: str) -> str:
        """Handle all common YouTube URL formats."""
        pattern = r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})"
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Cannot extract YouTube video ID from: {url}")
        return match.group(1)

    def _fetch_youtube_entries_sync(self, video_id: str) -> List[Dict]:
        """
        Synchronous transcript fetch — runs in executor.
        Priority: manual EN → auto-generated EN → any language (translated to EN).
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except TranscriptsDisabled:
            raise ValueError(f"Transcripts are disabled for video: {video_id}")
        except VideoUnavailable:
            raise ValueError(f"Video is unavailable: {video_id}")

        try:
            transcript = transcript_list.find_manually_created_transcript(
                ["en", "en-US", "en-GB"]
            )
            logger.info("Using manual EN transcript for %s", video_id)
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_generated_transcript(
                    ["en", "en-US", "en-GB"]
                )
                logger.info("Using auto-generated EN transcript for %s", video_id)
            except NoTranscriptFound:
                # Last resort: translate whatever language is available
                transcript = next(iter(transcript_list))
                logger.warning(
                    "No EN transcript for %s — translating from [%s]",
                    video_id,
                    transcript.language_code,
                )
                transcript = transcript.translate("en")

        return transcript.fetch()

    async def get_youtube_transcript(self, url: str) -> Dict[str, Any]:
        video_id = self._parse_youtube_id(url)
        loop = asyncio.get_event_loop()

        entries = await loop.run_in_executor(
            None, self._fetch_youtube_entries_sync, video_id
        )

        return {
            "text": " ".join(e["text"] for e in entries),
            "entries": entries,   # [{text: str, start: float, duration: float}]
            "source": "youtube_transcript_api",
            "raw_video_id": video_id,
        }

    # ------------------------------------------------------------------ #
    # Instagram                                                            #
    # ------------------------------------------------------------------ #

    def _download_audio_sync(self, url: str, output_base: str) -> str:
        """
        Synchronous yt-dlp download — runs in executor.
        Returns final .mp3 path.
        64kbps is sufficient for Whisper speech recognition and halves file size
        vs 128kbps, cutting Whisper API cost proportionally.
        """
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_base,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "64",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            logger.info(
                "Downloaded Instagram audio: %s (%.1fs)",
                info.get("title", "unknown"),
                info.get("duration", 0),
            )
        return output_base + ".mp3"

    async def get_instagram_transcript(self, url: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_base = os.path.join(tmpdir, "audio")

            audio_path = await loop.run_in_executor(
                None, self._download_audio_sync, url, audio_base
            )

            if not os.path.exists(audio_path):
                raise FileNotFoundError(
                    f"Audio file not created at {audio_path}. "
                    "Ensure ffmpeg is installed and the URL is accessible."
                )

            with open(audio_path, "rb") as f:
                response = await self._openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",  # gives us per-segment timestamps
                )

        entries = []
        if hasattr(response, "segments") and response.segments:
            entries = [
                {
                    "text": seg.text.strip(),
                    "start": seg.start,
                    "duration": seg.end - seg.start,
                }
                for seg in response.segments
            ]

        return {
            "text": response.text,
            "entries": entries,
            "source": "whisper-1",
            "raw_video_id": None,
        }

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def get_transcript(self, url: str, platform: str) -> Dict[str, Any]:
        """
        Entry point. platform must be 'youtube' or 'instagram'.
        Raises ValueError on bad input or extraction failure.
        """
        if platform == "youtube":
            return await self.get_youtube_transcript(url)
        if platform == "instagram":
            return await self.get_instagram_transcript(url)
        raise ValueError(f"Unsupported platform: {platform}")


transcript_service = TranscriptService()