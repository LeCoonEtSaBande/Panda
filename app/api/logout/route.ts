import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { clearGateCookieHeader } from "@/lib/auth/gate";

export const runtime = "nodejs";

export async function POST() {
  const sb = await createServerSupabase();
  await sb?.auth.signOut();
  const res = NextResponse.json({ ok: true });
  res.headers.append("Set-Cookie", clearGateCookieHeader());
  return res;
}
