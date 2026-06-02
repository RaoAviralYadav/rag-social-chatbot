import { VideoMetadata } from "@/types";

interface Props {
  video: VideoMetadata | null;
  label: "A" | "B";
}

export default function VideoCard({ video, label }: Props) {
  if (!video) {
    return (
      <div className="video-card">
        <h3>Video {label}</h3>
        <p style={{ color: "#444", fontSize: "0.85rem" }}>Not loaded yet</p>
      </div>
    );
  }

  return (
    <div className="video-card">
      <h3>Video {label} — {video.platform}</h3>
      {/* TODO: embed video player (YouTube iframe / Instagram oEmbed) */}
      <p style={{ fontSize: "0.85rem", marginTop: 8 }}>
        <strong>Creator:</strong> {video.creator}
      </p>
      <p style={{ fontSize: "0.85rem" }}>
        <strong>Engagement:</strong>{" "}
        {video.engagement_rate != null ? `${video.engagement_rate.toFixed(2)}%` : "—"}
      </p>
      {/* TODO: render full stats grid (views, likes, comments, followers, hashtags) */}
    </div>
  );
}