"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { SignalCard } from "./signal-card";
import { ThreeDotLoading } from "./three-dot-loading";

export interface DailyBrief {
  id: string;
  user_id: string;
  brief_date: string;
  status: "pending" | "processing" | "completed" | "failed";
  error_message?: string | null;
  generated_at?: string | null;
}

export interface SignalItem {
  signalId: string;
  title: string;
  summary: string | null;
  sourceCount: number;
  position: number;
}

interface DailyBriefContentProps {
  initialBrief: DailyBrief | null;
  initialSignals: SignalItem[];
  userId: string;
}

type DailyBriefUIState =
  | { type: "generating" }
  | { type: "ready"; signals: SignalItem[] }
  | { type: "no-signals" }
  | { type: "failed" }
  | { type: "all-seen"; signals: SignalItem[] };

function getUIState(
  brief: DailyBrief | null,
  signals: SignalItem[],
  seenIds: Set<string>
): DailyBriefUIState {
  if (!brief || brief.status === "pending" || brief.status === "processing") {
    return { type: "generating" };
  }
  if (brief.status === "failed") {
    return { type: "failed" };
  }
  if (signals.length === 0) {
    return { type: "no-signals" };
  }
  if (signals.every((s) => seenIds.has(s.signalId))) {
    return { type: "all-seen", signals };
  }
  return { type: "ready", signals };
}

export function DailyBriefContent({
  initialBrief,
  initialSignals,
  userId,
}: DailyBriefContentProps) {
  const router = useRouter();
  const todayISO = new Date().toISOString().split("T")[0];
  const SEEN_KEY = `seen-signals-${todayISO}`;

  const [brief, setBrief] = useState<DailyBrief | null>(initialBrief);
  const [signals, setSignals] = useState<SignalItem[]>(initialSignals);
  const [seenIds, setSeenIds] = useState<Set<string>>(() => {
    if (typeof window === "undefined") return new Set();
    try {
      return new Set(JSON.parse(sessionStorage.getItem(SEEN_KEY) ?? "[]") as string[]);
    } catch {
      return new Set();
    }
  });
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    const supabase = createClient();

    const fetchSignals = async (briefId: string) => {
      const { data: signalRows } = await supabase
        .from("daily_brief_signals")
        .select(`signal_id, position, signals(id, title, summary)`)
        .eq("daily_brief_id", briefId)
        .order("position", { ascending: true });

      if (!signalRows || signalRows.length === 0) return;

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

      setSignals(
        signalRows.map((row) => {
          const sig = row.signals as unknown as { id: string; title: string; summary: string | null } | null;
          return {
            signalId: row.signal_id as string,
            title: sig?.title ?? "",
            summary: sig?.summary ?? null,
            sourceCount: sourceCountMap[row.signal_id as string] ?? 5,
            position: row.position as number,
          };
        })
      );
    };

    const channel = supabase
      .channel("daily-brief-home")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "daily_briefs",
          filter: `user_id=eq.${userId}&brief_date=eq.${todayISO}`,
        },
        (payload) => {
          if (payload.eventType === "DELETE") return;
          const row = payload.new as DailyBrief;
          if (row.brief_date === todayISO) {
            setBrief(row);
            if (row.status === "completed") {
              fetchSignals(row.id);
            }
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, todayISO]);

  const markSeen = (signalId: string) => {
    const next = new Set([...seenIds, signalId]);
    setSeenIds(next);
    try {
      sessionStorage.setItem(SEEN_KEY, JSON.stringify([...next]));
    } catch {
      // sessionStorage 접근 실패 시 메모리 상태만 유지
    }
  };

  const handleCardClick = (signalId: string) => {
    markSeen(signalId);
    router.push(`/home/review/${signalId}`);
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    setBrief((prev) => (prev ? { ...prev, status: "pending" } : null));
    try {
      const { data: { session } } = await createClient().auth.getSession();
      const token = session?.access_token;
      const fastapiUrl = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";
      await fetch(`${fastapiUrl}/api/v1/daily-briefs/trigger`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    } catch {
      setBrief((prev) => (prev ? { ...prev, status: "failed" } : null));
    } finally {
      setIsRetrying(false);
    }
  };

  const uiState = getUIState(brief, signals, seenIds);

  return (
    <section>
      <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "16px" }}>
        <h1 className="text-section-title">
          오늘의 AI 기술 브리핑
        </h1>
        <span className="text-caption" style={{ color: "var(--text-secondary)" }}>
          {todayISO.replace(/-/g, ".")}
        </span>
      </div>

      {uiState.type === "generating" && (
        // WCAG 2.2 AA (Story 5.4 AC-B6, 2-4 defer): 스크린리더가 생성 진행을 인지하도록 라이브 리전.
        <p
          className="text-body"
          role="status"
          aria-live="polite"
          style={{ color: "var(--text-secondary)" }}
        >
          오늘의 브리핑을 생성하는 중입니다.{" "}
          <ThreeDotLoading />
        </p>
      )}

      {uiState.type === "failed" && (
        <div>
          <p className="text-body" style={{ color: "var(--text-secondary)", marginBottom: "12px" }}>
            오늘의 브리핑을 생성하지 못했습니다.
          </p>
          <button
            type="button"
            onClick={handleRetry}
            disabled={isRetrying}
            style={{
              backgroundColor: "var(--accent-primary)",
              color: "var(--accent-foreground)",
              border: "none",
              borderRadius: "var(--radius-pill)",
              padding: "10px 20px",
              minHeight: "44px",
              cursor: isRetrying ? "not-allowed" : "pointer",
              opacity: isRetrying ? 0.6 : 1,
            }}
            className="text-label"
          >
            다시 시도하기
          </button>
        </div>
      )}

      {uiState.type === "no-signals" && (
        <div>
          <p className="text-body" style={{ color: "var(--text-secondary)", marginBottom: "12px" }}>
            오늘은 새로운 기술 소식이 없습니다. 어제{" "}
            보관함에 저장한 항목을 이어서 학습할 수 있습니다.
          </p>
          <button
            type="button"
            onClick={() => router.push("/queue")}
            style={{
              backgroundColor: "var(--accent-primary)",
              color: "var(--accent-foreground)",
              border: "none",
              borderRadius: "var(--radius-pill)",
              padding: "10px 20px",
              minHeight: "44px",
              cursor: "pointer",
            }}
            className="text-label"
          >
            보관함 보기
          </button>
        </div>
      )}

      {(uiState.type === "ready" || uiState.type === "all-seen") && (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {uiState.signals.map((signal) => (
            <SignalCard
              key={signal.signalId}
              id={signal.signalId}
              title={signal.title}
              relevanceTag={signal.summary ?? signal.title}
              sourceCount={signal.sourceCount}
              isSeen={seenIds.has(signal.signalId)}
              onClick={() => handleCardClick(signal.signalId)}
            />
          ))}
          {uiState.type === "all-seen" && (
            <p
              className="text-caption"
              style={{ color: "var(--text-secondary)", textAlign: "center", marginTop: "4px" }}
            >
              오늘 브리핑을 모두 확인했습니다.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
