# Dynamique des lanes d'après la draft

- Parties : A = 29051, B = 9596 (Émeraude-Diamant). Prédictions toujours faites par un modèle qui n'a pas vu la partie.

## Étape 1 : la draft annonce-t-elle quelles lanes seront devant en or à 15 min ?

| Lane | Corrélation prédit / réel (B) | Écart réel moyen quand la draft annonce +500 or ou plus | Lanes annoncées devant (+500) qui le sont vraiment | Part des parties annoncées à ±500 |
|---|---|---|---|---|
| top | 0.27 | +749 or | 68 % | 31 % |
| jungle | 0.27 | +640 or | 71 % | 18 % |
| mid | 0.25 | +745 or | 68 % | 17 % |
| bot | 0.26 | +935 or | 65 % | 40 % |

## Étape 2 : quelle catégorie de jungler profite des lanes fortes ?

- Jugement sur B (millièmes de perte log, plus haut = mieux) : lanes annoncées seules -0.076 ; avec la catégorie du jungler -0.157. La différence mesure ce qu'apporte la catégorie.

Effet de 1 000 or annoncés en faveur de tes lanes, en points de victoire (à force de champions égale) :

| Jungler | top | mid | bot |
|---|---|---|---|
| tous (moyenne) | +0.3 | +0.4 | -0.4 |
| Engage (tanks) | +0.7 | +1.2 | -1.0 |
| Engage (bruisers) | -0.6 | +0.2 | -0.6 |
| Supports tanks | +0.9 | +1.1 | -0.4 |
| Pick (assassins) | +0.5 | -0.4 | +0.1 |
| Poke (artilleurs) | -0.4 | +1.2 | -0.3 |
| Carrys | +0.1 | -0.1 | -0.8 |
| Disengage (enchanteurs) | +1.3 | +0.4 | -0.4 |

Junglers par catégorie dans A : Engage (tanks) 12438, Engage (bruisers) 12757, Supports tanks 902, Pick (assassins) 23044, Poke (artilleurs) 2809, Carrys 5679, Disengage (enchanteurs) 473

