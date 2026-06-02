export interface VideoMetadata {
  video_id: string;
  url: string;
  platform: "youtube" | "instagram";
  creator: string;
  follower_count: number | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  hashtags: string[];
  upload_date: string | null;
  duration: number | null;
  engagement_rate: number | null;
}

export interface IngestResponse {
  status: string;
  video_a: VideoMetadata | null;
  video_b: VideoMetadata | null;
  message: string;
}

export interface SourceChunk {
  video_id: string;
  chunk_index: number;
  text: string;
  score?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
}

export interface ChatRequest {
  message: string;
  session_id: string;
  history: ChatMessage[];
}