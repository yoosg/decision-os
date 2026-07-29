interface Props {
  content: string;
  severity: "standard" | "high";
}

export function HonestBox({ content, severity }: Props) {
  return (
    <div
      style={{
        background: "var(--surface-honest-box)",
        borderRadius: "12px",
        padding: "16px",
        borderLeft:
          severity === "high"
            ? "3px solid var(--status-warning)"
            : undefined,
      }}
    >
      <p
        style={{
          fontSize: "11px",
          textTransform: "uppercase",
          fontWeight: 700,
          color: "var(--text-secondary)",
          marginBottom: "8px",
        }}
      >
        {/* WCAG 2.2 AA (Story 5.4 AC-B2): high severity를 색상(border)만으로 전달하지 않도록
            도형 기반 글리프(⚠) 병행 — 색맹/스크린리더 사용자도 구분 가능 */}
        {severity === "high" && (
          <>
            <span aria-hidden="true">⚠</span>{" "}
            <span
              style={{
                position: "absolute",
                width: "1px",
                height: "1px",
                padding: 0,
                margin: "-1px",
                overflow: "hidden",
                clip: "rect(0,0,0,0)",
                whiteSpace: "nowrap",
                border: 0,
              }}
            >
              주의 필요:{" "}
            </span>
          </>
        )}
        AI가 놓쳤을 수 있는 점
      </p>
      <p className="text-body">{content}</p>
    </div>
  );
}
