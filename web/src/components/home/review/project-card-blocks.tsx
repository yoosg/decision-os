"use client";

import { useState } from "react";
import type { CardProgress } from "./use-card-progress";

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

export const CARD_DIFFICULTY_DOTS: Record<ProjectCardPayload["difficulty"], string> = {
  first_step: "●○○",
  basic: "●●○",
  challenge: "●●●",
};

export function ProjectCardMeta({ payload }: { payload: ProjectCardPayload }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", marginBottom: "20px" }}>
      <span
        className="text-label"
        style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: "var(--surface-card, #F2F2F2)", borderRadius: "9999px", padding: "4px 12px" }}
      >
        {CARD_DIFFICULTY_LABEL[payload.difficulty]}
        <span aria-hidden="true" style={{ letterSpacing: "1px", fontSize: "11px" }}>
          {CARD_DIFFICULTY_DOTS[payload.difficulty]}
        </span>
      </span>
      <span className="text-label" style={{ color: "var(--text-secondary)" }}>
        ⏱ {payload.estimated_minutes}분 · 🎓 {payload.skill_label}
      </span>
    </div>
  );
}

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

function CheckableList<T>({
  items,
  checked,
  onToggle,
  renderLabel,
  header,
}: {
  items: T[];
  checked: Set<number>;
  onToggle: (i: number) => void;
  renderLabel: (item: T) => React.ReactNode;
  header?: React.ReactNode;
}) {
  return (
    <div>
      {header}
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {items.map((item, i) => (
          <li key={i} style={{ marginBottom: "12px" }}>
            <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={checked.has(i)}
                onChange={() => onToggle(i)}
                style={{ marginTop: "3px" }}
              />
              <span>{renderLabel(item)}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MilestoneList({
  milestones,
  checked,
  onToggle,
}: {
  milestones: ProjectCardPayload["milestones"];
  checked: Set<number>;
  onToggle: (i: number) => void;
}) {
  return (
    <CheckableList
      items={milestones}
      checked={checked}
      onToggle={onToggle}
      header={
        <p className="text-label" style={{ color: "var(--text-secondary)", marginBottom: "8px" }}>
          {checked.size}/{milestones.length}
        </p>
      }
      renderLabel={(m) => (
        <>
          <span className="text-body" style={{ display: "block" }}>{m.action}</span>
          <span className="text-body" style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
            끝나면: {m.done_signal}
          </span>
        </>
      )}
    />
  );
}

function SuccessChecklist({
  items,
  checked,
  onToggle,
}: {
  items: string[];
  checked: Set<number>;
  onToggle: (i: number) => void;
}) {
  return (
    <CheckableList
      items={items}
      checked={checked}
      onToggle={onToggle}
      renderLabel={(it) => <span className="text-body">{it}</span>}
    />
  );
}

export function ProjectCardBlocks({
  payload,
  progress,
}: {
  payload: ProjectCardPayload;
  progress?: CardProgress;
}) {
  // 로컬 폴백(progress 미제공 시). 훅은 항상 무조건 호출.
  const localMilestones = useCheckedSet();
  const localChecklist = useCheckedSet();

  const milestoneChecked = progress ? progress.milestonesChecked : localMilestones.checked;
  const milestoneToggle = progress ? progress.toggleMilestone : localMilestones.toggle;
  const checklistChecked = progress ? progress.checklistChecked : localChecklist.checked;
  const checklistToggle = progress ? progress.toggleChecklist : localChecklist.toggle;

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
        <MilestoneList
          milestones={payload.milestones ?? []}
          checked={milestoneChecked}
          onToggle={milestoneToggle}
        />
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
        <SuccessChecklist
          items={payload.success_checklist ?? []}
          checked={checklistChecked}
          onToggle={checklistToggle}
        />
      </section>
    </>
  );
}
