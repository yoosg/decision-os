"use client";

// 값(OUTCOME_OPTIONS)은 client 경계 밖 plain 모듈 `outcome-options.ts`에서 직접 import할 것.
// ("use client" 모듈이 값을 재-export하면 Server Component 소비 시 client-reference 프록시가 되어 크래시)
import { type OutcomeStatus } from "./outcome-options";

interface Props {
  status: OutcomeStatus;
  englishLabel: string;
  koreanLabel: string;
  isSelected: boolean;
  onSelect: (status: OutcomeStatus) => void;
}

export function OutcomeCard({ status, englishLabel, koreanLabel, isSelected, onSelect }: Props) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={isSelected}
      aria-label={`${englishLabel} — ${koreanLabel}`}
      onClick={() => onSelect(status)}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        background: "var(--surface-card)",
        borderRadius: "14px",
        padding: "16px",
        minHeight: "52px",
        border: isSelected
          ? "1.5px solid var(--accent-primary)"
          : "1px solid var(--border-card)",
        cursor: "pointer",
        fontSize: "15px",
        fontWeight: 500,
        color: "var(--text-primary)",
      }}
    >
      {koreanLabel}
    </button>
  );
}
