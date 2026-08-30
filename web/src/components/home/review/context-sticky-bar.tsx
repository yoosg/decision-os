"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api-config";
import { getAccessToken } from "@/lib/api";
import { trackEngagement } from "@/lib/engagement";

const REQUIRED_SECTIONS = new Set([
  "one_line_definition",
  "key_concepts",
  "problems_solved",
  "why_it_matters",
  "vs_existing_tech",
  "user_relevance",
  "risks",
  "recommendation_reason",
]);

interface Props {
  signalId: string;
  reviewId: string;
  barGateOverride?: string | null;
  recommendationReason: string;
}

export function ContextStickyBar({
  signalId,
  reviewId,
  barGateOverride,
  recommendationReason,
}: Props) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(() => barGateOverride === "enabled");
  const [seenSections, setSeenSections] = useState<Set<string>>(new Set());
  const prevEnabledRef = useRef(barGateOverride === "enabled");
  const ariaLiveRef = useRef<HTMLSpanElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const [queueSheetOpen, setQueueSheetOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [queueMemo, setQueueMemo] = useState("");

  // 섹션 engagement 추적 (bar_gate_override="enabled" 면 불필요)
  useEffect(() => {
    if (barGateOverride === "enabled") return;

    const elements = document.querySelectorAll("[data-section-key]");
    const seenSet = new Set<string>();

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const key = (entry.target as HTMLElement).dataset.sectionKey!;
            seenSet.add(key);
            setSeenSections(new Set(seenSet));
          }
        });
      },
      { threshold: 0.1 }
    );

    const focusHandlers: Array<[Element, () => void]> = [];
    elements.forEach((el) => {
      observer.observe(el);
      const handler = () => {
        const key = (el as HTMLElement).dataset.sectionKey!;
        seenSet.add(key);
        setSeenSections(new Set(seenSet));
      };
      el.addEventListener("focus", handler);
      focusHandlers.push([el, handler]);
    });

    return () => {
      observer.disconnect();
      focusHandlers.forEach(([el, h]) => el.removeEventListener("focus", h));
    };
  }, []); // 마운트 후 1회만 실행

  // REQUIRED_SECTIONS 모두 seen → enabled 전환
  useEffect(() => {
    if (barGateOverride === "enabled") return;
    if (REQUIRED_SECTIONS.size === 0) return;
    const allSeen = [...REQUIRED_SECTIONS].every((k) => seenSections.has(k));
    if (allSeen && !prevEnabledRef.current) {
      setEnabled(true);
      prevEnabledRef.current = true;
      if (ariaLiveRef.current) {
        ariaLiveRef.current.textContent = "지금 학습 버튼을 사용할 수 있습니다";
      }
      // Story 6.5: 필수 섹션 전부 열람 → read_through 1회 전송(fire-and-forget).
      // barGateOverride==='enabled'로 즉시 활성화된 케이스는 이 블록 위에서 early-return되므로
      // 여기 도달하지 않는다 → 자연 열람일 때만 전송(강제 활성화는 실제 읽기 아님, D).
      trackEngagement([{ signal_id: signalId, event_type: "read_through" }]);
    }
  }, [seenSections, barGateOverride]);

  // ESC 키로 Queue Sheet 닫기
  useEffect(() => {
    if (!queueSheetOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setQueueSheetOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [queueSheetOpen]);

  // P9: Queue Sheet 포커스 트랩
  useEffect(() => {
    if (!queueSheetOpen) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = dialog.querySelectorAll<HTMLElement>(
      'button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    // P5: focusable 요소 없을 시 dialog 자체에 포커스
    if (focusable.length === 0) { dialog.focus(); return; }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first.focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    dialog.addEventListener("keydown", trap);
    return () => dialog.removeEventListener("keydown", trap);
  }, [queueSheetOpen]);

  // Toast 자동 사라짐
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(null), 3000);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  const postDecision = async (payload: {
    review_id: string;
    choice: string;
    queue_timing?: string;
    memo?: string;
  }) => {
    const token = await getAccessToken();

    // P8: 세션 만료 감지
    if (!token) {
      setToastMessage("로그인 세션이 만료됐습니다. 새로고침 후 다시 시도해 주세요.");
      throw new Error("Unauthenticated");
    }

    const res = await fetch(`${API_BASE_URL}/api/v1/decisions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Decision request failed");
    return res.json();
  };

  const handleLearnNow = async () => {
    if (!enabled || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await postDecision({ review_id: reviewId, choice: "learn_now" });
      router.push(`/home/review/${signalId}/learning-path`);
    } catch {
      setIsSubmitting(false);
      setToastMessage("오류가 발생했습니다. 다시 시도해 주세요."); // P3: 실패 피드백
    }
  };

  // P1: 토스트가 보인 뒤 이동 — 1.5s 지연으로 AC-7 준수
  const handleIgnore = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await postDecision({ review_id: reviewId, choice: "ignore" });
      setToastMessage("이 기술 소식은 히스토리에서 다시 볼 수 있습니다.");
      setIsSubmitting(false); // P2: 성공 시 즉시 복구 (1.5s 지연 전)
      setTimeout(() => router.push("/home"), 1500);
    } catch {
      setIsSubmitting(false);
    }
  };

  // P6: isSubmitting 가드 추가 / P5: 오류 토스트 / D1: 성공 후 홈 이동
  const handleQueueTiming = async (timing: string) => {
    if (isSubmitting) return; // P6
    setQueueSheetOpen(false);
    setIsSubmitting(true);
    try {
      await postDecision({
        review_id: reviewId,
        choice: "queue",
        queue_timing: timing,
        memo: queueMemo || undefined,
      });
      const toastMap: Record<string, string> = {
        today: "오늘 학습 예정으로 저장됐습니다.",
        this_week: "이번 주 학습 예정으로 저장됐습니다.",
        later: "나중에 학습 예정으로 저장됐습니다.",
      };
      setToastMessage(toastMap[timing] ?? "저장됐습니다.");
      setQueueMemo("");
      router.push("/home"); // D1: 재결정 방지
    } catch {
      setToastMessage("저장 중 오류가 발생했습니다. 다시 시도해 주세요."); // P5
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Toast */}
      {toastMessage && (
        <div
          role="status"
          aria-live="assertive"
          style={{
            position: "fixed",
            bottom: "calc(148px + env(safe-area-inset-bottom))",
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

      {/* Queue Bottom Sheet */}
      {queueSheetOpen && (
        <>
          <div
            role="presentation"
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.4)",
              zIndex: 50,
            }}
            onClick={() => setQueueSheetOpen(false)}
          />
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label="학습 일정 선택"
            tabIndex={-1}
            style={{
              position: "fixed",
              bottom: 0,
              left: 0,
              right: 0,
              background: "var(--surface-base, #FFFFFF)",
              borderRadius: "24px 24px 0 0",
              padding: "12px 20px 40px",
              zIndex: 51,
              // iOS Safari 관성 스크롤 중 fixed 리페인트 지연 방지(자체 컴포지팅 레이어)
              transform: "translateZ(0)",
            }}
          >
            {/* drag handle */}
            <div
              style={{
                width: 36,
                height: 4,
                background: "#DDD",
                borderRadius: 9999,
                margin: "0 auto 16px",
              }}
            />
            <h3
              style={{
                fontSize: "17px",
                fontWeight: 600,
                margin: "0 0 16px",
              }}
            >
              언제 학습할까요?
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {[
                { label: "오늘", value: "today" },
                { label: "이번 주", value: "this_week" },
                { label: "나중에", value: "later" },
              ].map(({ label, value }) => (
                <button
                  key={value}
                  onClick={() => handleQueueTiming(value)}
                  style={{
                    minHeight: "44px",
                    border: "1px solid var(--border-subtle, #E5E5E5)",
                    borderRadius: "9999px",
                    background: "transparent",
                    cursor: "pointer",
                    fontSize: "15px",
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <textarea
              aria-label="메모 (선택)"
              value={queueMemo}
              onChange={(e) => setQueueMemo(e.target.value)}
              placeholder="메모를 남기세요 (선택)"
              style={{
                marginTop: "16px",
                width: "100%",
                minHeight: "72px",
                border: "1px solid var(--border-subtle, #E5E5E5)",
                borderRadius: "12px",
                padding: "10px 12px",
                fontSize: "14px",
                resize: "none",
                boxSizing: "border-box",
              }}
            />
          </div>
        </>
      )}

      {/* ContextStickyBar */}
      <div
        className="ctx-bar-root"
        style={{
          position: "fixed",
          // nav(고정, 64px + 홈 인디케이터 safe-area) 위에 얹는다.
          // safe-area를 더하지 않으면 실기기에서 하단 버튼이 nav에 가려짐.
          bottom: "calc(64px + env(safe-area-inset-bottom))",
          left: 0,
          right: 0,
          padding: "8px 20px 12px",
          background: "var(--surface-base, #FFFFFF)",
          borderTop: "1px solid var(--border-subtle, #E5E5E5)",
          zIndex: 40,
          // iOS Safari 관성 스크롤 중 fixed 리페인트 지연 방지(자체 컴포지팅 레이어)
          transform: "translateZ(0)",
        }}
      >
        {/* aria-live 영역 */}
        <span
          ref={ariaLiveRef}
          aria-live="polite"
          style={{
            position: "absolute",
            width: "1px",
            height: "1px",
            padding: 0,
            margin: "-1px",
            overflow: "hidden",
            clip: "rect(0,0,0,0)",
            whiteSpace: "nowrap",
            border: 0,
          }}
        />

        {!enabled ? (
          <>
            <p
              id="ctx-hint"
              style={{
                fontSize: "11px",
                color: "var(--text-secondary)",
                textAlign: "center",
                marginBottom: "8px",
              }}
            >
              추천 근거를 먼저 확인해 주세요{" "}
              <span aria-hidden="true">↑</span>
            </p>
            <button
              aria-disabled="true"
              aria-label="지금 학습 — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요"
              aria-describedby="ctx-hint"
              onClick={() => { /* no-op: 스크린리더 포커스 가능하도록 native disabled 제거 (P10) */ }}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                width: "100%",
                padding: "14px",
                borderRadius: "9999px",
                border: "none",
                background: "var(--text-disabled, #D1D1D1)",
                cursor: "not-allowed",
                color: "#FFFFFF",
                fontSize: "15px",
                fontWeight: 600,
                opacity: 1,
              }}
            >
              <svg
                aria-hidden="true"
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
              >
                <rect x="2" y="6" width="10" height="7" rx="1.5" fill="currentColor" />
                <path
                  d="M4.5 6V4.5a2.5 2.5 0 015 0V6"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
              지금 학습
            </button>
          </>
        ) : (
          <>
            {recommendationReason && (
              <p
                style={{
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  textAlign: "center",
                  marginBottom: "8px",
                  overflow: "hidden",
                  display: "-webkit-box" as const,
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical" as const,
                }}
              >
                {recommendationReason}
              </p>
            )}
            <button
              onClick={handleLearnNow}
              disabled={isSubmitting}
              aria-label="지금 학습"
              style={{
                display: "block",
                width: "100%",
                padding: "14px",
                borderRadius: "9999px",
                border: "none",
                background: "var(--accent-primary, #4F46E5)",
                cursor: isSubmitting ? "not-allowed" : "pointer",
                color: "var(--accent-foreground, #FFFFFF)",
                fontSize: "15px",
                fontWeight: 600,
                marginBottom: "8px",
              }}
            >
              지금 학습
            </button>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => !isSubmitting && setQueueSheetOpen(true)}
                disabled={isSubmitting}
                aria-label="나중에 학습 — 이 기술 소식을 보관함에 저장"
                style={{
                  flex: 1,
                  minHeight: "44px",
                  borderRadius: "9999px",
                  border: "1px solid var(--border-subtle, #E5E5E5)",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: 500,
                }}
              >
                나중에 학습
              </button>
              <button
                onClick={handleIgnore}
                aria-label="관심 없음 — 이 기술 소식을 넘김"
                style={{
                  flex: 1,
                  minHeight: "44px",
                  borderRadius: "9999px",
                  border: "1px solid var(--border-subtle, #E5E5E5)",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: 500,
                }}
              >
                관심 없음
              </button>
            </div>
          </>
        )}

        {/* P10: .ctx-bar-root 스코프로 한정 — 전역 * 선택자 제거 */}
        <style>{`
          @media (prefers-reduced-motion: reduce) {
            .ctx-bar-root *, .ctx-bar-root *::before, .ctx-bar-root *::after {
              transition: none !important;
              animation: none !important;
            }
          }
        `}</style>
      </div>
    </>
  );
}
