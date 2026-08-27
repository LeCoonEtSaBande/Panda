"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { PullRefresh } from "@/app/pull-refresh";
import { dueFilter, refreshDb, sortTasks, type Task } from "@/lib/local-db";
import { useDb } from "@/lib/use-db";

type DueF = "all" | "ajd" | "demain" | "semaine" | "mois";
type StF = "all" | "a_faire" | "en_attente";
type CtxF = "all" | "pro" | "perso";

function contactLabel(
  t: Task,
  contacts: { id: string; firstName: string; lastName: string; organization: string }[],
) {
  if (t.interlocutorId) {
    const c = contacts.find((x) => x.id === t.interlocutorId);
    if (c) return [c.firstName, c.lastName, c.organization].filter(Boolean).join(" ");
  }
  return t.interlocutorText;
}

export function TachesClient() {
  const db = useDb();
  const [q, setQ] = useState("");
  const [due, setDue] = useState<DueF>("all");
  const [st, setSt] = useState<StF>("all");
  const [ctx, setCtx] = useState<CtxF>("all");
  const [archive, setArchive] = useState(false);

  const reload = useCallback(async () => {
    refreshDb();
  }, []);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    let list = db.tasks.filter((t) =>
      archive ? t.archivedAt : !t.archivedAt && t.status !== "fait",
    );
    if (st !== "all") list = list.filter((t) => t.status === st);
    if (ctx !== "all") list = list.filter((t) => t.context === ctx);
    list = list.filter((t) => dueFilter(t.dueAt, due));
    if (needle) {
      list = list.filter((t) => {
        const hist = t.history.map((h) => h.action).join(" ");
        const who = contactLabel(t, db.contacts);
        return `${t.action} ${hist} ${who}`.toLowerCase().includes(needle);
      });
    }
    return sortTasks(list);
  }, [db, q, due, st, ctx, archive]);

  const byId = Object.fromEntries(db.tasks.map((t) => [t.id, t]));

  return (
    <PullRefresh onRefresh={reload}>
      <div className="taches-head">
        <h1>Tâches</h1>
        <button type="button" className="btn-refresh-pc" onClick={() => void reload()}>
          Rafraîchir
        </button>
      </div>
      <input
        type="search"
        placeholder="Recherche action, historique, interlocuteur"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <div className="filters">
        <select value={due} onChange={(e) => setDue(e.target.value as DueF)}>
          <option value="all">Avant le : tous</option>
          <option value="ajd">Aujourd’hui</option>
          <option value="demain">Demain</option>
          <option value="semaine">Semaine (dimanche)</option>
          <option value="mois">1 mois</option>
        </select>
        <select value={st} onChange={(e) => setSt(e.target.value as StF)}>
          <option value="all">Statut</option>
          <option value="a_faire">À faire</option>
          <option value="en_attente">En attente</option>
        </select>
        <select value={ctx} onChange={(e) => setCtx(e.target.value as CtxF)}>
          <option value="all">Pro / Perso</option>
          <option value="pro">Pro</option>
          <option value="perso">Perso</option>
        </select>
      </div>
      <label className="archive-pc">
        <input
          type="checkbox"
          checked={archive}
          onChange={(e) => setArchive(e.target.checked)}
        />{" "}
        Archive
      </label>
      {rows.length === 0 ? (
        <p className="muted">Aucune tâche. Parle à l’Assistant ou tire vers le bas pour rafraîchir.</p>
      ) : (
        <ul className="task-list">
          {rows.map((t) => {
            const deps = t.dependsOnIds
              .map((id) => byId[id])
              .filter(Boolean) as Task[];
            const isChild = db.tasks.some(
              (p) => !p.archivedAt && p.dependsOnIds.includes(t.id),
            );
            return (
              <li key={t.id} className={isChild ? "task-card is-dep" : "task-card"}>
                <Link href={`/taches/${t.id}`}>
                  <span className="task-id">{t.displayId}</span>
                  <strong>{t.action}</strong>
                  <span className="muted">
                    {t.status.replace("_", " ")}
                    {t.dueAt ? ` · ${t.dueAt}` : ""}
                    {contactLabel(t, db.contacts)
                      ? ` · ${contactLabel(t, db.contacts)}`
                      : ""}
                  </span>
                  {deps.length > 0 ? (
                    <span className="muted">
                      dépend de {deps.map((d) => d.displayId).join(", ")}
                    </span>
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </PullRefresh>
  );
}
