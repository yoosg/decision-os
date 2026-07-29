/**
 * history-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다. (signal-card.test.tsx / queue-content.test.tsx 컨벤션 동일)
 * 실행하려면 `npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` 후 설정 필요.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent } from "@testing-library/react";
import { HistoryContent, type HistoryItemData } from "../history-content";

const push = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

function makeItem(overrides: Partial<HistoryItemData> = {}): HistoryItemData {
  return {
    decisionId: "d1",
    signalId: "s1",
    title: "LLM Agents 최신 동향",
    choice: "learn_now",
    outcomeStatus: null,
    createdAt: "2026-07-05T02:00:00.000Z",
    ...overrides,
  };
}

describe("HistoryContent", () => {
  beforeEach(() => push.mockClear());

  it("항목이 하나도 없으면 AC-1 빈 상태 문구가 표시된다", () => {
    render(<HistoryContent items={[]} />);
    expect(
      screen.getByText(
        (_, node) =>
          node?.textContent ===
          "아직 기록된 학습 결정이 없습니다. Signal을 읽고 Learn Now를 선택하면 이곳에 기록이 시작됩니다."
      )
    ).toBeInTheDocument();
  });

  it("서로 다른 월의 항목은 각각 월 구분선으로 나뉜다", () => {
    render(
      <HistoryContent
        items={[
          makeItem({ decisionId: "d1", createdAt: "2026-07-05T02:00:00.000Z" }),
          makeItem({ decisionId: "d2", createdAt: "2026-06-20T02:00:00.000Z" }),
        ]}
      />
    );
    // KST 기준 (UTC+9)
    expect(screen.getByText("2026년 7월")).toBeInTheDocument();
    expect(screen.getByText("2026년 6월")).toBeInTheDocument();
  });

  it("Learn Now 후 Outcome 미기록 항목은 미완료(outcome-pending) 스타일로 표시된다 (AC-5)", () => {
    render(<HistoryContent items={[makeItem({ choice: "learn_now", outcomeStatus: null })]} />);
    // 미완료 도트는 "?" 글리프 + IN PROGRESS 타입 라벨
    expect(screen.getByText("IN PROGRESS")).toBeInTheDocument();
  });

  it("Outcome 이 기록되면 Outcome 스타일(영문 라벨)로 전환된다 (AC-2)", () => {
    render(<HistoryContent items={[makeItem({ choice: "learn_now", outcomeStatus: "applied" })]} />);
    expect(screen.getByText("APPLIED")).toBeInTheDocument();
    // 접근성: 버튼 composite aria-label
    expect(
      screen.getByRole("button", { name: /Applied 결과 — LLM Agents 최신 동향/ })
    ).toBeInTheDocument();
  });

  it("Queue/Ignore 결정은 Outcome 이 없어도 Decision 스타일 라벨을 유지한다 (설계 결정 1)", () => {
    render(
      <HistoryContent
        items={[
          makeItem({ decisionId: "q", choice: "queue", outcomeStatus: null, createdAt: "2026-07-05T02:00:00.000Z" }),
          makeItem({ decisionId: "i", choice: "ignore", outcomeStatus: null, createdAt: "2026-07-05T02:00:00.000Z" }),
        ]}
      />
    );
    expect(screen.getByText("QUEUE")).toBeInTheDocument();
    expect(screen.getByText("IGNORE")).toBeInTheDocument();
  });

  it("항목 탭 시 체인 상세로 이동한다 (AC-4)", () => {
    render(<HistoryContent items={[makeItem({ signalId: "sig-9" })]} />);
    fireEvent.click(screen.getByRole("button"));
    expect(push).toHaveBeenCalledWith("/history/chain/sig-9");
  });
});

/**
 * 추가 스펙 (page.tsx 서버 컴포넌트 매핑 — 렌더 테스트 범위 밖, 문서화):
 * - outcomes 1:N 임베드 배열에서 created_at 내림차순 첫 요소만 "최신 Outcome"으로 사용한다 (설계 결정 2).
 *   예: outcomes=[{status:'dropped',created_at:'...T01'},{status:'completed',created_at:'...T05'}]
 *       → outcomeStatus === 'completed'.
 * - reviews!inner 로 review/signal 이 없는 decision 은 리스트에서 제외된다.
 */
