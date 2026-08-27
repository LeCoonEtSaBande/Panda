"use client";

import { isRemoteMode } from "@/lib/store";
import { useDb } from "@/lib/use-db";

export default function ParametresPage() {
  const db = useDb();
  const remote = isRemoteMode();

  return (
    <main>
      <h1>Paramètres</h1>
      <p className="muted">
        {remote
          ? "Compte cloud (Supabase). Tes données suivent la connexion."
          : "Mode local : données dans ce navigateur tant que Supabase n’est pas branché."}
      </p>
      <p>
        {db.settings.displayName}
        <br />
        {db.settings.aliases.join(", ")}
        <br />
        Orgs : {db.settings.organizations.join(", ")}
      </p>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={async () => {
            await fetch("/api/logout", { method: "POST" });
            window.location.href = "/login";
          }}
        >
          Déconnexion
        </button>
    </main>
  );
}
