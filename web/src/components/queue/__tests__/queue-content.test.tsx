/**
 * queue-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 * 실행하려면 `npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` 후 설정 필요.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueueContent, type QueueGroups } from "../queue-content";

// useRouter mock
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

// Supabase 세션 mock
jest.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({
        data: { session: { access_token: "test-token" } },
      }),
    },
  }),
}));

function makeGroups(overrides: Partial<QueueGroups> = {}): QueueGroups {
  return {
    today: [],
    this_week: [],
    later: [],
    ...overrides,
  };
}

describe("QueueContent", () => {
  const item = {
    decisionId: "d1",
    signalId: "s1",
    title: "LLM Agents 최신 동향",
    queueTiming: "today" as const,
    isOverdue: false,
  };

  beforeEach(() => {
    global.fetch = jest.fn();
  });

  it("모든 그룹이 비어있으면 전체 빈 상태 메시지가 표시된다", () => {
    render(<QueueContent groups={makeGroups()} estimatedMinutes={30} userId="u1" />);
    expect(
      screen.getByText((_, node) => node?.textContent === "큐에 저장된 학습 항목이 없습니다. Signal을 읽고 Queue를 선택하면 여기에 저장됩니다.")
    ).toBeInTheDocument();
  });

  it("항목이 있는 그룹만 헤딩과 함께 렌더링되고, 빈 그룹은 숨겨진다", () => {
    render(
      <QueueContent
        groups={makeGroups({ today: [item] })}
        estimatedMinutes={30}
        userId="u1"
      />
    );
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.queryByText("This Week")).not.toBeInTheDocument();
    expect(screen.queryByText("Later")).not.toBeInTheDocument();
    expect(screen.getByText("LLM Agents 최신 동향")).toBeInTheDocument();
  });

  it("일정 변경 성공 시 항목이 새 그룹으로 낙관적으로 이동한 상태를 유지한다", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({}) });

    render(
      <QueueContent
        groups={makeGroups({ today: [item] })}
        estimatedMinutes={30}
        userId="u1"
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /^일정 변경/ }));
    fireEvent.click(screen.getByRole("button", { name: "Later" }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/decisions/d1"),
        expect.objectContaining({ method: "PATCH" })
      );
    });

    expect(screen.queryByText("Today")).not.toBeInTheDocument();
    expect(screen.getByText("Later")).toBeInTheDocument();
  });

  it("일정 변경 PATCH 실패 시 이전 그룹 상태로 롤백되고 오류 토스트가 표시된다", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: false });

    render(
      <QueueContent
        groups={makeGroups({ today: [item] })}
        estimatedMinutes={30}
        userId="u1"
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /^일정 변경/ }));
    fireEvent.click(screen.getByRole("button", { name: "Later" }));

    await waitFor(() => {
      expect(
        screen.getByText("저장 중 오류가 발생했습니다. 다시 시도해 주세요.")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.queryByText("Later")).not.toBeInTheDocument();
  });
});
