/**
 * profile-content.test.tsx
 *
 * NOTE: 이 저장소는 Jest/Vitest 러너가 없습니다(스펙 문서 컨벤션).
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProfileContent, type ProfileData } from "../profile-content";

jest.mock("next/navigation", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "tok" } } }),
      signOut: async () => ({}),
    },
  }),
}));

const initial: ProfileData = {
  displayName: "Sgyoo",
  role: "ai_engineer",
  experienceLevel: "intermediate",
  techStack: ["Python", "FastAPI"],
  projectGoal: "rag_service",
  interests: ["RAG"],
  dailyLearningTimeMin: 30,
};

describe("ProfileContent", () => {
  beforeEach(() => { global.fetch = jest.fn(); });

  it("AC-1: 조회 모드에서 값의 한글/영문 라벨을 표시한다(스텁 아님)", () => {
    render(<ProfileContent initial={initial} />);
    expect(screen.getByText("AI Engineer")).toBeInTheDocument();
    expect(screen.getByText("중급")).toBeInTheDocument();
    expect(screen.getByText("RAG 서비스 구축")).toBeInTheDocument();
    expect(screen.getByText("30분")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.queryByText("구현 예정")).not.toBeInTheDocument();
  });

  it("AC-2: 저장 시 PATCH /api/v1/users/profile 로 변경 필드를 전송한다", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: true });
    render(<ProfileContent initial={initial} />);
    fireEvent.click(screen.getByRole("button", { name: "프로필 편집" }));
    fireEvent.click(screen.getByText("고급")); // experience → advanced
    fireEvent.click(screen.getByText("15분")); // daily → 15
    fireEvent.click(screen.getByText("저장"));

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/users/profile"),
        expect.objectContaining({ method: "PATCH", body: expect.stringContaining('"experience_level":"advanced"') })
      )
    );
    // daily_learning_time_min ∈ {15,30,60}
    const body = (global.fetch as jest.Mock).mock.calls[0][1].body;
    expect(body).toContain('"daily_learning_time_min":15');
    await waitFor(() => expect(screen.getByText("프로필이 저장됐습니다. 다음 오늘의 브리핑에 반영됩니다.")).toBeInTheDocument());
  });

  it("AC-3: 편집 취소 시 원래 값으로 복원되고 저장 API를 호출하지 않는다", () => {
    render(<ProfileContent initial={initial} />);
    fireEvent.click(screen.getByRole("button", { name: "프로필 편집" }));
    fireEvent.click(screen.getByText("고급")); // 변경
    fireEvent.click(screen.getByText("취소"));
    // 다시 조회 모드에서 원래 값(중급) 유지
    expect(screen.getByText("중급")).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("AC-2: 저장 실패 시 에러 토스트를 노출한다", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: false });
    render(<ProfileContent initial={initial} />);
    fireEvent.click(screen.getByRole("button", { name: "프로필 편집" }));
    fireEvent.click(screen.getByText("저장"));
    await waitFor(() => expect(screen.getByText("저장 중 오류가 발생했습니다. 다시 시도해 주세요.")).toBeInTheDocument());
  });
});
