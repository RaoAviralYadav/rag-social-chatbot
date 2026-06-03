import { ChatMessage, IngestResponse, SourceChunk } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─────────────────────────────────────────────────────────────────────────────
// Health
// ─────────────────────────────────────────────────────────────────────────────

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// Ingest
// ─────────────────────────────────────────────────────────────────────────────

export async function ingestVideos(
  youtubeUrl: string,
  instagramUrl: string
): Promise<IngestResponse> {
  const res = await fetch(`${API_BASE}/api/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      youtube_url: youtubeUrl,
      instagram_url: instagramUrl,
    }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? "Ingestion failed");
  }
  return res.json();
}

export async function resetIngestion(): Promise<void> {
  await fetch(`${API_BASE}/api/ingest`, { method: "DELETE" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat — SSE stream
// ─────────────────────────────────────────────────────────────────────────────

export type StreamEvent =
  | { type: "token"; token: string }
  | { type: "sources"; sources: SourceChunk[] }
  | { type: "done" };

export async function* streamChatMessage(
  message: string,
  sessionId: string,
  history: ChatMessage[]
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      history: history.map(({ role, content }) => ({ role, content })),
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? "Chat request failed");
  }
  if (!res.body) throw new Error("No response body from stream endpoint");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE lines end with \n\n — split on that, keep partial tail
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;

      const data = line.slice(6); // strip "data: "

      if (data === "[DONE]") {
        yield { type: "done" };
        return;
      }

      if (data.startsWith("[SOURCES]")) {
        try {
          const sources: SourceChunk[] = JSON.parse(data.slice(9));
          yield { type: "sources", sources };
        } catch {
          console.warn("Failed to parse sources:", data.slice(9));
        }
        continue;
      }

      yield { type: "token", token: data };
    }
  }
}