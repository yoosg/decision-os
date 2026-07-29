import Link from "next/link";
import { ThreeDotLoading } from "@/components/home/three-dot-loading";

export function ReviewGeneratingState() {
  return (
    <div className="screen-container" style={{ paddingTop: "24px" }}>
      <p className="text-body" style={{ color: "var(--text-secondary)", marginBottom: "16px" }}>
        리뷰를 생성하는 중입니다. 앱을 닫아도 됩니다.{" "}
        <ThreeDotLoading />
      </p>
      <Link
        href="/home"
        className="text-label"
        style={{ color: "var(--text-secondary)" }}
      >
        홈으로 돌아가기
      </Link>
    </div>
  );
}
