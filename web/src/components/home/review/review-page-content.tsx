"use client";

import { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase";
import { API_BASE_URL } from "@/lib/api-config";
import { getAccessToken } from "@/lib/api";
import { trackEngagement } from "@/lib/engagement";
import { ResearchReviewContent } from "./research-review-content";
import type { ReviewPayload } from "./research-review-content";
import { ProjectCardContent } from "./project-card-content";
import type { ProjectCardPayload } from "./project-card-blocks";
import { ReviewGeneratingState } from "./review-generating-state";
import { ReviewFailedState } from "./review-failed-state";
import { toReviewType } from "./review-types";
import type { ReviewType } from "./review-types";

type ReviewUIState =
  | { type: "completed"; reviewId: string; payload: ReviewPayload | ProjectCardPayload; signalTitle: string; barGateOverride?: string | null; reviewType?: ReviewType | null }
  | { type: "generating" }
  | { type: "failed" };

type InitialReview = {
  id: string;
  status: string;
  signalTitle: string;
  payload?: ReviewPayload;
  barGateOverride?: string | null;
  reviewType?: ReviewType | null;
} | null;

interface ReviewPageContentProps {
  signalId: string;
  signalTitle: string;
  initialReview: InitialReview;
}

export function ReviewPageContent({ signalId, signalTitle, initialReview }: ReviewPageContentProps) {
  const [uiState, setUIState] = useState<ReviewUIState>(() => {
    if (initialReview?.status === "completed" && initialReview.payload) {
      return {
        type: "completed",
        reviewId: initialReview.id,
        payload: initialReview.payload,
        signalTitle: initialReview.signalTitle,
        barGateOverride: initialReview.barGateOverride,
        reviewType: initialReview.reviewType,
      };
    }
    return { type: "generating" };
  });

  const reviewIdRef = useRef<string | null>(
    initialReview?.status === "pending" || initialReview?.status === "processing"
      ? initialReview.id
      : null
  );
  const cleanupRef = useRef<(() => void) | undefined>(undefined);
  const retryInFlightRef = useRef(false); // P9: 동시 retry 방지
  const openTrackedSignalRef = useRef<string | null>(null); // 6.5: signalId별 open 1회

  // Story 6.5: review-page 진입 시 open engagement 1회 전송(fire-and-forget).
  // signalId 단위 가드 — 같은 signalId는 StrictMode 이중 마운트/재렌더에도 중복 전송 안 하고,
  // signalId가 바뀌면(리마운트 없이 리렌더되는 경우 포함) 새 시그널의 open을 정상 전송한다.
  useEffect(() => {
    if (openTrackedSignalRef.current === signalId) return;
    openTrackedSignalRef.current = signalId;
    trackEngagement([{ signal_id: signalId, event_type: "open" }]);
  }, [signalId]);

  // P7: async 제거 — cleanup 함수를 동기적으로 반환하여 unmount race 방지
  const triggerAndSubscribe = (reviewId: string) => {
    const supabase = createClient();
    const channel = supabase
      .channel(`review-${reviewId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "reviews",
          filter: `id=eq.${reviewId}`,
        },
        async (payload) => {
          const row = payload.new as { status: string };
          if (row.status === "completed") {
            // P2: bar_gate_override 유실 방지 — 항상 재조회하여 barGateOverride 정확히 반영
            const { data } = await supabase
              .from("reviews")
              .select("result, bar_gate_override")
              .eq("id", reviewId)
              .single();
            const fetched = data?.result?.payload as ReviewPayload | ProjectCardPayload | undefined;
            if (fetched) {
              setUIState({
                type: "completed",
                reviewId: reviewIdRef.current ?? reviewId,
                payload: fetched,
                signalTitle,
                barGateOverride: data?.bar_gate_override as string | null,
                reviewType: toReviewType(data?.result?.review_type),
              });
            } else {
              setUIState({ type: "failed" });
            }
          }
          if (row.status === "failed") {
            setUIState({ type: "failed" });
          }
        }
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  };

  const triggerAPI = async (): Promise<string | null> => {
    const token = await getAccessToken();
    const res = await fetch(`${API_BASE_URL}/api/v1/reviews/trigger`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ signal_id: signalId }),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json?.data?.review_id as string) ?? null;
  };

  useEffect(() => {
    const init = async () => {
      if (initialReview?.status === "completed") {
        return;
      }

      if (
        initialReview?.status === "pending" ||
        initialReview?.status === "processing"
      ) {
        cleanupRef.current = triggerAndSubscribe(initialReview.id); // P7: await 제거
        return;
      }

      // null 또는 failed — trigger API 호출
      setUIState({ type: "generating" });
      try {
        const reviewId = await triggerAPI();
        if (!reviewId) {
          setUIState({ type: "failed" });
          return;
        }
        reviewIdRef.current = reviewId;
        cleanupRef.current = triggerAndSubscribe(reviewId); // P7: await 제거
      } catch {
        setUIState({ type: "failed" });
      }
    };

    init();
    return () => { cleanupRef.current?.(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signalId]);

  const handleRetry = async () => {
    if (retryInFlightRef.current) return; // P9: 동시 retry 방지
    retryInFlightRef.current = true;
    cleanupRef.current?.();
    cleanupRef.current = undefined;
    setUIState({ type: "generating" });
    try {
      const reviewId = await triggerAPI();
      if (!reviewId) {
        setUIState({ type: "failed" });
        return;
      }
      reviewIdRef.current = reviewId;
      cleanupRef.current = triggerAndSubscribe(reviewId); // P7: await 제거
    } catch {
      setUIState({ type: "failed" });
    } finally {
      retryInFlightRef.current = false; // P9
    }
  };

  if (uiState.type === "completed") {
    if (uiState.reviewType === "project_card") {
      return (
        <ProjectCardContent
          signalId={signalId}
          signalTitle={uiState.signalTitle}
          payload={uiState.payload as ProjectCardPayload}
          reviewId={uiState.reviewId}
        />
      );
    }
    return (
      <ResearchReviewContent
        signalId={signalId}
        signalTitle={uiState.signalTitle}
        payload={uiState.payload as ReviewPayload}
        reviewId={uiState.reviewId}
        barGateOverride={uiState.barGateOverride}
      />
    );
  }

  if (uiState.type === "failed") {
    return <ReviewFailedState onRetry={handleRetry} />;
  }

  return <ReviewGeneratingState />;
}
