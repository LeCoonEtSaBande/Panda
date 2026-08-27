"use client";

import { autoPronom, canCreateContact } from "@/lib/contact-rules";
import { nextDisplayId, upsertContact } from "@/lib/store";
import type { Pronom } from "@/lib/types";
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
            {c.phone ? <a href={`tel:${c.phone}`}>appeler</a> : null}{" "}
            {c.email ? <a href={`mailto:${c.email}`}>mail</a> : null}
          </li>
        ))}
      </ul>
      <button type="button" className="btn" onClick={() => setOpen(true)}>
        Nouveau contact
      </button>
      {open ? (
        <NewContact orgs={db.settings.organizations} onClose={() => setOpen(false)} />
      ) : null}
    </main>
  );
}

function NewContact({
  orgs,
  onClose,
}: {
  orgs: string[];
  onClose: () => void;
}) {
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
        if (
          !canCreateContact({
            firstName,
            lastName,
            organization,
            phone,
            email,
            url,
          })
        ) {
          alert("Il faut (nom ou prénom ou org) et (tél ou email ou lien).");
          return;
        }
        void upsertContact({
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
          pronom: autoPronom(organization, orgs, pronom),
        });
        onClose();
      }}
    >
      <input placeholder="Prénom" value={firstName} onChange={(e) => setFirst(e.target.value)} />
      <input placeholder="Nom" value={lastName} onChange={(e) => setLast(e.target.value)} />
      <input
        placeholder="Organisation"
        value={organization}
        onChange={(e) => setOrg(e.target.value)}
      />
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
