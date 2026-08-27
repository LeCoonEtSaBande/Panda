# Panda — spécification

Source métier : [`definition_initiale_projet_panda.txt`](../definition_initiale_projet_panda.txt).

**Implémentable : oui.** Socle inchangé : une URL, Vercel, Claude Sonnet, Supabase. L’IA propose ; **Valider / Non / Tout annuler** (une action à la fois). Fermer la page = tout annuler. Pas de 2ᵉ message tant que le cycle n’est pas fini.

---

## Décisions figées (tes réponses)

| Sujet | Décision |
|---|---|
| iPhone / PC | Accueil = Assistant ; PC = même chose + visuel tâches riche + **archive** + **carnet** |
| Courses | **Proto**, action **immédiate** (pas de carte Valider) |
| Google / Maps | **Oublier** |
| Récurrence | Champ en base, **comportement après** le proto |
| Durée / 30 min | **Oublier** |
| Relancer (bouton) | **Supprimé**. Scénario 5 = chat **Libre**. Filtre `En attente` + question Assistant (scénario 6). |
| 2ᵉ message | **Bloqué** tant que Valider/Non/Tout annuler pas fini |
| Fermeture page | **Annule** la requête en cours |
| Plusieurs actions | **Une carte par action**, à la suite (Valider ou Non), ou Tout annuler |
| Identité | **Paramètres** dans l’app. Proto : Lee Sin ; Lee, L. Sin, M. Sin, Mr Sin ; org **Tecmotec**. |
| Tutoiement | Champ contact **`pronom`** : `tu` \| `vous`, **défaut `vous`**. `tu` si org ∈ tes organisations à la création, ou si tu le règles (ceux que tu tutoies déjà). |
| Visuel | gabin-météo + Cursor Night HC : fond `#0e0e0e`, accent beige `#b29f84`, **monospace** |
| Rédaction mail/SMS | Zones `mailto:` / `smsto:` + texte éditable + copier ; **C’est envoyé** = enchaîne comme un **Message envoyé** ; **Annuler** = rien |
| Ordre du jour | Texte simple, pas le flux mailto |

---

## Architecture

```text
iPhone (simple)  /  PC (complet)     même URL, même compte
        →  Vercel
              → Claude (outils selon ASSISTANT / REÇU / ENVOYÉ)
              → Supabase : tasks, contacts, grocery_items, settings
```

Libre = lecture seule. Courses via Assistant = écriture directe.

Clés API : uniquement variables Vercel, jamais Git.

---

## Téléphone vs PC

**iPhone — 4 pages**

1. **Accueil / Assistant** — 3 modes, champ bloqué pendant validation.  
2. **Validation** — une action, puis la suivante : Valider / Non / Tout annuler.  
3. **Courses** — cocher, ajouter, OK = barrés disparus + ajouts sauvés.  
4. **Chat libre**  
5. **Tâches** — recherche + filtres ; clic → Inspecter / SMS / Email (rédaction).  
Clic contact (sur une carte) → coords, puis `tel:` / `mailto:` / `sms:`.

**PC** : idem + tableau tâches plus complet + **archive** + **carnet d’adresses** + **Paramètres** (identité, orgs).

---

## Base

### `settings` (modifiable dans l’app)

`display_name`, `name_aliases[]`, `organizations[]`.

### `contacts`

id, display_id, nom, prénom, fonction, organisation, tél, email, lien, alias, **`pronom`** (`tu` \| `vous`, défaut `vous`).

Création si `(nom ∪ prénom ∪ org) ∩ (tél ∪ email ∪ lien)`.

### `tasks`

id, display_id, action, statut (`a_faire` \| `en_attente` \| `fait`), qui_agit (`moi` ou contact), interlocuteur_id **ou** texte, due_at, contexte, recurrence (stocké, ignoré en v1), history[], **`depends_on_ids uuid[]`** (liste ; toutes les dépendances sur la **tâche principale**, pas de cascade A→B→C — note l.97).

Tri liste : `due_at` croissant (vides en bas) puis `updated_at` **le plus ancien en haut**.

### `grocery_items`

label, checked. Pas d’archive. OK page = supprimer les cochés.

---

## Filtres tâches (remplacent Relancer)

1. **A faire avant le** : Ajd (jusqu’à minuit) / Demain / Semaine (jusqu’au **prochain dimanche**) / 1 mois (30 jours)  
2. **A faire / En attente**  
3. **Pro / Perso**

Recherche : Action, Historique, Interlocuteur.

« Personnes à relancer » = filtre **En attente**, tri déjà « moins récentes en haut ». L’Assistant peut quand même **lister** ça à l’oral (scénario 6).

---

## Agent

Outils selon le mode. Photo base compacte + consignes courtes. Tes scénarios = **tests**, pas le prompt.

Brouillons mail/SMS : `pronom` du contact (`tu` / `vous`).
