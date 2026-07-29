"use client";

import Link from "next/link";
import { ContextStickyBar } from "./context-sticky-bar";
import { ReviewSections, type ReviewPayload } from "./review-sections";

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
      <Link
        href="/home"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          color: "var(--text-secondary)",
          marginBottom: "20px",
        }}
        className="text-label"
      >
        <svg
          aria-hidden="true"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
        >
          <path
            d="M10 4L6 8l4 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        홈으로
      </Link>

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
