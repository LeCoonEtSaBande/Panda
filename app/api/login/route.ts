import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import {
  credentialsOk,
  gateConfigured,
  gateCookieHeader,
  makeGateToken,
} from "@/lib/auth/gate";
import { ensureOwnerUser, ownerEmail } from "@/lib/auth/owner";

export const runtime = "nodejs";

export async function POST(req: Request) {
  if (!gateConfigured()) {
    return NextResponse.json(
      { error: "PANDA_USER et PANDA_PASSWORD manquent sur Vercel." },
      { status: 500 },
    );
  }

  const body = (await req.json()) as { user?: string; password?: string };
  const user = body.user ?? "";
  const password = body.password ?? "";
  if (!credentialsOk(user, password)) {
    return NextResponse.json({ error: "Identifiant ou mot de passe incorrect." }, { status: 401 });
  }

  const token = await makeGateToken();
  if (!token) {
    return NextResponse.json({ error: "session" }, { status: 500 });
  }

  await ensureOwnerUser(password);

  const cookieStore = await cookies();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (url && anon) {
    const supabase = createServerClient(url, anon, {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options),
          );
        },
      },
    });
    await supabase.auth.signInWithPassword({
      email: ownerEmail(),
      password,
    });
  }

  cookieStore.set({
    name: "panda_gate",
    value: token,
    httpOnly: true,
    path: "/",
    sameSite: "lax",
    maxAge: 60 * 24 * 60 * 60,
    secure: process.env.NODE_ENV === "production",
  });

  const res = NextResponse.json({ ok: true });
  res.headers.append("Set-Cookie", gateCookieHeader(token));
  return res;
}
