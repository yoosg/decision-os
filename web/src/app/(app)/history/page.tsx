import type { Metadata } from "next";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { HistoryContent, type HistoryItemData } from "@/components/history/history-content";
import type { OutcomeStatus } from "@/components/home/outcome/outcome-options";

export const metadata: Metadata = { title: "히스토리 | Decision OS" };

const CHOICES = ["learn_now", "queue", "ignore"] as const;

type OutcomeRow = { status: string; created_at: string };

export default async function HistoryPage() {
  const supabase = await createServerSupabaseClient();
  // userId 는 직접 필터에 쓰지 않음 — RLS(decisions_select/outcomes_select)가 자동 필터링 (AD-3/AD-9)
  await supabase.auth.getUser();

  const { data } = await supabase
    .from("decisions")
    .select(`
      id, choice, created_at,
      reviews!inner ( signal_id, signals ( id, title, status ) ),
      outcomes ( status, created_at )
    `)
    .order("created_at", { ascending: false });

  const items: HistoryItemData[] = [];
  for (const row of data ?? []) {
    const choice = row.choice as (typeof CHOICES)[number];
    if (!CHOICES.includes(choice)) continue;

    const review = row.reviews as unknown as {
      signal_id: string;
      signals: { id: string; title: string; status: string } | null;
    } | null;
    if (!review?.signals) continue;

    // outcomes 는 1:N 임베드 → 배열. 최신 1건만 사용 (설계 결정 2)
    const outcomeRows = (row.outcomes as unknown as OutcomeRow[] | null) ?? [];
    const latestOutcome = outcomeRows
      .slice()
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];

    items.push({
      decisionId: row.id as string,
      signalId: review.signal_id,
      title: review.signals.title,
      choice,
      outcomeStatus: (latestOutcome?.status as OutcomeStatus | undefined) ?? null,
      createdAt: row.created_at as string,
    });
  }

  return (
    <div className="screen-container" style={{ paddingTop: "24px" }}>
      <h1 className="text-section-title" style={{ marginBottom: "20px" }}>
        히스토리
      </h1>
      <HistoryContent items={items} />
    </div>
  );
}
