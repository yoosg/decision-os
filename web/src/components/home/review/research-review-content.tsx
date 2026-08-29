"use client";

import Link from "next/link";
import { ContextStickyBar } from "./context-sticky-bar";
import { ReviewSections, type ReviewPayload } from "./review-sections";
import { BackLink } from "@/components/ui/back-link";

// 하위 호환: 기존 import 경로 유지 (queue/home review page, review-page-content)
export type { ReviewPayload };

interface Props {
  signalId: string;
  signalTitle: string;
  payload: ReviewPayload;
  reviewId: string;
  barGateOverride?: string | null;
}

export function ResearchReviewContent({ signalId, signalTitle, payload, reviewId, barGateOverride }: Props) {
  return (
    <div className="screen-container" style={{ paddingTop: "24px", paddingBottom: "144px" }}>
      <BackLink href="/home">홈으로</BackLink>

      <h1 className="text-screen-title" style={{ marginBottom: "24px" }}>
        {signalTitle}
      </h1>

      <ReviewSections payload={payload} />

      <Link
        href={`/home/review/${signalId}/chat`}
        className="text-body"
        style={{
          fontSize: "13px",
          color: "var(--text-secondary)",
          textDecoration: "underline",
          display: "block",
          marginBottom: "8px",
        }}
      >
        AI에게 질문하기
      </Link>

      <ContextStickyBar
        signalId={signalId}
        reviewId={reviewId}
        barGateOverride={barGateOverride}
        recommendationReason={payload.recommendation_reason}
      />
    </div>
  );
}
