"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import {
  ROLE_OPTIONS,
  EXPERIENCE_OPTIONS,
  TECH_OPTIONS,
  GOAL_OPTIONS,
  INTEREST_OPTIONS,
  TIME_OPTIONS,
} from "@/lib/profile-options";

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";

const TOTAL_STEPS = 6; // 1~6 질문 (0 = Welcome)

export default function OnboardingPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [step, setStep] = useState(0);

  const [role, setRole] = useState<string | null>(null);
  const [experience, setExperience] = useState<string | null>(null);
  const [techStack, setTechStack] = useState<string[]>([]);
  const [goal, setGoal] = useState<string | null>(null);
  const [interests, setInterests] = useState<string[]>([]);
  const [dailyTime, setDailyTime] = useState<number | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 세션 확인 + 완료자 가드 (AC-4)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const supabase = createClient();
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (!user) {
          router.replace("/signin");
          return;
        }
        const { data: profile } = await supabase
          .from("user_profiles")
          .select("onboarding_completed")
          .eq("id", user.id)
          .maybeSingle();
        if (cancelled) return;
        if (profile?.onboarding_completed) {
          router.replace("/home");
          return;
        }
        setReady(true);
      } catch {
        // 네트워크/Supabase 장애 시 영구 blank 방지 — fail-open으로 위저드 노출(제출 단계에서 재검증)
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const toggle = (list: string[], setList: (v: string[]) => void, value: string) => {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  };

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);
    try {
      const {
        data: { session },
      } = await createClient().auth.getSession();
      const token = session?.access_token;
      if (!token) {
        setError("로그인 세션이 만료됐습니다. 다시 로그인해 주세요.");
        setSubmitting(false);
        return;
      }
      const res = await fetch(`${FASTAPI_URL}/api/v1/onboarding/complete`, {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          role,
          experience_level: experience,
          tech_stack: techStack,
          project_goal: goal,
          interests,
          daily_learning_time_min: dailyTime,
        }),
      });
      if (!res.ok) throw new Error("failed");
      router.replace("/home");
    } catch {
      setError(
        controller.signal.aborted
          ? "요청 시간이 초과됐습니다. 다시 시도해 주세요."
          : "저장 중 오류가 발생했습니다. 다시 시도해 주세요."
      );
      setSubmitting(false);
    } finally {
      clearTimeout(timer);
    }
  };

  if (!ready) return null;

  // ── 스텝별 구성 ────────────────────────────────────────────────
  const canProceed = (() => {
    switch (step) {
      case 1: return role !== null;
      case 2: return experience !== null;
      case 3: return true; // 다중 선택 — 빈 값 허용
      case 4: return goal !== null;
      case 5: return true;
      case 6: return dailyTime !== null;
      default: return true;
    }
  })();

  // closure 캡처 step 기반 → rapid 더블클릭 시 두 번 모두 동일 목표값이라 스텝 스킵 방지
  const goNext = () => {
    if (step === TOTAL_STEPS) handleSubmit();
    else setStep(step + 1);
  };

  return (
    <div style={wrap}>
      <div style={card}>
        {step > 0 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
            <button type="button" onClick={() => setStep(step - 1)} style={backBtn} aria-label="이전 단계">
              ‹ 이전
            </button>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              {step} / {TOTAL_STEPS}
            </span>
          </div>
        )}

        {step === 0 && (
          <>
            <h1 style={title}>환영합니다 👋</h1>
            <p style={{ fontSize: 15, color: "var(--text-secondary)", marginBottom: 32 }}>
              몇 가지만 알려주시면 나에게 맞는 브리핑을 준비해 드릴게요.
            </p>
          </>
        )}

        {step === 1 && (
          <SingleSelect question="어떤 역할을 맡고 계신가요?" options={ROLE_OPTIONS} selected={role} onSelect={setRole} />
        )}
        {step === 2 && (
          <SingleSelect question="경험 수준을 알려주세요." options={EXPERIENCE_OPTIONS} selected={experience} onSelect={setExperience} />
        )}
        {step === 3 && (
          <MultiSelect
            question="주로 사용하는 기술 스택을 선택해 주세요."
            options={TECH_OPTIONS}
            selected={techStack}
            onToggle={(v) => toggle(techStack, setTechStack, v)}
          />
        )}
        {step === 4 && (
          <SingleSelect question="현재 무엇을 만들거나 배우고 계신가요?" options={GOAL_OPTIONS} selected={goal} onSelect={setGoal} />
        )}
        {step === 5 && (
          <MultiSelect
            question="관심 있는 기술 영역을 선택해 주세요."
            options={INTEREST_OPTIONS}
            selected={interests}
            onToggle={(v) => toggle(interests, setInterests, v)}
          />
        )}
        {step === 6 && (
          <SingleSelect
            question="하루에 AI 학습에 투자할 수 있는 시간은?"
            options={TIME_OPTIONS.map(([l, v]) => [l, String(v)] as [string, string])}
            selected={dailyTime === null ? null : String(dailyTime)}
            onSelect={(v) => setDailyTime(Number(v))}
          />
        )}

        {error && <p style={{ color: "var(--error)", fontSize: 13, fontWeight: 500, margin: "16px 0 0" }}>{error}</p>}

        <button type="button" onClick={goNext} disabled={!canProceed || submitting} style={cta(!canProceed || submitting)}>
          {step === 0 ? "시작하기" : step === TOTAL_STEPS ? (submitting ? "저장 중..." : "완료") : "다음"}
        </button>
      </div>
    </div>
  );
}

function SingleSelect({
  question,
  options,
  selected,
  onSelect,
}: {
  question: string;
  options: Array<[string, string]>;
  selected: string | null;
  onSelect: (v: string) => void;
}) {
  return (
    <>
      <h1 style={title}>{question}</h1>
      <div role="radiogroup" aria-label={question} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {options.map(([label, value]) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected === value}
            onClick={() => onSelect(value)}
            style={optionCard(selected === value)}
          >
            {label}
          </button>
        ))}
      </div>
    </>
  );
}

function MultiSelect({
  question,
  options,
  selected,
  onToggle,
}: {
  question: string;
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <>
      <h1 style={title}>{question}</h1>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {options.map((opt) => {
          const on = selected.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              aria-pressed={on}
              onClick={() => onToggle(opt)}
              style={chip(on)}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </>
  );
}

// ── styles ──────────────────────────────────────────────────────
const wrap: React.CSSProperties = {
  backgroundColor: "var(--surface-raised)",
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};
const card: React.CSSProperties = { width: "100%", maxWidth: 480, padding: "48px 24px" };
const title: React.CSSProperties = { fontSize: 24, fontWeight: 700, marginBottom: 24, color: "var(--text-primary)" };
const backBtn: React.CSSProperties = {
  background: "transparent",
  border: "none",
  cursor: "pointer",
  fontSize: 14,
  color: "var(--text-secondary)",
  padding: "8px 4px",
  minHeight: 44,
};
function optionCard(sel: boolean): React.CSSProperties {
  return {
    display: "block",
    width: "100%",
    textAlign: "left",
    background: "var(--surface-card)",
    borderRadius: 14,
    padding: 16,
    minHeight: 52,
    border: sel ? "1.5px solid var(--accent-primary)" : "1px solid var(--border-card)",
    cursor: "pointer",
    fontSize: 15,
    fontWeight: 500,
    color: "var(--text-primary)",
  };
}
function chip(on: boolean): React.CSSProperties {
  return {
    minHeight: 44,
    padding: "10px 16px",
    borderRadius: 9999,
    border: on ? "1.5px solid var(--accent-primary)" : "1px solid var(--border-card)",
    background: on ? "var(--accent-primary)" : "transparent",
    color: on ? "var(--accent-foreground)" : "var(--text-primary)",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 500,
  };
}
function cta(disabled: boolean): React.CSSProperties {
  return {
    backgroundColor: disabled ? "var(--text-disabled)" : "var(--accent-primary)",
    color: "var(--accent-foreground)",
    height: 52,
    borderRadius: 9999,
    width: "100%",
    fontSize: 17,
    fontWeight: 600,
    border: "none",
    cursor: disabled ? "not-allowed" : "pointer",
    marginTop: 32,
  };
}
