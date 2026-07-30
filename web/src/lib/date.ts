/**
 * 날짜 유틸 — 앱의 "오늘" 기준은 KST(Asia/Seoul).
 *
 * 기존에는 `new Date().toISOString()`(UTC)로 오늘을 계산해, 한국 사용자가
 * 오전 0~9시(KST)에 접속하면 날짜가 하루 어긋나 브리핑을 못 찾는 버그가 있었다.
 * 백엔드 brief_date도 KST로 통일했으므로(core/timeutil.today_kst), 웹도 KST로 맞춘다.
 */

/**
 * KST(Asia/Seoul) 기준 오늘 날짜를 YYYY-MM-DD로 반환.
 * @param now 기준 시각(테스트용 주입 가능, 기본값 현재 시각)
 */
export function kstToday(now: Date = new Date()): string {
  // en-CA 로케일은 YYYY-MM-DD 포맷을 준다. timeZone으로 KST 벽시계 날짜를 얻음.
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(now);
}
