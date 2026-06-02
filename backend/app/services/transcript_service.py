from typing import Optional


class TranscriptService:
    """
    Extracts transcripts from YouTube and Instagram videos.

    YouTube  → youtube-transcript-api (free, no API key needed)
    Instagram → yt-dlp download audio → Whisper transcription
    """

    async def get_youtube_transcript(self, url: str) -> Optional[str]:
        # TODO: from youtube_transcript_api import YouTubeTranscriptApi
        # Parse video_id from URL, fetch transcript, join into single string
        raise NotImplementedError("YouTube transcript extraction not implemented")

    async def get_instagram_transcript(self, url: str) -> Optional[str]:
        # TODO: yt-dlp to download audio → openai.audio.transcriptions.create (Whisper)
        raise NotImplementedError("Instagram transcript extraction not implemented")

    async def get_transcript(self, url: str, platform: str) -> Optional[str]:
        if platform == "youtube":
            return await self.get_youtube_transcript(url)
        elif platform == "instagram":
            return await self.get_instagram_transcript(url)
        raise ValueError(f"Unsupported platform: {platform}")


transcript_service = TranscriptService()