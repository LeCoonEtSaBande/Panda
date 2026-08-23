# Brief — à remplir par toi

Ce dossier, c’est **ta matière**. Moi je m’en sers pour coder. Tant qu’il est vide / à moitié, je n’ouvre pas le code agent.

## Comment je « vois » ton ordinateur

Le lien Cursor **ne lit pas** tes fichiers locaux. Je vois uniquement :

1. **ce repo GitHub** (le plus simple) ;
2. ce que tu **colles** dans cette conversation.

**Méthode recommandée (PC) :**

1. Clone le repo `Panda` (privé).
2. Remplis les fichiers de `docs/brief/` (modèles déjà dedans).
3. Commit + push sur la branche `cursor/spec-livrables-04ba`  
   **ou** ouvre le dossier dans Cursor desktop et dis-moi « c’est poussé ».
4. Je relis GitHub. Pas besoin de m’envoyer un zip.

Évite Word / Pages. **Markdown uniquement** (`.md`), UTF-8.

---

## Les 5 nouvelles demandes — c’est possible ?

**Oui.** Ça remplace même un morceau de la spec d’origine (écriture directe en base).

| Idée | Verdict | Comment on le fait sans exploser tokens / erreurs |
|---|---|---|
| Liste / modes (« ce que je dois faire », « ce que j’ai fait », coller un mail…) | Oui | Un **sélecteur en haut du chat**. Selon le mode, le serveur envoie à Claude **un sous-ensemble d’outils**. Moins d’outils = plus fiable, moins cher. |
| Proposition → **1 clic Valider** (ou je corrige) | Oui, et c’est mieux | L’IA **n’écrit plus** dans Postgres. Elle rend une **fiche de proposition**. Toi tu Valides / modifies / annules. Le serveur applique. |
| Mail type ou ordre du jour | Oui | Mode **Rédaction** : il sort un texte à copier. Option : l’enregistrer dans `notes` **après** ton clic. |
| Fenêtre conversation libre | Oui | Mode **Libre** : **aucun outil d’écriture**. Il discute. S’il faut toucher la base : « passe en mode … ». |

Sur iPhone, une **liste déroulante native** va bien ; encore mieux : **4–5 pastilles** (chips) larges sous le champ, pouce-friendly.

Schéma d’un message :

```text
Toi choisis un MODE  →  tu parles / tu colles
        ↓
Claude (outils de CE mode seulement)
        ↓
Carte PROPOSITION (diff base et/ou texte mail)
        ↓
[ Valider ]  [ Modifier ]  [ Annuler ]
        ↓
Valider = écriture SQL. Pas avant.
```

---

## Ordre de travail pour toi (ne pas tout faire d’un coup)

| Priorité | Fichier | Temps utile | Bloque le code ? |
|---|---|---|---|
| **P0** | [`02-phrases.md`](02-phrases.md) | Le gros morceau | **Oui** — c’est le carburant |
| **P0** | [`03-validation.md`](03-validation.md) | 20 min | **Oui** — l’écran central |
| **P1** | [`01-modes.md`](01-modes.md) | 15 min (renommer / fusionner) | Presque, 5 cases à cocher |
| **P1** | [`04-redaction.md`](04-redaction.md) | 30 min + 2 vrais exemples | Pour le mode mail / ODJ |
| **P2** | [`05-chat-libre.md`](05-chat-libre.md) | 10 min | Pour ne pas qu’il bricole la base |
| **P2** | [`06-regles-delta.md`](06-regles-delta.md) | seulement si tu changes une règle déjà tranchée | Non si tu laisses tel quel |

Les **10 phrases** d’origine restent des **tests** (fin de `02-phrases.md`). On ne les injecte pas dans le prompt.

---

## Ce que je n’ai **pas** besoin que tu rédiges

- Le SQL, les noms d’outils, le découpage Next.js / Vercel.
- Une charte graphique (sauf si tu détestes une chose précise → une ligne dans `03`).
- Toute ta boîte mail. **2 collages représentatifs** suffisent (un mail, un SMS).
- Une liste exhaustive de 200 phrases. **8 à 12 par mode**, bien remplis, > 40 vagues.

---

## Checklist « tu peux coder »

Je commence le code quand :

- [ ] `01-modes.md` : les modes sont cochés (noms figés)
- [ ] `02-phrases.md` : **au moins 8 fiches** au total, dont **2 collages** (reçu et/ou envoyé)
- [ ] `03-validation.md` : les 3 questions « Valider / Modifier / Annuler » répondues
- [ ] `04-redaction.md` : **1 mail** et **1 ordre du jour** modèles (même courts)
- [ ] `05-chat-libre.md` : oui/non « il a le droit de voir mes tâches »

Tu peux pousser un premier jet incomplet : mieux vaut 8 fiches nickel que 40 vides.
