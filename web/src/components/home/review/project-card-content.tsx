"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProjectCardBlocks, ProjectCardMeta, type ProjectCardPayload } from "./project-card-blocks";

interface Props {
  signalId: string;
  signalTitle: string;
  payload: ProjectCardPayload;
}

const OUTCOMES = [
  { key: "success", label: "🎉 성공" },
  { key: "stuck", label: "😵 막힘" },
  { key: "give_up", label: "🏳️ 포기" },
];

export function ProjectCardContent({ signalTitle, payload }: Props) {
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  return (
    <div className="screen-container" style={{ paddingTop: "24px", paddingBottom: "96px" }}>
      <Link
        href="/home"
        className="text-label"
        style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)", marginBottom: "20px" }}
      >
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 4L6 8l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        홈으로
      </Link>

      {/* 헤더 */}
      <h1 className="text-screen-title" style={{ marginBottom: "12px" }}>{signalTitle}</h1>
      <ProjectCardMeta payload={payload} />

      <ProjectCardBlocks payload={payload} />

      {/* ⑦ 결과 남기기 (인라인, UI만 — 저장 API는 다음 슬라이스) */}
      <section style={{ marginTop: "8px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>결과 남기기</h2>
        <div style={{ display: "flex", gap: "8px" }}>
          {OUTCOMES.map((o) => (
            <button
              key={o.key}
              type="button"
              onClick={() => setToast("결과 기록은 곧 지원돼요")}
              style={{
                flex: 1,
                minHeight: "44px",
                borderRadius: "9999px",
                border: "1px solid var(--border-subtle, #E5E5E5)",
                background: "transparent",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: 500,
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      </section>

      {toast && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            bottom: "calc(80px + env(safe-area-inset-bottom))",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            zIndex: 60,
            pointerEvents: "none",
          }}
        >
          <div style={{ background: "rgba(0,0,0,0.75)", color: "#fff", padding: "10px 20px", borderRadius: "9999px", fontSize: "14px" }}>
            {toast}
          </div>
        </div>
      )}
    </div>
  );
}
