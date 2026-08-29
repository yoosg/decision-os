"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { API_BASE_URL, getAccessToken } from "@/lib/api";
import {
  ROLE_OPTIONS,
  EXPERIENCE_OPTIONS,
  GOAL_OPTIONS,
  TECH_OPTIONS,
  INTEREST_OPTIONS,
  TIME_OPTIONS,
  labelOf,
} from "@/lib/profile-options";

export interface ProfileData {
  displayName: string | null;
  role: string | null;
  experienceLevel: string | null;
  techStack: string[];
  projectGoal: string | null;
  interests: string[];
  dailyLearningTimeMin: number | null;
}

interface Props {
  initial: ProfileData;
}

export function ProfileContent({ initial }: Props) {
  const router = useRouter();
  const [saved, setSaved] = useState<ProfileData>(initial); // 화면에 표시되는 확정 값
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<ProfileData>(initial);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const startEdit = () => {
    setForm(saved);
    setEditing(true);
  };
  const cancelEdit = () => {
    setForm(saved); // AC-3: 원본 복원
    setEditing(false);
  };

  const toggle = (arr: string[], value: string): string[] =>
    arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];

  const handleSave = async () => {
    if (submitting) return;
    setSubmitting(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);
    try {
      const token = await getAccessToken();
      if (!token) {
        setToast("로그인 세션이 만료됐습니다. 다시 로그인해 주세요.");
        setSubmitting(false);
        return;
      }
      // 부분 갱신: 값이 있는 필드만 전송(backend exclude_none)
      const payload: Record<string, unknown> = {
        tech_stack: form.techStack,
        interests: form.interests,
      };
      if (form.role) payload.role = form.role;
      if (form.experienceLevel) payload.experience_level = form.experienceLevel;
      if (form.projectGoal) payload.project_goal = form.projectGoal;
      if (form.dailyLearningTimeMin) payload.daily_learning_time_min = form.dailyLearningTimeMin;

      const res = await fetch(`${API_BASE_URL}/api/v1/users/profile`, {
        method: "PATCH",
        signal: controller.signal,
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("failed");
      setSaved(form); // 확정 값 갱신
      setEditing(false);
      setToast("프로필이 저장됐습니다. 다음 오늘의 브리핑에 반영됩니다.");
    } catch {
      setToast(
        controller.signal.aborted
          ? "요청 시간이 초과됐습니다. 다시 시도해 주세요."
          : "저장 중 오류가 발생했습니다. 다시 시도해 주세요."
      );
    } finally {
      clearTimeout(timer);
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await createClient().auth.signOut();
    router.push("/signin");
  };

  const v = editing ? form : saved;

  return (
    <section style={{ paddingBottom: 40 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <h1 className="text-section-title">프로필</h1>
        {!editing && (
          <button type="button" onClick={startEdit} style={ghostBtn} aria-label="프로필 편집">
            편집
          </button>
        )}
      </div>

      {saved.displayName && !editing && (
        <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 20px" }}>
          {saved.displayName}
        </p>
      )}

      {/* 역할 */}
      <Field label="역할">
        {editing ? (
          <SingleSelect options={ROLE_OPTIONS} selected={form.role} onSelect={(x) => setForm({ ...form, role: x })} />
        ) : (
          <ReadValue text={labelOf(ROLE_OPTIONS, v.role)} />
        )}
      </Field>

      {/* 경험 수준 */}
      <Field label="경험 수준">
        {editing ? (
          <SingleSelect
            options={EXPERIENCE_OPTIONS}
            selected={form.experienceLevel}
            onSelect={(x) => setForm({ ...form, experienceLevel: x })}
          />
        ) : (
          <ReadValue text={labelOf(EXPERIENCE_OPTIONS, v.experienceLevel)} />
        )}
      </Field>

      {/* 기술 스택 */}
      <Field label="기술 스택">
        {editing ? (
          <Chips
            options={TECH_OPTIONS}
            selected={form.techStack}
            onToggle={(x) => setForm({ ...form, techStack: toggle(form.techStack, x) })}
          />
        ) : (
          <ReadChips values={v.techStack} />
        )}
      </Field>

      {/* 프로젝트 목표 */}
      <Field label="프로젝트 목표">
        {editing ? (
          <SingleSelect options={GOAL_OPTIONS} selected={form.projectGoal} onSelect={(x) => setForm({ ...form, projectGoal: x })} />
        ) : (
          <ReadValue text={labelOf(GOAL_OPTIONS, v.projectGoal)} />
        )}
      </Field>

      {/* 관심 영역 */}
      <Field label="관심 영역">
        {editing ? (
          <Chips
            options={INTEREST_OPTIONS}
            selected={form.interests}
            onToggle={(x) => setForm({ ...form, interests: toggle(form.interests, x) })}
          />
        ) : (
          <ReadChips values={v.interests} />
        )}
      </Field>

      {/* 일일 학습 시간 */}
      <Field label="일일 학습 시간">
        {editing ? (
          <div style={{ display: "flex", gap: 8 }}>
            {TIME_OPTIONS.map(([lbl, val]) => (
              <button
                key={val}
                type="button"
                aria-pressed={form.dailyLearningTimeMin === val}
                onClick={() => setForm({ ...form, dailyLearningTimeMin: val })}
                style={segment(form.dailyLearningTimeMin === val)}
              >
                {lbl}
              </button>
            ))}
          </div>
        ) : (
          <ReadValue text={labelOf(TIME_OPTIONS, v.dailyLearningTimeMin)} />
        )}
      </Field>

      {editing ? (
        <div style={{ display: "flex", gap: 8, marginTop: 32 }}>
          <button type="button" onClick={cancelEdit} disabled={submitting} style={{ ...outlineBtn, flex: 1 }}>
            취소
          </button>
          <button type="button" onClick={handleSave} disabled={submitting} style={{ ...cta(submitting), flex: 1, marginTop: 0 }}>
            {submitting ? "저장 중..." : "저장"}
          </button>
        </div>
      ) : (
        <button type="button" onClick={handleLogout} style={{ ...outlineBtn, width: "100%", marginTop: 40 }}>
          로그아웃
        </button>
      )}

      {toast && (
        <div role="status" aria-live="assertive" style={toastWrap}>
          <div style={toastInner}>{toast}</div>
        </div>
      )}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <p className="text-label" style={{ color: "var(--text-secondary)", margin: "0 0 8px" }}>
        {label}
      </p>
      {children}
    </div>
  );
}
function ReadValue({ text }: { text: string }) {
  return <p className="text-body" style={{ margin: 0, color: "var(--text-primary)" }}>{text}</p>;
}
function ReadChips({ values }: { values: string[] }) {
  if (!values || values.length === 0) return <ReadValue text="-" />;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {values.map((val) => (
        <span key={val} style={readChip}>
          {val}
        </span>
      ))}
    </div>
  );
}
function SingleSelect({
  options,
  selected,
  onSelect,
}: {
  options: ReadonlyArray<readonly [string, string]>;
  selected: string | null;
  onSelect: (v: string) => void;
}) {
  return (
    <div role="radiogroup" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
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
  );
}
function Chips({
  options,
  selected,
  onToggle,
}: {
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {options.map((opt) => {
        const on = selected.includes(opt);
        return (
          <button key={opt} type="button" aria-pressed={on} onClick={() => onToggle(opt)} style={chip(on)}>
            {opt}
          </button>
        );
      })}
    </div>
  );
}

// ── styles ──────────────────────────────────────────────────────
const ghostBtn: React.CSSProperties = {
  background: "transparent",
  border: "1px solid var(--border-card)",
  borderRadius: 9999,
  padding: "8px 16px",
  minHeight: 44,
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
  color: "var(--text-primary)",
};
const readChip: React.CSSProperties = {
  background: "var(--surface-card)",
  color: "var(--text-primary)",
  borderRadius: 9999,
  padding: "6px 12px",
  fontSize: 13,
};
function optionCard(sel: boolean): React.CSSProperties {
  return {
    display: "block",
    width: "100%",
    textAlign: "left",
    background: "var(--surface-card)",
    borderRadius: 12,
    padding: "12px 14px",
    minHeight: 44,
    border: sel ? "1.5px solid var(--accent-primary)" : "1px solid var(--border-card)",
    cursor: "pointer",
    fontSize: 14,
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
function segment(on: boolean): React.CSSProperties {
  return {
    flex: 1,
    minHeight: 44,
    borderRadius: 9999,
    border: on ? "1px solid var(--accent-primary)" : "1px solid var(--border-card)",
    background: on ? "var(--accent-primary)" : "transparent",
    color: on ? "var(--accent-foreground)" : "var(--text-primary)",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 500,
  };
}
const outlineBtn: React.CSSProperties = {
  minHeight: 52,
  borderRadius: 9999,
  border: "1px solid var(--border-card)",
  background: "transparent",
  cursor: "pointer",
  fontSize: 15,
  fontWeight: 600,
  color: "var(--text-primary)",
};
function cta(disabled: boolean): React.CSSProperties {
  return {
    minHeight: 52,
    borderRadius: 9999,
    border: "none",
    background: disabled ? "var(--text-disabled)" : "var(--accent-primary)",
    color: "var(--accent-foreground)",
    cursor: disabled ? "not-allowed" : "pointer",
    fontSize: 15,
    fontWeight: 600,
  };
}
const toastWrap: React.CSSProperties = {
  position: "fixed",
  bottom: 80,
  left: 0,
  right: 0,
  display: "flex",
  justifyContent: "center",
  zIndex: 60,
  pointerEvents: "none",
};
const toastInner: React.CSSProperties = {
  background: "rgba(0,0,0,0.75)",
  color: "#fff",
  padding: "10px 20px",
  borderRadius: 9999,
  fontSize: 14,
};
