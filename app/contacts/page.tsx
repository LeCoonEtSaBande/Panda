"use client";

import { upsertContact, nextDisplayId, type Pronom } from "@/lib/local-db";
import { useDb } from "@/lib/use-db";
import { useState } from "react";

export default function ContactsPage() {
  const db = useDb();
  const [open, setOpen] = useState(false);

  return (
    <main>
      <h1>Carnet</h1>
      <p className="muted">Visible surtout sur PC. Pronom : vous par défaut.</p>
      <ul className="task-list">
        {db.contacts.map((c) => (
          <li key={c.id} className="task-card">
            <strong>
              {c.firstName} {c.lastName}
            </strong>
            <span className="muted">
              {c.organization} · {c.pronom}
              {c.phone ? ` · ${c.phone}` : ""}
              {c.email ? ` · ${c.email}` : ""}
            </span>
            {c.phone ? (
              <a href={`tel:${c.phone}`}>appeler</a>
            ) : null}{" "}
            {c.email ? <a href={`mailto:${c.email}`}>mail</a> : null}
          </li>
        ))}
      </ul>
      <button type="button" className="btn" onClick={() => setOpen(true)}>
        Nouveau contact
      </button>
      {open ? <NewContact onClose={() => setOpen(false)} /> : null}
    </main>
  );
}

function NewContact({ onClose }: { onClose: () => void }) {
  const [firstName, setFirst] = useState("");
  const [lastName, setLast] = useState("");
  const [organization, setOrg] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [url, setUrl] = useState("");
  const [pronom, setPronom] = useState<Pronom>("vous");

  return (
    <form
      className="muted"
      style={{ marginTop: 16 }}
      onSubmit={(e) => {
        e.preventDefault();
        const ok =
          (firstName || lastName || organization) && (phone || email || url);
        if (!ok) {
          alert("Il faut (nom ou prénom ou org) et (tél ou email ou lien).");
          return;
        }
        const orgs = ["Tecmotec"];
        const autoTu = orgs.some(
          (o) => o.toLowerCase() === organization.trim().toLowerCase(),
        );
        upsertContact({
          id: crypto.randomUUID(),
          displayId: nextDisplayId("C"),
          firstName,
          lastName,
          role: "",
          organization,
          phone,
          email,
          url,
          alias: "",
          pronom: autoTu ? "tu" : pronom,
        });
        onClose();
      }}
    >
      <input placeholder="Prénom" value={firstName} onChange={(e) => setFirst(e.target.value)} />
      <input placeholder="Nom" value={lastName} onChange={(e) => setLast(e.target.value)} />
      <input placeholder="Organisation" value={organization} onChange={(e) => setOrg(e.target.value)} />
      <input placeholder="Téléphone" value={phone} onChange={(e) => setPhone(e.target.value)} />
      <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="Lien" value={url} onChange={(e) => setUrl(e.target.value)} />
      <select value={pronom} onChange={(e) => setPronom(e.target.value as Pronom)}>
        <option value="vous">vous</option>
        <option value="tu">tu</option>
      </select>
      <button type="submit" className="btn">
        Enregistrer
      </button>
    </form>
  );
}
