# Ce que **toi** tu dois faire maintenant (comptes déjà créés)

Tu as GitHub, Vercel, Supabase, et une clé Claude. **Ne colle jamais les clés dans le chat Cursor.** Elles vont uniquement dans Vercel et, si tu testes en local, dans `.env.local`.

L’app parle à Claude et à Supabase **seulement après** les étapes ci-dessous.

---

## A. Supabase — créer les tables (2 min)

1. Ouvre [supabase.com](https://supabase.com) → ton projet.
2. Menu **SQL Editor** → New query.
3. Copie **tout** le fichier [`supabase/schema.sql`](../supabase/schema.sql) (dans le dépôt) → colle → **Run**.
4. Tu dois voir `Success`. Les tables `settings`, `contacts`, `tasks`, `grocery_items` existent.

### Auth (pour te connecter dans Panda)

1. **Authentication → Providers** : Email activé.
2. **Authentication → Providers → Email** : pour le proto, **désactive** « Confirm email » (sinon tu dois ouvrir un mail à chaque compte).
3. **Authentication → URL Configuration** :
   - Site URL : `http://localhost:3000` (en attendant Vercel)
   - Redirect URLs : ajoute
     - `http://localhost:3000/auth/callback`
     - plus tard `https://TON-PROJET.vercel.app/auth/callback`
4. **Project Settings → API** (tu n’envoies ça nulle part, tu le colles dans Vercel) :
   - Project URL → `NEXT_PUBLIC_SUPABASE_URL`
   - `anon` `public` → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (secret, serveur seulement)

---

## B. Vercel — une fois, puis c’est automatique

Vercel lit **`main`**. Tu n’as **pas** à choisir une autre branche.

### Si le projet n’existe pas encore

1. Va sur [vercel.com/new](https://vercel.com/new).
2. Import **Panda** (`LeCoonEtSaBande/Panda`).
3. **Project Name** : `panda-assistant` (URL = `https://panda-assistant.vercel.app` s’il est libre).
4. Framework : **Next.js**. Root Directory : **laisse vide**.
5. **Environment Variables** — coche Production **et** Preview :

| Nom | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | ta clé `sk-ant-…` |
| `NEXT_PUBLIC_SUPABASE_URL` | URL projet Supabase (`https://xxxxx.supabase.co`) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clé anon |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role |
| `PANDA_USER` | ton identifiant (pas dans Git) |
| `PANDA_PASSWORD` | ton mot de passe (pas dans Git) |

6. **Deploy**. Attends **Ready** (barre verte). Pas Error.

### Si le projet existe déjà (tu as eu une 404)

1. Projet **panda-assistant** → **Settings → Git** (ou **Settings → Environments → Production → Branch Tracking**) : branche = **`main`**.
2. **Settings → Environment Variables** : les 4 clés ci-dessus si ce n’est pas déjà fait.
3. Onglet **Deployments** → **Create Deployment** → branche **`main`** → Deploy.  
   Ou : le prochain push sur `main` déploie tout seul.
4. Attends **Ready**, puis ouvre `https://panda-assistant.vercel.app`.

5. Retourne dans Supabase → URL Configuration :
   - Site URL : `https://panda-assistant.vercel.app`
   - Redirect : `https://panda-assistant.vercel.app/auth/callback` **et** `http://localhost:3000/auth/callback`

---

## C. Premier lancement

1. Ouvre l’URL Vercel (ou `http://localhost:3000` si tu as un `.env.local`).
2. Page **Connexion** : **Créer un compte** (ton email + mot de passe) puis **Entrer**.
3. Assistant : « Je dois réparer ma douche avant Noël » → carte **Valider**.
4. « J’achète de la farine et 12 œufs » → courses **sans** Valider.
5. iPhone : Safari → Partager → **Sur l’écran d’accueil**.

---

## D. En local (en plus de Vercel)

Dans le dossier de l’app :

```bash
cp .env.example .env.local
```

Remplis `.env.local` **chez toi**, jamais dans Git. Puis :

```bash
npm install
npm run dev
```

→ [http://localhost:3000](http://localhost:3000)

Sans `.env.local`, l’app marche encore en **localStorage** (ce navigateur) ; Claude et le login cloud attendent les variables.

---

## E. Suivi des tokens Claude

Console [console.anthropic.com](https://console.anthropic.com) → usage / billing. Rien dans Panda.

---

## Pas encore

- Nom de domaine perso (`panda.fr`)
- Outlook
