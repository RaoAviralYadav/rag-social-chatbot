import { VideoMetadata } from "@/types";

interface Props {
  video: VideoMetadata | null;
  label: "A" | "B";
}

function fmtNum(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function fmtDuration(s: number | null | undefined): string {
  if (!s) return "—";
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function PlatformBadge({ platform }: { platform: string }) {
  const color = platform === "youtube" ? "#FF0000" : "#E1306C";
  return (
    <span
      style={{
        background: color,
        color: "#fff",
        fontSize: "0.7rem",
        padding: "2px 7px",
        borderRadius: 4,
        fontWeight: 600,
        letterSpacing: "0.03em",
        textTransform: "uppercase",
      }}
    >
      {platform}
    </span>
  );
}

export default function VideoCard({ video, label }: Props) {
  if (!video) {
    return (
      <div className="video-card">
        <h3>Video {label}</h3>
        <p style={{ color: "#333", fontSize: "0.85rem", marginTop: 8 }}>
          Not ingested yet
        </p>
      </div>
    );
  }

  const embedSrc =
    video.platform === "youtube"
      ? (() => {
          const match = video.url.match(
            /(?:v=|youtu\.be\/|shorts\/)([a-zA-Z0-9_-]{11})/
          );
          return match
            ? `https://www.youtube.com/embed/${match[1]}`
            : null;
        })()
      : null;

  return (
    <div className="video-card">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <h3 style={{ margin: 0 }}>Video {label}</h3>
        <PlatformBadge platform={video.platform} />
      </div>

      {/* Embedded player (YouTube only) */}
      {embedSrc ? (
        <iframe
          src={embedSrc}
          style={{ width: "100%", aspectRatio: "16/9", border: "none", borderRadius: 6, marginBottom: 12 }}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      ) : (
        <a
          href={video.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ display: "block", marginBottom: 12, color: "#60a5fa", fontSize: "0.85rem" }}
        >
          Open in Instagram ↗
        </a>
      )}

      {/* Stats grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 16px" }}>
        <Stat label="Creator" value={video.creator} />
        <Stat label="Followers" value={fmtNum(video.follower_count)} />
        <Stat label="Views" value={fmtNum(video.views)} />
        <Stat label="Likes" value={fmtNum(video.likes)} />
        <Stat label="Comments" value={fmtNum(video.comments)} />
        <Stat label="Duration" value={fmtDuration(video.duration)} />
        <Stat label="Uploaded" value={video.upload_date ?? "—"} />
        <Stat
          label="Engagement"
          value={video.engagement_rate != null ? `${video.engagement_rate.toFixed(2)}%` : "—"}
          highlight={video.engagement_rate != null}
        />
      </div>

      {/* Hashtags */}
      {video.hashtags.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 4 }}>
          {video.hashtags.slice(0, 10).map((tag) => (
            <span
              key={tag}
              style={{
                background: "#1e293b",
                color: "#94a3b8",
                fontSize: "0.72rem",
                padding: "2px 6px",
                borderRadius: 4,
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <div style={{ fontSize: "0.7rem", color: "#555", marginBottom: 1 }}>
        {label}
      </div>
      <div
        style={{
          fontSize: "0.88rem",
          fontWeight: highlight ? 700 : 400,
          color: highlight ? "#34d399" : "#e5e5e5",
        }}
      >
        {value}
      </div>
    </div>
  );
}