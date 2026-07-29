import { HonestBox } from "./honest-box";

export interface ReviewPayload {
  one_line_definition: string;
  key_concepts: string;
  problems_solved: string;
  why_it_matters: string;
  vs_existing_tech: string;
  user_relevance: string;
  learning_goals: string;
  learning_time_difficulty: {
    estimated_hours: number;
    difficulty: "beginner" | "intermediate" | "advanced";
  };
  practical_applicability: string;
  risks: string;
  recommendation_reason: string;
  reference_sources: string[];
  honest_box: {
    content: string;
    severity: "standard" | "high";
  };
}

export const SECTION_CONFIG = [
  { key: "one_line_definition", label: "핵심 한 줄 요약", sectionNum: 1 },
  { key: "key_concepts", label: "핵심 개념 설명", sectionNum: 2 },
  { key: "problems_solved", label: "해결하는 문제", sectionNum: 3 },
  { key: "why_it_matters", label: "왜 지금 중요한가", sectionNum: 4 },
  { key: "vs_existing_tech", label: "기존 기술과의 차이", sectionNum: 5 },
  { key: "user_relevance", label: "사용자 관련성", sectionNum: 6 },
  { key: "learning_goals", label: "학습 목표", sectionNum: 7 },
  {
    key: "learning_time_difficulty",
    label: "예상 학습 시간 + 난이도",
    sectionNum: 8,
  },
  {
    key: "practical_applicability",
    label: "실무 적용 가능성",
    sectionNum: 9,
  },
  { key: "risks", label: "위험 요소", sectionNum: 10 },
  { key: "recommendation_reason", label: "추천 이유", sectionNum: 11 },
  { key: "reference_sources", label: "참고 출처", sectionNum: 12 },
] as const;

export const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: "입문",
  intermediate: "중급",
  advanced: "고급",
};

export function renderSectionContent(
  sectionKey: string,
  payload: ReviewPayload
): React.ReactNode {
  if (sectionKey === "learning_time_difficulty") {
    const { estimated_hours, difficulty } = payload.learning_time_difficulty;
    return (
      <p className="text-body">
        {estimated_hours}시간 · {DIFFICULTY_LABEL[difficulty] ?? difficulty}
      </p>
    );
  }

  if (sectionKey === "reference_sources") {
    return (
      <ul style={{ paddingLeft: 0, listStyle: "none", margin: 0 }}>
        {payload.reference_sources.map((url, i) => (
          <li key={i} style={{ marginBottom: "4px" }}>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-body"
              style={{ color: "var(--text-secondary)", textDecoration: "underline", wordBreak: "break-all" }}
            >
              {url}
            </a>
          </li>
        ))}
      </ul>
    );
  }

  const value = payload[sectionKey as keyof ReviewPayload];
  return <p className="text-body">{String(value ?? "")}</p>;
}

interface Props {
  payload: ReviewPayload;
}

// 12개 섹션 + honest_box 렌더링만 담당 (뒤로가기/타이틀/Chat 링크/ContextStickyBar 제외)
export function ReviewSections({ payload }: Props) {
  return (
    <>
      {SECTION_CONFIG.map(({ key, label }) => (
        <section key={key} style={{ marginBottom: "24px" }}>
          <h2
            data-section-key={key}
            className="text-section-title"
            style={{ marginBottom: "8px" }}
          >
            {label}
          </h2>
          {key === "user_relevance" && (
            <p
              style={{
                fontSize: "11px",
                color: "var(--text-secondary)",
                marginBottom: "4px",
              }}
            >
              현재 프로필 기준
            </p>
          )}
          {renderSectionContent(key, payload)}
        </section>
      ))}

      {payload.honest_box.content && (
        <div style={{ marginBottom: "16px" }}>
          <HonestBox
            content={payload.honest_box.content}
            severity={payload.honest_box.severity}
          />
        </div>
      )}
    </>
  );
}
