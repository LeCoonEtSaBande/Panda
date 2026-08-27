"use client";

import { useState } from "react";
import { addGrocery } from "@/lib/local-db";

const MODES = [
  { id: "assistant", label: "Assistant" },
  { id: "recu", label: "Reçu" },
  { id: "envoye", label: "Envoyé" },
] as const;

function looksLikeGrocery(text: string) {
  return /acheter|courses|farine|oeufs|œufs/i.test(text);
}

function groceryLines(text: string): string[] {
  return text
    .replace(/^.*acheter\s+/i, "")
    .split(/\s+et\s+|,|\n/i)
    .map((s) => s.replace(/^de la\s+/i, "").replace(/^des\s+/i, "").trim())
    .filter((s) => s.length > 1);
}

export default function AssistantPage() {
  const [mode, setMode] = useState<(typeof MODES)[number]["id"]>("assistant");
  const [text, setText] = useState("");
  const [note, setNote] = useState("");

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
        Claude n’est pas encore branché (il te faudra une clé API). Les courses
        passent déjà tout de suite, sans écran Valider.
      </p>
      <textarea
        placeholder={
          mode === "assistant"
            ? "Dis à Panda ce qu’il faut faire…"
            : "Colle le message…"
        }
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        type="button"
        className="btn"
        onClick={() => {
          if (mode === "assistant" && looksLikeGrocery(text)) {
            groceryLines(text).forEach(addGrocery);
            setNote("Ajouté aux courses (sans validation).");
            setText("");
            return;
          }
          setNote(
            "Pas encore d’agent : crée un compte Anthropic + Vercel (voir docs/DEPLOIEMENT.md).",
          );
        }}
      >
        Envoyer
      </button>
      {note ? <p className="muted">{note}</p> : null}
    </main>
  );
}
