// RSC-safe: pure constant, no browser-client imports. Keep separate from api.ts
// (which pulls in the browser Supabase client via getAccessToken).
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";
