import type { Metadata } from "next";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { ReviewPageContent } from "@/components/home/review/review-page-content";
import type { ReviewPayload } from "@/components/home/review/research-review-content";
import { toReviewType } from "@/components/home/review/review-types";
import type { ReviewType } from "@/components/home/review/review-types";

export const metadata: Metadata = { title: "리뷰 | Decision OS" };

export type InitialReview = {
  id: string;
  status: string;
  signalTitle: string;
  payload?: ReviewPayload;
  barGateOverride?: string | null;
  reviewType?: ReviewType | null;
} | null;

export default async function ReviewPage({
  params,
}: {
  params: Promise<{ signalId: string }>;
}) {
  const { signalId } = await params;

  const supabase = await createServerSupabaseClient();
  // 한 signal에 리뷰 행이 여러 개일 수 있다(재시도 등). "최신 1개"만 집으면 최신 행이
  // failed일 때 멀쩡한 completed를 무시하고 실패로 표시 → 불필요한 재트리거·중복 생성까지
  // 유발한다. 그래서 completed가 있으면 그걸 우선하고, 없을 때만 최신 행을 쓴다.
  // (RLS로 현재 사용자 소유 리뷰만 조회됨)
  const { data: reviewRows, error } = await supabase
    .from("reviews")
    .select("id, status, result, bar_gate_override, signals(title)")
    .eq("signal_id", signalId)
    .eq("playbook_type", "ai_research")
    .order("created_at", { ascending: false })
    .limit(10);

  if (error) console.error("[ReviewPage] Supabase error:", error);

  const reviewRow =
    reviewRows?.find((r) => r.status === "completed") ?? reviewRows?.[0] ?? null;

  const signalsRaw = (reviewRow?.signals as unknown) as Record<string, unknown> | null;
  const signalTitle = typeof signalsRaw?.title === "string" ? signalsRaw.title : "";

  let initialReview: InitialReview = null;
  if (reviewRow) {
    const payload = reviewRow.result?.payload as ReviewPayload | undefined;
    initialReview = {
      id: reviewRow.id as string,
      status: reviewRow.status as string,
      signalTitle,
      payload,
      barGateOverride: reviewRow.bar_gate_override as string | null | undefined,
      reviewType: toReviewType(reviewRow.result?.review_type),
    };
  }

  return (
    <ReviewPageContent
      signalId={signalId}
      signalTitle={signalTitle}
      initialReview={initialReview}
    />
  );
}
