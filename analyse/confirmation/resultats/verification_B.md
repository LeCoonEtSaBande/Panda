# Vérification sur B de ce qu'affiche l'assistant

Appris sur A (ou Lolalytics), mesuré sur B. Confirmé = moins de 5 % de chances d'être un hasard après correction.

## 1. Lolalytics (13923 parties de B)

| Élément | Coefficient sur B (attendu ≈ 4 si les points sont justes) | Verdict |
|---|---|---|
| Force du patch | 3.6 ± 0.4 | confirmé |
| Contre de l'adversaire direct | 4.8 ± 0.5 | confirmé |
| Contres des autres adversaires | 3.0 ± 0.3 | confirmé |

- Quand la force + le contre direct donnent 3 points d'avance ou plus à un camp (8148 parties), il gagne 56 %.

## 2. Or à 15 min par lane

| Lane | Parties | Corrélation prédit / réel | Annoncée devant à 60 % ou plus : devant en vrai | Verdict |
|---|---|---|---|---|
| top | 10348 | 0.28 | 66 % (1789) | confirmé |
| jgl | 10348 | 0.27 | 63 % (2038) | confirmé |
| mid | 10348 | 0.25 | 65 % (1717) | confirmé |
| bot | 10348 | 0.26 | 66 % (1962) | confirmé |

## 3. Ganks réussis avant 15 min (10476 parties de B)

- Le modèle prédit mieux que la moyenne : gain 31.7 millièmes, **confirmé**.
- Le modèle prédit mieux que la seule catégorie du jungler : gain 10.8 millièmes, **confirmé**.

| Chance annoncée | Lignes | Annoncé | Réel |
|---|---|---|---|
| 0-50 % | 1588 | 46 % | 48 % |
| 50-60 % | 9540 | 56 % | 56 % |
| 60-70 % | 18451 | 65 % | 65 % |
| 70-80 % | 15534 | 75 % | 75 % |
| 80-100 % | 17743 | 86 % | 85 % |

## 4. Envahir (effets affichés par l'assistant)

| Minute | Jungler | A | B (envahir.py) | B (mesure) | Verdict |
|---|---|---|---|---|---|
| 5 | Engage (tanks) | +3.2 | +3.6 | +4.4 | rien |
| 5 | Engage (bruisers) | +5.6 | +2.6 | +3.0 | rien |
| 5 | Pick (assassins) | +1.8 | +1.8 | +1.9 | rien |
| 5 | Carrys | +4.9 | +1.3 | +2.0 | rien |
| 10 | Engage (tanks) | +2.3 | +1.0 | +1.2 | rien |
| 10 | Engage (bruisers) | +2.3 | +4.9 | +5.7 | à surveiller |
| 10 | Pick (assassins) | +2.3 | -2.5 | -2.7 | rien |
| 10 | Poke (artilleurs) | +3.0 | -3.0 | -6.0 | rien |
| 10 | Carrys | +4.2 | +5.2 | +7.0 | rien |
| 15 | Engage (tanks) | +6.5 | +3.7 | +4.5 | rien |
| 15 | Engage (bruisers) | +7.2 | +1.3 | +1.7 | rien |
| 15 | Pick (assassins) | +1.8 | +0.6 | +0.8 | rien |
| 15 | Poke (artilleurs) | +8.8 | +6.1 | +9.2 | rien |
| 15 | Carrys | +4.5 | -3.9 | -5.1 | rien |
| 20 | Engage (tanks) | +2.9 | +11.4 | +12.8 | confirmé |
| 20 | Engage (bruisers) | +1.7 | -1.0 | -1.7 | rien |
| 20 | Supports tanks | +4.2 | +8.5 | +15.2 | rien |
| 20 | Poke (artilleurs) | +2.2 | +8.3 | +10.5 | à surveiller |
| 20 | Carrys | +4.3 | +3.3 | +3.2 | rien |

