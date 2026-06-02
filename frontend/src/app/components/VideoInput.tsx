"use client";
import { useState } from "react";
import { ingestVideos } from "@/lib/api";
import { IngestResponse } from "@/types";

interface Props {
  onIngest: (data: IngestResponse) => void;
  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
}

export default function VideoInput({ onIngest, isLoading, setIsLoading }: Props) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!youtubeUrl || !instagramUrl) return;
    setError(null);
    setIsLoading(true);
    try {
      const data = await ingestVideos(youtubeUrl, instagramUrl);
      onIngest(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ingestion failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="video-input">
        <input
          type="text"
          placeholder="YouTube URL (Video A)"
          value={youtubeUrl}
          onChange={(e) => setYoutubeUrl(e.target.value)}
        />
        <input
          type="text"
          placeholder="Instagram Reel URL (Video B)"
          value={instagramUrl}
          onChange={(e) => setInstagramUrl(e.target.value)}
        />
        <button onClick={handleSubmit} disabled={isLoading || !youtubeUrl || !instagramUrl}>
          {isLoading ? "Processing…" : "Analyze Videos"}
        </button>
      </div>
      {error && <p style={{ color: "#f87171", fontSize: "0.85rem", marginTop: 6 }}>{error}</p>}
    </div>
  );
}