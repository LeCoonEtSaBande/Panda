# Panda

To-do + contacts + courses, agent **Assistant / Reçu / Envoyé**, chat **Libre** (lecture seule). Une URL : **simple sur iPhone**, **plus complète sur PC**.

## Par où commencer

| Si tu veux… | Ouvre |
|---|---|
| Comprendre les **branches** GitHub | [`docs/BRANCHES.md`](docs/BRANCHES.md) |
| **Créer les comptes** et mettre en ligne | [`docs/DEPLOIEMENT.md`](docs/DEPLOIEMENT.md) |
| Le plan technique | [`docs/PLAN.md`](docs/PLAN.md) |
| Les règles métier / 22 scénarios | [`definition_initiale_projet_panda.txt`](definition_initiale_projet_panda.txt) |
| Ton nom, orgs | [`config/identite.yml`](config/identite.yml) |

## État du code (proto)

- Thème gabin-météo / contraste Cursor (fond noir, beige, **monospace**).
- Pages : Assistant, Tâches (filtres), fiche tâche, Courses, Libre, Carnet (PC), Paramètres.
- **Tâches :** bouton **Rafraîchir** sur PC ; sur iPhone **tire vers le bas** au-delà du haut de liste.
- Données **dans le navigateur** pour l’instant. Claude et Supabase : après tes comptes ([déploiement](docs/DEPLOIEMENT.md)).
- Phrase type courses (« j’achète de la farine et 12 oeufs ») → liste **sans** écran Valider.

```bash
npm install
npm run dev
```

→ [http://localhost:3000](http://localhost:3000)

## Branches

- **`main`** — ce que Vercel déploiera (après merge).
- **`cursor/spec-livrables-04ba`** — **travail en cours** (cette PR).

Détail : [`docs/BRANCHES.md`](docs/BRANCHES.md).

## Secrets

Jamais dans Git ni dans le chat. Uniquement Vercel / `.env.local` (voir `.env.example`).
