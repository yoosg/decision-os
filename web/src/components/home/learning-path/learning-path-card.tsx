export interface LearningPathResource {
  type: "official_docs" | "core_material" | "github" | "practice_example" | "applied_idea" | string;
  title: string;
  url: string;
  descriptor: string;
  objective?: string;
  is_search_fallback?: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  official_docs: "공식 문서",
  core_material: "핵심 자료",
  github: "GitHub",
  practice_example: "실습 예제",
  applied_idea: "적용 아이디어",
};

interface LearningPathCardProps {
  resource: LearningPathResource;
  onVisit: () => void;
}

function isSafeExternalUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function LearningPathCard({ resource, onVisit }: LearningPathCardProps) {
  const label = TYPE_LABELS[resource.type] ?? resource.type;
  const hasUrl = Boolean(resource.url) && isSafeExternalUrl(resource.url);
  const isEnglishLabel = resource.type === "github";
  const isSearchFallback = Boolean(resource.is_search_fallback);

  const handleClick = () => {
    if (!hasUrl) return;
    window.open(resource.url, "_blank", "noopener noreferrer");
    onVisit();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={!hasUrl}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        backgroundColor: "var(--surface-card)",
        borderRadius: "var(--radius-card)",
        padding: "var(--card-padding)",
        border: "none",
        cursor: hasUrl ? "pointer" : "default",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <span
            className="text-badge"
            lang={isEnglishLabel ? "en" : undefined}
            style={{ color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}
          >
            {label}
          </span>
          <p style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
            {resource.title}
          </p>
          {resource.descriptor && (
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
              {resource.descriptor}
            </p>
          )}
          {resource.objective && (
            <p style={{ fontSize: "13px", color: "var(--text-tertiary)", margin: "6px 0 0" }}>
              이 단계에서: {resource.objective}
            </p>
          )}
        </div>
        {hasUrl &&
          (isSearchFallback ? (
            <span
              style={{
                flexShrink: 0,
                whiteSpace: "nowrap",
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--text-tertiary)",
              }}
            >
              🔍 검색으로 찾기
            </span>
          ) : (
            <svg
              aria-hidden="true"
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              style={{ flexShrink: 0, color: "var(--text-tertiary)" }}
            >
              <path
                d="M5.5 2.5H2.5C1.94772 2.5 1.5 2.94772 1.5 3.5V11.5C1.5 12.0523 1.94772 12.5 2.5 12.5H10.5C11.0523 12.5 11.5 12.0523 11.5 11.5V8.5"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M8 1.5H12.5V6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M12.5 1.5L6.5 7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ))}
      </div>
    </button>
  );
}
