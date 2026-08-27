"use client";

import { FormEvent, useState } from "react";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  if (!isSupabaseConfigured()) {
    return (
      <main>
        <h1>Connexion</h1>
        <p className="muted">
          Supabase n’est pas configuré sur cet appareil. L’app tourne en local
          (données dans ce navigateur). Pour le cloud, vois docs/DEPLOIEMENT.md.
        </p>
      </main>
    );
  }

  async function submit(mode: "in" | "up", e: FormEvent) {
    e.preventDefault();
    const sb = createClient();
    if (!sb) return;
    setBusy(true);
    setNote("");
    try {
      if (mode === "up") {
        const { error } = await sb.auth.signUp({ email, password });
        if (error) throw error;
        setNote(
          "Compte créé. S’il faut confirmer l’email, ouvre le mail — ou désactive la confirmation dans Supabase (Auth) pour le proto.",
        );
      } else {
        const { error } = await sb.auth.signInWithPassword({ email, password });
        if (error) throw error;
        window.location.href = "/";
      }
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <p className="brand" style={{ marginBottom: 24 }}>
        Panda
      </p>
      <h1>Connexion</h1>
      <form onSubmit={(e) => void submit("in", e)}>
        <input
          type="email"
          autoComplete="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          autoComplete="current-password"
          placeholder="Mot de passe"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
        />
        <button type="submit" className="btn" disabled={busy}>
          Entrer
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={busy}
          onClick={(e) => void submit("up", e)}
        >
          Créer un compte
        </button>
      </form>
      {note ? <p className="muted">{note}</p> : null}
    </main>
  );
}
