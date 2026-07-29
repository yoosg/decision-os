/**
 * context-sticky-bar.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 * 실행하려면 `npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` 후 설정 필요.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ContextStickyBar } from "../context-sticky-bar";

const defaultProps = {
  signalId: "sig-001",
  reviewId: "rev-001",
  barGateOverride: null,
  recommendationReason: "추천 이유입니다.",
};

// useRouter mock
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

describe("ContextStickyBar", () => {
  // AC-1: 초기 disabled 상태
  it("8.1: 초기 disabled 상태 — lock 아이콘, hint text, Queue/Ignore hidden", () => {
    render(<ContextStickyBar {...defaultProps} />);

    // Learn Now 버튼 disabled
    const btn = screen.getByRole("button", { name: /Learn Now/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-disabled", "true");
    expect(btn).toHaveAttribute("aria-describedby", "ctx-hint");

    // hint text 존재
    expect(screen.getByText(/추천 근거를 먼저 확인해 주세요/i)).toBeInTheDocument();

    // Queue / Ignore 버튼 없음
    expect(screen.queryByRole("button", { name: /Queue/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ignore/i })).not.toBeInTheDocument();
  });

  // AC-2: REQUIRED_SECTIONS 모두 seen → enabled 전환
  it("8.2: REQUIRED_SECTIONS 모두 seen → enabled 전환", async () => {
    // IntersectionObserver mock
    const observers: IntersectionObserver[] = [];
    const mockObserver = jest.fn().mockImplementation((cb) => {
      const obs = { observe: jest.fn(), disconnect: jest.fn() };
      observers.push({ ...obs, callback: cb } as any);
      return obs;
    });
    global.IntersectionObserver = mockObserver;

    // data-section-key h2 요소들을 DOM에 삽입
    const sectionKeys = [
      "one_line_definition", "key_concepts", "problems_solved", "why_it_matters",
      "vs_existing_tech", "user_relevance", "risks", "recommendation_reason",
    ];
    const container = document.createElement("div");
    sectionKeys.forEach((key) => {
      const h2 = document.createElement("h2");
      h2.setAttribute("data-section-key", key);
      container.appendChild(h2);
    });
    document.body.appendChild(container);

    render(<ContextStickyBar {...defaultProps} />);

    // 모든 섹션 intersection 트리거 (mock)
    await act(async () => {
      observers.forEach((obs: any) => {
        if (obs.callback) {
          sectionKeys.forEach((key) => {
            const el = document.querySelector(`[data-section-key="${key}"]`);
            if (el) obs.callback([{ isIntersecting: true, target: el }]);
          });
        }
      });
    });

    // enabled 상태: Learn Now 버튼이 활성화되어야 함
    const btn = screen.getByRole("button", { name: "Learn Now" });
    expect(btn).not.toBeDisabled();

    document.body.removeChild(container);
  });

  // AC-3: bar_gate_override="enabled" → 즉시 enabled
  it("8.3: bar_gate_override='enabled' → 즉시 enabled 상태", () => {
    render(<ContextStickyBar {...defaultProps} barGateOverride="enabled" />);

    // Learn Now 버튼 활성화
    const btn = screen.getByRole("button", { name: "Learn Now" });
    expect(btn).not.toBeDisabled();

    // Queue / Ignore 버튼 존재
    expect(screen.getByRole("button", { name: /Queue/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ignore/i })).toBeInTheDocument();

    // hint text 없음
    expect(screen.queryByText(/추천 근거를 먼저 확인해 주세요/i)).not.toBeInTheDocument();
  });

  // AC-8: ARIA 속성
  it("8.4: ARIA 속성 — disabled/enabled 각 상태", () => {
    // disabled 상태
    const { rerender } = render(<ContextStickyBar {...defaultProps} />);
    const disabledBtn = screen.getByRole("button", { name: /Learn Now/i });
    expect(disabledBtn).toHaveAttribute(
      "aria-label",
      "Learn Now — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요"
    );
    expect(disabledBtn).toHaveAttribute("aria-disabled", "true");

    // enabled 상태
    rerender(<ContextStickyBar {...defaultProps} barGateOverride="enabled" />);
    const enabledBtn = screen.getByRole("button", { name: "Learn Now" });
    expect(enabledBtn).toHaveAttribute("aria-label", "Learn Now");

    const queueBtn = screen.getByRole("button", { name: /Queue/i });
    expect(queueBtn).toHaveAttribute("aria-label", "Queue — 이 Signal을 큐에 저장");

    const ignoreBtn = screen.getByRole("button", { name: /Ignore/i });
    expect(ignoreBtn).toHaveAttribute("aria-label", "Ignore — 이 Signal을 무시");
  });

  // AC-6: Queue 선택 시 Bottom Sheet 오픈
  it("8.5: Queue 클릭 시 Bottom Sheet 오픈", () => {
    render(<ContextStickyBar {...defaultProps} barGateOverride="enabled" />);

    const queueBtn = screen.getByRole("button", { name: /Queue/i });
    fireEvent.click(queueBtn);

    // Bottom Sheet 다이얼로그 확인
    expect(screen.getByRole("dialog", { name: /학습 일정 선택/i })).toBeInTheDocument();
    expect(screen.getByText("언제 학습할까요?")).toBeInTheDocument();
    expect(screen.getByText("오늘")).toBeInTheDocument();
    expect(screen.getByText("이번 주")).toBeInTheDocument();
    expect(screen.getByText("나중에")).toBeInTheDocument();
  });
});
