export type QueueTiming = "today" | "this_week" | "later";

interface QueueItemProps {
  title: string;
  queueTiming: QueueTiming;
  estimatedMinutes: number;
  isOverdue: boolean;
  onTap: () => void;
  onReschedule: () => void;
}

function timingLabelEn(timing: QueueTiming): string {
  return { today: "Today", this_week: "This Week", later: "Later" }[timing];
}

export function QueueItem({
  title,
  queueTiming,
  estimatedMinutes,
  isOverdue,
  onTap,
  onReschedule,
}: QueueItemProps) {
  const label = timingLabelEn(queueTiming);
  // WCAG 2.2 AA (Story 5.4 AC-B2): 미완료(overdue) 상태는 색상 배지(aria-hidden)만이 아니라
  // composite label에도 포함하여 스크린리더가 인지하도록 함.
  const ariaLabel = `${label} 예약됨, ${title}, 약 ${estimatedMinutes}분${isOverdue ? ", 미완료" : ""}`;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        minHeight: "44px",
        backgroundColor: "var(--surface-card)",
        borderRadius: "var(--radius-card)",
        padding: "var(--card-padding)",
      }}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        onClick={onTap}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "6px",
          width: "100%",
          minHeight: "44px",
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            aria-hidden="true"
            lang="en"
            className="text-badge"
            style={{
              backgroundColor: "var(--surface-card-alt)",
              color: "var(--text-secondary)",
              borderRadius: "var(--radius-badge)",
              padding: "2px 6px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            {label}
          </span>
          {isOverdue && (
            <span
              aria-hidden="true"
              className="text-badge"
              style={{ color: "var(--status-warning)", background: "transparent" }}
            >
              미완료
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "8px" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p className="text-body-card" style={{ margin: 0, color: "var(--text-primary)" }}>
              {title}
            </p>
            <p className="text-caption" style={{ margin: "2px 0 0", color: "var(--text-secondary)" }}>
              약 {estimatedMinutes}분
            </p>
          </div>
          <svg
            aria-hidden="true"
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            style={{ flexShrink: 0, color: "var(--text-tertiary)" }}
          >
            <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </button>
      <button
        type="button"
        aria-label={`일정 변경 — ${title}`}
        onClick={onReschedule}
        style={{
          alignSelf: "flex-start",
          minHeight: "44px",
          display: "flex",
          alignItems: "center",
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          fontSize: "12px",
          color: "var(--text-secondary)",
          textDecoration: "underline",
        }}
      >
        일정 변경
      </button>
    </div>
  );
}
