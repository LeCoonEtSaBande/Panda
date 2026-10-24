# Identifier les champions forts du patch

Branche `champions-patch`. Workflow : **Identifier les champions forts du patch** (bouton « Run workflow »).

À lancer à la main à chaque patch, plusieurs fois si besoin : les parties s'ajoutent à celles déjà collectées pour ce patch.

## Ce que fait le workflow

1. **Collecte légère** (`collecte_patch.py`, réglages dans `patch.ini`) :
   - joueurs tirés au hasard en Platine, Émeraude et Diamant ;
   - seulement le détail des parties, sans timeline : un appel par partie, environ 2 500 parties par heure ;
   - seules les parties du patch en cours (dernière version de Data Dragon) sont gardées ; les autres sont notées dans `ecartees.csv` pour ne pas être retéléchargées ;
   - 5 h 15 de collecte, le job entier est limité à 6 heures ;
   - sauvegarde toutes les 10 minutes (`enregistrer_patch.sh`).
2. **Classement** (`champions_forts.py`) : pour chaque champion à chaque poste, le taux de victoire brut et le taux **corrigé de la force des 9 autres champions**, avec leur marge d'erreur, et un verdict fort / dans la moyenne / faible / pas assez de parties.

Il partage la file de **Lancer une collecte** : les deux utilisent la même clé Riot, ils ne tournent jamais en même temps (le second attend la fin du premier).

## Où sont les fichiers

| Fichier | Contenu |
|---|---|
| `analyse/donnees_patch/<patch>/parties.csv` | les parties du patch, même format que `analyse/donnees/parties.csv` |
| `analyse/donnees_patch/<patch>/ecartees.csv` | parties écartées (remake, autre patch…) |
| `analyse/resultats_patch/<patch>/champions_jungle.md` | **le résumé à lire** : ton pool, les junglers forts et faibles, puis les autres postes |
| `analyse/resultats_patch/<patch>/champions.csv` | tous les champions, tous les postes |

Les parties sont gardées d'un patch à l'autre : elles pourront servir à tester d'autres idées de prédiction.

## Combien de parties

Un lancement donne environ 12 000 parties. Un jungler joué dans 2 % des parties y apparaît environ 250 fois, soit une marge d'erreur d'environ ±6 points : assez pour repérer les champions très forts ou très faibles. Deux ou trois lancements par patch donnent un classement plus fin.
