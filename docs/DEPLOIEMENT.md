# Ce que **toi** tu dois faire (comptes + mise en ligne)

Le code est sur GitHub. **Il ne parle pas encore à Claude** tant que les clés ne sont pas dans Vercel. Tu n’as **rien à coller dans le chat Cursor** (surtout pas les clés).

Fais les 4 comptes **dans cet ordre**. 20–30 min.

---

## 1. GitHub (déjà là)

1. Ouvre [github.com/LeCoonEtSaBande/Panda](https://github.com/LeCoonEtSaBande/Panda).
2. Settings → **Private** (tes tâches et contacts).
3. Ne mets jamais `.env.local` dans Git.

Branche de travail : `cursor/spec-livrables-04ba` (voir [`BRANCHES.md`](BRANCHES.md)).  
Pour Vercel « production », on pointera sur **`main`** après merge de la [PR #1](https://github.com/LeCoonEtSaBande/Panda/pull/1). En attendant tu peux déployer **cette** branche.

---

## 2. Anthropic (Claude API) — pas Claude.ai Pro

L’abonnement **claude.ai** (chat) **ne sert pas** à Panda.

1. Va sur [console.anthropic.com](https://console.anthropic.com) → crée un compte (le tien, **pas** Enterprise).
2. **Billing** : carte + un **plafond** (ex. 10 $/mois).
3. **API keys** → Create → copie `sk-ant-…` **une fois**.
4. Garde-la dans un mot de passe. Tu la colleras **seulement** dans Vercel (étape 4).

Modèle prévu : **Claude Sonnet** (nom exact figé au branchement, ex. Sonnet 4/5).

---

## 3. Supabase (base + login)

1. [supabase.com](https://supabase.com) → New project (région `eu-west` si proposé).
2. **SQL Editor** → colle tout le fichier [`supabase/schema.sql`](../supabase/schema.sql) → Run.
3. **Authentication** → Providers → Email. Après **ton** premier compte, tu pourras interdire les inscriptions (Settings → Auth).
4. **Project Settings → API** note :
   - Project URL → `NEXT_PUBLIC_SUPABASE_URL`
   - `anon` `public` → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (**secret**, serveur seulement)

---

## 4. Vercel (le site en HTTPS)

1. [vercel.com](https://vercel.com) → Import **Panda** (GitHub).
2. **Root** = dépôt (pas de sous-dossier).
3. Framework : Next.js (détecté).
4. **Environment variables** (Production + Preview) :

| Nom | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-…` |
| `NEXT_PUBLIC_SUPABASE_URL` | URL projet |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clé anon |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role |

5. Branch de prod : **`main`** (après merge). Pour tester tout de suite : Preview sur `cursor/spec-livrables-04ba`.
6. Deploy. URL type `panda-xxx.vercel.app`.
7. iPhone : Safari → cette URL → Partager → **Sur l’écran d’accueil**.

---

## 5. Fichier identité (déjà dans Git)

[`config/identite.yml`](../config/identite.yml) : nom, alias, organisations (Tecmotec). Modifiable plus tard dans Paramètres.

---

## 6. Pas encore

- Nom de domaine
- Outlook

---

## En local chez toi (sans Vercel)

```bash
git clone … Panda
git checkout cursor/spec-livrables-04ba
npm install
npm run dev
```

`http://localhost:3000` — données dans **ce navigateur** (localStorage) tant que Supabase n’est pas branché. Les courses marchent. L’Assistant IA attend l’étape 2+4.
