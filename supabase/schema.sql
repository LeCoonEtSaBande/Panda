-- Panda — schéma proto (coller dans Supabase SQL editor)

create extension if not exists "pgcrypto";

create type task_status as enum ('a_faire', 'en_attente', 'fait');
create type task_context as enum ('pro', 'perso');
create type pronom_kind as enum ('tu', 'vous');

create table settings (
  user_id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null default '',
  aliases text[] not null default '{}',
  organizations text[] not null default '{}',
  tokens_par_mois integer not null default 2000000 check (tokens_par_mois > 0),
  jour_reset integer not null default 1 check (jour_reset between 1 and 28),
  updated_at timestamptz not null default now()
);

create table contacts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  display_id text not null,
  last_name text,
  first_name text,
  role text,
  organization text,
  phone text,
  email text,
  url text,
  alias text,
  pronom pronom_kind not null default 'vous',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, display_id)
);

create table tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  display_id text not null,
  action text not null,
  status task_status not null default 'a_faire',
  actor_is_me boolean not null default true,
  actor_contact_id uuid references contacts (id) on delete set null,
  interlocutor_id uuid references contacts (id) on delete set null,
  interlocutor_text text,
  due_at date,
  context task_context not null,
  recurrence text,
  history jsonb not null default '[]',
  depends_on_ids uuid[] not null default '{}',
  archived_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, display_id)
);

create table grocery_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  label text not null,
  checked boolean not null default false,
  sort integer not null default 0,
  created_at timestamptz not null default now()
);

create table token_usage (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  used_at timestamptz not null default now(),
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  cache_read_tokens integer not null default 0,
  cache_create_tokens integer not null default 0,
  model text
);

create index token_usage_user_at on token_usage (user_id, used_at desc);
create index tasks_user_active on tasks (user_id, status) where archived_at is null;

alter table settings enable row level security;
alter table contacts enable row level security;
alter table tasks enable row level security;
alter table grocery_items enable row level security;
alter table token_usage enable row level security;

create policy "own settings" on settings for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own contacts" on contacts for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own tasks" on tasks for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own grocery" on grocery_items for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own tokens" on token_usage for all using (user_id = auth.uid()) with check (user_id = auth.uid());
