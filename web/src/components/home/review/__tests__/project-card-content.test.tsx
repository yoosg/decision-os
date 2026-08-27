/**
 * project-card-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent } from "@testing-library/react";
import { ProjectCardContent } from "../project-card-content";

const payload = {
  skill_label: "웹폼 만들고 데이터 저장하기",
  difficulty: "first_step",
  estimated_minutes: 30,
  deliverable: "간단한 예약 폼 웹페이지",
  success_preview: "폼에 입력하면 목록에 추가돼요",
  prerequisites: "없어요, 바로 시작!",
  how_to_start: "AI 코딩 도구를 열고 붙여넣으세요.",
  example_prompt: "예약 폼 만들어줘.",
  milestones: [{ action: "폼 만들기", done_signal: "입력칸 보임" }],
  troubleshooting: [{ symptom: "저장 안 됨", fix: "다시 요청" }],
  success_checklist: ["폼이 보인다"],
};

test("헤더에 제목·난이도 뱃지·시간·스킬라벨이 나온다", () => {
  render(<ProjectCardContent signalId="s1" signalTitle="예약 폼 만들기" payload={payload} />);
  expect(screen.getByText("예약 폼 만들기")).toBeTruthy();
  expect(screen.getByText(/첫걸음/)).toBeTruthy();       // first_step → 첫걸음
  expect(screen.getByText(/30분/)).toBeTruthy();
  expect(screen.getByText(/웹폼 만들고 데이터 저장하기/)).toBeTruthy();
});

test("⑦ 결과 버튼: 단일 선택(클릭 시 활성) + 재탭 해제", () => {
  // reviewId 미전달 → 로컬 전용(저장 스킵). 결과는 로컬 상태로만 토글된다.
  render(<ProjectCardContent signalId="s1" signalTitle="t" payload={payload} />);
  const successBtn = screen.getByRole("button", { name: /성공/ });
  fireEvent.click(successBtn);
  expect(successBtn.getAttribute("aria-pressed")).toBe("true"); // 선택됨
  fireEvent.click(successBtn);
  expect(successBtn.getAttribute("aria-pressed")).toBe("false"); // 재탭 해제
});
