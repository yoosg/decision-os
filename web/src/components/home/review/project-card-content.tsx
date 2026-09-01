"use client";

import { useEffect, useState } from "react";
import { ProjectCardBlocks, ProjectCardMeta, type ProjectCardPayload } from "./project-card-blocks";
import { useCardProgress, type CardResult } from "./use-card-progress";
import { BackLink } from "@/components/ui/back-link";
import { VibeCodingGuide } from "./vibe-coding-guide";

interface Props {
  signalId: string;
  signalTitle: string;
  payload: ProjectCardPayload;
  reviewId?: string;
}

const OUTCOMES: { key: CardResult; label: string }[] = [
  { key: "success", label: "🎉 성공" },
  { key: "stuck", label: "😵 막힘" },
  { key: "dropped", label: "🏳️ 포기" },
];

export function ProjectCardContent({ signalTitle, payload, reviewId }: Props) {
  const progress = useCardProgress(reviewId ?? null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  // 저장 실패 시 토스트
  useEffect(() => {
    if (progress.saveError) setToast("저장에 실패했어요 — 다시 체크하면 재시도돼요");
  }, [progress.saveError]);

  return (
    <div className="screen-container" style={{ paddingTop: "24px", paddingBottom: "96px" }}>
      {/* 홈으로 백링크 — 기존 그대로 */}
      <BackLink href="/home">홈으로</BackLink>

      <h1 className="text-screen-title" style={{ marginBottom: "12px" }}>{signalTitle}</h1>
      <VibeCodingGuide />
      <ProjectCardMeta payload={payload} />

      <ProjectCardBlocks payload={payload} progress={progress} />

      <div style={{ height: "1px", background: "#F0F0F0", margin: "0 0 20px" }} />

      {/* ⑦ 결과 남기기 — 단일선택, 재탭 시 해제 */}
      <section>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>결과 남기기</h2>
        <div style={{ display: "flex", gap: "8px" }}>
          {OUTCOMES.map((o) => {
            const active = progress.result === o.key;
            return (
              <button
                key={o.key}
                type="button"
                aria-pressed={active}
                onClick={() => progress.setResult(active ? null : o.key)}
                style={{
                  flex: 1,
                  minHeight: "44px",
                  borderRadius: "9999px",
                  border: active ? "1px solid var(--text-primary, #111)" : "1px solid var(--border-subtle, #E5E5E5)",
                  background: active ? "var(--surface-card, #F2F2F2)" : "transparent",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: active ? 700 : 500,
                }}
              >
                {o.label}
              </button>
            );
          })}
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
