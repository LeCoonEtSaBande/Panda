"use client";

import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";
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
      {isSupabaseConfigured() ? (
        <button
          type="button"
          className="btn btn-ghost"
          onClick={async () => {
            const sb = createClient();
            await sb?.auth.signOut();
            window.location.href = "/login";
          }}
        >
          Déconnexion
        </button>
      ) : null}
    </main>
  );
}
