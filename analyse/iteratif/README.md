# Analyse itérative : trouver des biais de draft

Objectif : trouver, **à partir de la draft seule**, des situations où une équipe gagne nettement plus que ce que la force de ses champions laisse prévoir. Le but est d'alimenter l'assistant de draft (« si ton équipe est X et l'adverse Y, prends un jungler Z »).

Les timelines et les stats de jeu servent **seulement à ranger les champions** (bloc 1). Les biais se cherchent ensuite uniquement avec les 10 champions de la draft et le gagnant.

## La boucle en 4 blocs

```
            ┌──────────────────────────── bloc 4 : recuit simulé ─────────────────────────────┐
            │  change un peu les paramètres, garde ce qui améliore le score (parfois pire,    │
            │  pour sortir des optimums locaux), refroidit peu à peu, garde un palmarès       │
            ▼                                                                                 │
  bloc 1 : catalogue à l'instant T  ──►  bloc 2 : type de chaque compo  ──►  bloc 3 : score ──┘
  (groupe de chaque champion,            (somme pondérée par poste des        (biais de victoire
   capacités CC / front / magique)        groupes, seuil, jungler à part)      appris sur A, notés sur B)
```

| Bloc | Fichier | Ce qu'il fait | Paramètres que le recuit fait varier |
|---|---|---|---|
| 1 | `bloc1_champions.py` | Range chaque champion dans un groupe. Départ : le catalogue actuel (`Catalogue.csv`, style principal). Variante : la classification mesurée sur les timelines (`../classification.py`). | mode (catalogue ou mesuré), tanks séparés ou non, poids du style secondaire, poids des 8 familles d'indicateurs, nombre d'axes, nombre de groupes, **champions déplacés d'un groupe à l'autre** (le catalogue évolue) |
| 2 | `bloc2_compos.py` | Donne un type à chaque compo : le groupe le plus présent, pondéré par poste, s'il dépasse un seuil ; sinon « Mixte ». Calcule aussi le CC, le front et la part magique de l'équipe. | poids de chaque poste (jungle toujours au moins 0,5), seuil |
| 3 | `bloc3_biais.py` | Apprend sur A les biais de compo **en plus de la force des champions**, et mesure sur B s'ils prédisent mieux le gagnant. | régularisation (lambda) |
| 4 | `bloc4_recuit.py` | Le recuit simulé. Écrit le palmarès des meilleurs réglages et leurs biais. | — |
| — | `confirmer.py` | Réapprend les meilleurs réglages sur A + B et les mesure sur C. Seul juge final. | — |
| — | `commun.py` | Lit les drafts et fait le découpage en tas. | — |

### Bloc 3 : quels biais, et quel score

**Force des champions** : une régression logistique sur la draft, avec un coefficient par champion à son poste. C'est la référence. « Viego est fort ce patch » n'est pas un biais de compo.

**Biais cherchés**, en plus de cette force :
- type de compo ;
- compo X contre compo Y ;
- groupe du jungler contre compo adverse ;
- groupe du jungler avec compo alliée ;
- capacités : écart de CC, de front et de part magique, et croisements (notre CC contre leur front, etc.).

**Score** : de combien les biais appris sur A améliorent la prédiction du gagnant sur B. C'est la baisse de la perte logarithmique moyenne, en millièmes.
- 0 = rien de plus que la force des champions.
- Négatif = les biais appris sur A ne tiennent pas sur B (du bruit).
- Positif = ils tiennent.

Pour donner un ordre de grandeur : un vrai biais de 55 % au lieu de 50 %, dans une situation qui arrive dans 15 % des parties, donne environ +0,2.

## Les tas de parties

Émeraude et Diamant seulement : on apprend et on valide sur les mêmes rangs. Le Plat de l'archive est écarté. Le découpage est décrit dans `decoupage.json`. Il doit être **validé avec le propriétaire** (`"valide": true`) avant tout recuit ou confirmation.

| Tas | Contenu | Parties au 23/10 | Qui le lit |
|---|---|---|---|
| A, apprentissage | 2/3 de l'échantillon figé et de l'archive | 20 769 | le recuit, pour apprendre |
| B, validation | 1/3 de l'échantillon figé et de l'archive | 10 378 | le recuit, pour noter chaque réglage |
| C, confirmation | parties arrivées après l'échantillon figé (`../echantillon_fige.json`) | 2 431, à compléter par les collectes suivantes (~8 000 visées) | `confirmer.py` seulement, une fois à la fin |

- **Répartition A / B** : faite au hasard par une empreinte du numéro de partie. Une partie va toujours dans le même tas, et chaque tas a les mêmes proportions de Diamant, d'Émeraude, d'archive et de parties neuves.
- **Bloc 1** : il utilise les stats de l'échantillon figé (`champions_mesures.csv`). Il ne regarde jamais qui gagne.

## Garde-fous : pour qu'un biais trouvé soit vrai

Un algorithme qui essaie des milliers de réglages trouve toujours des « biais » par hasard. Garde-fous :

1. **Noter sur B, pas sur A.** Ce qui est appris par cœur sur A ne prédit rien sur B, et fait baisser le score.
2. **Pas de groupe par champion.**
   - Chaque groupe garde au moins 8 champions ; sinon le réglage est rejeté.
   - Au plus 12 groupes.
   - Au plus 10 champions déplacés.
   - Une situation n'est retenue que si elle apparaît dans au moins 50 parties de A.
3. **Régularisation.** Les effets sont rétrécis vers 0, d'autant plus qu'ils reposent sur peu de parties. La force des champions est réglée de la même façon, par validation croisée sur le tas d'apprentissage.
4. **Seuil de hasard.** Le même recuit tourne sur des **victoires mélangées au hasard** (workflow avec la case « hasard », ou `--melanger`). Le score qu'il atteint là, sans aucun vrai biais, est le seuil à dépasser. Ce seuil vient du fait qu'à force d'essayer des réglages, on finit par coller au bruit de B.
5. **Confirmation sur C.**
   - Réapprentissage sur A + B, puis mesure sur C, jamais vu.
   - Chaque biais est testé dans le sens trouvé.
   - Correction pour le nombre de tests (Benjamini-Hochberg).
   - **Confirmé** = moins de 5 % de risque d'être un hasard, après correction.
   - Pour l'assistant, on ne garde que les biais confirmés et d'au moins 53 %.

## Lancer

Dans GitHub, onglet Actions :
- **Lancer un recuit simulé** : durée, graine (une autre graine donne une autre exploration), case « hasard » pour mesurer le seuil de hasard.
- **Confirmer les résultats du recuit** : sur le dernier recuit, ou sur un fichier donné.

Les deux prennent le code sur la branche indiquée (`analyse-iterative` par défaut) et les données à jour sur `main`. Ils ne committent que `analyse/iteratif/resultats/`.

En local :

```
python3 analyse/iteratif/commun.py                         # comptes des tas
python3 analyse/iteratif/bloc1_champions.py --preparer     # recalcule champions_mesures.csv
python3 analyse/iteratif/bloc4_recuit.py --une-iteration   # itération 0 : catalogue actuel
python3 analyse/iteratif/bloc4_recuit.py --minutes 60 --graine 1
python3 analyse/iteratif/bloc4_recuit.py --minutes 60 --graine 1 --melanger   # seuil de hasard
python3 analyse/iteratif/confirmer.py
```

## Résultats (`resultats/`)

- `recuit_<date>.json` et `.md` : réglages essayés, palmarès des 10 meilleurs (paramètres, groupes, biais avec leur taux sur A et sur B). Suffixe `_hasard` pour les recuits sur victoires mélangées.
- `dernier_recuit.json` : le dernier vrai recuit, celui que la confirmation prend par défaut.
- `confirmation_<date>.json` et `.md` : verdict de chaque biais sur C.

## Une fois C regardé

Un recuit confirmé sur C a « consommé » C. Le suivant devra être confirmé sur des parties encore plus récentes. Pour cela, on fige un nouvel échantillon avant de relancer.
