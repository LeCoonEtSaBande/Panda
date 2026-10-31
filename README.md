# Panda — branche `scraping` : les stats Lolalytics du patch

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Cette branche ne contient que le scraper Lolalytics et ce qu'il a récupéré, un dossier par patch.

| Fichier | Rôle |
|---|---|
| `lolalytics/recuperer.py` | Le scraper. Une page toutes les 3 secondes, Platine et plus, tous serveurs, environ 800 pages par patch (la synergie en plus). |
| `lolalytics/<patch>/champions.csv` | Tier list de chaque poste : victoires, parties, pick, ban, part du poste. |
| `lolalytics/<patch>/matchups.csv` | Chaque champion contre chaque adversaire, à chaque poste : victoires, parties, `delta_2` (l'effet propre du matchup). |
| `lolalytics/<patch>/synergies.csv` | Chaque champion avec chaque allié, à chaque poste (si Lolalytics la publie) : victoires, parties, `delta_2` (ce que la paire gagne de plus que prévu). Depuis le 27/10/2026. |
| `lolalytics/<patch>/profils.csv` | Dégâts moyens par type (physiques, magiques, bruts) et parties / victoires par tranche de durée. |
| `lolalytics/<patch>/resume.md` | Junglers du patch et contres nets du pool, lisibles. |
| `lolalytics/valeurs_jeu.py`, `lolalytics/valeurs_jeu.json` | Valeurs et timers du patch pour la surcouche en jeu du lien client (recharge de Saut éclair et du Sablier de Zhonya, hâte des Bottes de lucidité et de Perspicacité cosmique, apparition des dragons et du Héraut, prix des objets). Data Dragon d'abord, puis le wiki, sinon la valeur précédente ou par défaut ; le résumé du bouton dit d'où vient chaque valeur. Refait à chaque passage du bouton 2. La surcouche télécharge ce fichier au lancement. |
| `lolalytics/tests/` | Tests du lecteur sur des pages miniatures, et des valeurs du patch. |

- **Lancer** : bouton « Récupérer les stats Lolalytics du patch » (sur `main`), une fois par patch, environ 40 minutes.
- **Politesse** : une page toutes les 3 secondes, arrêt immédiat sur un refus (403 ou 429), une seule fois par patch.
- **Tests** : `python3 -m unittest discover -s lolalytics/tests`.
