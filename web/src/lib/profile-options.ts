// 온보딩(1-7)/프로필(1-8) 공유 enum 옵션 — client 경계 밖 plain 모듈(Server Component 재사용 안전).
// 값 집합은 API 계약(api/routers/onboarding.py, users.py)의 Literal 과 정확히 일치.

export type Role = "frontend" | "backend" | "ai_engineer" | "pm" | "designer" | "student" | "other";
export type Experience = "beginner" | "intermediate" | "advanced";
export type Goal =
  | "ai_side_project"
  | "rag_service"
  | "agent_architecture"
  | "work_automation"
  | "ai_adoption"
  | "other";
export type DailyTime = 15 | 30 | 60;

export const ROLE_OPTIONS: Array<[string, Role]> = [
  ["Frontend Developer", "frontend"],
  ["Backend Developer", "backend"],
  ["AI Engineer", "ai_engineer"],
  ["Product Manager", "pm"],
  ["Designer", "designer"],
  ["Student", "student"],
  ["기타", "other"],
];

export const EXPERIENCE_OPTIONS: Array<[string, Experience]> = [
  ["입문", "beginner"],
  ["중급", "intermediate"],
  ["고급", "advanced"],
];

export const GOAL_OPTIONS: Array<[string, Goal]> = [
  ["AI 사이드 프로젝트 개발", "ai_side_project"],
  ["RAG 서비스 구축", "rag_service"],
  ["Agent Architecture 학습", "agent_architecture"],
  ["업무 자동화", "work_automation"],
  ["AI 도입 검토", "ai_adoption"],
  ["기타", "other"],
];

export const TECH_OPTIONS = ["React", "Next.js", "Python", "FastAPI", "LangGraph", "MCP", "Claude Code", "기타"];
export const INTEREST_OPTIONS = ["Agent", "RAG", "MCP", "Coding Agent", "Local LLM", "AI UX", "기타"];

export const TIME_OPTIONS: Array<[string, DailyTime]> = [
  ["15분", 15],
  ["30분", 30],
  ["1시간", 60],
];

// 값 → 라벨 역조회 (프로필 조회 표시용). 매칭 없으면 원값/"-" 반환.
export function labelOf(options: ReadonlyArray<readonly [string, string | number]>, value: string | number | null): string {
  if (value === null || value === undefined) return "-";
  return options.find(([, v]) => v === value)?.[0] ?? String(value);
}
