// web/src/lib/api.ts
import { createClient } from "@/lib/supabase";

// 브라우저 supabase 세션에서 액세스 토큰 추출(클라이언트 컴포넌트 전용)
export async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await createClient().auth.getSession();
  return session?.access_token ?? null;
}
