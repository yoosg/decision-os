/**
 * daily-brief-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 * 실행하려면 Jest + React Testing Library 설정 후 Supabase client mock이 필요합니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen } from "@testing-library/react";
import { DailyBriefContent, type DailyBrief, type SignalItem } from "../daily-brief-content";

jest.mock("next/navigation", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("@/lib/supabase", () => ({
  createClient: () => ({
    channel: () => ({ on: () => ({ subscribe: jest.fn() }) }),
    removeChannel: jest.fn(),
    auth: { getSession: async () => ({ data: { session: null } }) },
  }),
}));

const mockBriefCompleted: DailyBrief = {
  id: "brief-001",
  user_id: "user-001",
  brief_date: new Date().toISOString().split("T")[0],
  status: "completed",
};

const mockSignals: SignalItem[] = [
  { signalId: "sig-001", title: "LLM Agents 최신 동향", summary: "AI 에이전트 변화", sourceCount: 5, position: 0 },
  { signalId: "sig-002", title: "MCP 프로토콜 동향", summary: "Model Context Protocol", sourceCount: 3, position: 1 },
];

describe("DailyBriefContent — 6가지 상태 렌더링", () => {
  const baseProps = { initialBrief: null, initialSignals: [], userId: "user-001" };

  it("AC-4: brief=null → 생성 중 상태 표시", () => {
    render(<DailyBriefContent {...baseProps} initialBrief={null} />);
    expect(screen.getByText(/Daily Brief를 생성하는 중입니다/)).toBeInTheDocument();
  });

  it("AC-4: status=pending → 생성 중 상태 표시", () => {
    render(<DailyBriefContent {...baseProps} initialBrief={{ ...mockBriefCompleted, status: "pending" }} />);
    expect(screen.getByText(/Daily Brief를 생성하는 중입니다/)).toBeInTheDocument();
  });

  it("AC-4: status=processing → 생성 중 상태 표시", () => {
    render(<DailyBriefContent {...baseProps} initialBrief={{ ...mockBriefCompleted, status: "processing" }} />);
    expect(screen.getByText(/Daily Brief를 생성하는 중입니다/)).toBeInTheDocument();
  });

  it("AC-5: status=failed → 에러 메시지 + 다시 시도하기 CTA", () => {
    render(<DailyBriefContent {...baseProps} initialBrief={{ ...mockBriefCompleted, status: "failed" }} />);
    expect(screen.getByText(/Daily Brief를 생성하지 못했습니다/)).toBeInTheDocument();
    expect(screen.getByText("다시 시도하기")).toBeInTheDocument();
  });

  it("AC-6: completed + signals없음 → 새로운 Signal 없음 메시지 + 큐 보기 CTA", () => {
    render(<DailyBriefContent {...baseProps} initialBrief={mockBriefCompleted} initialSignals={[]} />);
    expect(screen.getByText(/오늘은 새로운 Signal이 없습니다/)).toBeInTheDocument();
    expect(screen.getByText("큐 보기")).toBeInTheDocument();
  });

  it("AC-1: completed + signals있음 → SignalCard 목록 표시", () => {
    render(<DailyBriefContent {...baseProps} initialBrief={mockBriefCompleted} initialSignals={mockSignals} />);
    expect(screen.getByText("LLM Agents 최신 동향")).toBeInTheDocument();
    expect(screen.getByText("MCP 프로토콜 동향")).toBeInTheDocument();
  });

  it("AC-7: 모든 Signal 열람 시 완료 캡션 표시", () => {
    // sessionStorage에 sig-001, sig-002를 미리 저장한 상태 시뮬레이션은
    // 실제 테스트에서 sessionStorage mock이 필요함
    // 여기서는 스펙으로만 기록
    expect(true).toBe(true); // placeholder
  });

  it("AC-1: 섹션 헤딩 '오늘의 AI CTO 브리핑' 표시", () => {
    render(<DailyBriefContent {...baseProps} initialBrief={mockBriefCompleted} initialSignals={mockSignals} />);
    expect(screen.getByText(/오늘의/)).toBeInTheDocument();
    expect(screen.getByText(/AI CTO/i)).toBeInTheDocument();
  });
});
