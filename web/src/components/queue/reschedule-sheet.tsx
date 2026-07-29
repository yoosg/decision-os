"use client";

import { useEffect, useRef } from "react";
import type { QueueTiming } from "./queue-item";

interface RescheduleSheetProps {
  currentTiming: QueueTiming;
  onSelect: (timing: QueueTiming) => void;
  onClose: () => void;
}

const OPTIONS: Array<{ label: string; value: QueueTiming }> = [
  { label: "Today", value: "today" },
  { label: "This Week", value: "this_week" },
  { label: "Later", value: "later" },
];

export function RescheduleSheet({ currentTiming, onSelect, onClose }: RescheduleSheetProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Escape 키로 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  // 포커스 트랩
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = dialog.querySelectorAll<HTMLElement>(
      'button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) {
      dialog.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first.focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    dialog.addEventListener("keydown", trap);
    return () => dialog.removeEventListener("keydown", trap);
  }, []);

  return (
    <>
      <div
        role="presentation"
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.4)",
          zIndex: 50,
        }}
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="일정 변경"
        tabIndex={-1}
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          background: "var(--surface-base, #FFFFFF)",
          borderRadius: "24px 24px 0 0",
          padding: "12px 20px 40px",
          zIndex: 51,
        }}
      >
        <div
          style={{
            width: 36,
            height: 4,
            background: "#DDD",
            borderRadius: 9999,
            margin: "0 auto 16px",
          }}
        />
        <h3 style={{ fontSize: "17px", fontWeight: 600, margin: "0 0 16px" }}>일정 변경</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {OPTIONS.map(({ label, value }) => {
            const isSelected = value === currentTiming;
            return (
              <button
                key={value}
                type="button"
                lang="en"
                onClick={() => onSelect(value)}
                style={{
                  minHeight: "44px",
                  border: isSelected
                    ? "1.5px solid var(--accent-primary, #4F46E5)"
                    : "1px solid var(--border-subtle, #E5E5E5)",
                  borderRadius: "9999px",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: "15px",
                }}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}
