# Les contres par lane

Workflow **Enrichir les contres** (bouton « Run workflow ») : à lancer de temps en temps, quand des collectes ont ajouté des parties. Code sur `analyse-iterative`, données à jour de `main`.

## Ce qu'il mesure

Pour chaque partie avec timeline, sur chaque lane, avant 15 minutes :
- **l'écart d'or à 15 min** entre les deux joueurs de la lane : la mesure principale (elle contient les kills, les sbires et les plaques) ;
- l'écart d'XP, le solde de kills (kills + assistances − morts), les plaques et la première tour de la lane.

Lanes : top, jungle (jungler contre jungler), mid, et bot, où le duo ADC + support est mesuré ensemble.

## Comment un contre est identifié

1. **Force de lane** de chaque champion : son écart d'or moyen à 15 min contre un adversaire quelconque.
2. **Effet propre** d'une paire A contre B : ce qui reste une fois les deux forces de lane retirées, rétréci vers 0 quand la paire a peu de parties.
3. **Contre identifié** : effet propre d'au moins 150 or, à plus de deux marges d'erreur de 0, sur au moins 20 parties.

Une paire sans contre identifié garde un résultat attendu : la force de lane de A moins celle de B. Les contres s'enrichissent au fil des collectes, et chaque passage signale ceux qui apparaissent ou disparaissent.

L'**accord entre deux moitiés des parties** dit, poste par poste, si les effets propres des paires sont réels (1) ou du bruit (0).

## Fichiers (`resultats/`)

| Fichier | Contenu |
|---|---|
| `contres.md` | le résumé à lire : fiabilité, changements depuis le passage précédent, contres identifiés, duels de ton pool en jungle |
| `contres_<poste>.csv` | toutes les paires vues 10 fois ou plus : résultat attendu, effet propre, marge d'erreur, statut, mesures brutes |
| `forces_<poste>.csv` | la force de lane de chaque champion |
| `etat.json`, `parties_connues.txt.gz` | ce que le passage précédent connaissait, pour signaler les nouveautés |
