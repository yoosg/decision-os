export function kstDateString(isoString: string): string {
  return new Date(new Date(isoString).getTime() + 9 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];
}

// "2026-07-15T..." → "2026-07" (KST 기준 월 그룹핑 키)
export function kstYearMonth(isoString: string): string {
  return kstDateString(isoString).slice(0, 7);
}

// "2026-07" → "2026년 7월" (월 구분선 표시)
export function formatMonthDivider(yearMonth: string): string {
  const [year, month] = yearMonth.split("-");
  return `${year}년 ${Number(month)}월`;
}

// "2026-07-05T..." → "7월 5일" (KST 기준 카드 날짜)
export function formatCardDate(isoString: string): string {
  const [, month, day] = kstDateString(isoString).split("-");
  return `${Number(month)}월 ${Number(day)}일`;
}
