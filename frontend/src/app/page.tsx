"use client";
import { useState } from "react";
import VideoInput from "./components/VideoInput";
import VideoCard from "./components/VideoCard";
import ChatPanel from "./components/ChatPanel";
import { IngestResponse, VideoMetadata } from "@/types";

export default function Home() {
  const [videoA, setVideoA] = useState<VideoMetadata | null>(null);
  const [videoB, setVideoB] = useState<VideoMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null); // ← ADD
  const [sessionId] = useState(() => crypto.randomUUID());

  const handleIngest = (data: IngestResponse) => {
    setVideoA(data.video_a);
    setVideoB(data.video_b);
    setStatusMessage(`[${data.status.toUpperCase()}] ${data.message}`); // ← ADD
  };

  return (
    <main className="app-layout">
      <header>
        <h1>RAG Social Chatbot</h1>
      </header>

      <VideoInput
        onIngest={handleIngest}
        isLoading={isLoading}
        setIsLoading={setIsLoading}
      />

      {statusMessage && (
        <p style={{
          padding: "10px 14px",
          borderRadius: 7,
          background: "#1a1a1a",
          border: "1px solid #2a2a2a",
          color: "#facc15",
          fontSize: "0.85rem",
        }}>
          {statusMessage}
        </p>
      )}

      <section className="video-grid">
        <VideoCard video={videoA} label="A" />
        <VideoCard video={videoB} label="B" />
      </section>

      <ChatPanel
        sessionId={sessionId}
        isReady={!!(videoA && videoB)}
      />
    </main>
  );
}