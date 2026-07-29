/**
 * contextual-chat.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 * 실행하려면 `npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` 후 설정 필요.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";

// ChatPage는 Next.js params Promise를 받으므로 mock으로 래핑
const TEST_SIGNAL_ID = "sig-test-001";
const TEST_SIGNAL_TITLE = "테스트 기술";
const TEST_REPLY = "훌륭한 질문입니다.";

// Next.js navigation mock
jest.mock("next/navigation", () => ({
  useRouter: () => ({ back: jest.fn(), push: jest.fn() }),
}));

// supabase client mock
jest.mock("@/lib/supabase", () => ({
  createClient: () => ({
    from: () => ({
      select: () => ({
        eq: () => ({
          maybeSingle: async () => ({ data: { title: TEST_SIGNAL_TITLE } }),
        }),
      }),
    }),
    auth: {
      getSession: async () => ({
        data: { session: { access_token: "test-token" } },
      }),
    },
  }),
}));

// fetch mock helper
function mockFetch(reply: string | null, status = 200) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () =>
      reply !== null
        ? { data: { reply }, error: null }
        : { data: null, error: { code: "llm_unavailable" } },
  });
}

// ─── 7.1: 초기 상태 검증 ─────────────────────────────────────────────────────

it("7.1: 초기 상태 — 상단 레이블, AI 첫 메시지, 입력 바 placeholder", async () => {
  const { default: ChatPage } = await import(
    "@/app/(app)/home/review/[signalId]/chat/page"
  );

  await act(async () => {
    render(<ChatPage params={Promise.resolve({ signalId: TEST_SIGNAL_ID })} />);
  });

  // 상단 컨텍스트 레이블
  await waitFor(() => {
    expect(
      screen.getByText(`Research Review — ${TEST_SIGNAL_TITLE}`)
    ).toBeInTheDocument();
  });

  // 초기 AI 메시지
  expect(
    screen.getByText("이 Review에 대해 궁금한 점을 물어보세요.")
  ).toBeInTheDocument();

  // 입력 바 placeholder
  expect(
    screen.getByPlaceholderText("이 Review에 대해 궁금한 점을 물어보세요.")
  ).toBeInTheDocument();
});

// ─── 7.2: 메시지 전송 → 사용자 메시지 추가 + API 호출 ─────────────────────────

it("7.2: 메시지 전송 → 사용자 메시지 스레드 추가, API 호출 확인", async () => {
  mockFetch(TEST_REPLY);
  const { default: ChatPage } = await import(
    "@/app/(app)/home/review/[signalId]/chat/page"
  );

  await act(async () => {
    render(<ChatPage params={Promise.resolve({ signalId: TEST_SIGNAL_ID })} />);
  });

  const input = screen.getByPlaceholderText(
    "이 Review에 대해 궁금한 점을 물어보세요."
  );
  fireEvent.change(input, { target: { value: "첫 번째 질문입니다." } });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /전송/i }));
  });

  expect(screen.getByText("첫 번째 질문입니다.")).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith(
    expect.stringContaining("/api/v1/chat/messages"),
    expect.objectContaining({ method: "POST" })
  );
});

// ─── 7.3: API 성공 → AI 응답 메시지 추가 ─────────────────────────────────────

it("7.3: API 성공 → AI 응답 메시지 스레드 추가", async () => {
  mockFetch(TEST_REPLY);
  const { default: ChatPage } = await import(
    "@/app/(app)/home/review/[signalId]/chat/page"
  );

  await act(async () => {
    render(<ChatPage params={Promise.resolve({ signalId: TEST_SIGNAL_ID })} />);
  });

  const input = screen.getByPlaceholderText(
    "이 Review에 대해 궁금한 점을 물어보세요."
  );
  fireEvent.change(input, { target: { value: "질문입니다." } });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /전송/i }));
  });

  await waitFor(() => {
    expect(screen.getByText(TEST_REPLY)).toBeInTheDocument();
  });
});

// ─── 7.4: API 실패(503) → 인라인 에러 + 재시도 CTA ──────────────────────────

it("7.4: API 실패(503) → 인라인 에러 + 재시도 CTA 표시", async () => {
  mockFetch(null, 503);
  const { default: ChatPage } = await import(
    "@/app/(app)/home/review/[signalId]/chat/page"
  );

  await act(async () => {
    render(<ChatPage params={Promise.resolve({ signalId: TEST_SIGNAL_ID })} />);
  });

  const input = screen.getByPlaceholderText(
    "이 Review에 대해 궁금한 점을 물어보세요."
  );
  fireEvent.change(input, { target: { value: "질문입니다." } });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /전송/i }));
  });

  await waitFor(() => {
    expect(
      screen.getByText("응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /재시도/i })).toBeInTheDocument();
  });
});

// ─── 7.5: 전송 중 입력 바 disabled ───────────────────────────────────────────

it("7.5: 전송 중 입력 바 disabled", async () => {
  // 느린 fetch 시뮬레이션
  let resolveFetch!: (v: unknown) => void;
  global.fetch = jest.fn().mockReturnValue(
    new Promise((resolve) => {
      resolveFetch = resolve;
    })
  );

  const { default: ChatPage } = await import(
    "@/app/(app)/home/review/[signalId]/chat/page"
  );

  await act(async () => {
    render(<ChatPage params={Promise.resolve({ signalId: TEST_SIGNAL_ID })} />);
  });

  const input = screen.getByPlaceholderText(
    "이 Review에 대해 궁금한 점을 물어보세요."
  );
  fireEvent.change(input, { target: { value: "질문입니다." } });
  fireEvent.click(screen.getByRole("button", { name: /전송/i }));

  // 전송 중 — input disabled
  expect(input).toBeDisabled();

  // resolve fetch
  await act(async () => {
    resolveFetch({
      ok: true,
      status: 200,
      json: async () => ({ data: { reply: "응답" }, error: null }),
    });
  });
});
