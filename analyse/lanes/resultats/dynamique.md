# Dynamique des lanes d'après la draft

- Parties : A = 42381, B = 13923 (Émeraude-Diamant). Prédictions toujours faites par un modèle qui n'a pas vu la partie.

## Étape 1 : la draft annonce-t-elle quelles lanes seront devant en or à 15 min ?

| Lane | Corrélation prédit / réel (B) | Écart réel moyen quand la draft annonce +500 or ou plus | Lanes annoncées devant (+500) qui le sont vraiment | Part des parties annoncées à ±500 |
|---|---|---|---|---|
| top | 0.28 | +758 or | 68 % | 31 % |
| jungle | 0.27 | +626 or | 69 % | 18 % |
| mid | 0.25 | +711 or | 68 % | 19 % |
| bot | 0.26 | +891 or | 65 % | 40 % |

## Étape 2 : quelle catégorie de jungler profite des lanes fortes ?

- Jugement sur B (millièmes de perte log, plus haut = mieux) : lanes annoncées seules +0.028 ; avec la catégorie du jungler -0.144. La différence mesure ce qu'apporte la catégorie.

Effet de 1 000 or annoncés en faveur de tes lanes, en points de victoire (à force de champions égale) :

| Jungler | top | mid | bot |
|---|---|---|---|
| tous (moyenne) | +0.4 | +0.7 | -0.1 |
| Engage (tanks) | +1.1 | +0.6 | -0.7 |
| Engage (bruisers) | -0.1 | +1.4 | -0.5 |
| Supports tanks | +1.0 | +1.7 | -0.3 |
| Pick (assassins) | +0.3 | +0.2 | +0.2 |
| Poke (artilleurs) | -0.3 | +1.7 | +0.2 |
| Carrys | -0.0 | +0.3 | -0.2 |
| Disengage (enchanteurs) | +1.2 | +0.5 | +0.1 |

Junglers par catégorie dans A : Engage (tanks) 18160, Engage (bruisers) 18697, Supports tanks 1263, Pick (assassins) 33674, Poke (artilleurs) 4021, Carrys 8298, Disengage (enchanteurs) 649

