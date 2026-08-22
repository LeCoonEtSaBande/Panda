# Panda

Liste de tâches personnelle, pilotée par un **agent conversationnel**.

Tu parles en français (texte ou, plus tard, dictée). L’agent crée et met à jour les tâches. Une page Safari sur iPhone (ajoutable à l’écran d’accueil) sert à **voir**, **corriger** et **archiver**. La vérité est une base Postgres, pas Rappels Apple ni un fichier Git.

**Statut :** spécification uniquement. Le code vient ensuite.

Spécification complète : [`docs/specification.md`](docs/specification.md).

---

## Ce que ça fait

- Créer / modifier des tâches en langage naturel (« j’ai appelé le plombier », « décale le store en décembre »).
- Champs métier : durée, perso/pro, contact, attente de retour, date butoir, sous-tâches, notes, liens.
- Suggestions (« qu’est-ce que je peux faire dans la demi-heure ? », « aujourd’hui je ne travaille pas »).
- Vue liste : corrections manuelles et archivage, sans passer par le chat.

Hors v1 : comptes multiples, WhatsApp, Siri comme cerveau, sync Rappels, anniversaires / cadences d’amis, pièces jointes fichiers, import mail automatique.

---

## Architecture (vue courte)

```text
iPhone Safari (PWA)
  onglet Chat ──────────────┐
  onglet Liste (édition) ───┤
                            ▼
                    API (Vercel)
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     Claude (Anthropic)              Supabase
     outils : créer, maj,            Postgres `tasks`
     lier, cascade, suggérer
```

Le navigateur **n’appelle jamais** l’IA ni la base directement. La clé API et la base restent côté serveur.

---

## Quel service d’IA, et comment

**Service : [Anthropic](https://console.anthropic.com/) — modèle Claude Sonnet (dernière version stable au moment du code).**

Pourquoi celui-là :

- Le produit, c’est l’**appel d’outils** (créer une tâche, la lier, décaler un butoir). Claude est fiable là-dessus.
- Le français et le suivi des règles d’agent (ne pas inventer une durée, confirmer en une ligne) tiennent bien.
- Un seul fournisseur, facturation à l’usage, pas d’appli tierce type ChatGPT à ouvrir.

**Comment ça s’utilise (mécanique, pas de code ici) :**

1. Tu crées un compte Anthropic Console, tu actives la facturation, tu génères une **clé API**.
2. La clé vit uniquement sur le serveur (variable d’environnement `ANTHROPIC_API_KEY`). Jamais dans la page Safari, jamais dans Git.
3. À chaque message, le serveur envoie à l’API Messages : l’historique court, le **contrat d’outils** (voir la spec), et un système qui reprend les règles métier.
4. Claude répond soit par un texte pour toi, soit par un ou plusieurs `tool_use`.
5. Le serveur exécute l’outil **contre Supabase**, renvoie le résultat à Claude, recommence jusqu’à une réponse texte.
6. Cette réponse s’affiche dans l’onglet Chat. La liste se rafraîchit.

**Budget perso attendu :** quelques euros par mois à usage quotidien (messages courts + quelques appels d’outils). Tu peux plafonner les dépenses dans la console Anthropic.

**Secours :** la même API d’outils existe chez OpenAI (GPT). On ne double pas en v1. Si Anthropic est down ou trop cher, le contrat d’outils est assez stable pour changer de modèle derrière le serveur sans changer la base ni l’UI.

**Ce qu’on n’utilise pas comme cerveau :** Apple Intelligence, Siri, ChatGPT dans le navigateur, n8n. Siri pourra plus tard **ouvrir** Panda ou envoyer une phrase à la même API ; il ne stocke pas les tâches.

Détail du contrat (outils, règles, phrases de test) : [section Contrat agent](docs/specification.md#3-contrat-de-lagent-conversationnel).

---

## Comptes à créer avant le code

| Service | Rôle | Lien |
|---|---|---|
| **GitHub** | Code (déjà là : ce repo). | [github.com](https://github.com) |
| **Supabase** | Base Postgres + auth (toi seul) + API. | [supabase.com](https://supabase.com) |
| **Anthropic** | Cerveau de l’agent (Claude). | [console.anthropic.com](https://console.anthropic.com) |
| **Vercel** | Héberge la page Safari et l’API. | [vercel.com](https://vercel.com) |

Tous en offre gratuite / crédits de départ, largement suffisants pour un usage perso. Compte **Supabase** et repo GitHub en **privé** : tél, mails collés, « Maman ».

Check-list et pièges : [section Services tiers](docs/specification.md#2-services-tiers--comptes-à-créer).

---

## Docs

| Fichier | Contenu |
|---|---|
| [docs/specification.md](docs/specification.md) | Architecture, comptes, contrat agent, SQL, page Safari |

Quand on passera au code : schéma SQL dans Supabase, API, page (chat + liste), clés en variables d’environnement.
