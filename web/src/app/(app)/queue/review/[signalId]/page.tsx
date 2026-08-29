import type { Metadata } from "next";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { ReviewPageContent } from "@/components/home/review/review-page-content";
import type { ReviewPayload } from "@/components/home/review/research-review-content";
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
  const { data: reviewRow, error } = await supabase
    .from("reviews")
    .select("id, status, result, bar_gate_override, signals(title)")
    .eq("signal_id", signalId)
    .eq("playbook_type", "ai_research")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) console.error("[ReviewPage] Supabase error:", error);

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
      reviewType: ((reviewRow.result?.review_type as ReviewType | undefined) ?? null),
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
