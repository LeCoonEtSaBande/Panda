# Vérification sur B de ce qu'affiche l'assistant

Appris sur A (ou Lolalytics), mesuré sur B. Confirmé = moins de 5 % de chances d'être un hasard après correction.

## 1. Lolalytics (18086 parties de B)

| Élément | Coefficient sur B (attendu ≈ 4 si les points sont justes) | Verdict |
|---|---|---|
| Force du patch | 3.8 ± 0.3 | confirmé |
| Contre de l'adversaire direct | 4.7 ± 0.4 | confirmé |
| Contres des autres adversaires | 3.3 ± 0.3 | confirmé |
| Synergie avec les alliés | 2.3 ± 0.3 | confirmé |

- Quand la force + le contre direct donnent 3 points d'avance ou plus à un camp (10851 parties), il gagne 57 %.

### Chance de victoire à la draft : **confirmé**

Apprise sur A, mesurée sur B : bon gagnant 56 % des parties ; perte log 0.6805 (50 / 50 : 0.6931).

| Annoncé | Parties | Réel |
|---|---|---|
| 0–40 % (moyenne 36 %) | 2047 | 36 % |
| 40–45 % (moyenne 43 %) | 3170 | 42 % |
| 45–48 % (moyenne 47 %) | 2605 | 46 % |
| 48–52 % (moyenne 50 %) | 3647 | 49 % |
| 52–55 % (moyenne 53 %) | 2384 | 54 % |
| 55–60 % (moyenne 57 %) | 2716 | 56 % |
| 60–100 % (moyenne 63 %) | 1517 | 64 % |

## 2. Or à 15 min par lane

| Lane | Parties | Corrélation prédit / réel | Annoncée devant à 60 % ou plus : devant en vrai | Verdict |
|---|---|---|---|---|
| top | 14612 | 0.28 | 67 % (2484) | confirmé |
| jgl | 14612 | 0.27 | 64 % (2776) | confirmé |
| mid | 14612 | 0.25 | 66 % (2289) | confirmé |
| bot | 14612 | 0.26 | 67 % (2700) | confirmé |

## 3. Ganks réussis avant 15 min (14787 parties de B)

- Le modèle prédit mieux que la moyenne : gain 32.3 millièmes, **confirmé**.
- Le modèle prédit mieux que la seule catégorie du jungler : gain 11.1 millièmes, **confirmé**.

| Chance annoncée | Lignes | Annoncé | Réel |
|---|---|---|---|
| 0-50 % | 2137 | 47 % | 48 % |
| 50-60 % | 13343 | 56 % | 56 % |
| 60-70 % | 26564 | 65 % | 65 % |
| 70-80 % | 21726 | 75 % | 75 % |
| 80-100 % | 24952 | 86 % | 85 % |

