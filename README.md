# Panda

Suivi d’actions (perso/pro) + carnet de contacts, avec un **agent à 3 modes** (Assistant, Message reçu, Message envoyé) et un chat **libre** en lecture seule. iPhone = version simple ; PC = version complète. Une URL.

**Statut :** spec à jour après `definition_initiale_projet_panda.txt`. Pas de code applicatif. **Aucune clé API dans ce repo.**

- Définition métier (23 scénarios) : [`definition_initiale_projet_panda.txt`](definition_initiale_projet_panda.txt)
- Spec technique : [`docs/specification.md`](docs/specification.md)
- Questions (tu réponds **dans le chat Cursor**, je remplis les fichiers) : [`docs/brief/README.md`](docs/brief/README.md)

## Socle

Safari/PC → Vercel → Claude (outils) + Supabase (`tasks`, `contacts`, `grocery_items`).

Comptes **plus tard** (jamais collés ici) : GitHub privé, Supabase, Anthropic, Vercel.
