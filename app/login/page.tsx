"use client";

import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setNote("");
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, password }),
      });
      const data = (await res.json()) as { error?: string };
      if (!res.ok) {
        setNote(data.error || "Erreur");
        return;
      }
      window.location.href = "/";
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
      <form onSubmit={(e) => void submit(e)}>
        <input
          type="text"
          autoComplete="username"
          placeholder="Identifiant"
          value={user}
          onChange={(e) => setUser(e.target.value)}
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
      </form>
      {note ? <p className="muted">{note}</p> : null}
    </main>
  );
}
