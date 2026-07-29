"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });
      if (authError) {
        setError(mapAuthError(authError.message));
        return;
      }

      // 온보딩 완료 여부 확인 후 라우팅 (AC-2)
      const { data: profile, error: profileError } = await supabase
        .from("user_profiles")
        .select("onboarding_completed")
        .eq("id", data.user.id)
        .single();

      if (profileError || !profile) {
        router.push("/onboarding"); // 조회 실패 시 온보딩으로 (safe default)
      } else if (profile.onboarding_completed) {
        router.push("/home");
      } else {
        router.push("/onboarding");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div
      style={{
        backgroundColor: "var(--surface-raised)",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ width: "100%", maxWidth: 480, padding: "48px 24px" }}>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            marginBottom: 32,
            color: "var(--text-primary)",
          }}
        >
          다시 오셨군요
        </h1>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>이메일</span>
            <input
              type="email"
              autoComplete="email"
              placeholder="이메일"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={inputStyle}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>비밀번호</span>
            <input
              type="password"
              autoComplete="current-password"
              placeholder="비밀번호"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={inputStyle}
            />
          </label>

          {error && (
            <p style={{ color: "var(--error)", fontSize: 13, fontWeight: 500, margin: 0 }}>
              {error}
            </p>
          )}

          <button type="submit" disabled={isLoading} style={ctaButtonStyle}>
            {isLoading ? "처리 중..." : "로그인"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-secondary)", marginTop: 24 }}>
          계정이 없으신가요?{" "}
          <Link href="/signup" style={{ color: "var(--text-primary)", fontWeight: 500 }}>
            회원가입
          </Link>
        </p>
      </div>
    </div>
  );
}

function mapAuthError(msg: string): string {
  if (msg.includes("Invalid login credentials")) return "이메일 또는 비밀번호가 올바르지 않습니다.";
  if (msg.includes("Email not confirmed")) return "이메일 확인이 필요합니다.";
  return "로그인 중 오류가 발생했습니다. 다시 시도해 주세요.";
}

const inputStyle: React.CSSProperties = {
  border: "1px solid var(--border-card)",
  borderRadius: "var(--radius-form-field, 12px)",
  padding: "12px 16px",
  fontSize: 15,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const ctaButtonStyle: React.CSSProperties = {
  backgroundColor: "var(--accent-primary)",
  color: "var(--accent-foreground)",
  height: 52,
  borderRadius: 9999,
  width: "100%",
  fontSize: 17,
  fontWeight: 600,
  border: "none",
  cursor: "pointer",
  marginTop: 8,
};
