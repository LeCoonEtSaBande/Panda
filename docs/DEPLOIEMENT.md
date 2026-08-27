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

## B. Vercel — coller les clés et déployer (5 min)

1. [vercel.com](https://vercel.com) → **Add New → Project** → Import le repo **Panda** (GitHub `LeCoonEtSaBande/Panda`).
2. Framework : Next.js (détecté). Root = dépôt.
3. **Environment Variables** — coche **Production** et **Preview** pour chacune :

| Nom | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | ta clé `sk-ant-…` |
| `NEXT_PUBLIC_SUPABASE_URL` | URL projet Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clé anon |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role |

4. **Branche à déployer tout de suite** : `cursor/spec-livrables-04ba`  
   (`main` n’a pas encore l’app : on merge la PR plus tard.)
   - Settings du projet Vercel → Git → Production Branch : tu peux laisser `main` et ouvrir l’onglet **Deployments** → cliquer les déploiements **Preview** de cette branche.
   - Ou : Settings → Production Branch = `cursor/spec-livrables-04ba` le temps du proto.
5. Deploy. URL du type `https://panda-xxx.vercel.app`.
6. Retourne dans Supabase → Redirect URLs : ajoute `https://panda-xxx.vercel.app/auth/callback` et Site URL = cette adresse.

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

- Fusionner la PR dans `main` (quand tu es content du Preview)
- Nom de domaine
- Outlook
