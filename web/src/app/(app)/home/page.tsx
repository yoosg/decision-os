import type { Metadata } from "next";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { kstToday } from "@/lib/date";
import {
  DailyBriefContent,
  type DailyBrief,
  type SignalItem,
} from "@/components/home/daily-brief-content";

export const metadata: Metadata = { title: "홈 | Decision OS" };

export default async function HomePage() {
  const supabase = await createServerSupabaseClient();
  const { data: userData } = await supabase.auth.getUser();
  const userId = userData.user?.id ?? "";
  const todayISO = kstToday();

  let brief: DailyBrief | null = null;
  let signals: SignalItem[] = [];

  const { data: briefData } = await supabase
    .from("daily_briefs")
    .select("id, user_id, brief_date, status, error_message, generated_at")
    .eq("user_id", userId)
    .eq("brief_date", todayISO)
    .order("generated_at", { ascending: false })
    .limit(1)
    .single();

  if (briefData) {
    brief = briefData as DailyBrief;

    if (brief.status === "completed") {
      const { data: signalRows } = await supabase
        .from("daily_brief_signals")
        .select(`
          signal_id,
          position,
          relevance_score,
          signals (
            id,
            title,
            technology_name,
            summary
          )
        `)
        .eq("daily_brief_id", brief.id)
        .order("position", { ascending: true });

      if (signalRows && signalRows.length > 0) {
        const signalIds = signalRows.map((r) => r.signal_id as string);

        const { data: sourcesData } = await supabase
          .from("signal_sources")
          .select("signal_id")
          .in("signal_id", signalIds);

        const sourceCountMap: Record<string, number> = {};
        for (const row of sourcesData ?? []) {
          const sid = row.signal_id as string;
          sourceCountMap[sid] = (sourceCountMap[sid] ?? 0) + 1;
        }

        signals = signalRows.map((row) => {
          const sig = row.signals as unknown as { id: string; title: string; summary: string | null } | null;
          return {
            signalId: row.signal_id as string,
            title: sig?.title ?? "",
            summary: sig?.summary ?? null,
            sourceCount: sourceCountMap[row.signal_id as string] ?? 5,
            position: row.position as number,
          };
        });
      }
    }
  }

  return (
    <div className="screen-container" style={{ paddingTop: "24px" }}>
      <DailyBriefContent
        initialBrief={brief}
        initialSignals={signals}
        userId={userId}
      />
    </div>
  );
}
