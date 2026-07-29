import type { Metadata } from "next";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { kstDateString } from "@/lib/kst";
import { QueueContent, type QueueItemData, type QueueGroups } from "@/components/queue/queue-content";

export const metadata: Metadata = { title: "큐 | Decision OS" };

const TIMINGS = ["today", "this_week", "later"] as const;

export default async function QueuePage() {
  const supabase = await createServerSupabaseClient();
  const { data: userData } = await supabase.auth.getUser();
  const userId = userData.user?.id ?? "";

  const { data: decisionRows } = await supabase
    .from("decisions")
    .select("id, queue_timing, updated_at, reviews(signal_id, signals(title))")
    .eq("choice", "queue")
    .order("created_at", { ascending: true });

  const { data: profileRow } = await supabase
    .from("user_profiles")
    .select("daily_learning_time_min")
    .eq("id", userId)
    .maybeSingle();

  const estimatedMinutes = profileRow?.daily_learning_time_min ?? 30;
  const todayKST = kstDateString(new Date().toISOString());

  const groups: QueueGroups = { today: [], this_week: [], later: [] };

  for (const row of decisionRows ?? []) {
    const review = row.reviews as unknown as {
      signal_id: string;
      signals: { title: string } | null;
    } | null;
    const queueTiming = row.queue_timing as (typeof TIMINGS)[number];
    if (!review || !TIMINGS.includes(queueTiming)) continue;

    const item: QueueItemData = {
      decisionId: row.id as string,
      signalId: review.signal_id,
      title: review.signals?.title ?? "",
      queueTiming,
      isOverdue:
        queueTiming === "today" &&
        kstDateString(row.updated_at as string) < todayKST,
    };
    groups[queueTiming].push(item);
  }

  return (
    <div className="screen-container" style={{ paddingTop: "24px" }}>
      <QueueContent groups={groups} estimatedMinutes={estimatedMinutes} />
    </div>
  );
}
