# Point 3 : jouer avec ses lanes

1. `dynamique.py` : d'après la draft seule, l'écart d'or attendu à 15 minutes sur chaque lane (modèle des contres de `../contres/`), vérifié sur des parties que le modèle n'a pas vues ; puis l'effet de ces lanes annoncées sur la victoire selon la catégorie du jungler (groupes teamfight du catalogue unifié). Écrit `resultats/dynamique.md` et `resultats/predictions.csv.gz`.
2. `comportement.py` (après `dynamique.py`) : envahir à 5 minutes, et jouer du côté de la lane annoncée la plus forte, vont-ils avec plus de victoires, selon la draft et la catégorie du jungler ? Écrit `resultats/comportement.md`. Ce sont des associations (comportements en partie), pas des causes.

3. `envahir.py` (après `dynamique.py`) : envahir la jungle adverse à 5, 10, 15 et 20 minutes, à force de champions égale **et à écart d'or égal** au même moment, par catégorie de jungler, appris séparément sur A et sur B. Écrit `resultats/envahir.md`.
4. `ganks.py` : la chance que le jungler participe à au moins un kill sur une lane avant 15 minutes, selon le jungler, ses laners et les laners adverses. Écrit `resultats/ganks.md` et `resultats/ganks_modele.json`.
5. `duree_degats.py [--lolalytics <dossier du patch>]` : le mix de dégâts (physiques, magiques, bruts) de chaque équipe et le caractère early / late de chaque champion, d'après Lolalytics (`profils.csv` de la branche `scraping`) ou, à défaut, nos parties. Vérifie sur A et sur B, à force de champions égale, que l'écart early/late entre deux équipes change la victoire selon la durée, et que les équipes presque toutes physiques ou toutes magiques gagnent moins. Écrit `resultats/duree_degats.md` et `resultats/duree_degats.json`, utilisé par l'assistant.

Tas : A pour apprendre, B pour vérifier (découpage n° 2). C n'est jamais lu.

```
python3 analyse/lanes/dynamique.py
python3 analyse/lanes/comportement.py
python3 analyse/lanes/envahir.py
python3 analyse/lanes/ganks.py
python3 analyse/lanes/duree_degats.py --lolalytics <dossier du patch>
```
