import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { ProfileContent, type ProfileData } from "@/components/profile/profile-content";
import { ROLE_OPTIONS, EXPERIENCE_OPTIONS, GOAL_OPTIONS, TIME_OPTIONS } from "@/lib/profile-options";

export const metadata: Metadata = { title: "프로필 | Decision OS" };

// 옵션 집합에 없는 저장값은 null 처리 — 편집 시 무효값 재전송(→ 백엔드 Literal 422) 방지
function inSet<T extends string | number>(
  options: ReadonlyArray<readonly [string, T]>,
  value: string | number | null | undefined
): T | null {
  if (value === null || value === undefined) return null;
  const hit = options.find(([, v]) => v === value);
  return hit ? hit[1] : null;
}

export default async function ProfilePage() {
  const supabase = await createServerSupabaseClient();
  const { data: userData } = await supabase.auth.getUser();
  if (!userData.user) redirect("/signin");
  const userId = userData.user.id;

  // RLS(user_profiles self-select)로 본인 행만 조회
  const { data, error } = await supabase
    .from("user_profiles")
    .select("role, experience_level, tech_stack, project_goal, interests, daily_learning_time_min, display_name")
    .eq("id", userId)
    .maybeSingle();
  if (error) console.error("[ProfilePage] user_profiles query error:", error);

  const row = data as unknown as {
    role: string | null;
    experience_level: string | null;
    tech_stack: string[] | null;
    project_goal: string | null;
    interests: string[] | null;
    daily_learning_time_min: number | null;
    display_name: string | null;
  } | null;

  const profile: ProfileData = {
    displayName: row?.display_name ?? null,
    role: inSet(ROLE_OPTIONS, row?.role),
    experienceLevel: inSet(EXPERIENCE_OPTIONS, row?.experience_level),
    techStack: row?.tech_stack ?? [],
    projectGoal: inSet(GOAL_OPTIONS, row?.project_goal),
    interests: row?.interests ?? [],
    dailyLearningTimeMin: inSet(TIME_OPTIONS, row?.daily_learning_time_min),
  };

  return (
    <div className="screen-container" style={{ paddingTop: "24px" }}>
      <ProfileContent initial={profile} />
    </div>
  );
}
