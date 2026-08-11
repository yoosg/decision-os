"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type TabKey = "home" | "queue" | "history" | "profile";

const tabs: Array<{ href: string; label: string; key: TabKey }> = [
  { href: "/home", label: "홈", key: "home" },
  { href: "/queue", label: "보관함", key: "queue" },
  { href: "/history", label: "히스토리", key: "history" },
  { href: "/profile", label: "프로필", key: "profile" },
];

function TabIcon({ name, active }: { name: TabKey; active: boolean }) {
  const common = {
    width: 24,
    height: 24,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: active ? 2.2 : 1.9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "home":
      return (
        <svg {...common}>
          <path d="M3 9.5 12 3l9 6.5V20a1 1 0 0 1-1 1h-4v-6h-4v6H4a1 1 0 0 1-1-1z" />
        </svg>
      );
    case "queue":
      // 보관함 — 저장/북마크 은유
      return (
        <svg {...common}>
          <path d="M19 21l-7-4.5L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
        </svg>
      );
    case "history":
      // 히스토리 — 시간 되돌리기 은유
      return (
        <svg {...common}>
          <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
          <path d="M3 3v5h5" />
          <path d="M12 8v4l3 2" />
        </svg>
      );
    case "profile":
      return (
        <svg {...common}>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21a8 8 0 0 1 16 0" />
        </svg>
      );
  }
}

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="주요 내비게이션"
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: "var(--surface-base)",
        borderTop: "1px solid var(--border-subtle)",
        zIndex: 50,
        paddingBottom: "env(safe-area-inset-bottom)",
        // iOS Safari 관성 스크롤 중 fixed 요소가 스크롤 레이어에 얹혀 mid-screen으로
        // 밀리는 리페인트 지연을 막기 위해 자체 컴포지팅 레이어로 승격한다.
        transform: "translateZ(0)",
      }}
    >
      <div className="screen-container">
        <ul
          role="list"
          style={{
            display: "flex",
            justifyContent: "space-around",
            padding: "8px 0",
            margin: 0,
            listStyle: "none",
          }}
        >
          {tabs.map((tab) => {
            const isActive =
              pathname === tab.href || pathname.startsWith(tab.href + "/");
            return (
              <li key={tab.href}>
                <Link
                  href={tab.href}
                  aria-current={isActive ? "page" : undefined}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "3px",
                    padding: "4px 12px",
                    minWidth: "44px",
                    minHeight: "44px",
                    color: isActive
                      ? "var(--accent-primary)"
                      : "var(--text-secondary)",
                    textDecoration: "none",
                    fontSize: "10px",
                    fontWeight: isActive ? 700 : 500,
                  }}
                >
                  <TabIcon name={tab.key} active={isActive} />
                  <span>{tab.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
