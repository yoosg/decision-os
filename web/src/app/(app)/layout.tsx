import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { BottomNav } from "@/components/layout/bottom-nav";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let user = null;
  try {
    const supabase = await createServerSupabaseClient();
    const { data } = await supabase.auth.getUser();
    user = data.user;
  } catch {
    redirect("/signin");
  }
  if (!user) redirect("/signin");

  return (
    <div className="flex flex-col min-h-svh">
      <main className="flex-1 pb-16">{children}</main>
      <BottomNav />
    </div>
  );
}
