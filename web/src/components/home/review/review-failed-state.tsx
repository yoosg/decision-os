import Link from "next/link";

interface ReviewFailedStateProps {
  onRetry: () => void;
}

export function ReviewFailedState({ onRetry }: ReviewFailedStateProps) {
  return (
    <div className="screen-container" style={{ paddingTop: "24px" }}>
      <p className="text-body" style={{ marginBottom: "16px" }}>
        리뷰를 생성하지 못했습니다.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "flex-start" }}>
        <button
          onClick={onRetry}
          className="btn-primary"
          style={{ padding: "12px 24px", borderRadius: "9999px" }}
        >
          다시 시도하기
        </button>
        <Link
          href="/home"
          className="text-label"
          style={{ color: "var(--text-secondary)" }}
        >
          홈으로 돌아가기
        </Link>
      </div>
    </div>
  );
}
