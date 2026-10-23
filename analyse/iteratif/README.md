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
| 3 | `bloc3_biais.py` | Apprend les biais de compo **en plus de la force des champions** et mesure s'ils prédisent mieux le gagnant sur des parties que l'apprentissage n'a pas vues (5 rotations sur A + B). | régularisation (lambda) |
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

**Score** : de combien les biais améliorent la prédiction du gagnant sur des parties non vues. C'est la baisse de la perte logarithmique moyenne, en millièmes. Elle est mesurée en **5 rotations** sur les parties de recherche (A + B) : on apprend sur 4/5, on note sur le 1/5 restant, cinq fois. Toutes les parties servent ainsi à noter, et le score dépend beaucoup moins de la chance qu'avec un seul tas B fixe.
- 0 = rien de plus que la force des champions.
- Négatif = les biais appris sur A ne tiennent pas sur B (du bruit).
- Positif = ils tiennent.

Pour donner un ordre de grandeur : un vrai biais de 55 % au lieu de 50 %, dans une situation qui arrive dans 15 % des parties, donne environ +0,2.

## Les tas de parties

Émeraude et Diamant seulement : on apprend et on valide sur les mêmes rangs. Le Plat de l'archive est écarté. Le découpage est décrit dans `decoupage.json`. Il doit être **validé avec le propriétaire** (`"valide": true`) avant tout recuit ou confirmation.

| Tas | Contenu | Parties au 23/10 | Qui le lit |
|---|---|---|---|
| A + B, recherche | l'échantillon figé et l'archive (A = 2/3, B = 1/3) | 31 147 | le recuit, en 5 rotations (apprendre sur 4/5, noter sur 1/5) ; les taux « sur A » et « sur B » des rapports sont donnés à part pour voir si un biais tient des deux côtés |
| C, confirmation | parties arrivées après l'échantillon figé (`../echantillon_fige.json`) | 2 431, à compléter par les collectes suivantes (~8 000 visées) | `confirmer.py` seulement, une fois à la fin |

- **Répartition A / B** : faite au hasard par une empreinte du numéro de partie. Une partie va toujours dans le même tas, et chaque tas a les mêmes proportions de Diamant, d'Émeraude, d'archive et de parties neuves.
- **Bloc 1** : il utilise les stats de l'échantillon figé (`champions_mesures.csv`). Il ne regarde jamais qui gagne.

## Garde-fous : pour qu'un biais trouvé soit vrai

Un algorithme qui essaie des milliers de réglages trouve toujours des « biais » par hasard. Garde-fous :

1. **Noter sur B, pas sur A.** Ce qui est appris par cœur sur A ne prédit rien sur B, et fait baisser le score.
2. **Pas de groupe par champion.**
   - Chaque groupe garde au moins 8 champions ; sinon le réglage est rejeté.
   - Au plus 12 groupes.
   - Au plus 10 champions déplacés, et seulement vers leur **groupe voisin** : le groupe mesuré le plus proche après le sien, ou le style secondaire dans le catalogue. Le catalogue reste lisible.
   - Une situation (compo X contre Y, jungler J contre compo Y…) n'est étudiée que si elle apparaît dans **au moins 200 parties de A**.
3. **Régularisation.** Les effets sont rétrécis vers 0 : lambda d'au moins 5, et plus fort pour les effets qui reposent sur peu de parties. La force des champions est réglée de la même façon, par validation croisée sur le tas d'apprentissage.
4. **Score en rotation.** Chaque partie de recherche sert à noter un modèle qui ne l'a pas vue (5 rotations). Un seul tas B fixe se laisse « apprendre » par le recuit à force d'essais : constaté le 23/10, le recuit atteignait sur B le même score avec de vraies victoires qu'avec des victoires tirées au sort.
5. **Seuil de hasard.** On refait le même recuit sur des victoires **tirées au sort selon la seule force des champions** (case « hasard » du workflow, ou `--melanger`). Là, la force des champions est vraie mais aucun biais de compo n'existe. Le score atteint malgré tout mesure combien le recuit sait « trouver » dans le bruit, à force d'essayer des réglages. Un vrai recuit doit le dépasser nettement, avec la même durée.
6. **Confirmation sur C.**
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
