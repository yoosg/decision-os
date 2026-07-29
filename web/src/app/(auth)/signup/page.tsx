"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";

export default function SignUpPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setError("비밀번호는 8자 이상이어야 합니다.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const { data, error: authError } = await supabase.auth.signUp({
        email: email.trim(),
        password,
      });
      if (authError) {
        setError(mapAuthError(authError.message));
        return;
      }
      if (!data.session) {
        setError("이메일을 확인해 주세요. 받은 편지함의 링크를 클릭한 후 로그인해 주세요.");
        return;
      }
      router.push("/onboarding");
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
            marginBottom: 8,
            color: "var(--text-primary)",
          }}
        >
          계정 만들기
        </h1>
        <p
          style={{
            fontSize: 14,
            color: "var(--text-secondary)",
            marginBottom: 32,
          }}
        >
          오늘의 AI 기술 브리핑을 받아보세요
        </p>

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
              autoComplete="new-password"
              placeholder="비밀번호 (8자 이상)"
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
            {isLoading ? "처리 중..." : "시작하기"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-secondary)", marginTop: 24 }}>
          이미 계정이 있으신가요?{" "}
          <Link href="/signin" style={{ color: "var(--text-primary)", fontWeight: 500 }}>
            로그인
          </Link>
        </p>
      </div>
    </div>
  );
}

function mapAuthError(msg: string): string {
  if (msg.includes("already registered") || msg.includes("User already registered")) {
    return "이미 등록된 이메일입니다.";
  }
  if (msg.includes("invalid email")) return "올바른 이메일 형식이 아닙니다.";
  if (msg.includes("Password should be at least")) return "비밀번호는 8자 이상이어야 합니다.";
  return "회원가입 중 오류가 발생했습니다. 다시 시도해 주세요.";
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
