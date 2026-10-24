# Panda : collecte, analyses et assistant de draft

Assistant de draft League of Legends pour un jungler. Pool : Fiddlesticks, Ivern, Dr. Mundo, Kayn bleu, Kayn rouge.
On collecte des parties classées solo EUW avec l'API Riot, puis on cherche des scénarios de compo où un jungler du pool gagne nettement plus que d'habitude.

Tout se fait en français : code, commentaires, messages de commit, réponses.

## Branches

- `main` reçoit les collectes : les commits de données et le rapport de fin de collecte y arrivent automatiquement.
- Le travail d'analyse peut se faire sur d'autres branches (par exemple `analyse-iterative`). Une branche de travail ne touche jamais aux fichiers de données ; elle est fusionnée dans `main` quand le propriétaire le décide.

| Dossier ou fichier | Rôle |
|---|---|
| `Catalogue.csv`, `Catalogue_champions_LoL.xlsx` | Le catalogue des champions. |
| `analyse/` | Collecte des parties (`collecte.py`, `collecte.ini`, `enregistrer.sh`), analyses (`rapport.py`, `profils.py`, `compos.py`, `regle.py`), lecture des données (`lecture.py`), tests. |
| `analyse/iteratif/` | **Le cœur de l'analyse** : la boucle en 4 blocs (catalogue → compos → biais → recuit simulé) qui cherche des biais de draft. Voir `analyse/iteratif/README.md`. |
| `analyse/donnees/` | Les données collectées (voir plus bas). |
| `analyse/resultats/` | Les résultats, régénérés à la fin de chaque collecte. |
| `archives/` | Copies figées d'anciennes données. |
| `assistant/`, `Assistant_draft.html` | La page d'assistant de draft, générée par `assistant/construire.py`. |
| `.github/workflows/lancer-collecte.yml` | **Lancer une collecte** : bouton « Run workflow », ou modification de `analyse/collecte.ini`. |
| `.github/workflows/assistant.yml` | **Page d'assistant** : régénère `Assistant_draft.html` quand `Catalogue.csv` ou `assistant/` change. |
| `.github/workflows/recuit.yml` | **Lancer un recuit simulé** : bouton « Run workflow » (code de la branche `analyse-iterative`, données de `main`). |
| `.github/workflows/confirmer.yml` | **Confirmer les résultats du recuit** : mesure les meilleurs réglages sur les parties jamais vues. |
| `.github/workflows/champions-patch.yml` | **Identifier les champions forts du patch** : collecte légère (sans timeline) du patch en cours en Platine-Diamant, puis classement des champions forts et faibles. Code et données sur la branche `champions-patch` (voir `analyse/patch/README.md` sur cette branche). Même file que les collectes. |

### Les analyses, dans l'ordre où elles ont été faites

| Fichier | Rôle |
|---|---|
| `analyse/lecture.py`, `analyse/tables.py` | Lire les données (toujours par là) ; `tables.py` les met en tables pandas. |
| `analyse/echantillon.py`, `analyse/echantillon_fige.json` | L'échantillon figé : les 15 249 premières parties complètes, base de toutes les recherches. |
| `analyse/controle.py` | Contrôle des données (rapport). |
| `analyse/profils.py`, `analyse/compos.py`, `analyse/regle.py` | Premières analyses, avec les styles du catalogue (rapport). |
| `analyse/categories.py`, `analyse/biais.py`, `analyse/hypotheses.json` | Profils mesurés par champion et poste, et 13 hypothèses fixées à l'avance (rapport). Résumé : `analyse/livrable_biais.md`. |
| `analyse/classification.py` | Classification des champions tous postes confondus, 7 groupes (rapport). Résumé : `analyse/proposition_categories.md`. |
| `analyse/iteratif/` | La recherche itérative de biais de draft (workflows recuit et confirmation). |
| `analyse/explorations/` | Explorations lancées à la main (confirmation sur l'archive, pistes du pool). |

Pendant une collecte, des commits de données arrivent sur `main` toutes les 10 minutes : toujours faire `git pull --rebase` avant de pousser sur `main`.

## Comment tourne une collecte

- Lancement : bouton « Run workflow » de **Lancer une collecte**, ou modification de `analyse/collecte.ini` sur `main`.
- `analyse/collecte.py` tire des joueurs dans les paliers de `collecte.ini` (dans l'ordre, avec passage au palier suivant quand le premier ne donne plus assez de parties neuves), télécharge leurs parties récentes (détail du match et timeline) et, pour chaque partie retenue, écrit d'abord les fichiers de détails puis, en dernier, une ligne dans `analyse/donnees/parties.csv`.
- Toutes les 10 minutes, `analyse/enregistrer.sh` committe et pousse **les données seulement** (`git pull --rebase` puis `git push`).
- À la fin, `analyse/enregistrer.sh --rapport` récupère la branche, lance `analyse/rapport.py` (qui appelle `profils.py` et `compos.py`), committe `analyse/resultats/` et pousse.
- Une collecte dure 5 h 15 (`minutes = 315`) ; l'étape « Collecter » est coupée à 325 minutes et le job à 6 h (360 minutes, la limite de GitHub). Rien ne doit dépasser 6 h.
- `mode` dans `collecte.ini` : `nouvelles` (par défaut) cherche de nouvelles parties ; `rattrapage` ne cherche rien de neuf et complète les détails des parties de `parties.csv` qui n'en ont pas encore, **sans jamais écrire dans `parties.csv`**. Un match introuvable (404) est noté dans `analyse/donnees/rattrapage_echecs.csv` et n'est plus retenté.
- **Clé Riot** : uniquement dans le secret `RIOT_API_KEY` du dépôt (**Settings → Secrets and variables → Actions → Repository secrets**), transmis par le workflow. Une clé de développement expire au bout de 24 heures : chaque jour, la régénérer sur [developer.riotgames.com](https://developer.riotgames.com) puis mettre à jour ce secret (bouton crayon, coller, « Update secret »). Mettre à jour le secret ne lance pas de collecte. En local : `RIOT_API_KEY=… python3 analyse/collecte.py`. Une clé `cle_api` écrite dans `collecte.ini` est ignorée, avec un avertissement.
- Débit : la clé de développement permet environ 3 000 appels par heure. Avec la timeline, une partie coûte deux appels : compter environ 1 350 parties par heure (environ 7 000 par collecte), contre 2 550 avant.

## Ce que Claude Code peut faire

- Ajouter ou modifier des scripts d'analyse dans `analyse/` (`rapport.py`, `profils.py`, `compos.py`, nouveaux fichiers) et leurs tests dans `analyse/tests/`.
- Ajouter des fichiers de sortie dans `analyse/resultats/`, à condition qu'ils soient produits par `rapport.py` (directement ou par un script qu'il appelle).
- Lire toutes les données, les résultats et les archives, lancer les analyses en local, y compris des calculs longs et des bibliothèques en plus (scikit-learn, réseaux de neurones…) pour les analyses locales.
- Créer des branches de travail et y pousser.
- Créer et faire évoluer des catalogues de travail (par exemple dans `analyse/catalogues/`), y compris reclasser des champions. `Catalogue.csv` reste la version qui alimente la page d'assistant : on y reporte une version de travail quand le propriétaire la valide.
- Faire évoluer la règle de compo, en gardant `analyse/regle.py` et `assistant/regle.js` identiques.
- Committer et pousser pendant une collecte : c'est prévu. Les changements de `collecte.py` et `enregistrer.sh` ne serviront qu'à partir de la collecte suivante ; ceux de `rapport.py` et des scripts qu'il appelle serviront dès la fin de la collecte en cours.

## Ce que Claude Code ne doit pas faire

Le seul but de ces règles : ne pas casser ni interrompre les collectes, et ne pas abîmer les données.

- **Données** : ne jamais modifier, trier, dédoublonner, réécrire ni supprimer `analyse/donnees/parties.csv`, `analyse/donnees/ecartees.csv` ni les fichiers de détails. Seule la collecte y écrit, en ajout. Seule exception : le propriétaire peut demander de repartir de zéro ; on archive alors d'abord dans `archives/`, puis on vide le fichier en gardant sa ligne d'en-tête (fait le 22/10/2026).
- **Résultats** : ne pas éditer `analyse/resultats/` à la main. Ces fichiers sont régénérés et écrasés à la fin de chaque collecte : changer le script qui les produit.
- **`analyse/collecte.ini`** : le pousser lance une collecte. Ne le modifier que pour lancer une collecte demandée. Pour tout autre changement de ce fichier, mettre `[skip ci]` dans le message du dernier commit poussé.
- **Clé Riot** : ne jamais l'écrire dans un fichier du dépôt, un commit, une issue ou un journal : le dépôt est public. Elle ne vit que dans le secret `RIOT_API_KEY`. Un test (`AucuneCleDansLeDepotTest`) échoue si une clé apparaît dans le code, la configuration ou la documentation. Si une clé a été poussée par erreur, la régénérer tout de suite sur le portail Riot : l'ancienne cesse de fonctionner.
- **Collectes** : ne jamais annuler ni interrompre une collecte en cours ; ne pas en lancer sans demande ; rien ne doit dépasser 6 h dans le workflow. Vérifier avec `gh run list` qu'aucune collecte ne tourne avant de toucher aux workflows.
- **Durée du rapport** : `rapport.py` tourne dans le temps restant du job (environ 35 minutes, moins les sauvegardes). Une analyse lente doit pouvoir être sautée.
- **Dépendances** : `collecte.py`, `enregistrer.sh` et `lecture.py` n'utilisent que la bibliothèque standard Python et bash. Ce que lance `rapport.py` peut utiliser `statsmodels`, `pandas` et `scipy` (installés par le workflow), mais doit continuer sans eux et ne jamais faire échouer le rapport.
- **Git** : pas de `push --force` ni de réécriture d'historique sur `main` (les commits de collecte en dépendent). Seule exception, à la demande du propriétaire : le 23/10/2026, l'historique de `main` a été réécrit pour remplacer les clés Riot par `RGAPI-[retirée]` ; les identifiants de commit d'avant cette date ont changé ; pas de changement de visibilité du dépôt (seul le propriétaire la change ; le dépôt est prévu pour être public).
- **Workflows** : vérifier que le YAML est valide avant de pousser (par exemple `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/lancer-collecte.yml'))"`).

## Format des données

`analyse/donnees/parties.csv`, séparateur `;`, une ligne par partie :

```
match;patch;palier;gagnant;b_top;b_jgl;b_mid;b_adc;b_sup;r_top;r_jgl;r_mid;r_adc;r_sup
```

- `match` : identifiant Riot sans le préfixe `EUW1_`. C'est la clé commune à tous les fichiers.
- `palier` : initiale et division, par exemple `P2`, `E1`, `D3`.
- `gagnant` : `b` (bleu) ou `r` (rouge).
- Les noms de champions sont ceux du catalogue. Kayn est séparé en `Kayn rouge` et `Kayn bleu` ; une partie où sa forme est inconnue est écartée.

`analyse/donnees/ecartees.csv` : `match;raison` (remake, postes, kayn_sans_forme, etc.). Une partie écartée n'est jamais retéléchargée, et n'a pas de détails.

`archives/` : copies figées des données et des résultats, une par dossier daté. On peut les lire (par exemple pour confirmer un résultat sur des parties indépendantes) ; ne jamais les modifier.

Le 22/10/2026, `parties.csv` a été vidé (en-tête gardé) pour repartir avec des données neuves, collectées avec tous leurs détails. Les 21 484 parties d'avant, sans détails, sont dans `archives/2026-10-22_avant_details/`. `ecartees.csv` a été gardé : les parties déjà écartées ne sont pas retéléchargées. Les parties archivées peuvent, elles, être recollectées, cette fois avec leurs détails.

### Détails des parties

Quatre dossiers dans `analyse/donnees/`, un par type de fichier. Chaque dossier est découpé en tranches de 2 000 parties (`joueurs/joueurs_0001.csv`, `joueurs_0002.csv`…) pour rester loin de la limite de 100 Mo de GitHub, puisque chaque sauvegarde recommite la tranche en cours. Séparateur `;`, en-têtes fixes (listés dans `analyse/collecte.py`), case vide quand une valeur est absente. Mêmes noms de champions que `parties.csv` (Kayn rouge / Kayn bleu) ; postes `top`, `jgl`, `mid`, `adc`, `sup` ; équipes `b` et `r`.

| Dossier | Une ligne par | Contenu |
|---|---|---|
| `details_parties/` | partie | durée, fin par abandon, 5 bans par équipe, et pour chaque objectif : `<cote>_<objectif>_premier` (0/1) et `<cote>_<objectif>_nb` |
| `joueurs/` | joueur (10 par partie, ordre de `parties.csv`) | KDA, or, cs, dégâts par type, soins, boucliers, contrôle, vision, sorts, rune principale, objets, et une sélection de `challenges` |
| `timeline_joueurs/` | joueur | à 5, 10, 15, 20, 25 et 30 minutes : or, xp, cs, niveau, dégâts aux champions, position |
| `evenements/` | événement | kills de champions, monstres épiques, bâtiments et plaques |

Ces fichiers suivent les mêmes règles que `parties.csv` : écrits en ajout par la collecte seulement, jamais modifiés à la main. Taille mesurée sur 12 vrais matchs : environ 13 Ko par partie (événements 9 Ko, joueurs 2,3 Ko, timeline 1,7 Ko, détails 0,2 Ko), soit environ 18 Mo pour une tranche d'événements.

### Lire les données

Toujours passer par `analyse/lecture.py` :

```python
from lecture import lire_details, matchs_avec_details
for joueur in lire_details("joueurs"):   # dictionnaires, valeurs en texte
    ...
```

- Pour chaque partie, la collecte écrit `joueurs`, puis `timeline_joueurs` et `evenements`, puis `details_parties`, et `parties.csv` en dernier. Une partie n'est donc complète que si elle figure dans `parties.csv` **et** dans `details_parties`. Une collecte coupée en pleine écriture peut laisser des lignes d'une partie inachevée : `lecture.py` les ignore.
- Une partie réécrite après une interruption peut apparaître deux fois : `lecture.py` ne garde que sa dernière écriture. Ne pas lire les tranches à la main sans refaire ce filtrage.
- Toutes les valeurs sont lues comme du texte ; une case vide veut dire « absente », pas zéro.
- Une partie peut avoir des détails sans timeline (timeline introuvable ou Riot indisponible) : elle n'a alors aucune ligne dans `timeline_joueurs` ni dans `evenements`. `matchs_presents("timeline_joueurs")` donne les parties qui en ont une. `volume.csv` compte `avec_details` et `avec_timeline`.
- Jointures : `match` partout ; `participant` (1 à 10) relie `joueurs`, `timeline_joueurs` et les colonnes `participant`, `victime` et `assistants` de `evenements`. Les participants 1 à 5 sont en général bleus, mais se fier à la colonne `equipe` de `joueurs`.

## API Riot : ce qui est appelé et comment les champs sont traduits

### Appels

| Appel | Serveur | Usage |
|---|---|---|
| `/lol/league/v4/entries/RANKED_SOLO_5x5/{palier}/{division}` | `euw1` | tirer des joueurs |
| `/lol/match/v5/matches/by-puuid/{puuid}/ids` | `europe` | leurs parties classées solo (file 420) des `jours` derniers jours |
| `/lol/match/v5/matches/{id}` | `europe` | détail du match : `parties.csv`, `details_parties`, `joueurs` |
| `/lol/match/v5/matches/{id}/timeline` | `europe` | ajouté le 22/10/2026 : `timeline_joueurs`, `evenements` |
| Data Dragon `champion.json` (dernière version, `en_US`) | ddragon | noms des champions à partir de leur identifiant |

- Un limiteur par serveur respecte l'en-tête `X-App-Rate-Limit`. 429 : attente de `Retry-After` ; 5xx, réseau ou réponse coupée en plein envoi (JSON tronqué) : jusqu'à 6 essais avec attente croissante, puis l'appel est sauté avec un avertissement, sans arrêter la collecte ni écarter la partie (elle pourra être reprise) ; 401/403 : clé refusée, arrêt de la collecte ; 404 : match introuvable (écarté, ou noté dans `rattrapage_echecs.csv` en rattrapage).
- Si la timeline échoue après les essais (ou renvoie 404), la partie est gardée sans timeline, avec un avertissement dans le journal.

### Traductions et pièges

- **Équipes** : `teamId` 100 = `b`, 200 = `r`. **Postes** : `teamPosition` (pas `individualPosition`), `TOP`/`JUNGLE`/`MIDDLE`/`BOTTOM`/`UTILITY` = `top`/`jgl`/`mid`/`adc`/`sup`.
- **Champions** : noms Data Dragon, identiques au catalogue ; un identifiant inconnu donne `?<id>`. Kayn : `championTransform` 1 = `Kayn rouge`, 2 = `Kayn bleu`. Un **ban** de Kayn reste `Kayn` (pas de forme en draft).
- **`details_parties`** :
  - `duree_s` = `info.gameDuration`, en secondes.
  - `fin_surrender` = 1 si un joueur a `gameEndedInSurrender`. `fin_surrender_precoce` (`gameEndedInEarlySurrender`) vaut toujours 0 en pratique : ces parties sont écartées comme remakes.
  - Bans triés par `pickTurn` ; `championId` -1 (pas de ban) donne une case vide.
  - Objectifs : clés de `info.teams[].objectives` vérifiées sur de vrais matchs d'octobre 2026 : `baron`, `champion` (kills de champions de l'équipe), `dragon`, `horde` (larves du Néant), `inhibitor`, `riftHerald`, `tower`, `voidGator`. **Il n'y a pas de clé `atakhan`** ; `voidGator` est l'objectif que Riot renvoie à la place, gardé tel quel. Un objectif absent du match donne deux cases vides.
- **`joueurs`** :
  - `niveau` = `champLevel`, `or_gagne` = `goldEarned`, `cs` = `totalMinionsKilled` + `neutralMinionsKilled`.
  - Dégâts : `physicalDamageDealtToChampions`, `magicDamageDealtToChampions`, `trueDamageDealtToChampions`, `totalDamageTaken` (subis), `damageSelfMitigated` (atténués).
  - Soins et boucliers : `totalHeal`, `totalHealsOnTeammates`, `totalDamageShieldedOnTeammates`.
  - Contrôle : `temps_cc_inflige` = `timeCCingOthers` (temps de contrôle pondéré, en secondes), `cc_total` = `totalTimeCCDealt`.
  - `degats_batiments` = `damageDealtToBuildings`, `degats_objectifs` = `damageDealtToObjectives`, `score_vision` = `visionScore`.
  - `sort1`, `sort2` : identifiants des sorts d'invocateur (4 Saut éclair, 11 Châtiment, 14 Embrasement, 12 Téléportation…).
  - `rune_principale` : identifiant de la rune clé (`perks.styles[primaryStyle].selections[0].perk`).
  - `item0`…`item6` : identifiants d'objets en fin de partie, 0 = emplacement vide, `item6` = la balise.
  - Colonnes `challenges` : noms Riot inchangés (camelCase). Les pourcentages sont des fractions (`killParticipation` 0,25 = 25 %). Certaines n'existent que pour un poste : `killsOnLanersEarlyJungleAsJungler` est vide hors jungle.
  - Les nombres à virgule sont arrondis à 4 décimales ; un flottant entier (66.0) est écrit `66`.
- **`timeline_joueurs`** :
  - Riot envoie un état toutes les 60 secondes, avec un léger décalage (300052 ms pour 5 min). Pour la minute M, on prend le premier état entre M et M+1 minutes ; si la partie s'est finie avant, les 7 cases de M sont vides.
  - Valeurs **cumulées** depuis le début : `or_M` = `totalGold` (or total gagné, pas l'or en poche), `xp_M`, `degats_champions_M` = `damageStats.totalDamageDoneToChampions`. `cs_M` = `minionsKilled` + `jungleMinionsKilled`.
  - `x_M`, `y_M` : position sur la carte à cet instant (unités Riot, de 0 à environ 15 000 ; base bleue en bas à gauche).
- **`evenements`** : seulement `CHAMPION_KILL`, `ELITE_MONSTER_KILL`, `BUILDING_KILL`, `TURRET_PLATE_DESTROYED` (pas `CHAMPION_SPECIAL_KILL` : premier sang, multikills…).
  - `t_ms` : millisecondes depuis le début de la partie.
  - `participant` = `killerId` : le tueur ou l'auteur, **0 pour un sbire, une tour ou un monstre** (exécution, plaque prise par les sbires).
  - `victime` : seulement pour `CHAMPION_KILL`. `assistants` : participants séparés par `|`, vide s'il n'y en a pas.
  - **`equipe` est toujours l'équipe de l'auteur, celle qui profite de l'événement.**
    - `CHAMPION_KILL` : l'équipe du tueur, ou l'équipe opposée à la victime si `participant` vaut 0.
    - `ELITE_MONSTER_KILL` : `killerTeamId`.
    - `BUILDING_KILL` et `TURRET_PLATE_DESTROYED` : **attention, Riot donne dans `teamId` l'équipe propriétaire du bâtiment, celle qui le perd**. Ici, c'est inversé pour donner l'équipe qui le détruit. L'équipe qui perd le bâtiment est donc l'autre.
  - `detail` :
    - monstre : `monsterType` ou `monsterType/monsterSubType`, par exemple `DRAGON/EARTH_DRAGON`, `HORDE`, `RIFTHERALD`, `BARON_NASHOR` ;
    - bâtiment : `buildingType/towerType/laneType` (par exemple `TOWER_BUILDING/OUTER_TURRET/BOT_LANE`, ou `INHIBITOR_BUILDING/MID_LANE` sans type de tour) ;
    - plaque : `laneType` ;
    - kill : vide.
  - `degats_recus_victime` (kills seulement) : somme des dégâts physiques, magiques et bruts de `victimDamageReceived`, toutes sources confondues (champions, tours, sbires, monstres). Riot n'y met que les dégâts reçus juste avant la mort, pas sur toute la vie du champion.
  - `nb_sources` (kills seulement) : nombre de champions **ennemis** distincts dans `victimDamageReceived` ; les tours, sbires et monstres ne comptent pas.

## Tests

```
python3 -m unittest discover -s analyse/tests
node --test assistant/tests/regle.test.js
```

Ils doivent passer avant chaque push.
