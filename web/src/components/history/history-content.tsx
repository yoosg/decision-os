"use client";

import { useRouter } from "next/navigation";
import { kstYearMonth, formatMonthDivider } from "@/lib/kst";
import { MemoryTimelineItem, type DotStyle } from "./memory-timeline-item";
import type { OutcomeStatus } from "@/components/home/outcome/outcome-options";

export interface HistoryItemData {
  decisionId: string;
  signalId: string;
  title: string;
  choice: "learn_now" | "queue" | "ignore";
  outcomeStatus: OutcomeStatus | null;
  createdAt: string;
}

// 결정/Outcome 상태 → 도트 스타일 (설계 결정 1, AC-2/AC-5)
function resolveDotStyle(item: HistoryItemData): DotStyle {
  if (item.outcomeStatus !== null) {
    return { kind: "outcome", status: item.outcomeStatus };
  }
  // Learn Now 후 Outcome 미기록 → 미완료 스타일 (AC-5 예외)
  if (item.choice === "learn_now") {
    return { kind: "outcome-pending" };
  }
  // Queue/Ignore 는 Outcome 이 발생하지 않으므로 영구 Decision 스타일
  return { kind: "decision", choice: item.choice };
}

interface Props {
  items: HistoryItemData[];
}

export function HistoryContent({ items }: Props) {
  const router = useRouter();

  if (items.length === 0) {
    return (
      <p className="text-body" style={{ color: "var(--text-secondary)" }}>
        아직 기록된 학습 결정이 없습니다. <span lang="en">Signal</span>을 읽고{" "}
        <span lang="en">Learn Now</span>를 선택하면 이곳에 기록이 시작됩니다.
      </p>
    );
  }

  // 이미 역시간순 정렬된 상태 — 순서 유지하며 월별 그룹핑만 수행
  const groups: Array<{ yearMonth: string; items: HistoryItemData[] }> = [];
  for (const item of items) {
    const ym = kstYearMonth(item.createdAt);
    const last = groups[groups.length - 1];
    if (last && last.yearMonth === ym) {
      last.items.push(item);
    } else {
      groups.push({ yearMonth: ym, items: [item] });
    }
  }

  return (
    <section>
      {groups.map((group) => (
        <div key={group.yearMonth} style={{ marginBottom: "24px" }}>
          <h2
            className="text-caption"
            style={{ color: "var(--text-secondary)", marginBottom: "12px" }}
          >
            {formatMonthDivider(group.yearMonth)}
          </h2>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {group.items.map((item) => (
              <MemoryTimelineItem
                key={item.decisionId}
                title={item.title}
                dateISO={item.createdAt}
                dotStyle={resolveDotStyle(item)}
                onTap={() => router.push(`/history/chain/${item.signalId}`)}
              />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
