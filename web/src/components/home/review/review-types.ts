// web/src/components/home/review/review-types.ts
export type ReviewType = "research" | "project_card";

export function isProjectCard(
  t: ReviewType | string | null,
): t is "project_card" {
  return t === "project_card";
}
