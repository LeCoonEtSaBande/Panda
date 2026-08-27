import { NextResponse } from "next/server";
import { runAgent } from "@/lib/agent/run";
import { createServerSupabase } from "@/lib/supabase/server";
import { gateConfigured, gateTokenOk, readGateCookie } from "@/lib/auth/gate";
import { cookies } from "next/headers";
import type { ChatMode, Db } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

const MODES: ChatMode[] = ["assistant", "recu", "envoye", "libre"];

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as {
      mode?: string;
      message?: string;
      db?: Db;
    };
    if (gateConfigured()) {
      const ok = await gateTokenOk(
        readGateCookie((await cookies()).getAll()),
      );
      if (!ok) {
        return NextResponse.json({ error: "unauth" }, { status: 401 });
      }
    } else {
      const sb = await createServerSupabase();
      if (sb) {
        const { data } = await sb.auth.getUser();
        if (!data.user) {
          return NextResponse.json({ error: "unauth" }, { status: 401 });
        }
      }
    }

    const mode = MODES.includes(body.mode as ChatMode)
      ? (body.mode as ChatMode)
      : "assistant";
    const message = (body.message ?? "").trim();
    if (!message) {
      return NextResponse.json({ error: "empty" }, { status: 400 });
    }
    if (!body.db) {
      return NextResponse.json({ error: "no_db" }, { status: 400 });
    }
    const result = await runAgent({ mode, message, db: body.db });
    return NextResponse.json(result);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "erreur";
    return NextResponse.json(
      {
        text: "",
        groceryLabels: [],
        proposals: [],
        draft: null,
        openUrl: null,
        error: msg,
      },
      { status: 500 },
    );
  }
}
