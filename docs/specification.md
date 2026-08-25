# Panda — spécification (après définition initiale)

Source métier : [`definition_initiale_projet_panda.txt`](../definition_initiale_projet_panda.txt) (23 scénarios = tests d’acceptation).

**Implémentable : oui.** Même socle technique. **La base change** (2 tables métier, plus une pour les courses). L’agent n’écrit plus tout seul : carte → **Valider**.

Les 23 phrases du `.txt` **gagnent** sur les anciennes règles (durée 15 min, sous-tâches en liste d’ids, contact dénormalisé sur la tâche).

---

## 1. Vision

Panda = **suivi d’actions** (perso + pro) + **carnet de contacts**, pilotés par un agent à **3 modes**, plus un chat **libre** (lecture seule).

Ce n’est pas un scanner d’inbox. Tu parles ou tu colles un extrait. Outlook / PJ / synchro contacts = **après**.

---

## 2. Architecture (maintenue)

```text
iPhone (simple)  ou  PC (complet)
        même URL, même compte
                │
                ▼
        Vercel (page + API)
                │
     ┌──────────┴──────────┐
     ▼                     ▼
 Claude Sonnet         Supabase
 (outils selon mode)   Postgres
                       tasks, contacts
                       grocery_items
                       auth
```

- **Anthropic Claude Sonnet** + tool use. Clé **uniquement** sur Vercel. Jamais dans Git, jamais dans le chat.
- **Supabase** = vérité. Pas Git, pas Rappels.
- **Une seule app web** (responsive). Pas deux codebases. Écrans **masqués ou simplifiés** sur téléphone.
- Cookie de session long (« déjà connecté ») + mot de passe ou magic link. Pas de reconnaissance d’appareil type empreinte hardware (fragile, douteux). « Rester connecté » = le même effet, fluide.

Hors v1 (déjà dans tes évolutions) : lecture/écriture Outlook, PJ, synchro carnet Outlook.

---

## 3. Téléphone vs PC

| | **iPhone (simple)** | **PC (complet)** |
|---|---|---|
| Connexion | Oui, puis invisible | Idem |
| 3 modes + chat + carte Valider | **Oui — écran principal** | Oui |
| Chat libre | Oui | Oui + **compteur tokens / budget** (plus lisible) |
| Rappels (aujourd’hui / semaine / mois / retard) | **Boutons** | Boutons + tableau |
| Personnes à relancer | **Bouton** | Bouton + tableau trié |
| Liste des tâches | Cartes, archiver 1 clic | Tableau + **blocs de dépendances** |
| Contacts | Fiche courte, tel/mail cliquables | **Carnet** : recherche, ajout, édition tous champs |
| Courses | Liste cochable (si v1) | Idem |
| Recherche Google / Maps | Barre (nouvel onglet) | Idem |
| Édition manuelle lourde (récurrence, dépendances, historique) | Non (agent ou PC) | Oui |
| Rédaction mail / ODJ | Texte à copier | Texte + large zone |

Sur iPhone on **ne** reconstruit **pas** un Excel. On capture et on relance.

---

## 4. Base de données (changée)

Plus une seule table `tasks` avec tél sur la ligne. **Deux** tables métier (+ courses).

### 4.1 `contacts`

| Colonne | Sens |
|---|---|
| `id` | UUID interne |
| `display_id` | Ex. `C2026001` (lisible) |
| `last_name`, `first_name` | Nom, prénom |
| `role` | Fonction |
| `organization` | |
| `phone`, `email`, `url` | Tél, mail, lien |
| `alias` | « Pédiatre de ma fille », « Papa » |
| `user_id` | Toi |
| `created_at`, `updated_at` | |

**Création autorisée seulement si :**  
`(nom OU prénom OU organisation) ET (téléphone OU email OU lien)`.  
Sinon l’agent **refuse** et le nom reste du **texte** sur la tâche (`interlocutor_text`).

### 4.2 `tasks`

| Colonne | Sens |
|---|---|
| `id` / `display_id` | UUID / `T20260001` |
| `action` | Intitulé **courant** (se met à jour, l’ancien va dans l’historique) |
| `status` | `a_faire` \| `en_attente` \| `fait` |
| `actor` | `moi` **ou** id contact (`qui_agit`) |
| `interlocutor_id` | Contact, nullable |
| `interlocutor_text` | Si pas de fiche (ex. « Rémi Parent » avant email) |
| `due_at` | Date butoir |
| `context` | `pro` \| `perso` |
| `recurrence` | Texte/json, **v1 tardive** si trop flou |
| `history` | Liste `{ date, action }` — append only |
| `depends_on_id` | **Une** autre tâche (prérequis) |
| `archived_at` | Null = active |
| `updated_at` | |

**Plus dans cette BDD :** `duration_min`, `waiting_for_reply` (remplacé par le statut `en_attente`), `notes`/`links` sur la tâche (l’historique + le contact portent le contexte), liste `subtask_ids` (remplacé par `depends_on_id` sur la tâche **bloquée**).

Règle d’intitulé : si l’interlocuteur est dans **une de tes organisations**, on **n’écrit pas** le nom de la boîte dans `action`. Sinon on le met (« de chez Roche »).

Quand statut → `en_attente` : `actor` = l’interlocuteur (c’est **lui** qui doit agir). Quand c’est toi : `actor` = `moi`.

### 4.3 `grocery_items` (courses, parallèle)

`id`, `user_id`, `label`, `checked`, `sort`, timestamps. Pas d’agent obligatoire : saisie manuelle + éventuellement l’assistant.

### 4.4 Paramètres utilisateur

`my_organizations` (liste de chaînes, ex. Tecmotec) — pour la règle d’intitulé.  
`monthly_ai_budget` — pour l’affichage « tokens / € restants » (estimation d’usage API, pas le solde Anthropic au centime).

---

## 5. Agent

### 5.1 Trois modes (outils différents)

| Mode | Entrée | Outils |
|---|---|---|
| **Assistant** | Tu parles à Panda | Créer/maj tâches **et** contacts, rédiger mail/ODJ, décaler des dates, lister relances |
| **Message reçu** | Collage mail/SMS **reçu** | Extraire contacts + tâches (toi = destinataire) |
| **Message envoyé** | Collage de ce **que tu as envoyé** | Contacts + tâches (souvent → `en_attente`) |

**Libre** (fenêtre à part) : **aucun** outil d’écriture. Lecture tâches/contacts. Peut **ouvrir un lien** (Doctolib). Si tu demandes une maj : *utilise Assistant*.

Boutons **sans** passer par Claude (SQL direct, 0 token) :

- Tâches dues : aujourd’hui / cette semaine / ce mois / en retard  
- Personnes à relancer : `en_attente`, tri **les plus anciennes** (date de passage en attente / dernier historique)

### 5.2 Carte proposition

Chaque réponse Assistant / Reçu / Envoyé → **diff** (tâches + contacts + éventuellement texte de mail).  
**Valider** = écriture. **Modifier** / **Annuler** = pas d’écriture (ou nouvelle proposition).

Libre : pas de carte d’écriture.

### 5.3 Contrat compact (prompt)

Règles courtes + schémas d’outils. Les 23 scénarios = **tests**, pas injectés à chaque message. Photo base : tâches actives **sans** tout l’historique + contacts cités. Prompt caching Anthropic.

---

## 6. Découpage réaliste

| V1 proto | Juste après | Plus tard (ton §6) |
|---|---|---|
| Auth, 2 tables, 3 modes, Valider, Libre lecture, boutons rappels/relances, liste+archive, carnet PC, Google/Maps en nouvel onglet | Courses, récurrence, compteur budget soigné, blocs dépendances soignés | Outlook, PJ, synchro contacts |

**Oui on maintient** Vercel + Claude + Supabase.  
**Non on ne maintient pas** l’ancienne table unique ni les 6 pastilles (À faire / Fait / Reçu / Envoyé / Rédiger / Libre comme modes d’écriture). Rédiger = **dans Assistant**. Libre = à part.
