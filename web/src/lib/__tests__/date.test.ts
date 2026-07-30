/**
 * date.test.ts — kstToday() 스펙.
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다(다른 *.test.* 파일과 동일 관례).
 * 런타임 검증은 `node -e`로 en-CA/Asia/Seoul 포맷 경계값을 확인했습니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { kstToday } from "../date";

describe("kstToday", () => {
  it("UTC 14:59 → KST 같은 날(23:59)", () => {
    expect(kstToday(new Date("2026-07-29T14:59:00Z"))).toBe("2026-07-29");
  });
  it("UTC 15:00 → KST 다음 날(00:00) 경계 넘어감", () => {
    expect(kstToday(new Date("2026-07-29T15:00:00Z"))).toBe("2026-07-30");
  });
  it("UTC 자정 직전(23:30) → KST 아침(08:30) 다음 날", () => {
    expect(kstToday(new Date("2026-07-29T23:30:00Z"))).toBe("2026-07-30");
  });
});
