const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function ingestVideos(youtubeUrl: string, instagramUrl: string) {
  const res = await fetch(`${API_BASE}/api/ingest/`, {   
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ youtube_url: youtubeUrl, instagram_url: instagramUrl }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  history: { role: string; content: string }[]
) {
  const res = await fetch(`${API_BASE}/api/chat/`, {     
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, history }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function* streamChatMessage(
  message: string,
  sessionId: string,
  history: { role: string; content: string }[]
): AsyncGenerator<string> {
  // TODO: implement SSE streaming reader
  yield "Streaming not yet implemented";
}