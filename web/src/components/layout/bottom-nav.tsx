"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/home", label: "홈", icon: "🏠" },
  { href: "/queue", label: "보관함", icon: "📋" },
  { href: "/history", label: "히스토리", icon: "🕐" },
  { href: "/profile", label: "프로필", icon: "👤" },
] as const;

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
                    gap: "2px",
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
                  <span aria-hidden="true" style={{ fontSize: "20px" }}>
                    {tab.icon}
                  </span>
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
