"use client";

import { useEffect, useRef, useState } from "react";
import { streamChatMessage } from "@/lib/api";
import { ChatMessage, SourceChunk } from "@/types";

interface Props {
  sessionId: string;
  isReady: boolean;
}

function SourceChips({ sources }: { sources: SourceChunk[] }) {
  if (!sources.length) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
      {sources.map((s, i) => (
        <span
          key={i}
          title={s.text}
          style={{
            background: "#1e293b",
            border: "1px solid #334155",
            color: "#7dd3fc",
            fontSize: "0.7rem",
            padding: "2px 7px",
            borderRadius: 12,
            cursor: "default",
          }}
        >
          Video {s.video_id}
          {s.score != null && (
            <span style={{ color: "#475569", marginLeft: 4 }}>
              {(s.score * 100).toFixed(0)}%
            </span>
          )}
        </span>
      ))}
    </div>
  );
}

function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`message message--${msg.role}`}>
      <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
        {msg.content}
        {msg.isStreaming && (
          <span
            style={{
              display: "inline-block",
              width: 6,
              height: 14,
              background: "#7dd3fc",
              marginLeft: 2,
              verticalAlign: "middle",
              animation: "blink 0.8s step-start infinite",
            }}
          />
        )}
      </div>
      {!isUser && msg.sources && <SourceChips sources={msg.sources} />}
    </div>
  );
}

const SUGGESTED = [
  "Why did Video A get more engagement than Video B?",
  "Compare the hooks in the first 5 seconds.",
  "What's the engagement rate of each video?",
  "Who is the creator of Video B and what's their follower count?",
  "Suggest improvements for B based on what worked in A.",
];

export default function ChatPanel({ sessionId, isReady }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on every new token
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const query = (text ?? input).trim();
    if (!query || !isReady || isStreaming) return;

    setInput("");
    setIsStreaming(true);

    const userMsg: ChatMessage = { role: "user", content: query };
    const placeholder: ChatMessage = {
      role: "assistant",
      content: "",
      sources: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, placeholder]);

    try {
      for await (const event of streamChatMessage(query, sessionId, messages)) {
        if (event.type === "token") {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = {
              ...last,
              content: last.content + event.token,
            };
            return updated;
          });
        } else if (event.type === "sources") {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              sources: event.sources,
            };
            return updated;
          });
        } else if (event.type === "done") {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              isStreaming: false,
            };
            return updated;
          });
        }
      }
    } catch (e) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: `Error: ${e instanceof Error ? e.message : "Something went wrong"}`,
          isStreaming: false,
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="chat-panel">
      <style>{`
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div style={{ margin: "auto", width: "100%" }}>
            {isReady ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <p style={{ color: "#444", fontSize: "0.82rem", marginBottom: 4 }}>
                  Try asking:
                </p>
                {SUGGESTED.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    style={{
                      background: "transparent",
                      border: "1px solid #222",
                      color: "#888",
                      textAlign: "left",
                      padding: "7px 10px",
                      borderRadius: 6,
                      fontSize: "0.82rem",
                      cursor: "pointer",
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            ) : (
              <p className="chat-hint">Ingest both videos to start chatting.</p>
            )}
          </div>
        ) : (
          messages.map((m, i) => <Message key={i} msg={m} />)
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder={
            isReady
              ? "Ask anything about the two videos…"
              : "Ingest videos first…"
          }
          disabled={!isReady || isStreaming}
        />
        <button onClick={() => handleSend()} disabled={!isReady || isStreaming}>
          {isStreaming ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}