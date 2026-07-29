import { OUTCOME_OPTIONS, type OutcomeStatus } from "@/components/home/outcome/outcome-options";
import { formatCardDate } from "@/lib/kst";

export type DecisionChoice = "learn_now" | "queue" | "ignore";

export type DotStyle =
  | { kind: "decision"; choice: DecisionChoice }
  | { kind: "outcome"; status: OutcomeStatus }
  | { kind: "outcome-pending" };

interface Props {
  title: string;
  dateISO: string;
  dotStyle: DotStyle;
  onTap: () => void;
}

// Outcome 도트 색상/글리프 (AC-2) — 라벨 문자열은 OUTCOME_OPTIONS 재사용
const OUTCOME_DOT_COLOR: Record<OutcomeStatus, string> = {
  completed: "var(--status-positive)",
  applied: "var(--status-positive)",
  dropped: "var(--text-primary)",
  not_useful: "var(--text-secondary)",
};
const OUTCOME_DOT_GLYPH: Record<OutcomeStatus, string> = {
  completed: "✓",
  applied: "→",
  dropped: "✕",
  not_useful: "−",
};

// Decision 스타일 type label (context-sticky-bar 버튼 라벨과 동일 영문 표기)
export const DECISION_TYPE_LABEL: Record<DecisionChoice, string> = {
  learn_now: "LEARN NOW",
  queue: "QUEUE",
  ignore: "IGNORE",
};

export function outcomeEnglishLabel(status: OutcomeStatus): string {
  return OUTCOME_OPTIONS.find((o) => o.status === status)?.englishLabel ?? status;
}

// 도트 색상/글리프 — Chain 상세 화면과 공유하는 시각 언어 (AC-2)
export function dotVisual(dotStyle: DotStyle): { color: string; glyph: string | null } {
  if (dotStyle.kind === "outcome") {
    return { color: OUTCOME_DOT_COLOR[dotStyle.status], glyph: OUTCOME_DOT_GLYPH[dotStyle.status] };
  }
  if (dotStyle.kind === "outcome-pending") {
    return { color: "var(--text-secondary)", glyph: "?" };
  }
  return { color: "var(--text-primary)", glyph: null };
}

export function MemoryTimelineItem({ title, dateISO, dotStyle, onTap }: Props) {
  const { color: dotColor, glyph } = dotVisual(dotStyle);
  let typeLabel: string;
  let ariaLabel: string;

  if (dotStyle.kind === "outcome") {
    const en = outcomeEnglishLabel(dotStyle.status);
    typeLabel = en.toUpperCase();
    // AC-2: Outcome 도트만 composite label (glyph 은 aria-hidden)
    ariaLabel = `${en} 결과 — ${title}`;
  } else if (dotStyle.kind === "outcome-pending") {
    typeLabel = "IN PROGRESS";
    ariaLabel = `미완료 결과 — ${title}`;
  } else {
    // Decision 스타일은 글리프 없음, 텍스트 라벨로 정보 전달
    typeLabel = DECISION_TYPE_LABEL[dotStyle.choice];
    ariaLabel = `${title}`;
  }

  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={onTap}
      style={{
        display: "flex",
        alignItems: "stretch",
        gap: "12px",
        width: "100%",
        minHeight: "44px",
        background: "transparent",
        border: "none",
        padding: 0,
        paddingBottom: "10px",
        cursor: "pointer",
        textAlign: "left",
        position: "relative",
      }}
    >
      {/* 좌측 spine + 도트 */}
      <span
        aria-hidden="true"
        style={{ position: "relative", width: "12px", flexShrink: 0 }}
      >
        {/* 2px spine */}
        <span
          style={{
            position: "absolute",
            left: "5px",
            top: 0,
            bottom: 0,
            width: "2px",
            background: "var(--border-subtle)",
          }}
        />
        {/* 12px 도트 */}
        <span
          style={{
            position: "absolute",
            left: 0,
            top: "14px",
            width: "12px",
            height: "12px",
            borderRadius: "9999px",
            background: dotColor,
            border: "2px solid var(--surface-base)",
            boxSizing: "content-box",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#FFFFFF",
            fontSize: "9px",
            lineHeight: 1,
            fontWeight: 700,
          }}
        >
          {glyph}
        </span>
      </span>

      {/* 카드 (AC-3) */}
      <span
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          background: "var(--surface-card)",
          borderRadius: "12px",
          padding: "12px 14px",
        }}
      >
        <span
          lang="en"
          className="text-badge"
          style={{ color: "var(--text-secondary)" }}
        >
          {typeLabel}
        </span>
        <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
          {title}
        </span>
        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          {formatCardDate(dateISO)}
        </span>
      </span>
    </button>
  );
}
