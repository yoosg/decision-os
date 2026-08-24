/**
 * review-page-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen } from "@testing-library/react";
import { ReviewPageContent } from "../review-page-content";

jest.mock("@/lib/engagement", () => ({ trackEngagement: jest.fn() }));
jest.mock("@/lib/supabase", () => ({ createClient: () => ({ auth: { getSession: async () => ({ data: { session: null } }) } }) }));

const cardPayload = {
  skill_label: "웹폼 만들기", difficulty: "first_step", estimated_minutes: 30,
  deliverable: "예약 폼", success_preview: "목록에 추가됨", prerequisites: "없음",
  how_to_start: "붙여넣기", example_prompt: "만들어줘",
  milestones: [{ action: "a", done_signal: "b" }],
  troubleshooting: [{ symptom: "s", fix: "f" }], success_checklist: ["c"],
};

test("review_type=project_card 면 카드 헤더 블록을 렌더한다", () => {
  render(
    <ReviewPageContent
      signalId="s1"
      signalTitle="카드 제목"
      initialReview={{ id: "r1", status: "completed", signalTitle: "카드 제목", payload: cardPayload, reviewType: "project_card" }}
    />
  );
  expect(screen.getByText("📦 완성하면 이게 나와")).toBeTruthy();
});

test("review_type 이 research/undefined 면 기존 13섹션(핵심 한 줄 요약)을 렌더한다", () => {
  const researchPayload = {
    one_line_definition: "정의", key_concepts: "", problems_solved: "", why_it_matters: "",
    vs_existing_tech: "", user_relevance: "", learning_goals: "",
    learning_time_difficulty: { estimated_hours: 1, difficulty: "beginner" },
    practical_applicability: "", risks: "", recommendation_reason: "", reference_sources: [],
    honest_box: { content: "", severity: "standard" },
  };
  render(
    <ReviewPageContent
      signalId="s2"
      signalTitle="리서치 제목"
      initialReview={{ id: "r2", status: "completed", signalTitle: "리서치 제목", payload: researchPayload }}
    />
  );
  expect(screen.getByText("핵심 한 줄 요약")).toBeTruthy();
});
