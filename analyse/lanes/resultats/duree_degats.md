# Mix de dégâts et compos early / late

- 24040 parties avec durée (A + B, Émeraude-Diamant). Profils : degats nos parties 792, late Lolalytics 0, late nos parties 264.
- Pente early/late d'un champion : points de victoire gagnés (late) ou perdus (early) par 10 minutes de partie en plus, par rapport à son propre taux moyen.

## Early / late : ça tient ?

- Coefficient (victoire selon l'écart de pente × durée, à force égale) : A 5.59, B 2.44, A + B 4.95 ; retenu pour l'assistant : 2.44. **Confirmé** (même signe sur A et B).
- Sur B, quand une équipe est nettement plus late que l'autre (écart de pente au-dessus de la médiane, 0.05) :

| Durée | Parties | L'équipe late gagne | Force des champions seule |
|---|---|---|---|
| 0-20 min | 224 | 37.1 % | 49.9 % |
| 20-25 min | 519 | 44.7 % | 49.8 % |
| 25-30 min | 1056 | 49.5 % | 49.8 % |
| 30-35 min | 773 | 55.8 % | 49.9 % |
| 35-40 min | 326 | 53.4 % | 50.1 % |
| 40-… min | 136 | 55.9 % | 49.9 % |

- **Les plus early** : Irelia (top) -8.7, Gnar (top) -6.1, Katarina (mid) -6.0, Tahm Kench (sup) -5.8, Yasuo (adc) -5.6, Blitzcrank (sup) -5.5, Pyke (sup) -5.4, Vi (jgl) -5.2, Lux (sup) -5.1, Ekko (mid) -4.7, Varus (adc) -4.6, Taliyah (jgl) -4.3, Kalista (adc) -4.3, Xerath (sup) -4.3, Hwei (sup) -4.2
- **Les plus late** : Master Yi (jgl) +6.5, Aurelion Sol (mid) +5.8, Evelynn (jgl) +5.6, Vladimir (top) +5.5, Aphelios (adc) +5.3, Veigar (mid) +5.2, Yuumi (sup) +5.0, Bel'Veth (jgl) +4.9, Aurelion Sol (adc) +4.8, Smolder (adc) +4.6, Vayne (top) +4.5, Gwen (top) +4.4, Teemo (jgl) +4.4, Braum (sup) +4.3, Ornn (top) +4.3

## Mix de dégâts : part magique de l'équipe

Points de victoire par rapport à une équipe à 30-70 % de dégâts magiques, à force de champions égale.

| Part magique | Équipes | A | B | Tient |
|---|---|---|---|---|
| magique < 20 % | 1578 | -3.7 | -2.6 | oui |
| magique 20-30 % | 8173 | -1.3 | -2.3 | oui |
| magique > 70 % | 1011 | -4.3 | -3.5 | oui |

