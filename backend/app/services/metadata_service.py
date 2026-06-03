import asyncio
import logging
from typing import Any, Dict, Optional

import yt_dlp

from app.models.schemas import VideoMetadata

logger = logging.getLogger(__name__)


class MetadataService:
    """
    Uses yt-dlp's extract_info (no download) for both platforms.
    One unified code path — yt-dlp normalises the info_dict across extractors.
    Runs in executor: yt-dlp is synchronous.
    """

    def detect_platform(self, url: str) -> str:
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        if "instagram.com" in url:
            return "instagram"
        raise ValueError(f"Unsupported URL: {url}")

    def compute_engagement_rate(
        self,
        likes: Optional[int],
        comments: Optional[int],
        views: Optional[int],
    ) -> Optional[float]:
        if not views:
            return None
        return round(((likes or 0) + (comments or 0)) / views * 100, 4)

    # ------------------------------------------------------------------ #
    # yt-dlp (sync — runs in executor)                                    #
    # ------------------------------------------------------------------ #

    def _extract_info_sync(self, url: str) -> Dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,      # metadata only — no media file
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return ydl.sanitize_info(info)  # removes non-serialisable objects

    def _parse_upload_date(self, raw: Optional[str]) -> Optional[str]:
        """yt-dlp returns YYYYMMDD → normalise to YYYY-MM-DD."""
        if not raw or len(raw) != 8:
            return raw
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"

    def _build_metadata(
        self, info: Dict[str, Any], video_id: str, platform: str
    ) -> VideoMetadata:
        likes = info.get("like_count")
        comments = info.get("comment_count")
        views = info.get("view_count")

        # yt-dlp key names differ slightly per extractor — try all variants
        follower_count = (
            info.get("channel_follower_count")
            or info.get("uploader_subscriber_count")
            or info.get("subscriber_count")
        )

        creator = (
            info.get("uploader")
            or info.get("channel")
            or info.get("creator")
            or "Unknown"
        )

        # Normalise tags → #hashtag format, cap at 30
        raw_tags: list = info.get("tags") or []
        hashtags = [
            f"#{t}" if not t.startswith("#") else t
            for t in raw_tags[:30]
        ]

        return VideoMetadata(
            video_id=video_id,
            url=info.get("webpage_url", url if (url := info.get("original_url", "")) else ""),
            platform=platform,
            creator=creator,
            follower_count=follower_count,
            views=views,
            likes=likes,
            comments=comments,
            hashtags=hashtags,
            upload_date=self._parse_upload_date(info.get("upload_date")),
            duration=info.get("duration"),
            engagement_rate=self.compute_engagement_rate(likes, comments, views),
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def get_metadata(self, url: str, video_id: str) -> VideoMetadata:
        platform = self.detect_platform(url)
        loop = asyncio.get_event_loop()

        try:
            info = await loop.run_in_executor(None, self._extract_info_sync, url)
            return self._build_metadata(info, video_id, platform)
        except Exception as e:
            logger.warning("Metadata fetch failed for Video %s: %s — using stub", video_id, e)
            return VideoMetadata(
                video_id=video_id,
                url=url,
                platform=platform,
                creator="Unknown (metadata unavailable)",
        )


metadata_service = MetadataService()