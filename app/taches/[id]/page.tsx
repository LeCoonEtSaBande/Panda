"use client";

import { useParams, useRouter } from "next/navigation";
import { upsertTask } from "@/lib/local-db";
import { useDb } from "@/lib/use-db";

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const db = useDb();
  const task = db.tasks.find((t) => t.id === id);
  if (!task) {
    return (
      <main>
        <p className="muted">Tâche introuvable (données locales de ce navigateur).</p>
      </main>
    );
  }

  const who =
    db.contacts.find((c) => c.id === task.interlocutorId) ||
    (task.interlocutorText ? { firstName: task.interlocutorText } : null);

  return (
    <main>
      <p className="muted">{task.displayId}</p>
      <h1>{task.action}</h1>
      <p className="muted">
        {task.context} · {task.status.replace("_", " ")}
        {task.dueAt ? ` · avant ${task.dueAt}` : ""}
      </p>
      {who ? (
        <p>
          Interlocuteur :{" "}
          {"lastName" in who
            ? [who.firstName, who.lastName].filter(Boolean).join(" ")
            : who.firstName}
        </p>
      ) : null}
      {task.history.length > 0 ? (
        <ul className="muted">
          {task.history.map((h, i) => (
            <li key={i}>
              {h.date} : {h.action}
            </li>
          ))}
        </ul>
      ) : null}
      <button
        type="button"
        className="btn"
        onClick={() => {
          upsertTask({
            ...task,
            status: "fait",
            history: [
              ...task.history,
              { date: new Date().toISOString().slice(0, 10), action: task.action },
            ],
            updatedAt: new Date().toISOString(),
          });
          router.push("/taches");
        }}
      >
        Marquer faite
      </button>
      <p className="muted" style={{ marginTop: 16 }}>
        SMS / Email (rédaction agent) : bientôt, depuis cette carte.
      </p>
    </main>
  );
}
