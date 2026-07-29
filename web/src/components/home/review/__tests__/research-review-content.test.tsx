/**
 * research-review-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 * 실행하려면 `npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` 후 설정 필요.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, within } from "@testing-library/react";
import { ResearchReviewContent } from "../research-review-content";

const mockPayload = {
  one_line_definition: "한 줄 정의 내용",
  key_concepts: "핵심 개념 설명 내용",
  problems_solved: "해결하는 문제 내용",
  why_it_matters: "왜 중요한가 내용",
  vs_existing_tech: "기존 기술 차이 내용",
  user_relevance: "사용자 관련성 내용",
  learning_goals: "학습 목표 내용",
  learning_time_difficulty: { estimated_hours: 10, difficulty: "intermediate" },
  practical_applicability: "실무 적용 가능성 내용",
  risks: "위험 요소 내용",
  recommendation_reason: "추천 이유 내용",
  reference_sources: ["https://example.com/source1", "https://example.com/source2"],
  honest_box: { content: "확인되지 않은 내용", severity: "standard" },
};

const defaultProps = {
  signalId: "sig-001",
  signalTitle: "LLM Agents 최신 동향",
  payload: mockPayload,
};

describe("ResearchReviewContent", () => {
  it("AC-1: signal title이 h1으로 렌더링된다", () => {
    render(<ResearchReviewContent {...defaultProps} />);
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toHaveTextContent("LLM Agents 최신 동향");
  });

  it("AC-2: 13개 섹션이 순서대로 렌더링된다 (data-section-key 확인)", () => {
    render(<ResearchReviewContent {...defaultProps} />);
    const expectedKeys = [
      "one_line_definition",
      "key_concepts",
      "problems_solved",
      "why_it_matters",
      "vs_existing_tech",
      "user_relevance",
      "learning_goals",
      "learning_time_difficulty",
      "practical_applicability",
      "risks",
      "recommendation_reason",
      "reference_sources",
    ];
    const headings = screen.getAllByRole("heading", { level: 2 });
    // 12개 h2 + HonestBox 제목(h2 아님) → h2는 12개
    expect(headings).toHaveLength(12);
    headings.forEach((h, i) => {
      expect(h).toHaveAttribute("data-section-key", expectedKeys[i]);
    });
  });

  it("AC-3: Section 6 위에 '현재 프로필 기준' 레이블이 표시된다", () => {
    render(<ResearchReviewContent {...defaultProps} />);
    expect(screen.getByText("현재 프로필 기준")).toBeInTheDocument();
    const section6Heading = screen
      .getAllByRole("heading", { level: 2 })
      .find((h) => h.getAttribute("data-section-key") === "user_relevance");
    expect(section6Heading).toBeTruthy();
    // 레이블이 section6 h2 다음 형제에 위치 (DOM 순서 확인)
    const label = screen.getByText("현재 프로필 기준");
    expect(label.compareDocumentPosition(section6Heading!)).toBe(
      Node.DOCUMENT_POSITION_PRECEDING
    );
  });

  it("AC-4a: honest_box.content가 비어있으면 HonestBox를 렌더링하지 않는다", () => {
    const props = {
      ...defaultProps,
      payload: { ...mockPayload, honest_box: { content: "", severity: "standard" } },
    };
    render(<ResearchReviewContent {...props} />);
    expect(screen.queryByText("AI가 확인하지 못한 정보")).not.toBeInTheDocument();
  });

  it("AC-4b: honest_box.content가 있으면 HonestBox를 표시한다", () => {
    render(<ResearchReviewContent {...defaultProps} />);
    expect(screen.getByText("AI가 확인하지 못한 정보")).toBeInTheDocument();
    expect(screen.getByText("확인되지 않은 내용")).toBeInTheDocument();
  });

  it("AC-4c: severity='high'이면 warning border 스타일이 적용된다", () => {
    const props = {
      ...defaultProps,
      payload: {
        ...mockPayload,
        honest_box: { content: "위험 내용", severity: "high" },
      },
    };
    const { container } = render(<ResearchReviewContent {...props} />);
    // HonestBox 컨테이너에 border-left 스타일 확인
    const honestBoxContainer = container.querySelector(
      '[style*="status-warning"]'
    );
    expect(honestBoxContainer).toBeTruthy();
  });

  it("AC-5a: 'AI에게 질문하기' 링크가 올바른 href를 가진다", () => {
    render(<ResearchReviewContent {...defaultProps} />);
    const link = screen.getByText("AI에게 질문하기");
    expect(link.closest("a")).toHaveAttribute(
      "href",
      "/home/review/sig-001/chat"
    );
  });

  it("AC-5b: ContextStickyBar가 DOM 마지막에 위치하고 aria-disabled='true'이다", () => {
    const { container } = render(<ResearchReviewContent {...defaultProps} />);
    const button = screen.getByRole("button", { name: /Learn Now/i });
    expect(button).toHaveAttribute("aria-disabled", "true");

    // ContextStickyBar가 "AI에게 질문하기" 링크보다 DOM 후순에 위치
    const link = screen.getByText("AI에게 질문하기");
    expect(
      link.compareDocumentPosition(button)
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });
});
