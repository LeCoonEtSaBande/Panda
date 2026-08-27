import { DEFAULT_IDENTITE } from "@/lib/identite-defaults";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";
import type { Contact, Db, Grocery, Settings, Task } from "@/lib/types";
import type { SupabaseClient } from "@supabase/supabase-js";

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function mapContact(row: Record<string, unknown>): Contact {
  return {
    id: str(row.id),
    displayId: str(row.display_id),
    lastName: str(row.last_name),
    firstName: str(row.first_name),
    role: str(row.role),
    organization: str(row.organization),
    phone: str(row.phone),
    email: str(row.email),
    url: str(row.url),
    alias: str(row.alias),
    pronom: row.pronom === "tu" ? "tu" : "vous",
  };
}

function mapTask(row: Record<string, unknown>): Task {
  const history = Array.isArray(row.history) ? row.history : [];
  const depends = Array.isArray(row.depends_on_ids) ? row.depends_on_ids : [];
  return {
    id: str(row.id),
    displayId: str(row.display_id),
    action: str(row.action),
    status:
      row.status === "en_attente" || row.status === "fait"
        ? row.status
        : "a_faire",
    actorIsMe: row.actor_is_me !== false,
    interlocutorId: row.interlocutor_id ? str(row.interlocutor_id) : null,
    interlocutorText: str(row.interlocutor_text),
    dueAt: row.due_at ? str(row.due_at) : null,
    context: row.context === "pro" ? "pro" : "perso",
    history: history.map((h) => {
      const x = h as { date?: string; action?: string };
      return { date: x.date ?? "", action: x.action ?? "" };
    }),
    dependsOnIds: depends.map((id) => String(id)),
    archivedAt: row.archived_at ? str(row.archived_at) : null,
    updatedAt: str(row.updated_at) || new Date().toISOString(),
  };
}

function mapGrocery(row: Record<string, unknown>): Grocery {
  return {
    id: str(row.id),
    label: str(row.label),
    checked: Boolean(row.checked),
  };
}

function mapSettings(row: Record<string, unknown> | null): Settings {
  if (!row) {
    return {
      displayName: DEFAULT_IDENTITE.display_name,
      aliases: DEFAULT_IDENTITE.aliases,
      organizations: DEFAULT_IDENTITE.organizations,
    };
  }
  return {
    displayName: str(row.display_name) || DEFAULT_IDENTITE.display_name,
    aliases: Array.isArray(row.aliases)
      ? row.aliases.map(String)
      : DEFAULT_IDENTITE.aliases,
    organizations: Array.isArray(row.organizations)
      ? row.organizations.map(String)
      : DEFAULT_IDENTITE.organizations,
  };
}

async function requireUser(sb: SupabaseClient): Promise<string> {
  const { data, error } = await sb.auth.getUser();
  if (error || !data.user) throw new Error("Non connecté");
  return data.user.id;
}

export async function fetchRemoteDb(): Promise<Db | null> {
  if (!isSupabaseConfigured()) return null;
  const sb = createClient();
  if (!sb) return null;
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return null;

  const [tasksRes, contactsRes, groceryRes, settingsRes] = await Promise.all([
    sb.from("tasks").select("*").eq("user_id", user.id),
    sb.from("contacts").select("*").eq("user_id", user.id),
    sb.from("grocery_items").select("*").eq("user_id", user.id).order("sort"),
    sb.from("settings").select("*").eq("user_id", user.id).maybeSingle(),
  ]);

  if (tasksRes.error) throw tasksRes.error;
  if (contactsRes.error) throw contactsRes.error;
  if (groceryRes.error) throw groceryRes.error;
  if (settingsRes.error) throw settingsRes.error;

  return {
    tasks: (tasksRes.data ?? []).map((r) => mapTask(r as Record<string, unknown>)),
    contacts: (contactsRes.data ?? []).map((r) =>
      mapContact(r as Record<string, unknown>),
    ),
    grocery: (groceryRes.data ?? []).map((r) =>
      mapGrocery(r as Record<string, unknown>),
    ),
    settings: mapSettings(
      (settingsRes.data as Record<string, unknown> | null) ?? null,
    ),
  };
}

export async function remoteUpsertTask(task: Task) {
  const sb = createClient();
  if (!sb) throw new Error("Supabase absent");
  const uid = await requireUser(sb);
  const { error } = await sb.from("tasks").upsert({
    id: task.id,
    user_id: uid,
    display_id: task.displayId,
    action: task.action,
    status: task.status,
    actor_is_me: task.actorIsMe,
    interlocutor_id: task.interlocutorId || null,
    interlocutor_text: task.interlocutorText || null,
    due_at: task.dueAt || null,
    context: task.context,
    history: task.history,
    depends_on_ids: task.dependsOnIds,
    archived_at: task.archivedAt,
    updated_at: task.updatedAt,
  });
  if (error) throw error;
}

export async function remoteUpsertContact(c: Contact) {
  const sb = createClient();
  if (!sb) throw new Error("Supabase absent");
  const uid = await requireUser(sb);
  const { error } = await sb.from("contacts").upsert({
    id: c.id,
    user_id: uid,
    display_id: c.displayId,
    last_name: c.lastName || null,
    first_name: c.firstName || null,
    role: c.role || null,
    organization: c.organization || null,
    phone: c.phone || null,
    email: c.email || null,
    url: c.url || null,
    alias: c.alias || null,
    pronom: c.pronom,
    updated_at: new Date().toISOString(),
  });
  if (error) throw error;
}

export async function remoteAddGrocery(label: string): Promise<Grocery> {
  const sb = createClient();
  if (!sb) throw new Error("Supabase absent");
  const uid = await requireUser(sb);
  const { data, error } = await sb
    .from("grocery_items")
    .insert({ user_id: uid, label, checked: false })
    .select("*")
    .single();
  if (error) throw error;
  return mapGrocery(data as Record<string, unknown>);
}

export async function remoteToggleGrocery(id: string, checked: boolean) {
  const sb = createClient();
  if (!sb) throw new Error("Supabase absent");
  await requireUser(sb);
  const { error } = await sb.from("grocery_items").update({ checked }).eq("id", id);
  if (error) throw error;
}

export async function remoteCommitGrocery(ids: string[]) {
  if (ids.length === 0) return;
  const sb = createClient();
  if (!sb) throw new Error("Supabase absent");
  await requireUser(sb);
  const { error } = await sb.from("grocery_items").delete().in("id", ids);
  if (error) throw error;
}

export async function remoteSeedSettings(settings: Settings) {
  const sb = createClient();
  if (!sb) return;
  const uid = await requireUser(sb);
  const { data } = await sb
    .from("settings")
    .select("user_id")
    .eq("user_id", uid)
    .maybeSingle();
  if (data) return;
  const { error } = await sb.from("settings").insert({
    user_id: uid,
    display_name: settings.displayName,
    aliases: settings.aliases,
    organizations: settings.organizations,
  });
  if (error) throw error;
}
