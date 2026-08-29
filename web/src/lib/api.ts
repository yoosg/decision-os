// web/src/lib/api.ts
import { createClient } from "@/lib/supabase";

// NEXT_PUBLIC_* 는 빌드타임 인라인 → 순수 상수라 RSC/클라이언트 어디서든 안전하게 import 가능
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";

// 브라우저 supabase 세션에서 액세스 토큰 추출(클라이언트 컴포넌트 전용)
export async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await createClient().auth.getSession();
  return session?.access_token ?? null;
}
