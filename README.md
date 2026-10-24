# Panda — branche `analyse` : ce qui fait gagner, et ce qui est confirmé

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Cette branche ne contient que les analyses qui alimentent l'assistant, leurs résultats et les confirmations.
Elle ne garde **aucune copie des données** : elle les lit depuis `main`.

## Préparer et lancer

```
bash analyse/preparer.sh            # récupère collecte/, donnees/, archives/ (main) et lolalytics/ (scraping), ignorés par git
python3 analyse/lanes/dynamique.py  # puis envahir.py, ganks.py, duels.py, duree_degats.py --lolalytics lolalytics/<patch>
python3 analyse/export/exporter.py  # écrit analyse/export/assistant_donnees.json pour l'assistant
python3 -m unittest discover -s analyse/tests
```

Le bouton « Générer l'assistant Draft » (sur `main`) fait tout cela lui-même sur les données à jour, puis génère la page.

## Les dossiers

| Dossier | Rôle |
|---|---|
| `analyse/lecture.py`, `analyse/preparer.sh` | Raccourci vers le lecteur des données de `main` (`collecte/lecture.py`), et le script qui les récupère. |
| `analyse/base/` | La base commune : table des drafts et découpage en tas A, B, C (`commun.py`, `decoupage.json`), force des champions et régressions (`bloc3_biais.py`), index des drafts (`bloc2_compos.py`). |
| `analyse/catalogues/` | Le catalogue unifié (`catalogue_unifie.csv`, relu avec le propriétaire le 24/10/2026), et la version utilisée par le recuit. |
| `analyse/contres/` | Le modèle des contres par lane : force de lane de chaque champion et effet propre de chaque paire, mesurés sur l'écart d'or à 15 min. |
| `analyse/lanes/` | Ce que l'assistant calcule : or à 15 min par lane (`dynamique.py`), ganks réussis avant 15 min (`ganks.py`), envahir à 5, 10, 15 et 20 min (`envahir.py`), early/late et mix de dégâts (`duree_degats.py`). Résultats dans `lanes/resultats/`. |
| `analyse/confirmation/` | Les confirmations sur C (parties jamais vues) et leurs résultats : `confirmation_C.py` (Lolalytics, lanes, ganks, envahir), `confirmer_duree_degats.py`, `confirmer_pistes.py` (recuit). |
| `analyse/recuit/` | Le recuit simulé n° 2 (pistes « scénarios » et « teamfight ») et son test au hasard. Gardé pour la trace : **non confirmé sur C**. |
| `analyse/export/` | `exporter.py` : rassemble les modèles pour l'assistant et **ne garde que ce qui est confirmé sur C**. |
| `analyse/tests/` | Tests (après `preparer.sh`). |

## Le découpage A, B, C

- **A** (apprendre, 3/4) et **B** (vérifier, 1/4) : l'archive et les parties de `donnees/parties.csv` jusqu'au **gel**, Émeraude-Diamant seulement, partagées par empreinte du numéro de partie (`base/decoupage.json`).
- **C** (confirmer) : les parties collectées après le gel, jamais lues avant une confirmation. Une fois une confirmation faite, C est « consommé » : on pose un nouveau gel et les parties suivantes forment le nouveau C.
- Historique : gel n° 2 le 23/10/2026 (C lu le 24/10/2026 pour les confirmations ci-dessous), gel n° 3 le 24/10/2026 au soir.

## Ce qui est confirmé (C, 24/10/2026, 12 600 à 14 900 parties jamais vues)

| Résultat | Verdict | Dans l'assistant |
|---|---|---|
| Force des champions du patch, contre direct, autres contres (Lolalytics) | confirmé | oui |
| Or à 15 min par lane (une lane annoncée devant à 60 % ou plus l'est 64 à 66 % du temps) | confirmé | oui |
| Ganks réussis avant 15 min (bien calibrés) | confirmé | oui |
| Envahir vers 15 min pour un jungler Engage (tanks) ou Engage (bruisers) : +6 à +7 points à or égal | confirmé | oui |
| Envahir à 5, 10 et 20 min, autres catégories de jungler | non confirmé | non |
| Early/late : la compo la plus late gagne 39 % avant 20 min et 60 % entre 35 et 40 min | confirmé | oui |
| Mix de dégâts : moins de 20 % ou plus de 70 % de dégâts magiques, −4 points | confirmé | oui |
| Duels de junglers à or et niveau égaux (`lanes/duels.py`) : modèle d'ensemble et évolution avec la minute | confirmé (C propre aux duels : dernier tiers des parties, `confirmation/decoupage_duels.json` ; accord des forces A/C 0,92) | oui |
| Force en duel de chaque jungler | confirmée pour 26 junglers (dont Kayn rouge et Kayn bleu) ; les autres comptent comme moyens | oui |
| Recuit teamfight (13 effets de compo) | non confirmé (28 tirages au hasard sur 40 font aussi bien) | non |

Détails : `analyse/confirmation/resultats/`.

## Règles propres à cette branche

- Ne jamais committer `collecte/`, `donnees/`, `archives/` ni `lolalytics/` ici (ils viennent de `main` et `scraping`).
- Un résultat n'entre dans l'assistant qu'après confirmation sur C ; l'export le vérifie lui-même.
- Toujours apprendre et vérifier sur les mêmes rangs (Émeraude-Diamant).
