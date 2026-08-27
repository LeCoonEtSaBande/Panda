"use client";

import { useState } from "react";

const MODES = [
  { id: "assistant", label: "Assistant" },
  { id: "recu", label: "Reçu" },
  { id: "envoye", label: "Envoyé" },
] as const;

export default function AssistantPage() {
  const [mode, setMode] = useState<(typeof MODES)[number]["id"]>("assistant");
  return (
    <main>
      <div className="modes">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={mode === m.id ? "mode is-active" : "mode"}
            onClick={() => setMode(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>
      <p className="muted">
        Mode {mode}. L’agent proposera des écritures ; tu valideras une action à
        la fois. (Branche Claude + Supabase ensuite.)
      </p>
      <textarea
        placeholder={
          mode === "assistant"
            ? "Dis à Panda ce qu’il faut faire…"
            : "Colle le message…"
        }
      />
      <button type="button" className="btn">
        Envoyer
      </button>
    </main>
  );
}
