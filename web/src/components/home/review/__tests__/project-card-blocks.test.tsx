/**
 * project-card-blocks.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent } from "@testing-library/react";
import { ProjectCardBlocks } from "../project-card-blocks";

const payload = {
  skill_label: "웹폼 만들고 데이터 저장하기",
  difficulty: "first_step",
  estimated_minutes: 30,
  deliverable: "간단한 예약 폼 웹페이지",
  success_preview: "폼에 입력하면 목록에 추가돼요",
  prerequisites: "없어요, 바로 시작!",
  how_to_start: "AI 코딩 도구를 열고 아래 프롬프트를 붙여넣으세요.",
  example_prompt: "예약 폼 만들어줘. 날짜·시간·인원 입력받고 목록에 저장해줘.",
  milestones: [
    { action: "폼 화면 만들기", done_signal: "입력칸이 보임" },
    { action: "저장 붙이기", done_signal: "목록에 추가됨" },
  ],
  troubleshooting: [{ symptom: "저장이 안 돼요", fix: "저장 코드를 추가해달라고 다시 요청하세요." }],
  success_checklist: ["폼이 보인다", "입력하면 목록에 남는다"],
};

test("①~⑥ 블록 헤더와 내용이 렌더된다", () => {
  render(<ProjectCardBlocks payload={payload} />);
  expect(screen.getByText("📦 완성하면 이게 나와")).toBeTruthy();
  expect(screen.getByText(payload.deliverable)).toBeTruthy();
  expect(screen.getByText("🧰 시작 전 준비물")).toBeTruthy();
  expect(screen.getByText("🚀 이렇게 시작해")).toBeTruthy();
  expect(screen.getByText("🗺️ 진행 과정")).toBeTruthy();
  expect(screen.getByText("🆘 막히면 이렇게")).toBeTruthy();
  expect(screen.getByText("✅ 다 됐는지 확인")).toBeTruthy();
});

test("④ 마일스톤 체크박스를 켜면 진도 카운트가 오른다", () => {
  render(<ProjectCardBlocks payload={payload} />);
  expect(screen.getByText("0/2")).toBeTruthy();
  const checkboxes = screen.getAllByRole("checkbox");
  fireEvent.click(checkboxes[0]);
  expect(screen.getByText("1/2")).toBeTruthy();
});

test("③ 복사 버튼이 example_prompt를 클립보드에 쓴다", () => {
  const writeText = jest.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  render(<ProjectCardBlocks payload={payload} />);
  fireEvent.click(screen.getByRole("button", { name: /복사/ }));
  expect(writeText).toHaveBeenCalledWith(payload.example_prompt);
});
