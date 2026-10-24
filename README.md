# Panda — branche `scraping` : les stats Lolalytics du patch

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Cette branche ne contient que le scraper Lolalytics et ce qu'il a récupéré, un dossier par patch.

| Fichier | Rôle |
|---|---|
| `lolalytics/recuperer.py` | Le scraper. Une page toutes les 3 secondes, Platine et plus, tous serveurs, environ 400 pages par patch. |
| `lolalytics/<patch>/champions.csv` | Tier list de chaque poste : victoires, parties, pick, ban, part du poste. |
| `lolalytics/<patch>/matchups.csv` | Chaque champion contre chaque adversaire, à chaque poste : victoires, parties, `delta_2` (l'effet propre du matchup). |
| `lolalytics/<patch>/profils.csv` | Dégâts moyens par type (physiques, magiques, bruts) et parties / victoires par tranche de durée. |
| `lolalytics/<patch>/resume.md` | Junglers du patch et contres nets du pool, lisibles. |
| `lolalytics/tests/` | Tests du lecteur sur des pages miniatures. |

- **Lancer** : bouton « Récupérer les stats Lolalytics du patch » (sur `main`), une fois par patch, environ 20 minutes.
- **Politesse** : une page toutes les 3 secondes, arrêt immédiat sur un refus (403 ou 429), une seule fois par patch.
- **Tests** : `python3 -m unittest discover -s lolalytics/tests`.
