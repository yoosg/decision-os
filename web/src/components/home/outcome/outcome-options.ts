// "use client" 경계 밖의 순수 모듈 — Server/Client 양쪽에서 실제 값으로 import 가능.
// (client 모듈에서 export하면 Server Component 에서 client reference 프록시가 되어
//  OUTCOME_OPTIONS.find 같은 배열 메서드 호출이 런타임에 실패한다.)

export type OutcomeStatus = "completed" | "applied" | "dropped" | "not_useful";

export const OUTCOME_OPTIONS: Array<{
  status: OutcomeStatus;
  englishLabel: string;
  koreanLabel: string;
}> = [
  { status: "completed", englishLabel: "Completed", koreanLabel: "학습을 완료했습니다" },
  { status: "applied", englishLabel: "Applied", koreanLabel: "실제 프로젝트에 적용했습니다" },
  { status: "dropped", englishLabel: "Dropped", koreanLabel: "학습을 중단했습니다" },
  { status: "not_useful", englishLabel: "Not Useful", koreanLabel: "현재 상황에 맞지 않았습니다" },
];
