# Vérification sur B : early / late et mix de dégâts

- Profils et sens figés sur A (duree_degats.py, profils degats Lolalytics 396, degats nos parties 407, late Lolalytics 400, late nos parties 2). Mesuré sur B : 13923 parties, dont 10487 avec durée. Force des champions apprise sur A.

## Early / late : **confirmé**

- Coefficient sur B 4.05 (± 0.45), sur A 4.16.
- Sur B, quand une équipe est nettement plus late (écart au-dessus de la médiane, 0.05) :

| Durée | Parties | L'équipe late gagne |
|---|---|---|
| 0-20 min | 386 | 36.8 % |
| 20-25 min | 930 | 41.2 % |
| 25-30 min | 1786 | 50.9 % |
| 30-35 min | 1392 | 55.5 % |
| 35-40 min | 536 | 61.0 % |
| 40-… min | 213 | 54.0 % |

## Mix de dégâts

| Part magique | Sur A | Sur B | Équipes de B | Verdict |
|---|---|---|---|---|
| magique < 20 % | -4.0 | -3.6 | 572 | à surveiller |
| magique 20-30 % | -1.6 | -1.4 | 2592 | rien |
| magique > 70 % | -4.1 | -5.1 | 351 | à surveiller |

