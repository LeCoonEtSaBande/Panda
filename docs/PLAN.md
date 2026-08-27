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

**Claude « Pro » :** l’abonnement **claude.ai** n’alimente **pas** une appli tierce. Panda parle à l’**API** (console.anthropic.com, compte **individuel / pay-as-you-go**, pas Enterprise). Chaque réponse contient `usage` ; on **cumule** ça. On ne lit pas le solde Console.

Jauge = `tokens_consommés depuis jour_reset` / `tokens_par_mois` (fichier identité, modifiable en Paramètres).

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

Pas d’illustration, pas de gradient. Chiffres tabulaires (jauge, dates).

---

## 3. Pages

| Route | iPhone | PC |
|---|---|---|
| `/` Assistant (3 modes + jauge) | oui | oui |
| `/validation` une action | oui | oui |
| `/redaction` mailto/smsto | oui | oui |
| `/courses` | oui | oui |
| `/libre` jauge | oui | oui |
| `/taches` recherche + 3 filtres | cartes | tableau + blocs |
| `/taches/[id]` inspecter | oui | oui |
| `/contacts` | non (fiche depuis tâche) | carnet |
| `/parametres` identité + plafond tokens | oui | oui |
| `/login` | oui | oui |
| Archive tâches | — | `/taches?archive=1` |

Nav bas iPhone : Assistant · Tâches · Courses · Libre.

---

## 4. Base (Supabase)

- `settings` — seed depuis `config/identite.yml` (nom, alias, orgs, `tokens_par_mois`, `jour_reset` 1–28)
- `contacts` — + **`pronom`** `tu` \| `vous`, **défaut `vous`**. À la création : `tu` si organisation ∈ tes orgs, sinon `vous`. Tu forces `tu` pour ceux que tu tutoies déjà.
- `tasks` — `depends_on_ids uuid[]` (liste, toutes sur la tâche principale)
- `grocery_items`
- `token_usage` — une ligne par appel Claude (`input_tokens`, `output_tokens`, cache)
- `pending_proposals` — file de validation (perdue si onglet fermé)

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
3. Jauge (compteur `token_usage` + plafond / jour reset)
4. Courses (manuel + Assistant sans Valider)
5. Tâches + filtres + inspecter (sans IA)
6. Contacts PC + `pronom`
7. Assistant + file de validation
8. Rédaction mail/SMS
9. Chat libre
10. Tests des scénarios 1–22 (ceux du `.txt`)

Hors proto : Outlook, PJ, synchro carnet, récurrence active, Google Maps.
