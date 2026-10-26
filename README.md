# Panda — branche `analyse` : ce qui fait gagner, et ce qui est confirmé

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Cette branche ne contient que les analyses qui alimentent l'assistant, leurs résultats et les confirmations.
Elle ne garde **aucune copie des données** : elle les lit depuis `main`.

## Préparer et lancer

```
bash analyse/preparer.sh            # récupère collecte/, donnees/, archives/ (main) et lolalytics/ (scraping), ignorés par git
python3 analyse/catalogues/datadragon.py   # catalogue et sorts (fait aussi par le bouton « Mettre à jour le catalogue (Data Dragon) »)
python3 analyse/types/classer.py         # types des champions (après validation du propriétaire)
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
| `analyse/catalogues/` | Le **catalogue unifié** (`catalogue_unifie.csv`) : chaque champion, son identifiant Riot et ses 10 types (« oui » dans la colonne du type). Les **sorts** (`sorts.csv`) : chaque sort dans une seule catégorie, contrôle, déplacement ou protection, d'après Data Dragon (`datadragon.py`, bilan dans `datadragon.md`), corrigés à la main dans `sorts_corrections.csv`. L'**ancien catalogue** (`ancien_catalogue_2026-10-24.csv` : styles, groupes teamfight), gardé pour les ganks et envahir (confirmés avec ses catégories de jungler) et pour le recuit ; `catalogue_unifie_recuit2.csv`, celui du recuit n° 2. |
| `analyse/types/` | La **classification en types** (`classer.py`) : mesures tirées des parties, apprises sur les champions de référence du propriétaire (`references.csv`), A pour apprendre, B pour vérifier ; ses choix à la main (`validations.csv`) passent avant le calcul. Résultats : `resultats/notes.csv` (note de 0 à 100 par type), `resultats/types.md`. |
| `analyse/contres/` | Le modèle des contres par lane : force de lane de chaque champion et effet propre de chaque paire, mesurés sur l'écart d'or à 15 min. |
| `analyse/lanes/` | Ce que l'assistant calcule : or à 15 min par lane (`dynamique.py`), ganks réussis avant 15 min (`ganks.py`), envahir à 5, 10, 15 et 20 min (`envahir.py`), duels de tous les champions, chacun avec l'or et le niveau habituels de son poste, vérifiés sur B (`duels.py`), early/late et mix de dégâts (`duree_degats.py`). Résultats dans `lanes/resultats/`. |
| `analyse/confirmation/` | Les confirmations sur C (parties jamais vues) et leurs résultats : `confirmation_C.py` (Lolalytics, lanes, ganks, envahir), `confirmer_duree_degats.py`, `confirmer_duels.py` (avec son propre découpage, `decoupage_duels.json`), `confirmer_pistes.py` (recuit). |
| `analyse/recuit/` | Le recuit simulé n° 2 (pistes « scénarios » et « teamfight ») et son test au hasard, lancé par le bouton « Lancer un recuit simulé », confirmé par « Confirmer un recuit sur C ». Le recuit teamfight du 24/10/2026 n'a **pas été confirmé sur C**. |
| `analyse/export/` | `exporter.py` : rassemble les modèles pour l'assistant et **ne garde que ce qui a passé sa vérification** (C pour les recuits et les analyses confirmées avant le 26/10/2026, B pour les duels et les types), avec les types, les sorts et les identifiants Riot. |
| `analyse/tests/` | Tests (après `preparer.sh`). |

## Les trois types d'analyse

- **Recuits** (règles de compo, scénarios) : tas **A** (choix des réglages), **B** (jugement), **C** (confirmation sur des parties jamais vues). On teste beaucoup de règles : sans C, le risque de garder un effet trouvé par hasard est trop grand.
- **Lolalytics** (« plus » et « moins » de victoire du patch) : pas de tas, chiffres de Lolalytics.
- **Nos parties** (avantage d'or, ganks, envahir, duels, classification des champions) : tas **A** (apprendre) et **B** (vérifier), sans C. Une seule question par analyse, ou beaucoup de petites questions corrigées pour leur nombre (Benjamini-Hochberg) : B suffit.
- Les résultats « nos parties » confirmés sur C avant le 26/10/2026 (or à 15 min, ganks, envahir, early/late, mix de dégâts) gardent cette confirmation.

## Le découpage A, B, C

- **A** (apprendre, 3/4) et **B** (vérifier, 1/4) : l'archive et les parties de `donnees/parties.csv` jusqu'au **gel**, Émeraude-Diamant seulement, partagées par empreinte du numéro de partie (`base/decoupage.json`).
- **C** (confirmer) : les parties collectées après le gel, jamais lues avant une confirmation. Une fois une confirmation faite, C est « consommé » : on pose un nouveau gel et les parties suivantes forment le nouveau C.
- Historique : gel n° 2 le 23/10/2026 (C lu le 24/10/2026 pour les confirmations ci-dessous), gel n° 3 le 24/10/2026 au soir (42 101 parties : C repart de zéro et se remplit avec les prochaines collectes).
- Sans nouvelle collecte, on peut confirmer sur un C pris dans le temps (les parties les plus récentes), à condition de fixer les règles et les tests avant de lancer le calcul : c'est ce qui a été fait pour les duels (`confirmation/decoupage_duels.json`).

## Ce qui est confirmé ou vérifié

Confirmé sur C le 24/10/2026 (12 600 à 14 900 parties jamais vues), sauf mention « vérifié sur B ».

| Résultat | Verdict | Dans l'assistant |
|---|---|---|
| Force des champions du patch, contre direct, autres contres (Lolalytics) | confirmé | oui |
| Or à 15 min par lane (une lane annoncée devant à 60 % ou plus l'est 64 à 66 % du temps) | confirmé | oui |
| Ganks réussis avant 15 min (bien calibrés) | confirmé | oui |
| Envahir vers 15 min pour un jungler Engage (tanks) ou Engage (bruisers) : +6 à +7 points à or égal | confirmé | oui |
| Envahir à 5, 10 et 20 min, autres catégories de jungler | non confirmé | non |
| Early/late : la compo la plus late gagne 39 % avant 20 min et 60 % entre 35 et 40 min | confirmé | oui |
| Mix de dégâts : moins de 20 % ou plus de 70 % de dégâts magiques, −4 points | confirmé | oui |
| Duels (1 contre 1) de tous les champions, chacun avec l'or et le niveau habituels de son poste (`lanes/duels.py`, 515 000 duels, 26/10/2026) : modèle d'ensemble et évolution avec la minute | vérifié sur B (gain 14 et 7 millièmes) | oui |
| Force en duel de chaque champion | vérifiée sur B pour 126 champions sur 173 (accord A/B 0,94) ; les autres comptent comme un champion moyen de leur poste, sans évolution avec la minute | oui |
| Types des champions (`types/classer.py`) | même décision sur A et sur B pour 94 à 100 % des champions selon le type ; en attente de la validation du propriétaire | oui |
| Recuit teamfight (13 effets de compo) | non confirmé (28 tirages au hasard sur 40 font aussi bien) | non |

Détails : `analyse/confirmation/resultats/`.

## Règles propres à cette branche

- Ne jamais committer `collecte/`, `donnees/`, `archives/` ni `lolalytics/` ici (ils viennent de `main` et `scraping`).
- Un résultat n'entre dans l'assistant qu'après la vérification de son type d'analyse (C pour un recuit, B pour une analyse de nos parties) ; l'export le vérifie lui-même.
- Les duels avant le 26/10/2026 comparaient l'or brut : un support, toujours moins riche, passait pour fort « à or égal » quand il gagnait malgré ce retard normal. Corrigé en comparant l'avance de chacun sur la normale de son poste.
- Toujours apprendre et vérifier sur les mêmes rangs (Émeraude-Diamant).
