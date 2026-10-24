# Point 3 : jouer avec ses lanes

1. `dynamique.py` : d'après la draft seule, l'écart d'or attendu à 15 minutes sur chaque lane (modèle des contres de `../contres/`), vérifié sur des parties que le modèle n'a pas vues ; puis l'effet de ces lanes annoncées sur la victoire selon la catégorie du jungler (groupes teamfight du catalogue unifié). Écrit `resultats/dynamique.md` et `resultats/predictions.csv.gz`.
2. `comportement.py` (après `dynamique.py`) : envahir à 5 minutes, et jouer du côté de la lane annoncée la plus forte, vont-ils avec plus de victoires, selon la draft et la catégorie du jungler ? Écrit `resultats/comportement.md`. Ce sont des associations (comportements en partie), pas des causes.

Tas : A pour apprendre, B pour vérifier (découpage n° 2). C n'est jamais lu.

```
python3 analyse/lanes/dynamique.py
python3 analyse/lanes/comportement.py
```
