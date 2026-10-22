# Panda : collecte et analyses

Assistant de draft League of Legends pour un jungler. Pool : Fiddlesticks, Ivern, Dr. Mundo, Kayn bleu, Kayn rouge.
On collecte des parties classées solo EUW avec l'API Riot, puis on cherche des scénarios de compo où un jungler du pool gagne nettement plus que d'habitude.

Tout se fait en français : code, commentaires, messages de commit, réponses.

## Les trois branches

| Branche | Rôle |
|---|---|
| `main` | Le catalogue (`Catalogue.csv`, `Catalogue_champions_LoL.xlsx`) et le bouton « Run workflow » (`.github/workflows/lancer-collecte.yml`). |
| `cursor/analyse-6da8` | Cette branche : collecte des parties et analyses. |
| `cursor/assistant-draft-6da8` | La page d'assistant de draft (`Assistant_draft.html`), générée par `assistant/construire.py`. |

Ne pas créer d'autre branche, ne pas en supprimer, ne pas fusionner sans demande explicite du propriétaire.

## Comment tourne une collecte

- Lancement : bouton « Run workflow » de **Lancer une collecte** (sur `main`), ou modification de `analyse/collecte.ini` sur cette branche.
- `analyse/collecte.py` tire des joueurs dans les paliers de `collecte.ini` (dans l'ordre, avec passage au palier suivant quand le premier ne donne plus assez de parties neuves), télécharge leurs parties récentes (détail du match et timeline) et, pour chaque partie retenue, écrit d'abord les fichiers de détails puis, en dernier, une ligne dans `analyse/donnees/parties.csv`.
- Toutes les 10 minutes, `analyse/enregistrer.sh` committe et pousse **les données seulement** (`git pull --rebase` puis `git push`).
- À la fin, `analyse/enregistrer.sh --rapport` récupère la branche, lance `analyse/rapport.py` (qui appelle `profils.py` et `compos.py`), committe `analyse/resultats/` et pousse.
- Une collecte dure 4 h 50 (`minutes = 290`) ; l'étape « Collecter » est coupée à 295 minutes et le job à 5 h 30 (330 minutes). Rien ne doit dépasser 5 h 30.
- `mode` dans `collecte.ini` : `nouvelles` (par défaut) cherche de nouvelles parties ; `rattrapage` ne cherche rien de neuf et complète les détails des parties de `parties.csv` qui n'en ont pas encore, **sans jamais écrire dans `parties.csv`**. Un match introuvable (404) est noté dans `analyse/donnees/rattrapage_echecs.csv` et n'est plus retenté.
- Débit : la clé de développement permet environ 3 000 appels par heure. Avec la timeline, une partie coûte deux appels : compter environ 1 350 parties par heure (environ 6 500 par collecte), contre 2 550 avant.

## Ce que Claude Code peut faire

- Ajouter ou modifier des scripts d'analyse dans `analyse/` (`rapport.py`, `profils.py`, `compos.py`, nouveaux fichiers) et leurs tests dans `analyse/tests/`.
- Ajouter des fichiers de sortie dans `analyse/resultats/`, à condition qu'ils soient produits par `rapport.py` (directement ou par un script qu'il appelle).
- Lire toutes les données et tous les résultats, lancer les analyses en local.
- Committer et pousser sur cette branche pendant une collecte : c'est prévu. Les changements de `collecte.py` et `enregistrer.sh` ne serviront qu'à partir de la collecte suivante ; ceux de `rapport.py` et des scripts qu'il appelle serviront dès la fin de la collecte en cours.

## Ce que Claude Code ne doit pas faire

- **Données** : ne jamais modifier, trier, dédoublonner, réécrire ni supprimer `analyse/donnees/parties.csv` et `analyse/donnees/ecartees.csv`. Seule la collecte y écrit, en ajout.
- **Résultats** : ne pas éditer `analyse/resultats/` à la main. Ces fichiers sont régénérés et écrasés à la fin de chaque collecte : changer le script qui les produit.
- **Catalogue** : ne pas modifier `Catalogue.csv` ni l'Excel, ne reclasser aucun champion. Seul le propriétaire décide du catalogue.
- **Règle de compo** : ne pas changer `analyse/regle.py` sans accord du propriétaire. Elle doit rester identique à `assistant/regle.js` sur la branche de l'assistant ; toute modification validée se fait dans les deux.
- **`analyse/collecte.ini`** : le pousser lance une collecte. Ne le modifier que pour lancer une collecte demandée. Pour tout autre changement de ce fichier, mettre `[skip ci]` dans le message de commit. Ne pas copier la clé `cle_api` ailleurs.
- **Collectes** : ne pas lancer de collecte sans demande, ne rien lancer qui dure plus de 5 h 30. Vérifier avec `gh run list` qu'aucune collecte ne tourne avant de toucher aux workflows.
- **Durée du rapport** : `rapport.py` tourne dans le temps restant du job (environ 35 minutes, moins les sauvegardes). Une analyse lente doit pouvoir être sautée.
- **Dépendances** : `collecte.py` et `enregistrer.sh` n'utilisent que la bibliothèque standard Python et bash. Les analyses peuvent utiliser `statsmodels` et `pandas` (installés par le workflow), mais doivent continuer sans eux et ne jamais faire échouer le rapport.
- **Git** : pas de `push --force`, pas de réécriture d'historique, pas de changement de visibilité du dépôt, pas de suppression de branche.
- **Workflows** : vérifier que le YAML est valide avant de pousser (par exemple `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/collecte.yml'))"`).

## Format des données

`analyse/donnees/parties.csv`, séparateur `;`, une ligne par partie :

```
match;patch;palier;gagnant;b_top;b_jgl;b_mid;b_adc;b_sup;r_top;r_jgl;r_mid;r_adc;r_sup
```

- `match` : identifiant Riot sans le préfixe `EUW1_`.
- `palier` : initiale et division, par exemple `P2`, `E1`, `D3`.
- `gagnant` : `b` (bleu) ou `r` (rouge).
- Les noms de champions sont ceux du catalogue. Kayn est séparé en `Kayn rouge` et `Kayn bleu` ; une partie où sa forme est inconnue est écartée.

`analyse/donnees/ecartees.csv` : `match;raison` (remake, postes, kayn_sans_forme, etc.). Une partie écartée n'est jamais retéléchargée.

### Détails des parties

Quatre dossiers dans `analyse/donnees/`, un par type de fichier. Chaque dossier est découpé en tranches de 2 000 parties (`joueurs/joueurs_0001.csv`, `joueurs_0002.csv`…) pour rester loin de la limite de 100 Mo de GitHub, puisque chaque sauvegarde recommite la tranche en cours. Séparateur `;`, en-têtes fixes (listés dans `analyse/collecte.py`), case vide quand une valeur est absente. Mêmes noms de champions que `parties.csv` (Kayn rouge / Kayn bleu) ; postes `top`, `jgl`, `mid`, `adc`, `sup` ; équipes `b` et `r`.

| Dossier | Une ligne par | Contenu |
|---|---|---|
| `details_parties/` | partie | durée, fin par abandon, 5 bans par équipe (« Kayn » sans forme), et pour chaque objectif de `info.teams[].objectives` (`baron`, `champion`, `dragon`, `horde`, `inhibitor`, `riftHerald`, `tower`, `voidGator`) : `<cote>_<objectif>_premier` (0/1) et `<cote>_<objectif>_nb` |
| `joueurs/` | joueur (10 par partie, ordre de `parties.csv`) | KDA, or, cs, dégâts par type, soins, boucliers, contrôle, vision, sorts, rune principale, objets, et une sélection de `challenges` |
| `timeline_joueurs/` | joueur | à 5, 10, 15, 20, 25 et 30 minutes : or, xp, cs, niveau, dégâts aux champions, position ; vide si la partie était finie |
| `evenements/` | événement | `CHAMPION_KILL`, `ELITE_MONSTER_KILL`, `BUILDING_KILL`, `TURRET_PLATE_DESTROYED` ; `equipe` est l'équipe de l'auteur (pour un bâtiment ou une plaque, l'équipe qui le détruit) ; `participant` vaut 0 pour un sbire ou une tour ; pour un kill, dégâts reçus par la victime et nombre d'ennemis distincts qui les ont infligés |

Il n'y a pas d'« atakhan » dans les objectifs renvoyés par Riot (vérifié sur de vrais matchs d'octobre 2026) ; `voidGator` y figure. Si la timeline échoue, la partie est gardée sans lignes `timeline_joueurs` ni `evenements`.

`details_parties` est écrit en dernier pour chaque partie : une partie y figure seulement si ses détails sont complets. Lire ces fichiers avec `analyse/lecture.py`, qui concatène les tranches, ne garde que les matchs présents dans `parties.csv` et dans `details_parties`, et dédoublonne par match (une partie réécrite après une interruption n'est comptée qu'une fois) :

```python
from lecture import lire_details
for joueur in lire_details("joueurs"):
    ...
```

Ces fichiers suivent les mêmes règles que `parties.csv` : écrits en ajout par la collecte seulement, jamais modifiés à la main. Taille mesurée sur 12 vrais matchs : environ 13 Ko par partie (événements 9 Ko, joueurs 2,3 Ko, timeline 1,7 Ko, détails 0,2 Ko), soit environ 18 Mo pour une tranche d'événements.

## Tests

```
python3 -m unittest discover -s analyse/tests
```

Ils doivent passer avant chaque push.
