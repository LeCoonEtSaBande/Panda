# Confirmation des duels de junglers

- Découpage propre aux duels, fixé avant calcul : A = les 28067 premières parties de parties.csv, C = les 14034 dernières (à partir de 8022301461). Duels : A 15657, C 7823.
- Le modèle de lanes/duels.py est rejoué tel quel, appris sur A, mesuré sur C.

## Ensemble

- Champions + minute + or + niveau, mieux que or + niveau seuls : gain 33.0 millièmes sur C, **confirmé**.
- Évolution avec la minute, mieux que sans : gain 11.0 millièmes sur C, **confirmé**.

## Chaque jungler (accord des forces A / C : 0.92)

| Jungler | À or égal sur A | Sur C | Duels A | Duels C | Verdict |
|---|---|---|---|---|---|
| Warwick | 73 % | 68 % | 372 | 203 | confirmé |
| Wukong | 66 % | 68 % | 1093 | 468 | confirmé |
| Cho'Gath | 64 % | 61 % | 626 | 289 | confirmé |
| Volibear | 63 % | 75 % | 170 | 115 | confirmé |
| Briar | 61 % | 62 % | 806 | 429 | confirmé |
| Lee Sin | 60 % | 58 % | 1106 | 542 | confirmé |
| Sylas | 60 % | 55 % | 794 | 415 | rien |
| Kayn rouge | 59 % | 58 % | 516 | 255 | confirmé |
| Shyvana | 59 % | 50 % | 651 | 368 | rien |
| Udyr | 59 % | 70 % | 273 | 166 | confirmé |
| Xin Zhao | 57 % | 61 % | 323 | 177 | confirmé |
| Vi | 55 % | 50 % | 505 | 227 | rien |
| Hecarim | 55 % | 52 % | 875 | 453 | rien |
| Rengar | 54 % | 57 % | 1070 | 611 | confirmé |
| Bel'Veth | 53 % | 47 % | 479 | 285 | rien |
| Amumu | 53 % | 60 % | 260 | 135 | confirmé |
| Master Yi | 52 % | 47 % | 983 | 504 | rien |
| Nocturne | 52 % | 46 % | 430 | 241 | rien |
| Diana | 52 % | 53 % | 628 | 323 | rien |
| Elise | 51 % | 57 % | 718 | 378 | confirmé |
| Evelynn | 50 % | 51 % | 580 | 227 | rien |
| Naafiri | 49 % | 49 % | 295 | 137 | rien |
| Fiddlesticks | 48 % | 48 % | 264 | 155 | rien |
| Kha'Zix | 47 % | 55 % | 1749 | 925 | rien |
| Shaco | 47 % | 44 % | 1052 | 435 | confirmé |
| Talon | 46 % | 43 % | 1541 | 715 | confirmé |
| Jarvan IV | 45 % | 48 % | 966 | 491 | rien |
| Lillia | 45 % | 43 % | 805 | 379 | confirmé |
| Viego | 44 % | 52 % | 1476 | 769 | rien |
| Kayn bleu | 44 % | 40 % | 567 | 304 | confirmé |
| Kindred | 44 % | 48 % | 485 | 228 | rien |
| Nidalee | 43 % | 43 % | 412 | 201 | rien |
| Graves | 39 % | 42 % | 926 | 519 | confirmé |
| Qiyana | 39 % | 39 % | 1657 | 794 | confirmé |
| Locke | 39 % | 50 % | 182 | 108 | rien |
| Ekko | 38 % | 41 % | 666 | 351 | confirmé |
| Nunu & Willump | 38 % | 35 % | 259 | 140 | confirmé |
| Zed | 35 % | 34 % | 474 | 175 | confirmé |
| Quinn | 28 % | 31 % | 264 | 148 | confirmé |
| Karthus | 24 % | 20 % | 364 | 180 | confirmé |
| Zyra | 23 % | 21 % | 187 | 129 | confirmé |
| Taliyah | 19 % | 19 % | 218 | 125 | confirmé |

