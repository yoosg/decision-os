"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL, getAccessToken } from "@/lib/api";
import { QueueItem, type QueueTiming } from "./queue-item";
import { RescheduleSheet } from "./reschedule-sheet";

export interface QueueItemData {
  decisionId: string;
  signalId: string;
  title: string;
  queueTiming: QueueTiming;
  isOverdue: boolean;
}

export type QueueGroups = Record<QueueTiming, QueueItemData[]>;

interface QueueContentProps {
  groups: QueueGroups;
  estimatedMinutes: number;
}

const GROUP_ORDER: Array<{ key: QueueTiming; label: string }> = [
  { key: "today", label: "Today" },
  { key: "this_week", label: "This Week" },
  { key: "later", label: "Later" },
];

async function postDecisionPatch(decisionId: string, queueTiming: QueueTiming) {
  const token = await getAccessToken();
  if (!token) throw new Error("Unauthenticated");

  const res = await fetch(`${API_BASE_URL}/api/v1/decisions/${decisionId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ queue_timing: queueTiming }),
  });
  if (!res.ok) throw new Error("Decision update failed");
  return res.json();
}

export function QueueContent({ groups: initialGroups, estimatedMinutes }: QueueContentProps) {
  const router = useRouter();
  const [groups, setGroups] = useState<QueueGroups>(initialGroups);
  const [rescheduleDecisionId, setRescheduleDecisionId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const isEmpty = GROUP_ORDER.every(({ key }) => groups[key].length === 0);

  const findItem = (decisionId: string): QueueItemData | undefined => {
    for (const { key } of GROUP_ORDER) {
      const found = groups[key].find((i) => i.decisionId === decisionId);
      if (found) return found;
    }
    return undefined;
  };

  const moveItem = (
    prev: QueueGroups,
    decisionId: string,
    targetTiming: QueueTiming,
    data: Omit<QueueItemData, "decisionId">
  ): QueueGroups => {
    const next: QueueGroups = {
      today: prev.today.filter((i) => i.decisionId !== decisionId),
      this_week: prev.this_week.filter((i) => i.decisionId !== decisionId),
      later: prev.later.filter((i) => i.decisionId !== decisionId),
    };
    next[targetTiming] = [...next[targetTiming], { ...data, decisionId, queueTiming: targetTiming }];
    return next;
  };

  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(null), 3000);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  const handleReschedule = async (decisionId: string, newTiming: QueueTiming) => {
    const item = findItem(decisionId);
    if (!item) return;
    const previousTiming = item.queueTiming;
    const previousIsOverdue = item.isOverdue;

    setGroups((prev) => moveItem(prev, decisionId, newTiming, { ...item, isOverdue: false }));
    setRescheduleDecisionId(null);

    try {
      await postDecisionPatch(decisionId, newTiming);
    } catch {
      setGroups((prev) =>
        moveItem(prev, decisionId, previousTiming, { ...item, isOverdue: previousIsOverdue })
      );
      setToastMessage("저장 중 오류가 발생했습니다. 다시 시도해 주세요.");
    }
  };

  const handleTap = (signalId: string) => {
    router.push(`/queue/review/${signalId}`);
  };

  const rescheduleItem = rescheduleDecisionId ? findItem(rescheduleDecisionId) : undefined;

  return (
    <section>
      {toastMessage && (
        <div
          role="status"
          aria-live="assertive"
          style={{
            position: "fixed",
            bottom: "80px",
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

      {isEmpty ? (
        <p className="text-body" style={{ color: "var(--text-secondary)" }}>
          아직 보관한 학습 항목이 없습니다. 기술 소식을 읽고 &lsquo;나중에 학습&rsquo;을 선택하면 여기에 저장됩니다.
        </p>
      ) : (
        GROUP_ORDER.map(({ key, label }) => {
          const items = groups[key];
          if (items.length === 0) return null;
          return (
            <div key={key} style={{ marginBottom: "24px" }}>
              <h2 className="text-section-title" lang="en" style={{ marginBottom: "12px" }}>
                {label}
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {items.map((item) => (
                  <QueueItem
                    key={item.decisionId}
                    title={item.title}
                    queueTiming={item.queueTiming}
                    estimatedMinutes={estimatedMinutes}
                    isOverdue={item.isOverdue}
                    onTap={() => handleTap(item.signalId)}
                    onReschedule={() => setRescheduleDecisionId(item.decisionId)}
                  />
                ))}
              </div>
            </div>
          );
        })
      )}

      {rescheduleDecisionId && (
        <RescheduleSheet
          currentTiming={rescheduleItem?.queueTiming ?? "today"}
          onSelect={(timing) => handleReschedule(rescheduleDecisionId, timing)}
          onClose={() => setRescheduleDecisionId(null)}
        />
      )}
    </section>
  );
}
