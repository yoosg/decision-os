interface SignalCardProps {
  id: string;
  title: string;
  relevanceTag: string;
  sourceCount: number;
  isSeen: boolean;
  onClick: () => void;
}

export function SignalCard({ title, relevanceTag, sourceCount, isSeen, onClick }: SignalCardProps) {
  const ariaLabel = `${title}${!isSeen ? ", NEW" : ""}, 출처 ${sourceCount}개, 읽기 약 5분`;

  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        width: "100%",
        minHeight: "44px",
        backgroundColor: "var(--surface-card)",
        borderRadius: "var(--radius-card)",
        padding: "var(--card-padding)",
        border: "none",
        cursor: "pointer",
        textAlign: "left",
        gap: "12px",
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
          <span className="text-body-card" style={{ color: "var(--text-primary)", flex: 1, minWidth: 0 }}>
            {title}
          </span>
          {!isSeen && (
            <span
              aria-hidden="true"
              lang="en"
              className="text-badge"
              style={{
                backgroundColor: "var(--accent-primary)",
                color: "var(--accent-foreground)",
                borderRadius: "var(--radius-badge)",
                padding: "2px 6px",
                flexShrink: 0,
              }}
            >
              NEW
            </span>
          )}
        </div>
        <p
          className="text-caption-lg"
          style={{
            color: "var(--text-secondary)",
            margin: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {relevanceTag}
        </p>
        <p className="text-caption" style={{ color: "var(--text-tertiary)", margin: "2px 0 0" }}>
          출처 {sourceCount}개 · 읽기 약 5분
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
        <path
          d="M6 4l4 4-4 4"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}
