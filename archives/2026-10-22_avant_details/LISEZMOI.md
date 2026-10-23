# Archive du 22/10/2026 : données d'avant les fichiers de détails

Copie figée de `analyse/donnees/` et `analyse/resultats/` au commit `5b65852` (`753b699` avant la réécriture de l’historique du 23/10/2026), juste avant la première collecte avec détails de partie, joueurs, timeline et événements.

- `parties.csv` : 21 484 parties (patch 16.20 : 18 628, patch 16.21 : 2 856), même format que `analyse/donnees/parties.csv`.
- `ecartees.csv` : 437 parties écartées.
- `resultats/` : le rapport produit sur ces 21 484 parties.

Après l'archivage, `analyse/donnees/parties.csv` a été vidé (en-tête gardé) pour repartir avec des données neuves ; `ecartees.csv` y est resté. Cette archive ne doit jamais être modifiée ; aucun script ne la lit ni ne l'écrit.

Empreintes SHA-256 au moment de l'archivage :

```
bd5a4909e325f01f590bf4053bfc8f0527c5240c9820f40ceef98cc9f5c3011a  parties.csv
90bfcf8c869c4f8a38754757e7896956167f882767c45560c3d9678741837c75  ecartees.csv
```
