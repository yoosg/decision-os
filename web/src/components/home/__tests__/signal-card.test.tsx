/**
 * signal-card.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 * 실행하려면 `npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` 후 설정 필요.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent } from "@testing-library/react";
import { SignalCard } from "../signal-card";

describe("SignalCard", () => {
  const defaultProps = {
    id: "sig-001",
    title: "LLM Agents 최신 동향",
    relevanceTag: "AI 에이전트 프레임워크의 핵심 변화",
    sourceCount: 7,
    isSeen: false,
    onClick: jest.fn(),
  };

  it("isSeen=false일 때 NEW 배지가 표시된다", () => {
    render(<SignalCard {...defaultProps} isSeen={false} />);
    expect(screen.getByText("NEW")).toBeInTheDocument();
  });

  it("isSeen=true일 때 NEW 배지가 없다", () => {
    render(<SignalCard {...defaultProps} isSeen={true} />);
    expect(screen.queryByText("NEW")).not.toBeInTheDocument();
  });

  it("aria-label composite — NEW 포함 (isSeen=false)", () => {
    render(<SignalCard {...defaultProps} isSeen={false} />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute(
      "aria-label",
      "LLM Agents 최신 동향, NEW, 출처 7개, 읽기 약 5분"
    );
  });

  it("aria-label composite — seen이면 NEW 없음 (isSeen=true)", () => {
    render(<SignalCard {...defaultProps} isSeen={true} />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute(
      "aria-label",
      "LLM Agents 최신 동향, 출처 7개, 읽기 약 5분"
    );
  });

  it("탭 시 onClick 콜백이 호출된다", () => {
    const onClick = jest.fn();
    render(<SignalCard {...defaultProps} onClick={onClick} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("출처 수와 메타 행이 렌더링된다", () => {
    render(<SignalCard {...defaultProps} />);
    expect(screen.getByText(/출처 7개 · 읽기 약 5분/)).toBeInTheDocument();
  });
});
