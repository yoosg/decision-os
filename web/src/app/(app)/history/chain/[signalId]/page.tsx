import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { ChainDetailContent, type ChainDetailData } from "@/components/history/chain-detail-content";
import type { ReviewPayload } from "@/components/home/review/review-sections";
import type { OutcomeStatus } from "@/components/home/outcome/outcome-options";
import type { DecisionChoice } from "@/components/history/memory-timeline-item";

export const metadata: Metadata = { title: "체인 상세 | Decision OS" };

export default async function ChainDetailPage({
  params,
}: {
  params: Promise<{ signalId: string }>;
}) {
  const { signalId } = await params;
  const supabase = await createServerSupabaseClient();

  // 1. Signal
  const { data: signalData } = await supabase
    .from("signals")
    .select("id, title, status")
    .eq("id", signalId)
    .maybeSingle();
  const signal = signalData as unknown as { id: string; title: string; status: string } | null;
  if (!signal) notFound();

  // 2. Review (완료된 최신 1건)
  const { data: reviewData } = await supabase
    .from("reviews")
    .select("id, status, result, created_at")
    .eq("signal_id", signalId)
    .eq("status", "completed")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  const reviewRow = reviewData as unknown as {
    id: string;
    result: { payload?: ReviewPayload } | null;
  } | null;

  // 3. Decision (review 있을 때만, 최신 1건, choice 필터 없음)
  let decisionRow: { id: string; choice: string; created_at: string } | null = null;
  if (reviewRow) {
    const { data } = await supabase
      .from("decisions")
      .select("id, choice, queue_timing, created_at")
      .eq("review_id", reviewRow.id)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    decisionRow = data as unknown as { id: string; choice: string; created_at: string } | null;
  }

  // 4. Outcome (decision 있을 때만, 최신 1건)
  type OutcomeRow = {
    status: string;
    useful: boolean | null;
    actual_learning_time_min: number | null;
    applied_project_note: string | null;
    memo: string | null;
    created_at: string;
  };
  let outcomeRow: OutcomeRow | null = null;
  if (decisionRow) {
    const { data } = await supabase
      .from("outcomes")
      .select("id, status, useful, actual_learning_time_min, applied_project_note, memo, created_at")
      .eq("decision_id", decisionRow.id)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    outcomeRow = data as unknown as OutcomeRow | null;
  }

  const payload = reviewRow?.result?.payload as ReviewPayload | undefined;

  const data: ChainDetailData = {
    signal: {
      id: signal.id as string,
      title: signal.title as string,
      status: signal.status as string,
    },
    review: payload ? { payload } : null,
    decision: decisionRow
      ? { choice: decisionRow.choice as DecisionChoice, createdAt: decisionRow.created_at }
      : null,
    outcome: outcomeRow
      ? {
          status: outcomeRow.status as OutcomeStatus,
          useful: outcomeRow.useful,
          actualLearningTimeMin: outcomeRow.actual_learning_time_min,
          appliedProjectNote: outcomeRow.applied_project_note,
          memo: outcomeRow.memo,
          createdAt: outcomeRow.created_at,
        }
      : null,
  };

  return <ChainDetailContent data={data} />;
}
