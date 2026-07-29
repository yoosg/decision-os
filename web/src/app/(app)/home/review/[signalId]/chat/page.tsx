"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { use } from "react";

type Message = {
  id: string;
  role: "ai" | "user";
  text: string;
  timestamp: Date;
  isError?: boolean;
};

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";

export default function ChatPage({ params }: { params: Promise<{ signalId: string }> }) {
  const { signalId } = use(params);
  const router = useRouter();

  const msgCountRef = useRef(1);
  const nextId = () => String(msgCountRef.current++);

  const [signalTitle, setSignalTitle] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([
    { id: "0", role: "ai", text: "이 리뷰에 대해 궁금한 점을 물어보세요.", timestamp: new Date() },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [retryMessage, setRetryMessage] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const supabase = createClient();
    let cancelled = false;
    supabase
      .from("signals")
      .select("title")
      .eq("id", signalId)
      .maybeSingle()
      .then(({ data }) => {
        if (!cancelled && data?.title) setSignalTitle(data.title);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [signalId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(messageToSend?: string) {
    const text = (messageToSend ?? input).trim();
    if (!text || isLoading) return;

    setInput("");
    setRetryMessage(null);
    setMessages((prev) => [...prev, { id: nextId(), role: "user", text, timestamp: new Date() }]);
    setIsLoading(true);

    try {
      const supabase = createClient();
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token ?? "";

      const res = await fetch(`${FASTAPI_URL}/api/v1/chat/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ signal_id: signalId, message: text }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const body = await res.json();
      const reply: string = body?.data?.reply ?? "";
      if (!reply) throw new Error("Empty reply");
      setMessages((prev) => [...prev, { id: nextId(), role: "ai", text: reply, timestamp: new Date() }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "ai",
          text: "응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.",
          timestamp: new Date(),
          isError: true,
        },
      ]);
      setRetryMessage(text);
    } finally {
      setIsLoading(false);
    }
  }

  const contextLabel = signalTitle ? `리서치 리뷰 — ${signalTitle}` : "리서치 리뷰";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        background: "var(--surface-base, #fff)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "16px 20px 12px",
          borderBottom: "1px solid var(--border-subtle, #E5E5E5)",
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => router.back()}
          style={{
            // WCAG 2.2 AA (Story 5.4 AC-B1): 최소 44×44pt 탭 타겟.
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minWidth: "44px",
            minHeight: "44px",
            marginLeft: "-12px",
            fontSize: "13px",
            color: "var(--text-secondary, #595D6A)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
          aria-label="뒤로 가기"
        >
          ←
        </button>
        <span
          style={{
            fontSize: "13px",
            color: "var(--text-secondary, #595D6A)",
            fontWeight: 500,
          }}
        >
          {contextLabel}
        </span>
      </div>

      {/* Message thread */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "80%",
                padding: "10px 14px",
                borderRadius: "12px",
                background:
                  msg.role === "user"
                    ? "var(--accent-primary, #0D0D0D)"
                    : "var(--surface-card, #F2F2F2)",
                color:
                  msg.role === "user"
                    ? "var(--accent-foreground, #fff)"
                    : "var(--text-primary, #0D0D0D)",
                fontSize: "15px",
                lineHeight: "1.5",
              }}
            >
              {msg.text}
            </div>
            {msg.role === "ai" && (
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--text-tertiary, #9CA3AF)",
                  marginTop: "4px",
                }}
              >
                {msg.timestamp.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
            {msg.isError && retryMessage && (
              <button
                onClick={() => handleSend(retryMessage)}
                style={{
                  // WCAG 2.2 AA (Story 5.4 AC-B1): 최소 44pt 탭 타겟.
                  marginTop: "6px",
                  minHeight: "44px",
                  fontSize: "13px",
                  color: "var(--text-secondary, #595D6A)",
                  background: "none",
                  border: "1px solid var(--border-subtle, #E5E5E5)",
                  borderRadius: "6px",
                  padding: "4px 10px",
                  cursor: "pointer",
                }}
              >
                재시도
              </button>
            )}
          </div>
        ))}

        {isLoading && (
          <div style={{ display: "flex", alignItems: "flex-start" }}>
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "12px",
                background: "var(--surface-card, #F2F2F2)",
                color: "var(--text-tertiary, #9CA3AF)",
                fontSize: "15px",
              }}
            >
              ···
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          padding: "12px 20px",
          borderTop: "1px solid var(--border-subtle, #E5E5E5)",
          flexShrink: 0,
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={isLoading}
          autoFocus
          placeholder="이 리뷰에 대해 궁금한 점을 물어보세요."
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: "8px",
            border: "1px solid var(--border-card, #DCDCDC)",
            fontSize: "15px",
            outline: "none",
            background: isLoading ? "var(--surface-raised, #F9F9F9)" : "#fff",
            color: "var(--text-primary, #0D0D0D)",
          }}
        />
        <button
          onClick={() => handleSend()}
          disabled={isLoading || !input.trim()}
          aria-label="전송"
          style={{
            // WCAG 2.2 AA (Story 5.4 AC-B1): 최소 44pt 탭 타겟.
            minHeight: "44px",
            padding: "10px 16px",
            borderRadius: "8px",
            background: "var(--accent-primary, #0D0D0D)",
            color: "var(--accent-foreground, #fff)",
            border: "none",
            fontSize: "15px",
            cursor: isLoading || !input.trim() ? "not-allowed" : "pointer",
            opacity: isLoading || !input.trim() ? 0.4 : 1,
          }}
        >
          전송
        </button>
      </div>
    </div>
  );
}
