import Link from "next/link";
import { ReviewSections, type ReviewPayload } from "@/components/home/review/review-sections";
import { ProjectCardBlocks, ProjectCardIdentity, ProjectCardMeta, type ProjectCardPayload } from "@/components/home/review/project-card-blocks";
import { OUTCOME_OPTIONS, type OutcomeStatus } from "@/components/home/outcome/outcome-options";
import { ArchivedBanner } from "./archived-banner";
import { dotVisual, DECISION_TYPE_LABEL, type DecisionChoice } from "./memory-timeline-item";
import { formatCardDate } from "@/lib/kst";
import { BackLink } from "@/components/ui/back-link";
import { VibeCodingGuide } from "@/components/home/review/vibe-coding-guide";

export interface ChainDetailData {
  signal: { id: string; title: string; status: string };
  review:
    | { reviewType: "project_card"; payload: ProjectCardPayload }
    | { reviewType: "research"; payload: ReviewPayload }
    | null;
  decision: { choice: DecisionChoice; createdAt: string } | null;
  outcome: {
    status: OutcomeStatus;
    useful: boolean | null;
    actualLearningTimeMin: number | null;
    appliedProjectNote: string | null;
    memo: string | null;
    createdAt: string;
  } | null;
}

// 체인 상세의 단일 노드 (Signal/Review/Decision/Outcome 공통 시각 언어)
function ChainNode({
  color,
  glyph,
  typeLabel,
  isLast,
  dim,
  children,
}: {
  color: string;
  glyph: string | null;
  typeLabel: string;
  isLast?: boolean;
  dim?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", gap: "12px", alignItems: "stretch", opacity: dim ? 0.55 : 1 }}>
      <span aria-hidden="true" style={{ position: "relative", width: "12px", flexShrink: 0 }}>
        {!isLast && (
          <span
            style={{
              position: "absolute",
              left: "5px",
              top: "14px",
              bottom: 0,
              width: "2px",
              background: "var(--border-subtle)",
            }}
          />
        )}
        <span
          style={{
            position: "absolute",
            left: 0,
            top: "2px",
            width: "12px",
            height: "12px",
            borderRadius: "9999px",
            background: color,
            border: "2px solid var(--surface-base)",
            boxSizing: "content-box",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#FFFFFF",
            fontSize: "9px",
            lineHeight: 1,
            fontWeight: 700,
          }}
        >
          {glyph}
        </span>
      </span>

      <div style={{ flex: 1, minWidth: 0, paddingBottom: isLast ? 0 : "24px" }}>
        <p lang="en" className="text-badge" style={{ color: "var(--text-secondary)", marginBottom: "6px" }}>
          {typeLabel}
        </p>
        {children}
      </div>
    </div>
  );
}

function outcomeKoreanLabel(status: OutcomeStatus): string {
  return OUTCOME_OPTIONS.find((o) => o.status === status)?.koreanLabel ?? status;
}

interface Props {
  data: ChainDetailData;
}

export function ChainDetailContent({ data }: Props) {
  const { signal, review, decision, outcome } = data;
  const isLearnNow = decision?.choice === "learn_now";

  return (
    <div className="screen-container" style={{ paddingTop: "24px", paddingBottom: "48px" }}>
      <BackLink href="/history">히스토리로</BackLink>

      {signal.status === "archived" && (
        <div style={{ marginBottom: "24px" }}>
          <ArchivedBanner />
        </div>
      )}

      {/* Signal 노드 */}
      <ChainNode color="var(--text-secondary)" glyph={null} typeLabel="SIGNAL">
        <h1 className="text-screen-title">{signal.title}</h1>
      </ChainNode>

      {/* Review 노드 */}
      {review && (
        <ChainNode color="var(--text-secondary)" glyph={null} typeLabel="REVIEW">
          {review.reviewType === "project_card" ? (
            <>
              <VibeCodingGuide />
              <ProjectCardIdentity payload={review.payload} signalTitle={signal.title} variant="chain" />
              <ProjectCardMeta payload={review.payload} />
              <ProjectCardBlocks payload={review.payload} />
            </>
          ) : (
            <ReviewSections payload={review.payload} />
          )}
        </ChainNode>
      )}

      {/* Decision 노드 */}
      {decision && (
        <ChainNode color="var(--text-primary)" glyph={null} typeLabel="DECISION">
          <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
            {DECISION_TYPE_LABEL[decision.choice]}
          </p>
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            {formatCardDate(decision.createdAt)}
          </p>
          {isLearnNow && (
            <Link
              href={`/home/review/${signal.id}/learning-path`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                marginTop: "10px",
                padding: "8px 14px",
                borderRadius: "9999px",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontSize: "13px",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              학습 경로 보기
            </Link>
          )}
        </ChainNode>
      )}

      {/* Outcome 노드 (AC-5) */}
      {outcome ? (
        (() => {
          const { color, glyph } = dotVisual({ kind: "outcome", status: outcome.status });
          return (
            <ChainNode color={color} glyph={glyph} typeLabel="OUTCOME" isLast>
              <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
                {outcomeKoreanLabel(outcome.status)}
              </p>
              {outcome.actualLearningTimeMin != null && (
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                  실제 학습 시간 약 {outcome.actualLearningTimeMin}분
                </p>
              )}
              {outcome.appliedProjectNote && (
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                  {outcome.appliedProjectNote}
                </p>
              )}
              {outcome.memo && (
                <p className="text-body" style={{ marginTop: "8px" }}>
                  {outcome.memo}
                </p>
              )}
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                {formatCardDate(outcome.createdAt)}
              </p>
            </ChainNode>
          );
        })()
      ) : (
        // 미기록: learn_now 는 "미완료"(AC-5), queue/ignore 는 흐리게 통일 (설계 결정 1 / Task 9.6)
        <ChainNode color="var(--text-secondary)" glyph="?" typeLabel="OUTCOME" isLast dim={!isLearnNow}>
          <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)" }}>미완료</p>
          {isLearnNow && (
            <Link
              href={`/home/review/${signal.id}/outcome`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                marginTop: "10px",
                padding: "10px 16px",
                borderRadius: "9999px",
                background: "var(--accent-primary)",
                color: "var(--accent-foreground, #FFFFFF)",
                fontSize: "14px",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              결과 기록하기
            </Link>
          )}
        </ChainNode>
      )}
    </div>
  );
}
