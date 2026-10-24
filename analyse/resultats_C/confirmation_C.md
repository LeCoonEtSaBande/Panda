# Confirmation sur C de ce qu'affiche l'assistant

Appris sur A + B (ou Lolalytics), mesuré sur C. Confirmé = moins de 5 % de chances d'être un hasard après correction.

## 1. Lolalytics (12579 parties de C)

| Élément | Coefficient sur C (attendu ≈ 4 si les points sont justes) | Verdict |
|---|---|---|
| Force du patch | 4.5 ± 0.4 | confirmé |
| Contre de l'adversaire direct | 5.8 ± 0.5 | confirmé |
| Contres des autres adversaires | 3.2 ± 0.3 | confirmé |

- Quand la force + le contre direct donnent 3 points d'avance ou plus à un camp (7410 parties), il gagne 58 %.

## 2. Or à 15 min par lane

| Lane | Parties | Corrélation prédit / réel | Annoncée devant à 60 % ou plus : devant en vrai | Verdict |
|---|---|---|---|---|
| top | 12425 | 0.28 | 66 % (2035) | confirmé |
| jgl | 12425 | 0.27 | 64 % (2453) | confirmé |
| mid | 12425 | 0.25 | 66 % (1847) | confirmé |
| bot | 12425 | 0.25 | 65 % (2483) | confirmé |

## 3. Ganks réussis avant 15 min (12566 parties de C)

- Le modèle prédit mieux que la moyenne : gain 32.1 millièmes, **confirmé**.
- Le modèle prédit mieux que la seule catégorie du jungler : gain 10.4 millièmes, **confirmé**.

| Chance annoncée | Lignes | Annoncé | Réel |
|---|---|---|---|
| 0-50 % | 1236 | 47 % | 45 % |
| 50-60 % | 11056 | 56 % | 55 % |
| 60-70 % | 24198 | 65 % | 65 % |
| 70-80 % | 17943 | 75 % | 75 % |
| 80-100 % | 20963 | 85 % | 85 % |

## 4. Envahir (effets affichés par l'assistant)

| Minute | Jungler | A | B | C | Verdict |
|---|---|---|---|---|---|
| 5 | Engage (tanks) | +2.5 | +2.4 | +1.5 | rien |
| 5 | Pick (assassins) | +3.0 | +2.8 | +1.9 | rien |
| 5 | Poke (artilleurs) | -3.7 | -7.1 | -9.1 | rien |
| 10 | Carrys | +4.0 | +1.9 | +4.3 | rien |
| 15 | Engage (tanks) | +6.5 | +5.5 | +7.3 | confirmé |
| 15 | Engage (bruisers) | +5.8 | +3.4 | +6.3 | confirmé |
| 15 | Poke (artilleurs) | +9.0 | +4.4 | +11.5 | à surveiller |
| 20 | Engage (tanks) | +3.0 | +10.5 | +5.6 | à surveiller |
| 20 | Poke (artilleurs) | +2.6 | +10.3 | -4.5 | rien |
| 20 | Carrys | +6.0 | +8.9 | -2.7 | rien |

