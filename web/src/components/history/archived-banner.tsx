// "보관된 Review" 배너 (설계 결정 3) — honest-box 셸 구조 재사용, 중립 정보 톤
export function ArchivedBanner() {
  return (
    <div
      style={{
        background: "var(--surface-card-alt)",
        borderRadius: "12px",
        padding: "16px",
        borderLeft: "3px solid var(--text-secondary)",
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
        보관된 REVIEW
      </p>
      <p className="text-body">
        이 <span lang="en">Signal</span>은 보관되어 최신 정보 갱신이 중단되었습니다. 아래 내용은 결정 당시 기록입니다.
      </p>
    </div>
  );
}
