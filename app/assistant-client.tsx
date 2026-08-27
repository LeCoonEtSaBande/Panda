"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  abortProposalCycle,
  addGrocery,
  applyProposal,
  beginProposalCycle,
  getCachedDb,
} from "@/lib/store";
import { useDb } from "@/lib/use-db";
import type { ChatMode, ChatResponse, DraftMessage, Proposal } from "@/lib/types";

const MODES = [
  { id: "assistant" as const, label: "Assistant" },
  { id: "recu" as const, label: "Reçu" },
  { id: "envoye" as const, label: "Envoyé" },
];

function looksLikeGrocery(text: string) {
  return /achet|courses|farine|oeufs|œufs/i.test(text);
}

function groceryLines(text: string): string[] {
  const rest = text
    .replace(/^[\s\S]*?(?:acheter|achète|achetes|achètes|achete)\s+/i, "")
    .trim();
  return (rest || text)
    .split(/\s+et\s+|,|\n/i)
    .map((s) =>
      s
        .replace(/^(de la|de l['’]|des|du|le|la|les|un|une)\s+/i, "")
        .trim(),
    )
    .filter((s) => s.length > 1);
}

export default function AssistantPage() {
  const db = useDb();
  const params = useSearchParams();
  const [mode, setMode] = useState<(typeof MODES)[number]["id"]>("assistant");
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [queue, setQueue] = useState<Proposal[]>([]);
  const [draft, setDraft] = useState<DraftMessage | null>(null);
  const [openUrl, setOpenUrl] = useState<string | null>(null);
  const auto = useRef(false);

  const locked = queue.length > 0 || Boolean(draft) || busy;

  const redigerHint = useMemo(() => {
    const kind = params.get("rediger");
    const tid = params.get("tache");
    if (!kind || !tid) return null;
    const task = db.tasks.find((t) => t.id === tid);
    if (!task) return null;
    const who =
      db.contacts.find((c) => c.id === task.interlocutorId) ||
      (task.interlocutorText
        ? { firstName: task.interlocutorText, lastName: "", organization: "", phone: "", email: "" }
        : null);
    const canal = kind === "sms" ? "SMS" : "email";
    const dest = who
      ? [who.firstName, who.lastName, who.organization].filter(Boolean).join(" ")
      : "l’interlocuteur";
    return `Rédige un ${canal} pour faire avancer la tâche ${task.displayId} : ${task.action}. Destinataire : ${dest}.`;
  }, [params, db.tasks, db.contacts]);

  useEffect(() => {
    if (!redigerHint || auto.current) return;
    auto.current = true;
    setMode("assistant");
    setText(redigerHint);
  }, [redigerHint]);

  useEffect(() => {
    const cancel = () => abortProposalCycle();
    window.addEventListener("pagehide", cancel);
    return () => {
      window.removeEventListener("pagehide", cancel);
      abortProposalCycle();
    };
  }, []);

  async function send(override?: { mode: ChatMode; message: string }) {
    const payload = (override?.message ?? text).trim();
    const m = override?.mode ?? mode;
    if (!payload || locked) return;
    setBusy(true);
    setNote("");
    setReply("");
    setOpenUrl(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: m, message: payload, db: getCachedDb() }),
      });
      if (!res.ok && res.headers.get("content-type")?.includes("text/html")) {
        setNote("Session expirée. Recharge la page et reconnecte-toi.");
        return;
      }
      const data = (await res.json()) as ChatResponse;

      if (data.error === "missing_key") {
        if (m === "assistant" && looksLikeGrocery(payload)) {
          for (const line of groceryLines(payload)) await addGrocery(line);
          setNote("Ajouté aux courses (sans validation). Branche la clé Claude pour le reste.");
          setText("");
          return;
        }
        setNote(
          "Pas de clé Claude sur le serveur. En local : .env.local. En ligne : variables Vercel (docs/DEPLOIEMENT.md).",
        );
        return;
      }

      if (data.error) {
        setNote(data.error);
        return;
      }

      for (const label of data.groceryLabels) await addGrocery(label);
      if (data.groceryLabels.length && !data.proposals.length && !data.draft) {
        setNote(
          `Courses à jour : ${data.groceryLabels.join(", ")} (sans validation).`,
        );
      }
      setReply(data.text);
      setOpenUrl(data.openUrl);
      setDraft(data.draft);
      if (data.proposals.length) {
        beginProposalCycle();
        setQueue(data.proposals);
      }
      setText("");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erreur réseau";
      setNote(
        /load failed|failed to fetch|networkerror/i.test(msg)
          ? "La requête a été coupée. Réessaie dans un instant."
          : msg,
      );
    } finally {
      setBusy(false);
    }
  }

  const current = queue[0] ?? null;

  async function valider() {
    if (!current) return;
    setBusy(true);
    try {
      await applyProposal(current);
      setQueue((q) => q.slice(1));
      if (queue.length <= 1) abortProposalCycle();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Échec validation");
    } finally {
      setBusy(false);
    }
  }

  function non() {
    setQueue((q) => q.slice(1));
    if (queue.length <= 1) abortProposalCycle();
  }

  function toutAnnuler() {
    abortProposalCycle();
    setQueue([]);
  }

  async function cEstEnvoye() {
    if (!draft) return;
    const body = draft.body;
    const to = draft.to;
    setDraft(null);
    await send({
      mode: "envoye",
      message: `Message ${draft.kind} envoyé à ${to} :\n${body}`,
    });
  }

  return (
    <main>
      <div className="modes">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={mode === m.id ? "mode is-active" : "mode"}
            disabled={locked}
            onClick={() => setMode(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {draft ? (
        <DraftCard
          draft={draft}
          onChange={setDraft}
          onSend={() => void cEstEnvoye()}
          onCancel={() => setDraft(null)}
        />
      ) : current ? (
        <section className="card-validate">
          <p className="muted">
            Action {queue.length > 1 ? `1 / ${queue.length}` : "à valider"}
          </p>
          <h1>{current.summary}</h1>
          <p className="muted">{detailProposal(current)}</p>
          <div className="btn-row">
            <button type="button" className="btn" disabled={busy} onClick={() => void valider()}>
              Valider
            </button>
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={non}>
              Non
            </button>
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={toutAnnuler}>
              Tout annuler
            </button>
          </div>
        </section>
      ) : (
        <>
          <textarea
            placeholder={
              mode === "assistant"
                ? "Dis à Panda ce qu’il faut faire…"
                : "Colle le message…"
            }
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
        </>
      )}

      {reply ? <p className="reply">{reply}</p> : null}
      {openUrl ? (
        <p>
          <a href={openUrl} target="_blank" rel="noreferrer">
            Ouvrir {openUrl}
          </a>
        </p>
      ) : null}
      {note ? <p className="muted">{note}</p> : null}
    </main>
  );
}

function detailProposal(p: Proposal): string {
  if (p.kind === "create_contact") {
    const c = p.contact;
    return ["Nouveau contact", c.firstName, c.lastName, c.organization, c.phone, c.email]
      .filter(Boolean)
      .join(" · ");
  }
  if (p.kind === "update_contact") {
    return `Maj contact · ${Object.keys(p.patch).join(", ")}`;
  }
  if (p.kind === "create_task") {
    const t = p.task;
    return `${t.action} · ${t.status.replace("_", " ")} · ${t.context}${t.dueAt ? ` · avant ${t.dueAt}` : ""}`;
  }
  return `Maj tâche · ${Object.keys(p.patch).join(", ")}`;
}

function DraftCard({
  draft,
  onChange,
  onSend,
  onCancel,
}: {
  draft: DraftMessage;
  onChange: (d: DraftMessage) => void;
  onSend: () => void;
  onCancel: () => void;
}) {
  const href =
    draft.kind === "sms"
      ? `sms:${draft.to}?body=${encodeURIComponent(draft.body)}`
      : `mailto:${draft.to}?subject=${encodeURIComponent(draft.subject ?? "")}&body=${encodeURIComponent(draft.body)}`;

  return (
    <section className="card-validate">
      <p className="muted">
        {draft.kind === "sms" ? `smsto : ${draft.to}` : `mailto : ${draft.to}`}
      </p>
      {draft.kind === "email" ? (
        <input
          type="text"
          value={draft.subject ?? ""}
          placeholder="Objet"
          onChange={(e) => onChange({ ...draft, subject: e.target.value })}
        />
      ) : null}
      <textarea
        value={draft.body}
        onChange={(e) => onChange({ ...draft, body: e.target.value })}
      />
      <div className="btn-row">
        <a className="btn btn-link" href={href}>
          Ouvrir
        </a>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => void navigator.clipboard.writeText(draft.body)}
        >
          Copier
        </button>
      </div>
      <div className="btn-row">
        <button type="button" className="btn" onClick={onSend}>
          C’est envoyé
        </button>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          Annuler
        </button>
      </div>
    </section>
  );
}
