"use client";
import { useState } from "react";
import { sendChatMessage } from "@/lib/api";
import { ChatMessage } from "@/types";

interface Props {
  sessionId: string;
  isReady: boolean;
}

export default function ChatPanel({ sessionId, isReady }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || !isReady || isStreaming) return;

    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    try {
      // TODO: replace with streaming version (streamChatMessage)
      const data = await sendChatMessage(input, sessionId, messages);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: could not get a response." },
      ]);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-hint">
            {isReady ? "Ask anything about the two videos." : "Ingest videos first to start chatting."}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`message message--${m.role}`}>
            {m.content}
            {/* TODO: render m.sources as citation chips */}
          </div>
        ))}
        {isStreaming && (
          <div className="message message--assistant" style={{ opacity: 0.6 }}>
            Thinking…
          </div>
        )}
      </div>
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Why did Video A outperform Video B?"
          disabled={!isReady || isStreaming}
        />
        <button onClick={handleSend} disabled={!isReady || isStreaming}>
          {isStreaming ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}