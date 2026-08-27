# Plan définitif — Panda

Document d’exécution. Métier : [`definition_initiale_projet_panda.txt`](../definition_initiale_projet_panda.txt). Identité seed : [`config/identite.yml`](../config/identite.yml).

---

## 1. Architecture

```text
iPhone / PC  (même URL, PWA)
        │
        ▼
Next.js (App Router) sur Vercel
        │
        ├── Claude API  (Messages + tools)     clé ANTHROPIC_API_KEY
        └── Supabase Postgres + Auth           URL + service_role côté serveur
```

Une app, CSS responsive : iPhone = 4–5 pages simples ; PC = + archive + carnet + tableau.

**Claude « Pro » :** l’abonnement **claude.ai** n’alimente **pas** une appli tierce. Panda parle à l’**API** (console.anthropic.com). La conso se suit **dans la Console Anthropic**, pas dans Panda.

---

## 2. Identité visuelle

Inspiré **gabin-météo** (`affichage-web`) + contraste type Cursor Night High Contrast.

| Jeton | Valeur |
|---|---|
| Fond | `#0e0e0e` (proche noir) |
| Surface | `#161616` |
| Trait | `#2a2a2a` → un peu plus marqué sur focus |
| Texte | `#e6e6e6` / `#f2f2f2` |
| Muet | `#7a7a7a` |
| Accent | `#b29f84` (beige gabin) |
| Police | `ui-monospace, "SF Mono", Menlo, "Cascadia Mono", Consolas, monospace` |
| Tap | ≥ 44 px, pastilles mode soulignées beige |

Pas d’illustration, pas de gradient. Chiffres tabulaires (dates).

---

## 3. Pages

| Route | iPhone | PC |
|---|---|---|
| `/` Assistant (3 modes) | oui | oui |
| `/validation` une action | oui | oui |
| `/redaction` mailto/smsto | oui | oui |
| `/courses` | oui | oui |
| `/libre` | oui | oui |
| `/taches` recherche + 3 filtres | cartes | tableau + blocs |
| `/taches/[id]` inspecter | oui | oui |
| `/contacts` | non (fiche depuis tâche) | carnet |
| `/parametres` identité | oui | oui |
| `/login` | oui | oui |
| Archive tâches | — | `/taches?archive=1` |

Nav bas iPhone : Assistant · Tâches · Courses · Libre.

---

## 4. Base (Supabase)

- `settings` — seed depuis `config/identite.yml` (nom, alias, orgs)
- `contacts` — + **`pronom`** `tu` \| `vous`, **défaut `vous`**. À la création : `tu` si organisation ∈ tes orgs, sinon `vous`. Tu forces `tu` pour ceux que tu tutoies déjà.
- `tasks` — `depends_on_ids uuid[]` (liste, toutes sur la tâche principale)
- `grocery_items`
- `pending_proposals` — file de validation **dans l’onglet** (perdue si page fermée)

RLS : `user_id = auth.uid()`.

---

## 5. Agent

Modes : `ASSISTANT` | `MESSAGE_RECU` | `MESSAGE_ENVOYE`. Outils filtrés. Libre = lecture + ouvrir lien.

Validation : **une** proposition à la fois. Valider / Non / Tout annuler. Champ Assistant **verrouillé**. Courses : écriture **immédiate**.

**C’est envoyé** → même pipeline que Message envoyé.

Consignes courtes + cache prompt. Scénarios du `.txt` = tests, pas le prompt.

---

## 6. Ordre de code (proto)

1. App Next + thème gabin/HC + PWA shell + auth
2. SQL + seed identité
3. Courses (manuel + Assistant sans Valider)
4. Tâches + filtres + inspecter (sans IA)
5. Contacts PC + `pronom`
6. Assistant + file de validation
7. Rédaction mail/SMS
8. Chat libre
9. Tests des scénarios 1–22 (ceux du `.txt`)

Hors proto : Outlook, PJ, synchro carnet, récurrence active, Google Maps.
