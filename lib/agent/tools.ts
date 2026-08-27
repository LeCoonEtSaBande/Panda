import type Anthropic from "@anthropic-ai/sdk";
import type { ChatMode } from "@/lib/types";

type Tool = Anthropic.Messages.Tool;

const readTools: Tool[] = [
  {
    name: "list_snapshot",
    description: "Relire un résumé contacts / tâches / courses si la photo ne suffit pas.",
    input_schema: {
      type: "object",
      properties: {
        what: {
          type: "string",
          enum: ["all", "tasks", "contacts", "grocery"],
        },
      },
      required: ["what"],
    },
  },
];

const groceryTool: Tool = {
  name: "add_grocery_items",
  description:
    "Ajouter des articles à la liste de courses. Écriture immédiate, sans validation.",
  input_schema: {
    type: "object",
    properties: {
      labels: {
        type: "array",
        items: { type: "string" },
        description: "Articles, un par un (ex. farine, 12 œufs).",
      },
    },
    required: ["labels"],
  },
};

const writeTools: Tool[] = [
  {
    name: "propose_create_contact",
    description: "Proposer une fiche contact (validée ensuite par l’humain).",
    input_schema: {
      type: "object",
      properties: {
        temp_id: { type: "string", description: "Id temporaire, ex. tmp-c1" },
        summary: { type: "string" },
        last_name: { type: "string" },
        first_name: { type: "string" },
        role: { type: "string" },
        organization: { type: "string" },
        phone: { type: "string" },
        email: { type: "string" },
        url: { type: "string" },
        alias: { type: "string" },
        pronom: { type: "string", enum: ["tu", "vous"] },
      },
      required: ["temp_id", "summary"],
    },
  },
  {
    name: "propose_update_contact",
    description: "Proposer une mise à jour de contact existant (id UUID).",
    input_schema: {
      type: "object",
      properties: {
        id: { type: "string" },
        summary: { type: "string" },
        last_name: { type: "string" },
        first_name: { type: "string" },
        role: { type: "string" },
        organization: { type: "string" },
        phone: { type: "string" },
        email: { type: "string" },
        url: { type: "string" },
        alias: { type: "string" },
        pronom: { type: "string", enum: ["tu", "vous"] },
      },
      required: ["id", "summary"],
    },
  },
  {
    name: "propose_create_task",
    description: "Proposer une nouvelle tâche (validée ensuite).",
    input_schema: {
      type: "object",
      properties: {
        temp_id: { type: "string" },
        summary: { type: "string" },
        action: { type: "string" },
        status: { type: "string", enum: ["a_faire", "en_attente", "fait"] },
        actor_is_me: { type: "boolean" },
        interlocutor_id: { type: "string" },
        interlocutor_temp_id: { type: "string" },
        interlocutor_text: { type: "string" },
        due_at: { type: "string", description: "YYYY-MM-DD ou vide" },
        context: { type: "string", enum: ["pro", "perso"] },
        depends_on_ids: { type: "array", items: { type: "string" } },
      },
      required: ["temp_id", "summary", "action", "status", "actor_is_me", "context"],
    },
  },
  {
    name: "propose_update_task",
    description: "Proposer une mise à jour de tâche existante (id UUID).",
    input_schema: {
      type: "object",
      properties: {
        id: { type: "string" },
        summary: { type: "string" },
        action: { type: "string" },
        status: { type: "string", enum: ["a_faire", "en_attente", "fait"] },
        actor_is_me: { type: "boolean" },
        interlocutor_id: { type: "string" },
        interlocutor_temp_id: { type: "string" },
        interlocutor_text: { type: "string" },
        due_at: { type: "string" },
        context: { type: "string", enum: ["pro", "perso"] },
        depends_on_ids: { type: "array", items: { type: "string" } },
        archived: { type: "boolean" },
      },
      required: ["id", "summary"],
    },
  },
];

const draftTool: Tool = {
  name: "draft_message",
  description:
    "Rédiger un email ou un SMS (zone mailto/smsto). Pas pour un ordre du jour.",
  input_schema: {
    type: "object",
    properties: {
      kind: { type: "string", enum: ["email", "sms"] },
      to: { type: "string" },
      subject: { type: "string" },
      body: { type: "string" },
    },
    required: ["kind", "to", "body"],
  },
};

const openTool: Tool = {
  name: "open_link",
  description: "Proposer d’ouvrir un lien (ex. prise de RDV).",
  input_schema: {
    type: "object",
    properties: {
      url: { type: "string" },
    },
    required: ["url"],
  },
};

export function toolsFor(mode: ChatMode): Tool[] {
  if (mode === "libre") return [...readTools, openTool];
  if (mode === "assistant")
    return [...readTools, groceryTool, ...writeTools, draftTool, openTool];
  return [...readTools, ...writeTools];
}
