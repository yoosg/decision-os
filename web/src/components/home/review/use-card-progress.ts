"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase";

export type CardResult = "success" | "stuck" | "dropped";

export interface CardProgress {
  milestonesChecked: Set<number>;
  checklistChecked: Set<number>;
  result: CardResult | null;
  toggleMilestone: (i: number) => void;
  toggleChecklist: (i: number) => void;
  setResult: (r: CardResult | null) => void;
  saveError: boolean;
}

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";
const DEBOUNCE_MS = 600;

async function getToken(): Promise<string | null> {
  const { data: { session } } = await createClient().auth.getSession();
  return session?.access_token ?? null;
}

export function useCardProgress(reviewId: string | null): CardProgress {
  const [milestonesChecked, setMilestones] = useState<Set<number>>(new Set());
  const [checklistChecked, setChecklist] = useState<Set<number>>(new Set());
  const [result, setResultState] = useState<CardResult | null>(null);
  const [saveError, setSaveError] = useState(false);

  // 최신 상태를 debounced save가 읽도록 ref로 유지
  const latest = useRef({ milestonesChecked, checklistChecked, result });
  latest.current = { milestonesChecked, checklistChecked, result };
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // 유저가 최초로 상호작용했는지 — 로드가 사용자 편집을 덮어쓰지 않도록 방지
  const dirtyRef = useRef(false);
  // 언마운트 후 setState 호출을 방지
  const mountedRef = useRef(true);

  // 마운트 시 저장상태 로드(있으면). 토큰/ reviewId 없으면 로컬 전용.
  useEffect(() => {
    if (!reviewId) return;
    let cancelled = false;
    (async () => {
      const token = await getToken();
      if (!token || cancelled) return;
      try {
        const res = await fetch(`${FASTAPI_URL}/api/v1/project-cards/${reviewId}/progress`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok || cancelled) return;
        const json = await res.json();
        const d = json?.data;
        if (!d || cancelled) return;
        // 유저가 이미 상호작용했으면 서버 상태로 덮어쓰지 않음
        if (dirtyRef.current) return;
        setMilestones(new Set<number>(d.milestones_checked ?? []));
        setChecklist(new Set<number>(d.checklist_checked ?? []));
        setResultState((d.result as CardResult | null) ?? null);
      } catch {
        // 로드 실패 — 로컬 전용으로 진행
      }
    })();
    return () => { cancelled = true; };
  }, [reviewId]);

  const scheduleSave = useCallback(() => {
    if (!reviewId) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      const token = await getToken();
      if (!token) return; // 미인증 → 로컬 전용
      try {
        const res = await fetch(`${FASTAPI_URL}/api/v1/project-cards/${reviewId}/progress`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            milestones_checked: [...latest.current.milestonesChecked],
            checklist_checked: [...latest.current.checklistChecked],
            result: latest.current.result,
          }),
        });
        if (mountedRef.current) setSaveError(!res.ok);
      } catch {
        if (mountedRef.current) setSaveError(true);
      }
    }, DEBOUNCE_MS);
  }, [reviewId]);

  useEffect(() => () => {
    mountedRef.current = false;
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const toggleMilestone = useCallback((i: number) => {
    dirtyRef.current = true;
    setMilestones((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
    scheduleSave();
  }, [scheduleSave]);

  const toggleChecklist = useCallback((i: number) => {
    dirtyRef.current = true;
    setChecklist((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
    scheduleSave();
  }, [scheduleSave]);

  const setResult = useCallback((r: CardResult | null) => {
    dirtyRef.current = true;
    setResultState(r);
    scheduleSave();
  }, [scheduleSave]);

  return {
    milestonesChecked, checklistChecked, result,
    toggleMilestone, toggleChecklist, setResult, saveError,
  };
}
