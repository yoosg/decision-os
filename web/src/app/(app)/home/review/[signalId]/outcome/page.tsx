"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { API_BASE_URL } from "@/lib/api-config";
import { getAccessToken } from "@/lib/api";
import { OutcomeCard } from "@/components/home/outcome/outcome-card";
import { OUTCOME_OPTIONS, type OutcomeStatus } from "@/components/home/outcome/outcome-options";

export default function OutcomePage({ params }: { params: Promise<{ signalId: string }> }) {
  const { signalId } = use(params);
  const router = useRouter();

  const [decisionId, setDecisionId] = useState<string | null>(null);
  const [signalTitle, setSignalTitle] = useState("");
  const [loadFailed, setLoadFailed] = useState(false);

  const [selectedStatus, setSelectedStatus] = useState<OutcomeStatus | null>(null);
  const [appliedProjectNote, setAppliedProjectNote] = useState("");
  const [useful, setUseful] = useState(true);
  const [learningTimeMin, setLearningTimeMin] = useState("");
  const [memo, setMemo] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // signalId → decision_id 조회 + Signal 제목 조회
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const supabase = createClient();

      const { data: signalRow } = await supabase
        .from("signals")
        .select("title")
        .eq("id", signalId)
        .maybeSingle();
      if (!cancelled && signalRow?.title) setSignalTitle(signalRow.title);

      const { data: reviewRow } = await supabase
        .from("reviews")
        .select("id")
        .eq("signal_id", signalId)
        .eq("status", "completed")
        .limit(1)
        .maybeSingle();
      if (cancelled) return;
      if (!reviewRow) {
        setLoadFailed(true);
        return;
      }

      const { data: decisionRow } = await supabase
        .from("decisions")
        .select("id")
        .eq("review_id", reviewRow.id)
        .eq("choice", "learn_now")
        .limit(1)
        .maybeSingle();
      if (cancelled) return;
      if (!decisionRow) {
        setLoadFailed(true);
        return;
      }
      setDecisionId(decisionRow.id);
    })();
    return () => {
      cancelled = true;
    };
  }, [signalId]);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(null), 3000);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  useEffect(() => {
    if (loadFailed) router.push("/home");
  }, [loadFailed, router]);

  const handleSubmit = async () => {
    if (!selectedStatus || !decisionId || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const token = await getAccessToken();
      if (!token) {
        setToastMessage("로그인 세션이 만료됐습니다. 새로고침 후 다시 시도해 주세요.");
        setIsSubmitting(false);
        return;
      }

      const res = await fetch(`${API_BASE_URL}/api/v1/outcomes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          decision_id: decisionId,
          status: selectedStatus,
          useful,
          actual_learning_time_min: learningTimeMin.trim() ? parseInt(learningTimeMin, 10) : null,
          applied_project_note: selectedStatus === "applied" ? appliedProjectNote : null,
          memo,
        }),
      });
      if (!res.ok) throw new Error("Outcome request failed");

      setToastMessage("결과가 기록됐습니다. 다음 브리핑에 반영됩니다.");
      setTimeout(() => router.push("/home"), 1500);
    } catch {
      setIsSubmitting(false);
      setToastMessage("오류가 발생했습니다. 다시 시도해 주세요.");
    }
  };

  if (loadFailed) return null;

  return (
    <div style={{ minHeight: "100dvh", background: "var(--surface-base)", paddingBottom: "24px" }}>
      <div className="screen-container" style={{ paddingTop: "24px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 700, margin: "0 0 8px" }}>
          학습 결과를 기록해 주세요
        </h1>
        {signalTitle && (
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 24px" }}>
            {signalTitle}
          </p>
        )}

        <div
          role="radiogroup"
          aria-label="학습 결과를 선택해 주세요"
          style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "24px" }}
        >
          {OUTCOME_OPTIONS.map(({ status, englishLabel, koreanLabel }) => (
            <div key={status}>
              <OutcomeCard
                status={status}
                englishLabel={englishLabel}
                koreanLabel={koreanLabel}
                isSelected={selectedStatus === status}
                onSelect={setSelectedStatus}
              />
              {status === "applied" && selectedStatus === "applied" && (
                <input
                  type="text"
                  aria-label="어떤 프로젝트에 적용했나요? (선택)"
                  placeholder="어떤 프로젝트에 적용했나요? (선택)"
                  value={appliedProjectNote}
                  onChange={(e) => setAppliedProjectNote(e.target.value)}
                  style={{
                    marginTop: "8px",
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "12px 14px",
                    borderRadius: "12px",
                    border: "1px solid var(--border-card)",
                    fontSize: "14px",
                  }}
                />
              )}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "32px" }}>
          <div>
            <p className="text-label" style={{ margin: "0 0 8px" }}>유용했나요?</p>
            <div style={{ display: "flex", gap: "8px" }}>
              {[
                { label: "예", value: true },
                { label: "아니오", value: false },
              ].map(({ label, value }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => setUseful(value)}
                  style={{
                    flex: 1,
                    minHeight: "44px",
                    borderRadius: "9999px",
                    border: useful === value
                      ? "1px solid var(--accent-primary)"
                      : "1px solid var(--border-subtle, #E5E5E5)",
                    background: useful === value ? "var(--accent-primary)" : "transparent",
                    color: useful === value ? "var(--accent-foreground, #FFFFFF)" : "var(--text-primary)",
                    cursor: "pointer",
                    fontSize: "14px",
                    fontWeight: 500,
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="learning-time" className="text-label" style={{ display: "block", margin: "0 0 8px" }}>
              실제 학습 시간
            </label>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                id="learning-time"
                type="number"
                min="0"
                value={learningTimeMin}
                onChange={(e) => setLearningTimeMin(e.target.value)}
                style={{
                  width: "100px",
                  boxSizing: "border-box",
                  padding: "12px 14px",
                  borderRadius: "12px",
                  border: "1px solid var(--border-card)",
                  fontSize: "14px",
                }}
              />
              <span style={{ fontSize: "14px", color: "var(--text-secondary)" }}>분</span>
            </div>
          </div>

          <div>
            <label htmlFor="memo" className="text-label" style={{ display: "block", margin: "0 0 8px" }}>
              메모
            </label>
            <textarea
              id="memo"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="적용 방식, 막힌 부분, 다음 단계 등을 남겨두세요"
              style={{
                width: "100%",
                minHeight: "96px",
                boxSizing: "border-box",
                padding: "12px 14px",
                borderRadius: "12px",
                border: "1px solid var(--border-card)",
                fontSize: "14px",
                resize: "none",
              }}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!selectedStatus || !decisionId || isSubmitting}
          style={{
            width: "100%",
            padding: "14px",
            borderRadius: "9999px",
            border: "none",
            background:
              !selectedStatus || !decisionId || isSubmitting ? "var(--text-disabled)" : "var(--accent-primary)",
            color: "var(--accent-foreground, #FFFFFF)",
            cursor: !selectedStatus || !decisionId || isSubmitting ? "not-allowed" : "pointer",
            fontSize: "15px",
            fontWeight: 600,
          }}
        >
          기록하기
        </button>
      </div>

      {toastMessage && (
        <div
          role="status"
          aria-live="assertive"
          style={{
            position: "fixed",
            bottom: "32px",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            zIndex: 60,
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              background: "rgba(0,0,0,0.75)",
              color: "#fff",
              padding: "10px 20px",
              borderRadius: "9999px",
              fontSize: "14px",
            }}
          >
            {toastMessage}
          </div>
        </div>
      )}
    </div>
  );
}
