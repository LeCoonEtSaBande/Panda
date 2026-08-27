"use client";

import { useState } from "react";
import { addGrocery, getCachedDb } from "@/lib/store";
import type { ChatResponse } from "@/lib/types";

export default function LibrePage() {
  const [text, setText] = useState("");
  const [thread, setThread] = useState<{ role: "user" | "panda"; text: string }[]>(
    [],
  );
  const [busy, setBusy] = useState(false);
  const [openUrl, setOpenUrl] = useState<string | null>(null);

  async function send() {
    const payload = text.trim();
    if (!payload || busy) return;
    setBusy(true);
    setOpenUrl(null);
    setThread((t) => [...t, { role: "user", text: payload }]);
    setText("");
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "libre",
          message: payload,
          db: getCachedDb(),
        }),
      });
      const data = (await res.json()) as ChatResponse;
      if (data.error === "missing_key") {
        setThread((t) => [
          ...t,
          {
            role: "panda",
            text: "Lecture seule. Branche la clé Claude (Vercel / .env.local) pour que je réponde.",
          },
        ]);
        return;
      }
      if (data.error) {
        setThread((t) => [...t, { role: "panda", text: data.error ?? "Erreur" }]);
        return;
      }
      if (data.groceryLabels.length) {
        for (const label of data.groceryLabels) await addGrocery(label);
      }
      setOpenUrl(data.openUrl);
      setThread((t) => [
        ...t,
        { role: "panda", text: data.text || "(pas de réponse)" },
      ]);
    } catch (e) {
      setThread((t) => [
        ...t,
        { role: "panda", text: e instanceof Error ? e.message : "Erreur" },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>Libre</h1>
      <p className="muted">
        Lecture seule sur les bases. Pas d’écriture. Pour modifier, utilise
        Assistant.
      </p>
      <ul className="thread">
        {thread.map((m, i) => (
          <li key={i} className={m.role === "user" ? "bubble-user" : "bubble-panda"}>
            {m.text}
          </li>
        ))}
      </ul>
      {openUrl ? (
        <p>
          <a href={openUrl} target="_blank" rel="noreferrer">
            Ouvrir {openUrl}
          </a>
        </p>
      ) : null}
      <textarea
        placeholder="Question…"
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        type="button"
        className="btn"
        disabled={busy || !text.trim()}
        onClick={() => void send()}
      >
        {busy ? "…" : "Envoyer"}
      </button>
    </main>
  );
}
