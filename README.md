# Panda — branche `analyse` : ce qui fait gagner, et ce qui est confirmé

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Cette branche ne contient que les analyses qui alimentent l'assistant, leurs résultats et les confirmations.
Elle ne garde **aucune copie des données** : elle les lit depuis `main`.

## Préparer et lancer

```
bash analyse/preparer.sh            # récupère collecte/, donnees/, archives/ (main) et lolalytics/ (scraping), ignorés par git
python3 analyse/catalogues/datadragon.py   # catalogue et sorts (fait aussi par le bouton « 3 · Data Dragon »)
python3 analyse/types/classer.py         # types des champions (ses choix de validations.csv passent avant le calcul)
python3 analyse/lanes/dynamique.py  # puis envahir.py, ganks.py, duels.py, duree_degats.py --lolalytics lolalytics/<patch>
python3 analyse/export/exporter.py  # écrit analyse/export/assistant_donnees.json pour l'assistant
python3 -m unittest discover -s analyse/tests
```

Le bouton « 5 · Générer l'assistant Draft » (sur `main`) recalcule lui-même les lanes, les ganks, envahir, les duels, les dégâts, les types et l'export sur les données à jour, puis génère la page (sans committer ces recalculs ici). Le catalogue a son bouton (« 3 · Data Dragon »), le recuit aussi (« 4 · Recuit »).

## Les dossiers

| Dossier | Rôle |
|---|---|
| `analyse/lecture.py`, `analyse/preparer.sh` | Raccourci vers le lecteur des données de `main` (`collecte/lecture.py`), et le script qui les récupère. |
| `analyse/base/` | La base commune : table des drafts et découpage en tas A, B, C (`commun.py`, `decoupage.json`), force des champions et régressions (`bloc3_biais.py`), index des drafts (`bloc2_compos.py`). |
| `analyse/catalogues/` | Le **catalogue unifié** (`catalogue_unifie.csv`) : chaque champion, son identifiant Riot et ses 10 types (« oui » dans la colonne du type). Les **sorts** (`sorts.csv`) : chaque sort dans une seule catégorie, contrôle, déplacement ou protection, d'après Data Dragon (`datadragon.py`, bilan dans `datadragon.md`), corrigés à la main dans `sorts_corrections.csv`. L'**ancien catalogue** (`ancien_catalogue_2026-10-24.csv` : styles, groupes teamfight), gardé pour les ganks et envahir (confirmés avec ses catégories de jungler) et pour le recuit ; `catalogue_unifie_recuit2.csv`, celui du recuit n° 2. |
| `analyse/types/` | Les **types des champions** : les choix du propriétaire (`validations.csv`, tous les champions revus dans la page « Types des champions » le 26/10/2026, avec ses remarques dans `remarques.csv`) font le catalogue. `classer.py` note chaque type de 0 à 100 à partir de nos parties (1 à 3 mesures par type, apprises sur ses choix, mesures du tas A vérifiées sur B) : ces notes classent ses types (l'assistant affiche Carry, Tank et HP, plus les deux autres styles les mieux notés), montrent ce que les parties voient en plus de ses choix (`resultats/types.md`), classent un champion pas encore revu et disent qui est **fragile** (encaisse peu par minute : une cible même sans être carry ni enchanteur). Le 11e type, **HP** (27/10/2026 : encaisse beaucoup sans être un tank), validé par le propriétaire le 27/10 (49 champions) et appris comme les autres (dégâts encaissés et atténués par minute). |
| `analyse/contres/` | Le modèle des contres par lane : force de lane de chaque champion et effet propre de chaque paire, mesurés sur l'écart d'or à 15 min. |
| `analyse/lanes/` | Ce que l'assistant calcule : or à 15 min par lane (`dynamique.py`), ganks réussis avant 15 min (`ganks.py`), envahir à 5, 10, 15 et 20 min (`envahir.py`), duels de tous les champions, chacun avec l'or et le niveau habituels de son poste, vérifiés sur B (`duels.py`), early/late et mix de dégâts (`duree_degats.py`). Résultats dans `lanes/resultats/`. |
| `analyse/confirmation/` | Les confirmations sur C (parties jamais vues) et leurs résultats : `confirmation_C.py` (Lolalytics, lanes, ganks, envahir), `confirmer_duree_degats.py`, `confirmer_duels.py` (avec son propre découpage, `decoupage_duels.json`), `confirmer_pistes.py` (recuit). |
| `analyse/recuit/` | Le **recuit n° 3** (`recuit_styles.py`, 27/10/2026) : règles de compo sur les 11 types du catalogue unifié, sans reclassement (le recuit ne règle que le coefficient de chaque type, le poids des postes et le seuil « compo X ») ; piste « styles » (les 10 scénarios relus avec le propriétaire, avec leur sens attendu) et piste « styles_libre » (tous les croisements de types, sans scénarios) ; le catalogue utilisé est figé dans le résultat pour la confirmation. Le recuit simulé n° 2 (pistes « scénarios » et « teamfight », ancien catalogue) et son test au hasard, lancé par le bouton « 4 · Recuit », qui enchaîne tout seul le recuit (A et B), la confirmation sur C s'il y a au moins 5 000 parties C (`apres_recuit.py`), puis un nouveau gel. Le recuit teamfight du 24/10/2026 n'a **pas été confirmé sur C**. |
| `analyse/export/` | `exporter.py` : rassemble les modèles pour l'assistant et **ne garde que ce qui a passé sa vérification** (C pour les recuits, B pour tout ce qui vient de nos parties : `verification_B*.json`), avec les types, les sorts et les identifiants Riot. |
| `analyse/tests/` | Tests (après `preparer.sh`). |

## Les trois types d'analyse

- **Recuits** (règles de compo, scénarios) : tas **A** (choix des réglages), **B** (jugement), **C** (confirmation sur des parties jamais vues). On teste beaucoup de règles : sans C, le risque de garder un effet trouvé par hasard est trop grand.
- **Lolalytics** (« plus » et « moins » de victoire du patch) : pas de tas, chiffres de Lolalytics.
- **Nos parties** (avantage d'or, ganks, envahir, early/late, mix de dégâts, duels, classification des champions) : **toutes les parties**, tas **A** (apprendre) et **B** (vérifier), sans C (`commun.drafts_ab`). Une seule question par analyse, ou beaucoup de petites questions corrigées pour leur nombre (Benjamini-Hochberg) : B suffit. La vérification est refaite à chaque génération : `confirmation/confirmation_C.py --sur B` (Lolalytics, lanes, ganks, envahir) et `confirmation/confirmer_duree_degats.py --sur B` (early/late, mix), qui écrivent `verification_B*.json`, lus par l'export avant les anciennes confirmations sur C.

## Le découpage A, B, C

- **Nos parties** : toutes les parties Émeraude-Diamant (archive et `donnees/parties.csv`) en **A** (3/4) et **B** (1/4), par empreinte du numéro de partie (`commun.drafts_ab`, graine de `base/decoupage.json`). Une nouvelle collecte entre directement en A et B.
- **Recuit** : **A** et **B** jusqu'au **gel**, partagés de la même façon (une partie a le même tas dans les deux découpages), et **C** après le gel (`commun.drafts`).
- **C** (confirmer) : les parties collectées après le gel, jamais lues avant une confirmation. Une fois une confirmation faite, C est « consommé » : le bouton 4 pose lui-même un nouveau gel (même graine, chaque partie garde son tas), les parties suivantes forment le nouveau C.
- Historique : gel n° 2 le 23/10/2026 (C lu le 24/10/2026 pour les confirmations ci-dessous), gel n° 3 le 24/10/2026 au soir (42 101 parties), gel n° 4 le 27/10/2026 à 10 h 09 pour le recuit n° 3 (45 503 lignes de `parties.csv` : toutes les parties déjà collectées en A et B, environ 44 800 et 14 700 avec l'archive ; C = les collectes suivantes).
- Sans nouvelle collecte, on peut confirmer sur un C pris dans le temps (les parties les plus récentes), à condition de fixer les règles et les tests avant de lancer le calcul : c'est ce qui a été fait pour les duels (`confirmation/decoupage_duels.json`).

## Ce qui est vérifié

Vérifié sur B le 26/10/2026 (13 900 parties de B, appris sur A ; détails dans `confirmation/resultats/verification_B*.md`). Refait à chaque génération.

| Résultat | Verdict | Dans l'assistant |
|---|---|---|
| Force des champions du patch, contre direct, autres contres (Lolalytics) : coefficients 3,6 / 4,8 / 3,0 pour 4 attendus | confirmé | oui |
| Synergie avec les alliés (Lolalytics, 27/10/2026) : coefficient 2,1 ± 0,3 pour 4 attendus, donc comptée à 52 % dans l'assistant | confirmé | oui |
| Chance de victoire à la draft (force, contres, synergie ; apprise sur A, 27/10/2026) : sur 18 086 parties de B, chaque tranche annoncée est juste à 1 point près (annoncé 57 %, gagné 56 %) ; bon gagnant 56 % du temps | confirmé | oui |
| Or à 15 min par lane : une lane annoncée devant à 60 % ou plus l'est 63 à 66 % du temps | confirmé | oui |
| Ganks réussis avant 15 min : bien calibrés (annoncé 65 %, réel 65 %…) | confirmé | oui |
| Envahir | retiré le 27/10/2026 (choix du propriétaire : pas assez fiable) ; `lanes/envahir.py` reste pour la trace, il n'est plus calculé | non |
| Early/late : la compo la plus late gagne 37 % avant 20 min et 61 % entre 35 et 40 min | confirmé | oui |
| Mix de dégâts : moins de 20 % ou plus de 70 % de dégâts magiques, −4 à −5 points | à surveiller (confirmé sur C le 24/10, pas assez d'équipes sur B) | non |
| Duels (1 contre 1), chacun avec l'or et le niveau habituels de son poste (515 000 duels) : modèle d'ensemble et évolution avec la minute | vérifié (gain 14 et 7 millièmes) | oui |
| Force en duel de chaque champion | vérifiée pour 126 champions sur 173 (accord A/B 0,94) ; les autres comptent comme un champion moyen de leur poste | oui |
| Types des champions (`types/classer.py`) | choix du propriétaire ; les notes des parties retrouvent ses choix sans les voir (justesse par type dans `types/resultats/types.md`) et donnent la même décision sur A et sur B pour la plupart des champions | oui |
| Recuit teamfight (13 effets de compo, sur C) | non confirmé (28 tirages au hasard sur 40 font aussi bien) | non |

Les anciennes confirmations sur C (24/10/2026) restent dans `confirmation/resultats/confirmation_C*.md` pour la trace.

Détails : `analyse/confirmation/resultats/`.

## Règles propres à cette branche

- Ne jamais committer `collecte/`, `donnees/`, `archives/` ni `lolalytics/` ici (ils viennent de `main` et `scraping`).
- Un résultat n'entre dans l'assistant qu'après la vérification de son type d'analyse (C pour un recuit, B pour une analyse de nos parties, refaite à chaque génération) ; l'export le vérifie lui-même.
- Les duels avant le 26/10/2026 comparaient l'or brut : un support, toujours moins riche, passait pour fort « à or égal » quand il gagnait malgré ce retard normal. Corrigé en comparant l'avance de chacun sur la normale de son poste.
- Toujours apprendre et vérifier sur les mêmes rangs (Émeraude-Diamant).
