# Mix de dégâts et compos early / late

- 24246 parties avec durée (A + B, Émeraude-Diamant). Profils : degats Lolalytics 396, degats nos parties 396, late Lolalytics 400, late nos parties 2 (Lolalytics patch 16.21, Platine et plus).
- Pente early/late d'un champion : points de victoire gagnés (late) ou perdus (early) par 10 minutes de partie en plus, par rapport à son propre taux moyen.

## Early / late : ça tient ?

- Coefficient (victoire selon l'écart de pente × durée, à force égale) : A 4.04, B 3.47, A + B 4.18 ; retenu pour l'assistant : 4.18. **Confirmé** (même signe sur A et B).
- Sur B, quand une équipe est nettement plus late que l'autre (écart de pente au-dessus de la médiane, 0.05) :

| Durée | Parties | L'équipe late gagne | Force des champions seule |
|---|---|---|---|
| 0-20 min | 230 | 37.0 % | 49.9 % |
| 20-25 min | 527 | 39.1 % | 50.0 % |
| 25-30 min | 1024 | 51.7 % | 50.1 % |
| 30-35 min | 805 | 55.3 % | 50.2 % |
| 35-40 min | 320 | 61.3 % | 50.3 % |
| 40-… min | 148 | 56.8 % | 50.1 % |

- **Les plus early** : Irelia (top) -6.2, Irelia (mid) -5.4, Swain (adc) -5.1, Vel'Koz (adc) -5.1, Varus (adc) -4.6, Yasuo (adc) -4.5, Lux (adc) -4.5, Illaoi (top) -4.3, Vel'Koz (sup) -4.3, Hwei (adc) -4.3, Elise (sup) -4.3, Mel (adc) -4.2, Ziggs (adc) -4.0, Sylas (sup) -3.9, Yorick (top) -3.9
- **Les plus late** : Kayle (top) +8.9, Bel'Veth (jgl) +8.0, Kayle (mid) +7.2, Aurelion Sol (mid) +7.1, Smolder (mid) +7.0, Smolder (top) +6.3, Yuumi (sup) +6.2, Ornn (top) +5.4, Ryze (mid) +5.1, Twitch (adc) +5.1, Teemo (jgl) +4.7, Kassadin (mid) +4.6, Rengar (jgl) +4.5, Smolder (adc) +4.4, Master Yi (top) +4.4

## Mix de dégâts : part magique de l'équipe

Points de victoire par rapport à une équipe à 30-70 % de dégâts magiques, à force de champions égale.

| Part magique | Équipes | A | B | Tient |
|---|---|---|---|---|
| magique < 20 % | 1555 | -3.9 | -4.0 | oui |
| magique 20-30 % | 7902 | -1.3 | -1.9 | oui |
| magique > 70 % | 1039 | -3.8 | -3.7 | oui |

