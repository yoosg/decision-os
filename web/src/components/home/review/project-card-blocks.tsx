"use client";

import { useState } from "react";

export interface ProjectCardPayload {
  skill_label: string;
  difficulty: "first_step" | "basic" | "challenge";
  estimated_minutes: number;
  deliverable: string;
  success_preview: string;
  prerequisites: string;
  how_to_start: string;
  example_prompt: string;
  milestones: { action: string; done_signal: string }[];
  troubleshooting: { symptom: string; fix: string }[];
  success_checklist: string[];
}

export const CARD_DIFFICULTY_LABEL: Record<ProjectCardPayload["difficulty"], string> = {
  first_step: "첫걸음",
  basic: "기본",
  challenge: "도전",
};

function useCheckedSet() {
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const toggle = (i: number) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  return { checked, toggle };
}

function CopyPromptButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // 클립보드 미지원 환경 — 무시
    }
  };
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="text-label"
      style={{
        border: "1px solid var(--border-subtle, #E5E5E5)",
        borderRadius: "9999px",
        background: "transparent",
        padding: "4px 12px",
        cursor: "pointer",
      }}
    >
      {copied ? "복사됨!" : "📋 복사"}
    </button>
  );
}

function MilestoneList({ milestones }: { milestones: ProjectCardPayload["milestones"] }) {
  const { checked, toggle } = useCheckedSet();
  return (
    <div>
      <p className="text-label" style={{ color: "var(--text-secondary)", marginBottom: "8px" }}>
        {checked.size}/{milestones.length}
      </p>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {milestones.map((m, i) => (
          <li key={i} style={{ marginBottom: "12px" }}>
            <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={checked.has(i)}
                onChange={() => toggle(i)}
                style={{ marginTop: "3px" }}
              />
              <span>
                <span className="text-body" style={{ display: "block" }}>{m.action}</span>
                <span className="text-body" style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                  끝나면: {m.done_signal}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SuccessChecklist({ items }: { items: string[] }) {
  const { checked, toggle } = useCheckedSet();
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {items.map((it, i) => (
        <li key={i} style={{ marginBottom: "8px" }}>
          <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={checked.has(i)}
              onChange={() => toggle(i)}
              style={{ marginTop: "3px" }}
            />
            <span className="text-body">{it}</span>
          </label>
        </li>
      ))}
    </ul>
  );
}

export function ProjectCardBlocks({ payload }: { payload: ProjectCardPayload }) {
  return (
    <>
      {/* ① 완성하면 이게 나와 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>📦 완성하면 이게 나와</h2>
        <p className="text-body">{payload.deliverable}</p>
        <p className="text-body" style={{ color: "var(--text-secondary)", marginTop: "8px" }}>
          이렇게 보이면 성공 — {payload.success_preview}
        </p>
      </section>

      {/* ② 시작 전 준비물 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🧰 시작 전 준비물</h2>
        <p className="text-body">{payload.prerequisites}</p>
      </section>

      {/* ③ 이렇게 시작해 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🚀 이렇게 시작해</h2>
        <p className="text-body" style={{ marginBottom: "12px" }}>{payload.how_to_start}</p>
        <div
          style={{
            background: "var(--surface-raised, #F9F9F9)",
            border: "1px solid var(--border-subtle, #E5E5E5)",
            borderRadius: "12px",
            padding: "12px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span className="text-label" style={{ color: "var(--text-secondary)" }}>예시 프롬프트</span>
            <CopyPromptButton text={payload.example_prompt} />
          </div>
          <p className="text-body" style={{ whiteSpace: "pre-wrap" }}>{payload.example_prompt}</p>
        </div>
      </section>

      {/* ④ 진행 과정 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🗺️ 진행 과정</h2>
        <MilestoneList milestones={payload.milestones ?? []} />
      </section>

      {/* ⑤ 막히면 이렇게 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🆘 막히면 이렇게</h2>
        {(payload.troubleshooting ?? []).map((t, i) => (
          <div key={i} style={{ marginBottom: "12px" }}>
            <p className="text-body" style={{ fontWeight: 600 }}>{t.symptom}</p>
            <p className="text-body" style={{ color: "var(--text-secondary)" }}>{t.fix}</p>
          </div>
        ))}
      </section>

      {/* ⑥ 다 됐는지 확인 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>✅ 다 됐는지 확인</h2>
        <SuccessChecklist items={payload.success_checklist ?? []} />
      </section>
    </>
  );
}
