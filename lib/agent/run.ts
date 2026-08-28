import Anthropic from "@anthropic-ai/sdk";
import { autoPronom, canCreateContact } from "@/lib/contact-rules";
import { systemPrompt } from "@/lib/agent/prompt";
import { toolsFor } from "@/lib/agent/tools";
import { coerceDueAt, todayISO } from "@/lib/dates";
import type {
  ChatMode,
  ChatResponse,
  Db,
  DraftMessage,
  Proposal,
} from "@/lib/types";

const MODEL =
  process.env.ANTHROPIC_MODEL?.trim() || "claude-sonnet-4-6";

function asRecord(input: unknown): Record<string, unknown> {
  return input && typeof input === "object"
    ? (input as Record<string, unknown>)
    : {};
}

function str(v: unknown): string {
  return typeof v === "string" ? v.trim() : "";
}

function compactSlice(db: Db, what: string): string {
  if (what === "grocery")
    return db.grocery.map((g) => g.label).join(", ") || "(vide)";
  if (what === "contacts")
    return db.contacts
      .map((c) => `${c.displayId} ${c.firstName} ${c.lastName} ${c.organization}`)
      .join("\n") || "(aucun)";
  if (what === "tasks")
    return db.tasks
      .filter((t) => !t.archivedAt)
      .map((t) => `${t.displayId} ${t.action} [${t.status}]`)
      .join("\n") || "(aucune)";
  return `${db.contacts.length} contacts, ${db.tasks.length} tâches, ${db.grocery.length} courses`;
}

export async function runAgent(opts: {
  mode: ChatMode;
  message: string;
  db: Db;
  today?: string;
}): Promise<ChatResponse> {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) {
    return {
      text: "",
      groceryLabels: [],
      proposals: [],
      draft: null,
      openUrl: null,
      error: "missing_key",
    };
  }

  const today = opts.today && /^\d{4}-\d{2}-\d{2}$/.test(opts.today)
    ? opts.today
    : todayISO();

  const client = new Anthropic({ apiKey: key, timeout: 45_000 });
  const tools = toolsFor(opts.mode);
  const groceryLabels: string[] = [];
  const proposals: Proposal[] = [];
  let draft: DraftMessage | null = null;
  let openUrl: string | null = null;

  const messages: Anthropic.Messages.MessageParam[] = [
    { role: "user", content: opts.message },
  ];

  try {
    for (let i = 0; i < 4; i += 1) {
      const res = await client.messages.create({
        model: MODEL,
        max_tokens: 2048,
        system: systemPrompt(opts.mode, opts.db, today),
        tools,
        messages,
      });

      const toolUses = res.content.filter((b) => b.type === "tool_use");
      if (res.stop_reason !== "tool_use" || toolUses.length === 0) {
        const text = res.content
          .filter((b) => b.type === "text")
          .map((b) => b.text)
          .join("\n")
          .trim();
        return { text, groceryLabels, proposals, draft, openUrl };
      }

      const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];
      for (const block of toolUses) {
        const input = asRecord(block.input);
        let result = "ok";
        try {
          result = handleTool(block.name, input, opts.db, today, {
            groceryLabels,
            proposals,
            setDraft: (d) => {
              draft = d;
            },
            setOpen: (u) => {
              openUrl = u;
            },
          });
        } catch (e) {
          result = e instanceof Error ? e.message : "erreur outil";
        }
        toolResults.push({
          type: "tool_result",
          tool_use_id: block.id,
          content: result,
        });
      }

      messages.push({ role: "assistant", content: res.content });
      messages.push({ role: "user", content: toolResults });
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : "erreur Claude";
    return {
      text: "",
      groceryLabels,
      proposals,
      draft,
      openUrl,
      error: msg,
    };
  }

  return {
    text: "Trop d’étapes d’outils. Réessaie plus simplement.",
    groceryLabels,
    proposals,
    draft,
    openUrl,
  };
}

function handleTool(
  name: string,
  input: Record<string, unknown>,
  db: Db,
  today: string,
  acc: {
    groceryLabels: string[];
    proposals: Proposal[];
    setDraft: (d: DraftMessage) => void;
    setOpen: (u: string) => void;
  },
): string {
  if (name === "list_snapshot") {
    return compactSlice(db, str(input.what) || "all");
  }
  if (name === "add_grocery_items") {
    const labels = Array.isArray(input.labels)
      ? input.labels.map(String).map((s) => s.trim()).filter(Boolean)
      : [];
    acc.groceryLabels.push(...labels);
    return labels.length ? `Ajouté: ${labels.join(", ")}` : "rien";
  }
  if (name === "open_link") {
    const url = str(input.url);
    if (url) acc.setOpen(url);
    return url ? "lien proposé" : "url manquante";
  }
  if (name === "draft_message") {
    const kind = input.kind === "sms" ? "sms" : "email";
    acc.setDraft({
      kind,
      to: str(input.to),
      subject: str(input.subject) || undefined,
      body: str(input.body),
    });
    return "brouillon prêt";
  }
  if (name === "propose_create_contact") {
    const contact = {
      lastName: str(input.last_name),
      firstName: str(input.first_name),
      role: str(input.role),
      organization: str(input.organization),
      phone: str(input.phone),
      email: str(input.email),
      url: str(input.url),
      alias: str(input.alias),
      pronom: autoPronom(
        str(input.organization),
        db.settings.organizations,
        input.pronom === "tu" || input.pronom === "vous"
          ? input.pronom
          : undefined,
      ),
    };
    if (!canCreateContact(contact)) {
      return "Refusé: il faut (nom ou prénom ou org) et (tél ou email ou lien). Mets le nom en texte sur la tâche.";
    }
    acc.proposals.push({
      kind: "create_contact",
      summary: str(input.summary) || "Nouveau contact",
      tempId: str(input.temp_id) || `tmp-c-${acc.proposals.length}`,
      contact,
    });
    return "proposition contact";
  }
  if (name === "propose_update_contact") {
    const id = str(input.id);
    const cur = db.contacts.find((c) => c.id === id || c.displayId === id);
    if (!cur) return "contact introuvable";
    const patch: {
      lastName?: string;
      firstName?: string;
      role?: string;
      organization?: string;
      phone?: string;
      email?: string;
      url?: string;
      alias?: string;
      pronom?: "tu" | "vous";
    } = {};
    if (input.last_name !== undefined) patch.lastName = str(input.last_name);
    if (input.first_name !== undefined) patch.firstName = str(input.first_name);
    if (input.role !== undefined) patch.role = str(input.role);
    if (input.organization !== undefined)
      patch.organization = str(input.organization);
    if (input.phone !== undefined) patch.phone = str(input.phone);
    if (input.email !== undefined) patch.email = str(input.email);
    if (input.url !== undefined) patch.url = str(input.url);
    if (input.alias !== undefined) patch.alias = str(input.alias);
    if (input.pronom === "tu" || input.pronom === "vous")
      patch.pronom = input.pronom;
    acc.proposals.push({
      kind: "update_contact",
      summary: str(input.summary) || `Maj ${cur.displayId}`,
      id: cur.id,
      patch,
    });
    return "proposition maj contact";
  }
  if (name === "propose_create_task") {
    acc.proposals.push({
      kind: "create_task",
      summary: str(input.summary) || str(input.action),
      tempId: str(input.temp_id) || `tmp-t-${acc.proposals.length}`,
      interlocutorTempId: str(input.interlocutor_temp_id) || undefined,
      task: {
        action: str(input.action),
        status:
          input.status === "en_attente" || input.status === "fait"
            ? input.status
            : "a_faire",
        actorIsMe: input.actor_is_me !== false,
        interlocutorId: str(input.interlocutor_id) || null,
        interlocutorText: str(input.interlocutor_text),
        dueAt: coerceDueAt(str(input.due_at), today),
        context: input.context === "pro" ? "pro" : "perso",
        history: [],
        dependsOnIds: Array.isArray(input.depends_on_ids)
          ? input.depends_on_ids.map(String)
          : [],
      },
    });
    return "proposition tâche";
  }
  if (name === "propose_update_task") {
    const id = str(input.id);
    const cur = db.tasks.find((t) => t.id === id || t.displayId === id);
    if (!cur) return "tâche introuvable";
    acc.proposals.push({
      kind: "update_task",
      summary: str(input.summary) || `Maj ${cur.displayId}`,
      id: cur.id,
      interlocutorTempId: str(input.interlocutor_temp_id) || undefined,
      patch: {
        ...(input.action !== undefined ? { action: str(input.action) } : {}),
        ...(input.status === "a_faire" ||
        input.status === "en_attente" ||
        input.status === "fait"
          ? { status: input.status }
          : {}),
        ...(input.actor_is_me !== undefined
          ? { actorIsMe: Boolean(input.actor_is_me) }
          : {}),
        ...(input.interlocutor_id !== undefined
          ? { interlocutorId: str(input.interlocutor_id) || null }
          : {}),
        ...(input.interlocutor_text !== undefined
          ? { interlocutorText: str(input.interlocutor_text) }
          : {}),
        ...(input.due_at !== undefined
          ? { dueAt: coerceDueAt(str(input.due_at), today) }
          : {}),
        ...(input.context === "pro" || input.context === "perso"
          ? { context: input.context }
          : {}),
        ...(Array.isArray(input.depends_on_ids)
          ? { dependsOnIds: input.depends_on_ids.map(String) }
          : {}),
        ...(input.archived === true
          ? { archivedAt: new Date().toISOString() }
          : {}),
      },
    });
    return "proposition maj tâche";
  }
  return "outil inconnu";
}
