"use client";

import { useEffect, useState } from "react";

const SEEN_KEY = "vibecoding_guide_seen";

const SETUP_STEPS: { title: string; desc: string }[] = [
  { title: "설치", desc: "터미널에 npm install -g @anthropic-ai/claude-code (또는 데스크톱 앱 설치)" },
  { title: "로그인", desc: "claude 실행 후 화면 안내대로 로그인" },
  { title: "폴더 열기", desc: "프로젝트 폴더를 만들고 그 안에서 claude 실행" },
  { title: "첫 프롬프트", desc: "카드의 '예시 프롬프트'를 그대로 붙여넣기" },
];

// 이 6단계 백본은 후속 P1(마일스톤 프로세스화)에서 재사용 예정 — 그때 공용 상수로 추출.
const FLOW_STEPS: { title: string; desc: string }[] = [
  { title: "브레인스토밍", desc: "\"이 아이디어로 뭘 만들 수 있어?\" Claude에게 옵션 펼쳐달라 하기" },
  { title: "구체화", desc: "그중 하나를 골라 한 문장으로 좁히기" },
  { title: "기획·설계", desc: "필요한 화면·데이터·기능을 목록으로 적기" },
  { title: "개발", desc: "화면부터 만들고, 그다음 기능 붙이기" },
  { title: "테스트", desc: "직접 써보며 안 되는 걸 Claude에게 고쳐달라 하기" },
  { title: "마무리·다음", desc: "정리하고 \"다음엔 뭘 더 해볼까?\" 물어보기" },
];

export function VibeCodingGuide() {
  // SSR/hydration mismatch 회피: 서버·클라 모두 초기엔 접힘(false)으로 렌더 →
  // 마운트 후 useEffect에서 첫 방문이면 펼친다.
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(SEEN_KEY)) {
        setOpen(true);
        localStorage.setItem(SEEN_KEY, "1");
      }
    } catch {
      // localStorage 접근 불가(프라이빗 모드 등) → 접힌 기본값 유지
    }
  }, []);

  const listStyle = { margin: "0 0 16px", paddingLeft: "18px", fontSize: "13px", color: "var(--text-secondary)" } as const;
  const headingStyle = { fontSize: "13px", fontWeight: 700, margin: "0 0 8px" } as const;

  return (
    <section
      style={{
        border: "1px solid var(--border-subtle, #E5E5E5)",
        borderRadius: "12px",
        padding: "12px 14px",
        marginBottom: "20px",
        background: "var(--surface-card, #F7F7F7)",
      }}
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: 700,
          color: "var(--text-primary, #111)",
        }}
      >
        <span>🧭 바이브코딩 가이드</span>
        <span aria-hidden="true" style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
          {open ? "접기 ▴" : "펼치기 ▾"}
        </span>
      </button>

      {open && (
        <div style={{ marginTop: "12px" }}>
          <h3 style={headingStyle}>🧰 처음이라면: Claude Code 켜기</h3>
          <ol style={listStyle}>
            {SETUP_STEPS.map((s) => (
              <li key={s.title} style={{ marginBottom: "4px" }}>
                <strong style={{ color: "var(--text-primary)" }}>{s.title}</strong> — {s.desc}
              </li>
            ))}
          </ol>

          <h3 style={headingStyle}>🧭 바이브코딩은 이렇게 흘러가요</h3>
          <ol style={{ ...listStyle, marginBottom: 0 }}>
            {FLOW_STEPS.map((s) => (
              <li key={s.title} style={{ marginBottom: "4px" }}>
                <strong style={{ color: "var(--text-primary)" }}>{s.title}</strong> — {s.desc}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
