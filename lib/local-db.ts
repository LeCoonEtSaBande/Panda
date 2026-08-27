export type TaskStatus = "a_faire" | "en_attente" | "fait";
export type TaskContext = "pro" | "perso";
export type Pronom = "tu" | "vous";

export type Contact = {
  id: string;
  displayId: string;
  lastName: string;
  firstName: string;
  role: string;
  organization: string;
  phone: string;
  email: string;
  url: string;
  alias: string;
  pronom: Pronom;
};

export type Task = {
  id: string;
  displayId: string;
  action: string;
  status: TaskStatus;
  actorIsMe: boolean;
  interlocutorId: string | null;
  interlocutorText: string;
  dueAt: string | null;
  context: TaskContext;
  history: { date: string; action: string }[];
  dependsOnIds: string[];
  archivedAt: string | null;
  updatedAt: string;
};

export type Grocery = { id: string; label: string; checked: boolean };

export type Db = {
  tasks: Task[];
  contacts: Contact[];
  grocery: Grocery[];
};

const KEY = "panda.local.v1";

function empty(): Db {
  return { tasks: [], contacts: [], grocery: [] };
}

function read(): Db {
  if (typeof window === "undefined") return empty();
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return empty();
    return { ...empty(), ...JSON.parse(raw) };
  } catch {
    return empty();
  }
}

function write(db: Db) {
  localStorage.setItem(KEY, JSON.stringify(db));
  listeners.forEach((fn) => fn());
}

const listeners = new Set<() => void>();

export function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export function getDb(): Db {
  return read();
}

export function refreshDb(): Db {
  const db = read();
  listeners.forEach((fn) => fn());
  return db;
}

let seq = 0;
function nid(prefix: string) {
  seq += 1;
  return `${prefix}-${Date.now()}-${seq}`;
}

export function nextDisplayId(kind: "T" | "C"): string {
  const db = read();
  const year = new Date().getFullYear();
  const ids =
    kind === "T"
      ? db.tasks.map((t) => t.displayId)
      : db.contacts.map((c) => c.displayId);
  let n = 1;
  for (const id of ids) {
    const m = id.match(new RegExp(`^${kind}${year}(\\d+)$`));
    if (m) n = Math.max(n, Number(m[1]) + 1);
  }
  return `${kind}${year}${String(n).padStart(4, "0")}`;
}

export function upsertTask(patch: Task) {
  const db = read();
  const i = db.tasks.findIndex((t) => t.id === patch.id);
  if (i >= 0) db.tasks[i] = patch;
  else db.tasks.push(patch);
  write(db);
}

export function addGrocery(label: string) {
  const text = label.trim();
  if (!text) return;
  const db = read();
  db.grocery.push({ id: nid("g"), label: text, checked: false });
  write(db);
}

export function toggleGrocery(id: string) {
  const db = read();
  db.grocery = db.grocery.map((g) =>
    g.id === id ? { ...g, checked: !g.checked } : g,
  );
  write(db);
}

export function commitGrocery() {
  const db = read();
  db.grocery = db.grocery.filter((g) => !g.checked);
  write(db);
}

export function upsertContact(c: Contact) {
  const db = read();
  const i = db.contacts.findIndex((x) => x.id === c.id);
  if (i >= 0) db.contacts[i] = c;
  else db.contacts.push(c);
  write(db);
}

export function sortTasks(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    if (a.dueAt && b.dueAt && a.dueAt !== b.dueAt)
      return a.dueAt < b.dueAt ? -1 : 1;
    if (a.dueAt && !b.dueAt) return -1;
    if (!a.dueAt && b.dueAt) return 1;
    return a.updatedAt < b.updatedAt ? -1 : 1;
  });
}

export function dueFilter(
  dueAt: string | null,
  filter: "all" | "ajd" | "demain" | "semaine" | "mois",
): boolean {
  if (filter === "all") return true;
  if (!dueAt) return false;
  const due = new Date(dueAt + "T00:00:00");
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const endToday = new Date(startToday);
  endToday.setHours(23, 59, 59, 999);
  const tomorrow = new Date(startToday);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const endTomorrow = new Date(tomorrow);
  endTomorrow.setHours(23, 59, 59, 999);
  if (filter === "ajd") return due >= startToday && due <= endToday;
  if (filter === "demain") return due >= tomorrow && due <= endTomorrow;
  if (filter === "semaine") {
    const sun = new Date(startToday);
    const day = sun.getDay();
    const add = day === 0 ? 0 : 7 - day;
    sun.setDate(sun.getDate() + add);
    sun.setHours(23, 59, 59, 999);
    return due >= startToday && due <= sun;
  }
  const month = new Date(startToday);
  month.setDate(month.getDate() + 30);
  return due >= startToday && due <= month;
}
