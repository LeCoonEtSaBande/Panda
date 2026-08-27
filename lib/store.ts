"use client";

import { DEFAULT_IDENTITE } from "@/lib/identite-defaults";
import {
  addGrocery as localAddGrocery,
  allocateId,
  commitGrocery as localCommitGrocery,
  getDb as localGetDb,
  nextDisplayId as localNextDisplayId,
  refreshDb as localRefresh,
  subscribe as localSubscribe,
  toggleGrocery as localToggleGrocery,
  upsertContact as localUpsertContact,
  upsertTask as localUpsertTask,
} from "@/lib/local-db";
import {
  fetchRemoteDb,
  remoteAddGrocery,
  remoteCommitGrocery,
  remoteSeedSettings,
  remoteToggleGrocery,
  remoteUpsertContact,
  remoteUpsertTask,
} from "@/lib/remote-db";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import type { Contact, Db, Proposal, Task } from "@/lib/types";

const empty = (): Db => ({
  tasks: [],
  contacts: [],
  grocery: [],
  settings: {
    displayName: DEFAULT_IDENTITE.display_name,
    aliases: DEFAULT_IDENTITE.aliases,
    organizations: DEFAULT_IDENTITE.organizations,
  },
});

let cache: Db = empty();
let remote = false;
const listeners = new Set<() => void>();
const tempIds = new Map<string, string>();

function notify() {
  listeners.forEach((fn) => fn());
}

export function isRemoteMode() {
  return isSupabaseConfigured();
}

export function subscribeStore(fn: () => void) {
  listeners.add(fn);
  const unsubLocal = localSubscribe(() => {
    if (!remote) {
      cache = localGetDb();
      notify();
    }
  });
  return () => {
    listeners.delete(fn);
    unsubLocal();
  };
}

export function getCachedDb(): Db {
  return cache;
}

export async function hydrateDb(): Promise<Db> {
  if (!isSupabaseConfigured()) {
    remote = false;
    cache = localGetDb();
    notify();
    return cache;
  }
  remote = true;
  const db = await fetchRemoteDb();
  cache = db ?? empty();
  if (db) {
    await remoteSeedSettings(cache.settings);
  }
  notify();
  return cache;
}

export async function refreshStore(): Promise<Db> {
  if (!remote) {
    cache = localRefresh();
    notify();
    return cache;
  }
  return hydrateDb();
}

export function nextDisplayId(kind: "T" | "C"): string {
  return localNextDisplayId(kind, cache);
}

export async function upsertTask(task: Task) {
  if (remote) await remoteUpsertTask(task);
  else localUpsertTask(task);
  const i = cache.tasks.findIndex((t) => t.id === task.id);
  if (i >= 0) cache.tasks[i] = task;
  else cache.tasks.push(task);
  if (!remote) cache = localGetDb();
  notify();
}

export async function upsertContact(c: Contact) {
  if (remote) await remoteUpsertContact(c);
  else localUpsertContact(c);
  const i = cache.contacts.findIndex((x) => x.id === c.id);
  if (i >= 0) cache.contacts[i] = c;
  else cache.contacts.push(c);
  if (!remote) cache = localGetDb();
  notify();
}

export async function addGrocery(label: string) {
  const text = label.trim();
  if (!text) return;
  if (remote) {
    const g = await remoteAddGrocery(text);
    cache.grocery.push(g);
  } else {
    localAddGrocery(text);
    cache = localGetDb();
  }
  notify();
}

export async function toggleGrocery(id: string) {
  const g = cache.grocery.find((x) => x.id === id);
  if (!g) return;
  if (remote) await remoteToggleGrocery(id, !g.checked);
  else localToggleGrocery(id);
  cache.grocery = cache.grocery.map((x) =>
    x.id === id ? { ...x, checked: !x.checked } : x,
  );
  if (!remote) cache = localGetDb();
  notify();
}

export async function commitGrocery() {
  const ids = cache.grocery.filter((g) => g.checked).map((g) => g.id);
  if (remote) await remoteCommitGrocery(ids);
  else localCommitGrocery();
  cache.grocery = cache.grocery.filter((g) => !g.checked);
  if (!remote) cache = localGetDb();
  notify();
}

function resolveContactId(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const c = cache.contacts.find((x) => x.id === raw || x.displayId === raw);
  return c?.id ?? (raw.startsWith("tmp-") ? null : raw);
}

function resolveTaskIds(ids: string[]): string[] {
  return ids.map((raw) => {
    const t = cache.tasks.find((x) => x.id === raw || x.displayId === raw);
    return t?.id ?? raw;
  });
}

export function beginProposalCycle() {
  tempIds.clear();
}

export function abortProposalCycle() {
  tempIds.clear();
}

export async function applyProposal(p: Proposal): Promise<void> {
  const now = new Date().toISOString();
  const today = now.slice(0, 10);

  if (p.kind === "create_contact") {
    const id = allocateId();
    const contact: Contact = {
      id,
      displayId: nextDisplayId("C"),
      ...p.contact,
    };
    tempIds.set(p.tempId, id);
    await upsertContact(contact);
    return;
  }

  if (p.kind === "update_contact") {
    const cur =
      cache.contacts.find((c) => c.id === p.id) ||
      cache.contacts.find((c) => c.displayId === p.id);
    if (!cur) throw new Error("Contact introuvable");
    await upsertContact({ ...cur, ...p.patch });
    return;
  }

  if (p.kind === "create_task") {
    const interlocutorId =
      (p.interlocutorTempId && tempIds.get(p.interlocutorTempId)) ||
      resolveContactId(p.task.interlocutorId);
    const task: Task = {
      id: allocateId(),
      displayId: nextDisplayId("T"),
      action: p.task.action,
      status: p.task.status,
      actorIsMe: p.task.actorIsMe,
      interlocutorId,
      interlocutorText: p.task.interlocutorText,
      dueAt: p.task.dueAt,
      context: p.task.context,
      history: p.task.history?.length ? p.task.history : [],
      dependsOnIds: resolveTaskIds(p.task.dependsOnIds ?? []),
      archivedAt: null,
      updatedAt: now,
    };
    if (p.tempId) tempIds.set(p.tempId, task.id);
    await upsertTask(task);
    return;
  }

  const cur =
    cache.tasks.find((t) => t.id === p.id) ||
    cache.tasks.find((t) => t.displayId === p.id);
  if (!cur) throw new Error("Tâche introuvable");
  const interlocutorId =
    (p.interlocutorTempId && tempIds.get(p.interlocutorTempId)) ||
    (p.patch.interlocutorId !== undefined
      ? resolveContactId(p.patch.interlocutorId)
      : cur.interlocutorId);
  const nextAction = p.patch.action ?? cur.action;
  const history =
    p.patch.history ??
    (p.patch.action && p.patch.action !== cur.action
      ? [...cur.history, { date: today, action: cur.action }]
      : cur.history);
  await upsertTask({
    ...cur,
    ...p.patch,
    interlocutorId,
    history,
    dependsOnIds: p.patch.dependsOnIds
      ? resolveTaskIds(p.patch.dependsOnIds)
      : cur.dependsOnIds,
    updatedAt: now,
    action: nextAction,
  });
}
