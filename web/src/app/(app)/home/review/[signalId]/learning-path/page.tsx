"use client";

import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { ThreeDotLoading } from "@/components/home/three-dot-loading";
import { LearningPathCard, type LearningPathResource } from "@/components/home/learning-path/learning-path-card";

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";

type UIState =
  | { type: "generating" }
  | { type: "ready"; resources: LearningPathResource[]; goal?: string }
  | { type: "failed" };

export default function LearningPathPage({ params }: { params: Promise<{ signalId: string }> }) {
  const { signalId } = use(params);
  const router = useRouter();

  const [uiState, setUIState] = useState<UIState>({ type: "generating" });
  const [signalTitle, setSignalTitle] = useState("");
  const [hasVisitedExternal, setHasVisitedExternal] = useState(false);
  const [showOutcomePrompt, setShowOutcomePrompt] = useState(false);

  const decisionIdRef = useRef<string | null>(null);
  const cleanupRef = useRef<(() => void) | undefined>(undefined);
  const retryInFlightRef = useRef(false);

  // 헤더용 signal 제목 조회
  useEffect(() => {
    const supabase = createClient();
    let cancelled = false;
    (async () => {
      try {
        const { data } = await supabase.from("signals").select("title").eq("id", signalId).maybeSingle();
        if (!cancelled && data?.title) setSignalTitle(data.title);
      } catch {
        // 제목 조회 실패는 헤더 표시 실패로 무시 가능
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [signalId]);

  const getToken = async () => {
    const {
      data: { session },
    } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  };

  const triggerAPI = async (decisionId: string): Promise<string | null> => {
    const token = await getToken();
    const res = await fetch(`${FASTAPI_URL}/api/v1/learning-paths/trigger`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ decision_id: decisionId }),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json?.data?.learning_path_id as string) ?? null;
  };

  const subscribe = (learningPathId: string) => {
    const supabase = createClient();

    const applyCompleted = (resources: LearningPathResource[], goal?: string) => {
      if (resources.length === 5) {
        setUIState({ type: "ready", resources, goal });
      } else {
        setUIState({ type: "failed" });
      }
    };

    const fetchAndApplyCompleted = async () => {
      const { data, error } = await supabase
        .from("learning_paths")
        .select("resources, goal")
        .eq("id", learningPathId)
        .maybeSingle();
      if (error) {
        console.error("learning_paths resources 조회 실패:", error);
        setUIState({ type: "failed" });
        return;
      }
      applyCompleted(
        (data?.resources as LearningPathResource[] | undefined) ?? [],
        (data?.goal as string | undefined) ?? undefined,
      );
    };

    const channel = supabase
      .channel(`learning-path-${learningPathId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "learning_paths",
          filter: `id=eq.${learningPathId}`,
        },
        async (payload) => {
          const row = payload.new as { status: string };
          if (row.status === "completed") {
            await fetchAndApplyCompleted();
          }
          if (row.status === "failed") {
            setUIState({ type: "failed" });
          }
        }
      )
      .subscribe();

    // 초기 조회 이후 채널이 실제로 연결되기까지의 시간차 동안 발생한 상태 전이를 놓치지 않도록
    // 구독 직후 현재 상태를 한 번 더 확인한다.
    (async () => {
      const { data, error } = await supabase
        .from("learning_paths")
        .select("status, resources, goal")
        .eq("id", learningPathId)
        .maybeSingle();
      if (error) {
        console.error("learning_paths 상태 재확인 실패:", error);
        return;
      }
      if (data?.status === "completed") {
        applyCompleted(
          (data.resources as LearningPathResource[] | undefined) ?? [],
          (data.goal as string | undefined) ?? undefined,
        );
      } else if (data?.status === "failed") {
        setUIState({ type: "failed" });
      }
    })();

    return () => {
      supabase.removeChannel(channel);
    };
  };

  const resolveAndStart = async (isCancelled: () => boolean = () => false) => {
    setUIState({ type: "generating" });
    const supabase = createClient();

    const { data: reviewRow, error: reviewError } = await supabase
      .from("reviews")
      .select("id")
      .eq("signal_id", signalId)
      .eq("status", "completed")
      .limit(1)
      .maybeSingle();
    if (isCancelled()) return;
    if (reviewError) console.error("reviews 조회 실패:", reviewError);
    if (!reviewRow) {
      setUIState({ type: "failed" });
      return;
    }

    const { data: decisionRow, error: decisionError } = await supabase
      .from("decisions")
      .select("id")
      .eq("review_id", reviewRow.id)
      .eq("choice", "learn_now")
      .limit(1)
      .maybeSingle();
    if (isCancelled()) return;
    if (decisionError) console.error("decisions 조회 실패:", decisionError);
    if (!decisionRow) {
      setUIState({ type: "failed" });
      return;
    }
    decisionIdRef.current = decisionRow.id;

    const { data: lpRow, error: lpError } = await supabase
      .from("learning_paths")
      .select("id, status, resources, goal")
      .eq("decision_id", decisionRow.id)
      .limit(1)
      .maybeSingle();
    if (isCancelled()) return;
    if (lpError) console.error("learning_paths 조회 실패:", lpError);

    if (lpRow) {
      if (lpRow.status === "completed") {
        const resources = (lpRow.resources as LearningPathResource[] | undefined) ?? [];
        setUIState({ type: "ready", resources, goal: (lpRow.goal as string | undefined) ?? undefined });
        return;
      }
      if (lpRow.status === "failed") {
        setUIState({ type: "failed" });
        return;
      }
      // pending | processing
      cleanupRef.current = subscribe(lpRow.id);
      return;
    }

    // 신규 trigger
    try {
      const learningPathId = await triggerAPI(decisionRow.id);
      if (isCancelled()) return;
      if (!learningPathId) {
        setUIState({ type: "failed" });
        return;
      }
      cleanupRef.current = subscribe(learningPathId);
    } catch {
      if (!isCancelled()) setUIState({ type: "failed" });
    }
  };

  useEffect(() => {
    let cancelled = false;
    resolveAndStart(() => cancelled);
    return () => {
      cancelled = true;
      cleanupRef.current?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signalId]);

  // 외부 링크 방문 후 앱으로 복귀 감지
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible" && hasVisitedExternal) {
        setShowOutcomePrompt(true);
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [hasVisitedExternal]);

  const handleRetry = async () => {
    if (retryInFlightRef.current) return;
    retryInFlightRef.current = true;
    cleanupRef.current?.();
    cleanupRef.current = undefined;
    setUIState({ type: "generating" });
    try {
      const decisionId = decisionIdRef.current;
      if (!decisionId) {
        await resolveAndStart();
        return;
      }
      const learningPathId = await triggerAPI(decisionId);
      if (!learningPathId) {
        setUIState({ type: "failed" });
        return;
      }
      cleanupRef.current = subscribe(learningPathId);
    } catch {
      setUIState({ type: "failed" });
    } finally {
      retryInFlightRef.current = false;
    }
  };

  const headerLabel = signalTitle ? `${signalTitle} Learning Path` : "Learning Path";

  return (
    <div
      style={{
        minHeight: "100dvh",
        background: "var(--surface-base)",
        paddingBottom: showOutcomePrompt && uiState.type === "ready" ? "96px" : "24px",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "16px 20px 12px",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <button
          onClick={() => router.push(`/home/review/${signalId}`)}
          aria-label="뒤로 가기"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
            fontSize: "13px",
            color: "var(--text-secondary)",
          }}
        >
          ←
        </button>
        <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)" }}>
          {headerLabel}
        </span>
      </div>

      <div className="screen-container" style={{ paddingTop: "20px" }}>
        {uiState.type === "generating" && (
          <p className="text-body" style={{ color: "var(--text-secondary)" }}>
            학습 경로를 생성하는 중입니다. <ThreeDotLoading />
          </p>
        )}

        {uiState.type === "failed" && (
          <div>
            <p className="text-body" style={{ marginBottom: "16px" }}>
              학습 경로를 생성하지 못했습니다.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "flex-start" }}>
              <button
                onClick={handleRetry}
                style={{
                  padding: "12px 24px",
                  borderRadius: "9999px",
                  border: "none",
                  background: "var(--accent-primary)",
                  color: "var(--accent-foreground)",
                  fontSize: "15px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                다시 시도하기
              </button>
              <button
                onClick={() => router.push("/home")}
                className="text-label"
                style={{
                  color: "var(--text-secondary)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                홈으로 돌아가기
              </button>
            </div>
          </div>
        )}

        {uiState.type === "ready" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {uiState.goal && (
              <div
                style={{
                  backgroundColor: "var(--surface-card)",
                  borderRadius: "var(--radius-card)",
                  padding: "var(--card-padding)",
                  borderLeft: "3px solid var(--border-strong, var(--text-tertiary))",
                }}
              >
                <span
                  className="text-badge"
                  style={{ color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}
                >
                  이 경로의 목표
                </span>
                <p style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                  {uiState.goal}
                </p>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column" }}>
              {uiState.resources.map((resource, idx) => {
                const isLast = idx === uiState.resources.length - 1;
                return (
                  <div key={`${resource.type}-${idx}`} style={{ display: "flex", gap: "12px" }}>
                    {/* 번호 원 + 세로 연결선 */}
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                      <div
                        aria-hidden="true"
                        style={{
                          width: "24px",
                          height: "24px",
                          borderRadius: "9999px",
                          border: "1px solid var(--border-subtle)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "12px",
                          fontWeight: 600,
                          color: "var(--text-secondary)",
                          backgroundColor: "var(--surface-base)",
                        }}
                      >
                        {idx + 1}
                      </div>
                      {!isLast && (
                        <div style={{ flex: 1, width: "1px", backgroundColor: "var(--border-subtle)", minHeight: "12px" }} />
                      )}
                    </div>
                    {/* 카드 */}
                    <div style={{ flex: 1, minWidth: 0, paddingBottom: isLast ? 0 : "12px" }}>
                      <LearningPathCard resource={resource} onVisit={() => setHasVisitedExternal(true)} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {showOutcomePrompt && uiState.type === "ready" && (
        <div
          style={{
            position: "fixed",
            bottom: 0,
            left: 0,
            right: 0,
            padding: "12px 20px 20px",
            background: "var(--surface-base)",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <p className="text-label" style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>
            학습을 완료했나요? 결과를 기록해 주세요.
          </p>
          <button
            onClick={() => router.push(`/home/review/${signalId}/outcome`)}
            style={{
              width: "100%",
              padding: "12px",
              borderRadius: "9999px",
              border: "none",
              background: "var(--accent-primary)",
              color: "var(--accent-foreground)",
              fontSize: "15px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            결과 기록하기
          </button>
        </div>
      )}
    </div>
  );
}
