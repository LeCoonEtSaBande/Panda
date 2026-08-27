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

export type Settings = {
  displayName: string;
  aliases: string[];
  organizations: string[];
};

export type Db = {
  tasks: Task[];
  contacts: Contact[];
  grocery: Grocery[];
  settings: Settings;
};

export type ChatMode = "assistant" | "recu" | "envoye" | "libre";

export type Proposal =
  | {
      kind: "create_contact";
      summary: string;
      tempId: string;
      contact: Omit<Contact, "id" | "displayId">;
    }
  | {
      kind: "update_contact";
      summary: string;
      id: string;
      patch: Partial<Omit<Contact, "id" | "displayId">>;
    }
  | {
      kind: "create_task";
      summary: string;
      tempId: string;
      interlocutorTempId?: string;
      task: Omit<Task, "id" | "displayId" | "updatedAt" | "archivedAt"> & {
        interlocutorId?: string | null;
      };
    }
  | {
      kind: "update_task";
      summary: string;
      id: string;
      interlocutorTempId?: string;
      patch: Partial<Omit<Task, "id" | "displayId">>;
    };

export type DraftMessage = {
  kind: "email" | "sms";
  to: string;
  subject?: string;
  body: string;
};

export type ChatResponse = {
  text: string;
  groceryLabels: string[];
  proposals: Proposal[];
  draft: DraftMessage | null;
  openUrl: string | null;
  error?: string;
};
