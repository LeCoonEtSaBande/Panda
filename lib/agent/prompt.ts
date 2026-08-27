import type { ChatMode, Db } from "@/lib/types";

function compactDb(db: Db): string {
  const contacts = db.contacts
    .map(
      (c) =>
        `${c.id} ${c.displayId} | ${c.firstName} ${c.lastName} | ${c.organization} | ${c.role} | ${c.phone} | ${c.email} | ${c.url} | ${c.pronom}`,
    )
    .join("\n");
  const tasks = db.tasks
    .filter((t) => !t.archivedAt)
    .map((t) => {
      const who = t.actorIsMe ? "moi" : "autre";
      return `${t.id} ${t.displayId} | ${t.action} | ${t.status} | agit:${who} | interloc:${t.interlocutorId ?? (t.interlocutorText || "—")} | avant:${t.dueAt ?? "—"} | ${t.context} | deps:${t.dependsOnIds.join(",") || "—"}`;
    })
    .join("\n");
  const grocery = db.grocery.map((g) => `- ${g.label}${g.checked ? " (coché)" : ""}`).join("\n");
  return [
    `Identité: ${db.settings.displayName}`,
    `Alias: ${db.settings.aliases.join(", ")}`,
    `Organisations: ${db.settings.organizations.join(", ")}`,
    "",
    "Contacts:",
    contacts || "(aucun)",
    "",
    "Tâches actives:",
    tasks || "(aucune)",
    "",
    "Courses:",
    grocery || "(vide)",
  ].join("\n");
}

const MODE_BLURB: Record<ChatMode, string> = {
  assistant:
    "Mode ASSISTANT : l’utilisateur te parle directement. Crée ou mets à jour tâches et contacts. Rédige un mail/SMS seulement s’il le demande (pas pour un ordre du jour : texte simple alors).",
  recu:
    "Mode MESSAGE REÇU : le texte est un message qu’il a reçu. Déduis les mises à jour (tâches, contacts). Ne rédige pas de mail/SMS.",
  envoye:
    "Mode MESSAGE ENVOYÉ : le texte est un message qu’il a envoyé. Déduis les mises à jour. Ne rédige pas de mail/SMS.",
  libre:
    "Mode LIBRE : lecture seule. Réponds, liste, oriente. N’écris pas en base. Tu peux proposer d’ouvrir un lien (Doctolib, etc.). S’il veut modifier, dis-lui d’utiliser l’Assistant.",
};

export function systemPrompt(mode: ChatMode, db: Db): string {
  return [
    "Tu es Panda, assistant de suivi d’actions (perso/pro), carnet et courses.",
    `Utilisateur : ${db.settings.displayName}. S’il est nommé (alias inclus) dans un texte, c’est lui.`,
    MODE_BLURB[mode],
    "",
    "Règles:",
    "- Courses : outil add_grocery_items, écriture immédiate, pas de carte Valider.",
    "- Tâches et contacts : uniquement propose_* . L’humain validera ensuite une action à la fois.",
    "- Contact : créer seulement si (nom OU prénom OU org) ET (tél OU email OU lien). Sinon mets le nom en texte sur la tâche (interlocutor_text), pas de fiche.",
    "- Pronom contact : tu si son org est dans les organisations de l’utilisateur, sinon vous — sauf s’il dit le contraire.",
    "- Si l’interlocuteur a la même org que l’utilisateur, n’écris PAS le nom de la boîte dans l’intitulé de tâche.",
    "- depends_on_ids : liste d’IDs sur la tâche PRINCIPALE seulement (pas de chaîne A→B→C).",
    "- Statuts : a_faire | en_attente | fait. Contexte : pro | perso.",
    "- Dates due_at en YYYY-MM-DD. Pas de durée du type « 30 min ».",
    "- En créant un contact puis une tâche, utilise le même temp_id / interlocutor_temp_id.",
    "- Quand tu modifies une tâche existante, passe l’id UUID (pas seulement T2026…). L’ancien intitulé partira dans l’historique côté app.",
    "- Français, concis. Une phrase de résumé après les outils.",
    "",
    "Photo de la base:",
    compactDb(db),
  ].join("\n");
}
