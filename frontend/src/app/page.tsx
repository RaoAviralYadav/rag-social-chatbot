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
  // Stable session ID for the lifetime of this page load
  const [sessionId] = useState(() => crypto.randomUUID());

  const handleIngest = (data: IngestResponse) => {
    setVideoA(data.video_a);
    setVideoB(data.video_b);
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