/**
 * queue-item.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 * 실행하려면 `npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` 후 설정 필요.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent } from "@testing-library/react";
import { QueueItem } from "../queue-item";

describe("QueueItem", () => {
  const defaultProps = {
    title: "LLM Agents 최신 동향",
    queueTiming: "today" as const,
    estimatedMinutes: 30,
    isOverdue: false,
    onTap: jest.fn(),
    onReschedule: jest.fn(),
  };

  it("queueTiming에 맞는 영어 타이밍 배지가 표시된다", () => {
    render(<QueueItem {...defaultProps} queueTiming="this_week" />);
    expect(screen.getByText("This Week")).toBeInTheDocument();
  });

  it("isOverdue=false일 때 미완료 배지가 없다", () => {
    render(<QueueItem {...defaultProps} isOverdue={false} />);
    expect(screen.queryByText("미완료")).not.toBeInTheDocument();
  });

  it("isOverdue=true일 때 미완료 배지가 표시된다", () => {
    render(<QueueItem {...defaultProps} isOverdue={true} />);
    expect(screen.getByText("미완료")).toBeInTheDocument();
  });

  it("메인 버튼 aria-label composite — Today 예약됨", () => {
    render(<QueueItem {...defaultProps} queueTiming="today" />);
    const mainButton = screen.getByRole("button", {
      name: "Today 예약됨, LLM Agents 최신 동향, 약 30분",
    });
    expect(mainButton).toBeInTheDocument();
  });

  it('"일정 변경" 버튼은 별도 aria-label을 가진 독립된 요소다', () => {
    render(<QueueItem {...defaultProps} />);
    const rescheduleButton = screen.getByRole("button", {
      name: "일정 변경 — LLM Agents 최신 동향",
    });
    expect(rescheduleButton).toBeInTheDocument();
  });

  it("메인 버튼과 일정 변경 버튼은 중첩되지 않은 형제 요소다(각각 독립적으로 클릭 이벤트 발생)", () => {
    const onTap = jest.fn();
    const onReschedule = jest.fn();
    render(<QueueItem {...defaultProps} onTap={onTap} onReschedule={onReschedule} />);

    fireEvent.click(screen.getByRole("button", { name: /예약됨/ }));
    expect(onTap).toHaveBeenCalledTimes(1);
    expect(onReschedule).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /^일정 변경/ }));
    expect(onReschedule).toHaveBeenCalledTimes(1);
    expect(onTap).toHaveBeenCalledTimes(1); // 여전히 1회 — 서로 간섭하지 않음
  });

  it("예상 시간 텍스트가 렌더링된다", () => {
    render(<QueueItem {...defaultProps} estimatedMinutes={15} />);
    expect(screen.getByText("약 15분")).toBeInTheDocument();
  });
});
