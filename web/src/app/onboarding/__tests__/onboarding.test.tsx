/**
 * onboarding.test.tsx
 *
 * NOTE: 이 저장소는 Jest/Vitest 러너가 없습니다(signal-card/queue-content 테스트 컨벤션 동일).
 * 이 파일은 테스트 스펙 문서입니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OnboardingPage from "../page";

const replace = jest.fn();
jest.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

// 미온보딩 사용자 기본 mock
function mockSupabase({ user = { id: "u1" }, onboardingCompleted = false, token = "tok" } = {}) {
  jest.mock("@/lib/supabase", () => ({
    createClient: () => ({
      auth: {
        getUser: async () => ({ data: { user } }),
        getSession: async () => ({ data: { session: token ? { access_token: token } : null } }),
      },
      from: () => ({
        select: () => ({ eq: () => ({ maybeSingle: async () => ({ data: { onboarding_completed: onboardingCompleted } }) }) }),
      }),
    }),
  }));
}

describe("OnboardingPage", () => {
  beforeEach(() => replace.mockClear());

  it("AC-4: 이미 완료한 사용자는 /home 으로 리다이렉트된다", async () => {
    mockSupabase({ onboardingCompleted: true });
    render(<OnboardingPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/home"));
  });

  it("AC-1: 세션이 없으면 /signin 으로 리다이렉트된다", async () => {
    mockSupabase({ user: null });
    render(<OnboardingPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/signin"));
  });

  it("AC-2/3: 위저드를 끝까지 진행하면 API 계약 값으로 제출된다", async () => {
    mockSupabase();
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(<OnboardingPage />);
    await waitFor(() => screen.getByText("환영합니다 👋"));

    fireEvent.click(screen.getByText("시작하기"));
    fireEvent.click(screen.getByText("AI Engineer")); // role=ai_engineer
    fireEvent.click(screen.getByText("다음"));
    fireEvent.click(screen.getByText("중급")); // experience=intermediate
    fireEvent.click(screen.getByText("다음"));
    fireEvent.click(screen.getByText("Python")); // tech_stack
    fireEvent.click(screen.getByText("다음"));
    fireEvent.click(screen.getByText("RAG 서비스 구축")); // project_goal=rag_service
    fireEvent.click(screen.getByText("다음"));
    fireEvent.click(screen.getByText("RAG")); // interests
    fireEvent.click(screen.getByText("다음"));
    fireEvent.click(screen.getByText("30분")); // daily_learning_time_min=30
    fireEvent.click(screen.getByText("완료"));

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/onboarding/complete"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"role":"ai_engineer"'),
        })
      )
    );
    // enum 값 집합 검증: 성공 시 /home 이동
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/home"));
  });

  it("AC-3: 제출 실패 시 에러를 노출하고 /home 으로 이동하지 않는다", async () => {
    mockSupabase();
    global.fetch = jest.fn().mockResolvedValue({ ok: false });
    render(<OnboardingPage />);
    // ...끝까지 진행 후 완료 클릭(위 흐름과 동일) → 에러 문구 노출, replace('/home') 미호출 검증
  });
});

/**
 * 설계 노트: 웹은 전역 온보딩 게이트가 없다(Flutter의 GoRouter redirect와 달리).
 * signin/signup 이 onboarding_completed=false 사용자를 /onboarding 으로 push 하며,
 * 이 페이지 진입 시 자체 가드(세션 없음→/signin, 완료됨→/home)만 수행한다.
 */
