# Panda : assistant de draft League of Legends

Un assistant de draft pour un jungler (pool : Fiddlesticks, Ivern, Dr. Mundo, Kayn, Viego, Maokai, Skarner), utilisable
aussi par d'autres joueurs et à tous les postes grâce aux profils. On collecte des parties classées solo EUW avec l'API
Riot, on récupère les stats du patch sur Lolalytics, on cherche ce qui fait gagner, et on ne garde dans l'assistant que
ce qui est **confirmé sur des parties jamais vues**.

Tout se fait en français : code, commentaires, messages de commit, réponses.
Résultats en pourcentages de victoire simples (« X gagne 45 % dans tel cas, contre 50 % sinon »), avec un verdict clair : confirmé, à surveiller ou rien. L'assistant n'affiche que ce qui a passé la vérification prévue pour son type d'analyse (voir « Les trois types d'analyse »).

## Les trois types d'analyse

Chaque résultat appartient à un de ces trois types, qui fixe la façon de le vérifier avant de l'afficher dans l'assistant.

| Type | Ce qu'on cherche | Tas | Vérification | Où |
|---|---|---|---|---|
| **Recuits** | Des règles de compo et des scénarios (« telle compo gagne plus contre telle autre ») : on essaie beaucoup de règles, le risque de trouver un effet par hasard est grand. | **A, B, C** | Réglages choisis sur A, jugés sur B, puis **confirmés sur C** (parties collectées après le gel, jamais lues). Un C lu est consommé : nouveau gel. | bouton « 4 · Recuit » (recuit sur A et B, puis confirmation sur C toute seule) |
| **Lolalytics** | Les « plus » et « moins » de victoire du patch : force des champions, contres, matchups. | — | Chiffres de Lolalytics (Platine et plus, tous serveurs), sur des centaines de milliers de parties. | bouton « 2 · Lolalytics » |
| **Nos parties** | Avantage d'or à 15 min par lane, ganks, envahir, early/late, mix de dégâts, duels, et la classification des champions en types. | **A, B** | **Toutes les parties** (archive comprise), appris sur A (3/4), **vérifié sur B** (1/4, partage stable par empreinte du numéro de partie), avec correction pour le nombre de tests ; refait à chaque génération, donc chaque collecte en profite tout de suite. | recalculés et vérifiés par « 5 · Générer l'assistant Draft » |

Le gel et le tas C ne servent plus qu'au recuit. Une partie a le même tas A ou B dans les deux découpages (même graine).

## Les quatre branches

Chaque branche ne contient que ce qui la concerne. Les boutons des workflows sont tous sur `main` (GitHub l'exige).

| Branche | Contenu | Bouton (onglet Actions) |
|---|---|---|
| `main` | **Collecte** : `collecte/` (code, réglages, bilan), `donnees/` (les parties), `archives/`, les workflows. | **1 · Collecte** |
| `scraping` | **Lolalytics** : `lolalytics/` (le scraper et un dossier par patch). | **2 · Lolalytics** |
| `analyse` | **Analyses** : `analyse/` (catalogue unifié et sorts, types des champions, contres, lanes, duels, recuits, confirmations, export pour l'assistant). Lit les données de `main`, n'y écrit jamais. | **3 · Data Dragon**, **4 · Recuit** (les autres analyses sont recalculées par le bouton 5) |
| `assistant` | **Assistant** : `assistant/` (générateur de la page, lien client), `Assistant Draft - DL - <date>.html` et `Assistant Draft - Lien client.exe`. | **5 · Générer l'assistant Draft** |

Chaque branche a son propre README qui détaille son contenu. Les anciennes branches `analyse-iterative` et `champions-patch` ne servent plus : le propriétaire les supprime depuis l'onglet « Branches » (Claude n'en a pas le droit).

## Les boutons, dans l'ordre

Onglet Actions de GitHub. Le numéro est l'ordre à suivre pour générer un assistant **en partant de zéro** ; chaque bouton rappelle en tête de son résumé à quoi il sert.

| Bouton | À quoi il sert | Quand |
|---|---|---|
| **1 · Collecte** | Télécharger des parties classées Émeraude-Diamant EUW (détails et timeline) dans `donnees/` : la matière de toutes nos analyses. 5 h 15, environ 7 000 parties. Mettre à jour le secret `RIOT_API_KEY` avant (la clé expire au bout de 24 h). | En premier ; puis dès qu'on veut plus de parties. |
| **2 · Lolalytics** | Force de chaque champion à chaque poste, contres et matchups du patch (branche `scraping`). Environ 20 min. | À chaque nouveau patch. |
| **3 · Data Dragon** | Nouveaux champions au catalogue, sorts de chacun rangés en contrôle, déplacement ou protection (branche `analyse`). Moins d'une minute. | À chaque nouveau patch. |
| **4 · Recuit** (facultatif) | Chercher des règles de compo (piste `styles` : les 10 scénarios sur les 11 types ; `styles_libre` : sans scénarios) sur A et B, puis, s'il y a au moins 5 000 parties C, les confirmer sur C tout seul ; C est alors consommé et un nouveau gel est posé. Seules les règles confirmées entrent dans l'assistant. | Après une ou deux collectes (pour remplir C). |
| **5 · Générer l'assistant Draft** | Recalculer nos analyses sur les parties (or à 15 min, ganks, envahir, duels, dégâts, types des champions), puis produire la page et le lien client Windows. | En dernier, après chaque passage par 1, 2, 3 ou 4. |

**Récupérer la page** : sur GitHub, branche `assistant`, cliquer sur `Assistant Draft - DL - <date>.html`, puis sur « Download raw file ». Un « Enregistrer sous » de la page GitHub donne une page vide (le fichier fait 2 Mo, GitHub ne l'affiche pas). Même chose pour `Assistant Draft - Lien client.exe`, à mettre dans le même dossier et à lancer avant de jouer : la page voit alors la sélection des champions du client. La page avertit en haut à droite quand le jeu a changé de patch.

## Sur `main`

| Dossier ou fichier | Rôle |
|---|---|
| `collecte/collecte.py`, `collecte/collecte.ini` | La collecte et ses réglages. **Pousser `collecte.ini` lance une collecte.** |
| `collecte/enregistrer.sh` | Committe et pousse les données pendant la collecte ; à la fin, écrit `collecte/bilan.md`. |
| `collecte/bilan.py`, `collecte/bilan.md` | Le bilan de fin de collecte : parties par patch et par palier, avec ou sans détails. |
| `collecte/lecture.py` | Lire les données (toujours par là, voir plus bas). Les analyses l'utilisent aussi. |
| `collecte/tests/` | Tests de la collecte et de la lecture. |
| `donnees/` | Les données collectées (voir « Format des données »). |
| `archives/` | Copies figées d'anciennes données. |
| `.github/workflows/` | `lancer-collecte.yml` (1), `lolalytics.yml` (2), `datadragon.yml` (3), `recuit.yml` (4), `assistant.yml` (5). |

Pendant une collecte, des commits de données arrivent sur `main` toutes les 10 minutes : toujours faire `git pull --rebase` avant de pousser sur `main`.

## Comment tourne une collecte

- Lancement : bouton « Run workflow » de **1 · Collecte**, ou modification de `collecte/collecte.ini` sur `main`.
- `collecte/collecte.py` tire des joueurs dans les paliers de `collecte.ini` (dans l'ordre, avec passage au palier suivant quand le premier ne donne plus assez de parties neuves), télécharge leurs parties récentes (détail du match et timeline) et, pour chaque partie retenue, écrit d'abord les fichiers de détails puis, en dernier, une ligne dans `donnees/parties.csv`.
- Toutes les 10 minutes, `collecte/enregistrer.sh` committe et pousse **les données seulement** (`git pull --rebase` puis `git push`).
- À la fin, `collecte/enregistrer.sh --rapport` récupère la branche, lance `collecte/bilan.py`, committe `collecte/bilan.md` et pousse.
- Une collecte dure 5 h 15 (`minutes = 315`) ; l'étape « Collecter » est coupée à 325 minutes et le job à 6 h (360 minutes, la limite de GitHub). Rien ne doit dépasser 6 h.
- `mode` dans `collecte.ini` : `nouvelles` (par défaut) cherche de nouvelles parties ; `rattrapage` ne cherche rien de neuf et complète les détails des parties de `parties.csv` qui n'en ont pas encore, **sans jamais écrire dans `parties.csv`**. Un match introuvable (404) est noté dans `donnees/rattrapage_echecs.csv` et n'est plus retenté.
- **Clé Riot** : uniquement dans le secret `RIOT_API_KEY` du dépôt (**Settings → Secrets and variables → Actions → Repository secrets**), transmis par le workflow. Une clé de développement expire au bout de 24 heures : chaque jour, la régénérer sur [developer.riotgames.com](https://developer.riotgames.com) puis mettre à jour ce secret (bouton crayon, coller, « Update secret »). Mettre à jour le secret ne lance pas de collecte. En local : `RIOT_API_KEY=… python3 collecte/collecte.py`. Une clé `cle_api` écrite dans `collecte.ini` est ignorée, avec un avertissement.
- Débit : la clé de développement permet environ 3 000 appels par heure. Avec la timeline, une partie coûte deux appels : compter environ 1 350 parties par heure (environ 7 000 par collecte).

## Ce que Claude Code peut faire

- Faire évoluer la collecte (`collecte/`) et ses tests, les analyses (branche `analyse`), le scraper (branche `scraping`) et l'assistant (branche `assistant`), chacun sur sa branche.
- Lire toutes les données, les résultats et les archives, lancer les analyses en local, y compris des calculs longs et des bibliothèques en plus (scikit-learn…).
- Faire évoluer le catalogue unifié (`analyse/catalogues/catalogue_unifie.csv`, branche `analyse`) quand le propriétaire valide un reclassement.
- Committer et pousser pendant une collecte, y compris modifier les workflows : c'est prévu, sauf ce qui déplace ou renomme `donnees/` ou les fichiers de la collecte (attendre la fin de la collecte). Les changements de `collecte.py` et `enregistrer.sh` ne serviront qu'à partir de la collecte suivante.
- Lancer un workflow (`gh workflow run`) quand le propriétaire le demande ; sinon, c'est lui qui les lance.

## Ce que Claude Code ne doit pas faire

Le seul but de ces règles : ne pas casser ni interrompre les collectes, et ne pas abîmer les données.

- **Données** (`donnees/`, `archives/`) : on peut les **déplacer, renommer ou réorganiser**, à condition que leur contenu reste identique (vérifier après coup que chaque fichier est le même, octet par octet) et qu'aucune collecte ne tourne. On ne les **supprime jamais**, ni en entier ni en partie (fichier, lignes, dédoublonnage, remise à zéro), **sauf si le propriétaire le demande** ; dans ce cas, archiver d'abord dans `archives/`. Seule la collecte ajoute des lignes ; personne ne réécrit les lignes existantes.
- **Données sur les autres branches** : `analyse`, `scraping` et `assistant` ne contiennent jamais de copie des données ; les analyses les lisent depuis `main`.
- **`collecte/collecte.ini`** : le pousser lance une collecte. Ne le modifier que pour lancer une collecte demandée. Pour tout autre changement de ce fichier, mettre `[skip ci]` dans le message du dernier commit poussé.
- **Clé Riot** : ne jamais l'écrire dans un fichier du dépôt, un commit, une issue ou un journal : le dépôt est public. Elle ne vit que dans le secret `RIOT_API_KEY`. Un test (`AucuneCleDansLeDepotTest`) échoue si une clé apparaît dans le code, la configuration ou la documentation. Si une clé a été poussée par erreur, la régénérer tout de suite sur le portail Riot : l'ancienne cesse de fonctionner.
- **Collectes** : ne jamais annuler ni interrompre une collecte en cours ; ne pas en lancer sans demande ; rien ne doit dépasser 6 h dans le workflow. Avant de déplacer `donnees/` ou les fichiers de `collecte/`, vérifier avec `gh run list --status in_progress` qu'aucune collecte ne tourne.
- **Dépendances** : `collecte/` n'utilise que la bibliothèque standard Python et bash.
- **Git** : pas de `push --force` ni de réécriture d'historique sur `main` (les commits de collecte en dépendent), sauf demande explicite du propriétaire (fait une fois, le 23/10/2026, pour retirer des clés Riot). La visibilité du dépôt (public) ne change que par le propriétaire.
- **Workflows** : vérifier que le YAML est valide avant de pousser (par exemple `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/lancer-collecte.yml'))"`).

## Historique en bref

- Premières analyses (styles du catalogue d'origine, hypothèses, classification en 7 groupes), puis recherche itérative de biais de draft par recuit simulé : supprimées de `main` le 24/10/2026, retrouvables dans l'historique git.
- Recuit teamfight : prometteur sur B, **non confirmé sur C** (24/10/2026) ; ses effets ne sont pas dans l'assistant.
- Utilisés par l'assistant : force du patch et contres (Lolalytics) ; vérifiés sur B à chaque génération : or à 15 min par lane, ganks, envahir, early/late, mix de dégâts, duels (1 contre 1), types des champions. Détails sur la branche `analyse`.
- 26/10/2026 (après-midi) : les analyses de nos parties prennent toutes les parties en A et B (plus de C pour elles) et sont vérifiées sur B à chaque génération. Premier passage : envahir vérifié à 20 min pour les junglers Engage (tanks) (à 15 min, il ne tient plus), mix de dégâts « à surveiller » donc plus affiché ; le reste tient.
- 25/10/2026 : lien avec le client League (lecture de la sélection, pré-picks de son équipe compris).
- 26/10/2026 : assistant v1.5 (version du jeu et côté lus dans le client, tes 5 duels, dégâts AD / AP / Bruts, carte en jauges, tableau « Qui est qui », blocs « Atteindre leurs cibles » et « Protéger vos cibles »). Catalogue unifié refait : les 10 types (Carry, Enchanteur, Assassin, Plongeur, Attrapeur, Tank, Bloqueur, Dueliste, Splitpusher, Teamfighter) classés sur nos parties à partir des références du propriétaire, et mis à jour par Data Dragon ; l'ancienne classification (styles, groupes teamfight) est gardée à part pour les ganks, envahir et le recuit. Duels corrigés : or et niveau par rapport à la normale du poste. Les trois types d'analyse sont posés (ci-dessus) ; les boutons sont numérotés de 1 à 5 dans l'ordre où les lancer, le recuit et sa confirmation sur C ne font plus qu'un (bouton 4).

## Format des données

`donnees/parties.csv`, séparateur `;`, une ligne par partie :

```
match;patch;palier;gagnant;b_top;b_jgl;b_mid;b_adc;b_sup;r_top;r_jgl;r_mid;r_adc;r_sup
```

- `match` : identifiant Riot sans le préfixe `EUW1_`. C'est la clé commune à tous les fichiers.
- `palier` : initiale et division, par exemple `P2`, `E1`, `D3`.
- `gagnant` : `b` (bleu) ou `r` (rouge).
- Les noms de champions sont ceux du catalogue. Kayn est séparé en `Kayn rouge` et `Kayn bleu` ; une partie où sa forme est inconnue est écartée.

`donnees/ecartees.csv` : `match;raison` (remake, postes, kayn_sans_forme, etc.). Une partie écartée n'est jamais retéléchargée, et n'a pas de détails.

`archives/` : copies figées des données et des résultats, une par dossier daté. On peut les lire (par exemple pour confirmer un résultat sur des parties indépendantes) ; ne jamais les modifier.

Le 22/10/2026, `parties.csv` a été vidé (en-tête gardé) pour repartir avec des données neuves, collectées avec tous leurs détails. Les 21 484 parties d'avant, sans détails, sont dans `archives/2026-10-22_avant_details/`. `ecartees.csv` a été gardé : les parties déjà écartées ne sont pas retéléchargées. Les parties archivées peuvent, elles, être recollectées, cette fois avec leurs détails.

### Détails des parties

Quatre dossiers dans `donnees/`, un par type de fichier. Chaque dossier est découpé en tranches de 2 000 parties (`joueurs/joueurs_0001.csv`, `joueurs_0002.csv`…) pour rester loin de la limite de 100 Mo de GitHub, puisque chaque sauvegarde recommite la tranche en cours. Séparateur `;`, en-têtes fixes (listés dans `collecte/collecte.py`), case vide quand une valeur est absente. Mêmes noms de champions que `parties.csv` (Kayn rouge / Kayn bleu) ; postes `top`, `jgl`, `mid`, `adc`, `sup` ; équipes `b` et `r`.

| Dossier | Une ligne par | Contenu |
|---|---|---|
| `details_parties/` | partie | durée, fin par abandon, 5 bans par équipe, et pour chaque objectif : `<cote>_<objectif>_premier` (0/1) et `<cote>_<objectif>_nb` |
| `joueurs/` | joueur (10 par partie, ordre de `parties.csv`) | KDA, or, cs, dégâts par type, soins, boucliers, contrôle, vision, sorts, rune principale, objets, et une sélection de `challenges` |
| `timeline_joueurs/` | joueur | à 5, 10, 15, 20, 25 et 30 minutes : or, xp, cs, niveau, dégâts aux champions, position |
| `evenements/` | événement | kills de champions, monstres épiques, bâtiments et plaques |

Ces fichiers suivent les mêmes règles que `parties.csv` : écrits en ajout par la collecte seulement, jamais modifiés à la main. Taille mesurée sur 12 vrais matchs : environ 13 Ko par partie (événements 9 Ko, joueurs 2,3 Ko, timeline 1,7 Ko, détails 0,2 Ko), soit environ 18 Mo pour une tranche d'événements.

### Lire les données

Toujours passer par `collecte/lecture.py` :

```python
from lecture import lire_details, matchs_avec_details
for joueur in lire_details("joueurs"):   # dictionnaires, valeurs en texte
    ...
```

- Pour chaque partie, la collecte écrit `joueurs`, puis `timeline_joueurs` et `evenements`, puis `details_parties`, et `parties.csv` en dernier. Une partie n'est donc complète que si elle figure dans `parties.csv` **et** dans `details_parties`. Une collecte coupée en pleine écriture peut laisser des lignes d'une partie inachevée : `lecture.py` les ignore.
- Une partie réécrite après une interruption peut apparaître deux fois : `lecture.py` ne garde que sa dernière écriture. Ne pas lire les tranches à la main sans refaire ce filtrage.
- Toutes les valeurs sont lues comme du texte ; une case vide veut dire « absente », pas zéro.
- Une partie peut avoir des détails sans timeline (timeline introuvable ou Riot indisponible) : elle n'a alors aucune ligne dans `timeline_joueurs` ni dans `evenements`. `matchs_presents("timeline_joueurs")` donne les parties qui en ont une. `collecte/bilan.md` compte les parties avec détails et avec timeline.
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
python3 -m unittest discover -s collecte/tests
```

Ils doivent passer avant chaque push. Chaque autre branche a ses propres tests (voir son README).
