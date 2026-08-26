# 4 — Écarts (numéros de lignes dans `definition_initiale_projet_panda.txt`)

Tu corriges **dans ce `.txt`**, pas ici. Ci-dessous : uniquement ce qui casse une date, un id, ou le sens.

Les n° sont les **lignes du fichier GitHub** actuel.

---

## À corriger (clair)

| Ligne(s) | Scénario | Problème | Correction probable |
|---|---|---|---|
| **114** | 3 | Tél dans la phrase : `06060606060` (11 chiffres) | Même n° qu’en ligne **121** : `0606060606` |
| **170** | 7 | `Date de modification; 27/08/2026` alors que la phrase est le **30/08** (l.166) | `30/08/2026` |
| **235** | 10 | `A Faire Avant le; 31/09/2026` — **septembre n’a pas 31 jours**. La phrase dit « aujourd’hui » le 31/08 (l.225–226) | `31/08/2026` |
| **324** | 13 | Tâche « Envoyer à **Aurélie** … » mais `Interlocuteur; C2026003` = **Pallot** | `C2026002` (Aurélie), sauf si tu veux garder Pallot exprès |
| **350** | 14 | `Date de modification; 31/08/2026` alors que le message est le **08/09** (l.332) | `08/09/2026` |
| **358** | 14 | Historique : `37/08/2026` — date impossible | `31/08/2026` (création de T20260004) |
| **386** | 17 | `Date de modification; 08/09/2026` alors que la phrase est le **09/09** (l.382) | `09/09/2026` |

---

## À trancher (pas forcément une faute)

| Ligne(s) | Scénario | Question |
|---|---|---|
| **169–178** | 7 | « Ma douche est réparée » passe en **Fait** alors qu’on n’a jamais reçu le devis (on était En attente l.145). Volontaire (tu coupes le suivi) ? |
| **178 vs 184–189** | 7 et 8 | L’affichage historique (l.188–189) a la ligne devis + « Tâche complétée » ; le champ `Historique` de la tâche (l.178) **n’a pas** la ligne devis du 27/08. Aligner les deux. |
| **408–420** | 18 | **Préparer** un mail passe déjà la tâche en **En attente** (comme si c’était envoyé). Tu confirmes : Valider le brouillon = envoyé ? |
| **443** | 19 | `Dépend de; T20260008` alors que T08 n’est **créée qu’en l.445**. Le lien est bon (T05 bloquée par l’accès info) ; mets T08 **avant** dans le texte, ou laisse comme résultat final. |
| **450** | 19 | « Demander au **service informatique** » mais `Interlocuteur; C2026003` = Pallot. Interlocuteur vide, ou un contact « DSI », ou Pallot volontaire ? |

---

## Pas un bug

- **l.246–251** : décalage +7 jours `07/09/2026` — cohérent **si** tu corriges la l.235 en `31/08/2026`.
- **l.307 / l.320** : org absente pour Pallot (Tecmotec = chez toi), org Roche pour Aurélie — cohérent avec ta règle.

Quand tu as corrigé le `.txt` et poussé, dis-le : je retire les lignes de ce tableau.