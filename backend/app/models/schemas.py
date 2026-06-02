from pydantic import BaseModel
from typing import Optional, List


class VideoIngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str


class VideoMetadata(BaseModel):
    video_id: str           # "A" or "B"
    url: str
    platform: str           # "youtube" | "instagram"
    creator: str
    follower_count: Optional[int] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    hashtags: List[str] = []
    upload_date: Optional[str] = None
    duration: Optional[int] = None   # seconds
    engagement_rate: Optional[float] = None  # computed: (likes+comments)/views*100


class IngestResponse(BaseModel):
    status: str
    video_a: Optional[VideoMetadata] = None
    video_b: Optional[VideoMetadata] = None
    message: str


class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class SourceChunk(BaseModel):
    video_id: str
    chunk_index: int
    text: str
    score: Optional[float] = None


class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = []
    session_id: str