"use client";

/**
 * Story 6.5 — 웹 engagement 계측 헬퍼 (fire-and-forget).
 *
 * 프론트로 치면 Google Analytics의 track() 같은 것: 사용자 반응(open·read_through)을 백엔드에
 * 남긴다. 단, **화면을 절대 느리게 하면 안 된다** — 그래서 호출부는 await 하지 않고(fire-and-forget),
 * 여기서 세션 조회·fetch를 비동기로 던지고 실패는 전부 삼킨다. 렌더/네비게이션을 막지 않는다.
 *
 * decision·impression은 서버 정본이라 여기서 보내지 않는다(엔드포인트도 decision을 거절).
 * impression 타입을 허용 목록에 둔 건 향후 클라 뷰포트 계측 확장 여지를 위한 것으로, 지금 웹은
 * open·read_through만 전송한다(D2/D3).
 */
import { API_BASE_URL } from "@/lib/api-config";
import { getAccessToken } from "@/lib/api";

type EngagementEventType = "impression" | "open" | "read_through";

export interface EngagementEvent {
  signal_id: string;
  event_type: EngagementEventType;
  daily_brief_id?: string;
  metadata?: Record<string, unknown>;
}

export function trackEngagement(events: EngagementEvent[]): void {
  if (events.length === 0) return;
  // void + 즉시실행 async: 호출부는 반환을 기다리지 않는다(fire-and-forget).
  void (async () => {
    try {
      const token = await getAccessToken();
      if (!token) return; // 비로그인/세션만료 → 조용히 스킵(계측은 부수효과)

      await fetch(`${API_BASE_URL}/api/v1/engagement`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ events }),
        keepalive: true, // 페이지 이탈 중에도 전송 시도(read_through 직후 네비게이션 대비)
      });
    } catch {
      // fire-and-forget: 모든 실패 무시 (UX 무영향)
    }
  })();
}
