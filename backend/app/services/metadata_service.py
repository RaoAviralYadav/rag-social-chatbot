from typing import Optional
from app.models.schemas import VideoMetadata


class MetadataService:
    """
    Fetches video metadata from YouTube and Instagram.

    YouTube  → yt-dlp (free) or YouTube Data API v3
    Instagram → yt-dlp (scraped)
    """

    def detect_platform(self, url: str) -> str:
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        elif "instagram.com" in url:
            return "instagram"
        raise ValueError(f"Unsupported platform for URL: {url}")

    def compute_engagement_rate(
        self, likes: Optional[int], comments: Optional[int], views: Optional[int]
    ) -> Optional[float]:
        if not views or views == 0:
            return None
        return round(((likes or 0) + (comments or 0)) / views * 100, 4)

    async def get_youtube_metadata(self, url: str, video_id: str) -> VideoMetadata:
        # TODO: use yt-dlp info_dict to extract title, uploader, view_count,
        #       like_count, comment_count, upload_date, duration, tags
        raise NotImplementedError("YouTube metadata extraction not implemented")

    async def get_instagram_metadata(self, url: str, video_id: str) -> VideoMetadata:
        # TODO: use yt-dlp info_dict (limited fields available without login)
        raise NotImplementedError("Instagram metadata extraction not implemented")

    async def get_metadata(self, url: str, video_id: str) -> VideoMetadata:
        platform = self.detect_platform(url)
        if platform == "youtube":
            return await self.get_youtube_metadata(url, video_id)
        return await self.get_instagram_metadata(url, video_id)


metadata_service = MetadataService()