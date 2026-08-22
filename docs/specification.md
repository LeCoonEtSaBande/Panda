# Panda — spécification v1

Livrables de conception. Pas de code dans ce document. Décisions déjà tranchées avec le produit.

---

## 1. Architecture

### 1.1 Principe

Une **page web** (PWA) ouverte dans Safari iPhone, plus tard ajoutable à l’écran d’accueil. Un **agent** (Claude) qui ne mémorise pas les tâches : il appelle des **outils**. Une **base Postgres** (Supabase) est la seule source de vérité.

Pas d’app Store, pas de WhatsApp, pas de Rappels Apple comme base, pas de JSON dans Git.

### 1.2 Schéma

```text
┌─────────────────────────────────────────┐
│  iPhone — Safari / icône écran d’accueil │
│                                         │
│  [ Chat ]  [ Liste ]                    │
│     │           │                       │
│     │           │ corrections, archive  │
│     ▼           ▼                       │
│         HTTPS (cookie session)          │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Vercel — Next.js (ou équivalent)        │
│                                         │
│  POST /api/chat     → boucle outils IA  │
│  GET/PATCH /api/tasks → liste / édition │
│  POST /api/tasks/:id/archive            │
└─────────────┬─────────────┬─────────────┘
              │             │
              ▼             ▼
     Anthropic API     Supabase
     Claude + tools    Postgres `tasks`
                       Auth (un utilisateur)
```

### 1.3 Flux chat (un message)

1. L’utilisateur envoie une phrase.
2. Le serveur charge les tâches **ouvertes non archivées** (contexte court : id, description, due_at, duration_min, category, waiting_for_reply, subtask_ids).
3. Il appelle Claude avec le système + les outils + l’historique récent.
4. Tant que Claude demande un outil : le serveur l’exécute en SQL, renvoie le JSON résultat.
5. Claude produit une **confirmation courte** (ce qui a changé, pas un roman).
6. Le client affiche la réplique et rafraîchit la liste.

L’édition manuelle dans l’onglet Liste **ne passe pas** par Claude : PATCH direct sur la ligne.

### 1.4 Ce qui ne change pas plus tard

Siri, un raccourci, ou un bot ne feront qu’envoyer une phrase à `POST /api/chat`. Même base, mêmes outils.

### 1.5 Hors v1

Comptes familiaux, notifications push, vocaux, pièces jointes (photos, PDF), sync Contacts / Rappels, table `Personnes` (anniversaires, cadences d’amis), templates WhatsApp.

---

## 2. Services tiers — comptes à créer

| # | Service | Compte | Rôle dans Panda | Offre de départ |
|---|---|---|---|---|
| 1 | **GitHub** | Déjà existant (`Panda`) | Code, PR, déploiement Vercel. **Repo privé.** | Gratuit |
| 2 | **Supabase** | À créer | Postgres, Row Level Security, Auth e-mail magic link (toi seul), URL + clés projet | Free tier |
| 3 | **Anthropic** | À créer | API Claude, outils de l’agent | Pay-as-you-go (crédits, plafond à poser) |
| 4 | **Vercel** | À créer (GitHub) | Build + HTTPS + variables d’env. Une URL = l’appli Safari | Hobby gratuit |

### 2.1 Rôle de chaque clé (jamais dans le repo)

| Variable | Où | Pourquoi |
|---|---|---|
| `ANTHROPIC_API_KEY` | Vercel | Appels Claude |
| `SUPABASE_URL` | Vercel | Projet |
| `SUPABASE_SERVICE_ROLE_KEY` | Vercel **seulement** | Le serveur lit/écrit `tasks` sans passer par le RLS navigateur |
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel + client | Auth navigateur |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel + client | Auth navigateur, RLS |

Le navigateur n’a **pas** la clé Anthropic ni la `service_role`.

### 2.2 À faire dans chaque console (avant ou pendant le premier code)

**Supabase**

1. New project, région proche (ex. `eu-west`).
2. Auth : désactiver les inscriptions publiques après **ton** premier compte, ou restreindre à une allowlist d’e-mail.
3. Coller le SQL de la section 4.
4. RLS : un utilisateur authentifié = ses lignes (`user_id = auth.uid()`). En v1 il n’y a que toi ; on pose quand même `user_id` pour ne pas tout refactorer.

**Anthropic**

1. Console → API keys → Create.
2. Billing + **limite mensuelle** (ex. 10 $).
3. Modèle : Sonnet courant (nom exact figé au moment du code, ex. `claude-sonnet-4-5` ou successeur).

**Vercel**

1. Import du repo GitHub privé.
2. Variables d’environnement ci-dessus.
3. URL type `panda-xxx.vercel.app` — suffisant ; pas de nom de domaine en v1.

**GitHub** : Settings → visibilité **Private** si ce n’est pas déjà le cas.

### 2.3 Services volontairement absents

Pas de Twilio, Meta Cloud API, OpenAI, S3, Resend, domaine custom, Apple Developer.

---

## 3. Service d’IA — lequel et comment

### 3.1 Choix

**Anthropic Claude, palier Sonnet**, API Messages + **tool use**.

Pas GPT en v1 (contrat portable si besoin). Pas Apple Intelligence (pas d’outils vers *notre* schéma). Pas d’agent no-code.

### 3.2 Comment l’appeler

Endpoint officiel Messages. Un tour =

- `system` : règles de la section 3.4 (copiées telles quelles dans le prompt système) ;
- `tools` : les 6 outils ci-dessous, schémas JSON stricts ;
- `messages` : historique de la session (fenêtre courte, ex. 20 derniers messages) + un message `user` avec la phrase **et** un bloc compact « tâches actives » (évite que Claude hallucine un id).

Boucle classique `stop_reason = tool_use` → exécution serveur → `tool_result` → nouvel appel, jusqu’à un texte.

Température basse (0–0.2) : on veut de l’exécution, pas de la prose.

### 3.3 Ce que Claude n’a pas le droit de faire

- Inventer un id, un téléphone, une durée de travaux.
- Créer une deuxième tâche quand une maj suffit (« j’ai trouvé un plombier »).
- Marquer `done` un parent tant qu’un enfant est `open`.
- Écrire dans la base autrement que via les outils (pas de SQL dans la bouche de Claude).

---

## 4. Contrat de l’agent conversationnel

### 4.1 Identité

Tutoiement, français, ton factuel. Après une action : **une à trois lignes** listant les champs écrits. Si c’est ambigu : **une** question, zéro action.

### 4.2 Constantes métier

| Règle | Valeur |
|---|---|
| Durée « faible » / un appel | `15` minutes |
| Travaux sans durée dite | **Demander**, ne pas inventer |
| « Fin septembre » | `due_at` = **30 septembre** (année en cours, ou suivante si déjà passé) |
| « Décembre » (glissement store) | `due_at` = **15 décembre** |
| « Aujourd’hui » | `due_at` = date du jour (Europe/Paris) |
| Sous-tâche | Nécessaire à la réalisation du parent = prérequis de clôture. Un seul lien : `subtask_ids` sur le **parent** |
| Cascade de butoir | Parent + enfants encore `open` (pas `done` / pas archivés) |
| `waiting_for_reply = true` | Exclue des suggestions « qu’est-ce que je peux faire » |
| Parent avec enfant `open` | Exclu des mêmes suggestions ; on propose les enfants |
| Anniversaires / amis réguliers | Répondre que ce n’est pas encore là ; ne pas créer de bricolage |

Catégorie par défaut si la phrase est clairement maison / famille : `perso`. Si le boulot est clair : `pro`. Sinon : demander.

### 4.3 Outils

Tous les outils s’exécutent **pour l’utilisateur connecté** uniquement. Les ids sont des UUID renvoyés par la base.

#### `create_task`

Créer une tâche `open`, non archivée.

| Paramètre | Type | Obligatoire | Notes |
|---|---|---|---|
| `description` | string | oui | |
| `duration_min` | integer | non | Défaut 15 si appel / « faible » ; sinon omettre et demander |
| `category` | `perso` \| `pro` | oui | |
| `due_at` | date `YYYY-MM-DD` | non | |
| `contact_name` | string | non | |
| `contact_phone` | string | non | Chiffres / espaces, tel quel |
| `contact_email` | string | non | |
| `notes` | string | non | Texte libre, mail collé |
| `links` | string[] | non | URLs |
| `parent_id` | uuid | non | Si fourni : après insert, **ajouter** le nouvel id à `subtask_ids` du parent ; recopier `due_at` du parent si le nouveau n’en a pas |

Retour : objet tâche créé (tous les champs).

#### `update_task`

Modifier une tâche existante. Tous les champs ci-dessous sont optionnels ; n’envoyer **que** ceux à changer. Interdit de vider un champ par oubli.

| Paramètre | Type | Notes |
|---|---|---|
| `id` | uuid | obligatoire |
| `description` | string | |
| `duration_min` | integer | |
| `category` | `perso` \| `pro` | |
| `due_at` | date ou `null` | `null` = retirer le butoir |
| `contact_name` | string ou `null` | |
| `contact_phone` | string ou `null` | |
| `contact_email` | string ou `null` | |
| `waiting_for_reply` | boolean | |
| `contacted_at` | date ou `null` | « j’ai appelé » → aujourd’hui |
| `status` | `open` \| `done` | Refusé si `done` et un enfant `open` |
| `notes` | string | **Remplace** tout le champ si envoyé. Pour ajouter : `append_notes` |
| `links` | string[] | **Remplace** la liste si envoyé. Pour ajouter : `add_links` |

#### `append_notes`

| Paramètre | Type |
|---|---|
| `id` | uuid |
| `text` | string (concaténé à `notes` avec un saut de ligne) |

#### `add_links`

| Paramètre | Type |
|---|---|
| `id` | uuid |
| `urls` | string[] (ajoutés, sans doublon) |

#### `shift_due_date`

Décale le butoir d’une tâche et de ses sous-tâches `open` non archivées.

| Paramètre | Type |
|---|---|
| `id` | uuid (racine, ex. le store) |
| `due_at` | date (ex. 15 décembre) |

Retour : liste des tâches effectivement modifiées (id, description, ancien `due_at`, nouveau).

#### `suggest_tasks`

Ne **modifie** rien. Filtre côté serveur (pas à Claude de trier de tête).

| Paramètre | Type | Notes |
|---|---|---|
| `max_duration_min` | integer | non ; ex. 30 |
| `category` | `perso` \| `pro` | non |
| `exclude_waiting` | boolean | défaut `true` |
| `exclude_blocked_parents` | boolean | défaut `true` (parent avec enfant `open`) |

Tri : `due_at` croissant (les `null` à la fin), puis `duration_min` croissant.

Retour : liste courte (id, description, duration_min, due_at, category, contact_name).

**Pas d’outil `delete`.** On archive (liste UI ou, plus tard, un outil). En v1 l’agent ne archive pas tout seul sauf demande explicite du type « archive le store » → alors `update` n’y suffit pas : on ajoutera `archive_task` au code si la phrase arrive. Pour la spec v1 : **outil `archive_task(id)`** déjà prévu, utilisé par l’agent *et* par le bouton Liste.

#### `archive_task`

| Paramètre | Type |
|---|---|
| `id` | uuid |

Pose `archived_at = maintenant`. N’efface pas. Les enfants ne sont pas archivés automatiquement.

### 4.4 Résolution d’identité

Claude ne « devine » pas un UUID. Il s’appuie sur le bloc « tâches actives » injecté par le serveur.

- Une seule candidate claire (« le plombier », « réparer le store ») → il prend cet id.
- 0 ou 2+ → **question**, aucun outil.

« J’ai trouvé un plombier » = `update_task` sur la tâche plombier existante, **pas** `create_task`.

### 4.5 Phrases d’acceptation (tests de l’agent)

À rejouer telles quelles après le code. Aujourd’hui = date réelle du test.

| # | Phrase | Effet attendu |
|---|---|---|
| 1 | Je dois contacter un plombier pour la maison | `create_task` : perso, duration 15, pas de due_at, pas de contact |
| 2 | J’ai trouvé un plombier c’est Qualitec 0606060606 | `update_task` contact_name Qualitec, phone 0606060606 |
| 3 | J’ai appelé le plombier | waiting_for_reply true, contacted_at aujourd’hui |
| 4 | Je dois faire réparer le store du salon avant fin septembre | perso, due_at 30 sept ; **demander la durée** si absente |
| 5 | Pour réparer le store je dois contacter un électricien pour faire un diagnostic | `create_task` + `parent_id` du store ; même due_at 30 sept ; id poussé dans `subtask_ids` du store |
| 6 | J’ai trouvé l’électricien c’est souffiane 0707070707 | maj de la tâche **électricien**, pas du store |
| 7 | Je ne vais pas pouvoir faire réparer le store avant décembre | `shift_due_date` store → 15 déc, enfants `open` aussi |
| 8 | Qu’est-ce que je peux faire dans la demi-heure qui vient ? | `suggest_tasks` max 30 ; sans waiting, sans parents bloqués ; tri urgence (butoir) |
| 9 | Aujourd’hui je ne travaille pas | `suggest_tasks` category perso |
| 10 | Je dois rappeler ma mère aujourd’hui | perso, contact_name Maman, due_at aujourd’hui, duration 15 |

Notes / URLs (exemples, pas dans les 10 d’origine) :

- « Je te colle le mail du plombier : … » → `append_notes`
- « Le devis est sur https://… » → `add_links`

---

## 5. Structure de la base de données

Un projet Supabase, un schéma `public`, **une table métier**. Auth : table `auth.users` gérée par Supabase.

### 5.1 Types

```sql
create type task_category as enum ('perso', 'pro');
create type task_status as enum ('open', 'done');
```

### 5.2 Table `tasks`

```sql
create table tasks (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references auth.users (id) on delete cascade,
  description       text not null,
  created_at        timestamptz not null default now(),
  duration_min      integer check (duration_min is null or duration_min > 0),
  category          task_category not null,
  contact_name      text,
  contact_phone     text,
  contact_email     text,
  waiting_for_reply boolean not null default false,
  contacted_at      date,
  due_at            date,
  subtask_ids       uuid[] not null default '{}',
  status            task_status not null default 'open',
  archived_at       timestamptz,
  notes             text not null default '',
  links             text[] not null default '{}',
  updated_at        timestamptz not null default now()
);
```

| Colonne | Sens |
|---|---|
| `id` | Identifiant stable (sous-tâches, agent, UI) |
| `user_id` | Propriétaire (toi) |
| `description` | Intitulé |
| `created_at` | Création |
| `duration_min` | Durée estimée, minutes. Null = inconnue (travaux, l’agent doit avoir demandé) |
| `category` | `perso` ou `pro` |
| `contact_*` | Personne / boîte liée à **cette** tâche (texte, pas une fiche Contacts) |
| `waiting_for_reply` | Appel fait, on attend un retour |
| `contacted_at` | Date d’appel / prise de contact |
| `due_at` | Date butoir (jour calendaire, pas d’heure en v1) |
| `subtask_ids` | Enfants nécessaires à la clôture du parent |
| `status` | `open` ou `done` |
| `archived_at` | Null = visible dans la liste active ; non null = archivée (conservée) |
| `notes` | Non structuré (mail collé, compte-rendu) |
| `links` | URLs |
| `updated_at` | Dernière écriture (agent ou UI) |

Pas de table `subtasks`. Le graphe est `subtask_ids` sur le parent. Pas de cycle à faire respecter en SQL v1 : le serveur refuse un `parent_id` qui créerait une boucle (id déjà ancêtre).

### 5.3 Index utiles

```sql
create index tasks_user_active_idx
  on tasks (user_id, status)
  where archived_at is null;

create index tasks_user_due_idx
  on tasks (user_id, due_at)
  where archived_at is null;
```

Trigger `updated_at = now()` sur `UPDATE`.

### 5.4 Intégrité applicative (serveur, pas forcément SQL)

- `done` interdit si un id de `subtask_ids` pointe vers une tâche `open` non archivée.
- `shift_due_date` ne touche que `open` et `archived_at is null`.
- Téléphone / e-mail : pas de format strict (Qualitec `0606060606` tel quel).
- `links` : chaînes non vides ; pas de validation HTTP obligatoire.

### 5.5 RLS (idée)

```text
select / insert / update / delete
  where user_id = auth.uid()
```

Le service_role (API serveur) bypass RLS ; il **filtre quand même** sur `user_id` de la session.

### 5.6 Plus tard (non créé)

`people` (anniversaire, cadence de contact). Les `contact_*` resteront dénormalisés sur la tâche en v1.

---

## 6. Page Safari

PWA mobile-first, une URL, deux onglets. Pas de desktop fancy en v1 (ça s’ouvre quand même sur Mac).

### 6.1 Coquille

- En-tête : **Panda** + indicateur de session (e-mail).
- Nav bas (pouce) : **Chat** | **Liste**.
- Fond clair, zones de tap ≥ 44 px, pas de hover comme seul moyen d’éditer.
- Safari : Partager → **Sur l’écran d’accueil**. `manifest` + thème ; push **non**.

Auth : écran unique magic link / e-mail avant d’entrer. Sans session : rien de la base.

### 6.2 Onglet Chat

- Fil de conversation (toi à droite, agent à gauche).
- Champ texte + envoi. Dictée = micro clavier iOS, pas un STT custom.
- Pendant les outils : état discret (« mise à jour… »), pas de dump JSON.
- Chaque réponse agent = le texte de confirmation. Un tap sur une tâche mentionnée peut ouvrir la Liste filtrée sur cet id (nice-to-have ; pas bloquant).

Le chat **n’est pas** un éditeur de fiche. Pour corriger un chiffre, onglet Liste.

### 6.3 Onglet Liste (visualisation)

Vue par défaut : `archived_at is null`, `status = open`, tri `due_at` (sans date en bas) puis description.

**Filtres** (chips) : Toutes | Perso | Pro | En attente de retour | Fait (`done` non archivé) | Archivées. Option « ≤ 30 min ».

**Carte tâche**

- Description, catégorie, durée, butoir.
- Contact (nom + tél / mail si présents) — tél cliquable `tel:`.
- Badge si `waiting_for_reply`.
- Sous-tâches : titres des ids (chargés avec la liste), pas seulement des UUID.
- Notes : aperçu 2 lignes, dépliable.
- Liens : ancres cliquables.

**Corrections manuelles** (sans l’agent)

Tap → fiche / mode édition :

- description, duration_min, category, due_at, contact_*, waiting_for_reply, contacted_at, notes, links (liste + ajout d’une URL) ;
- statut `open` / `done` (erreur explicite si enfants ouverts) ;
- **pas** d’édition brute de `subtask_ids` en v1 (le graphe se fait au chat, trop fragile au pouce).

Sauvegarde = PATCH immédiat (ou bouton Enregistrer sur la fiche, un des deux ; préférer Enregistrer pour éviter les PATCH à chaque frappe).

**Archiver**

- Sur la carte et sur la fiche : bouton **Archiver**.
- Confirmation courte (« Ça sort de la liste active, ce n’est pas supprimé »).
- `archive_task` : `archived_at = now()`.
- Filtre Archivées : bouton **Désarchiver**.
- Pas de suppression définitive en v1.

L’archivage manuel est volontairement **dans la Liste**, pas caché dans le chat : tu fais le ménage les yeux sur les cartes.

### 6.4 États vides et erreurs

- Liste vide : « Rien d’ouvert. Dis-le au chat. »
- Hors ligne : message, pas de fausse sauvegarde.
- 401 : retour login.

### 6.5 Accessibilité / langue

UI en français. Dates affichées jj/mm/aaaa, saisies natives `type="date"` (calendrier iOS).

---

## 7. Ordre de code (prochaine étape, pas maintenant)

1. Table + RLS sur Supabase.
2. Auth + lecture liste.
3. PATCH + archiver (onglet Liste utilisable **sans** IA).
4. `POST /api/chat` + les 7 outils + les 10 phrases.
5. PWA (manifest, écran d’accueil).

On peut déjà se servir de la Liste après l’étape 3 ; l’agent arrive à l’étape 4.
