# Types des champions

- Appris sur les choix du propriétaire : 173 champions revus (10 types chacun), plus ses références ; mesures du tas A, vérifiées sur B. Un champion revu garde ses choix ; un autre prend les types à 50 sur 100 ou plus (3 au plus, au moins un).
- L'assistant affiche Carry ou Enchanteur, plus les deux autres styles les mieux notés de chaque champion ; « fragile » (cible même sans être carry ni enchanteur) : encaisse par minute à plus d'un demi-écart-type sous la moyenne des champions (70 champions).
- Parties de 15 min et plus : A 31273, B 10359 environ ; postes avec au moins 150 parties.

| Type | Champions retenus | Ses oui retrouvés sans les voir | Faux oui | Justesse sans les voir | Même décision A et B | Mesures (poids) |
|---|---|---|---|---|---|---|
| carry | 56 | 47 sur 56 | 6 | 91 % | 90 % | part de ses parties en ADC +1.65, or par minute (comparé à son poste) +1.13, où il meurt après 14 min (0 = chez lui, 1 = base adverse) (comparé à son poste) -1.46 |
| enchanteur | 13 | 13 sur 13 | 2 | 99 % | 99 % | alliés sauvés de la mort +4.18, dégâts encaissés et atténués par minute (comparé à son poste) -1.33 |
| assassin | 28 | 26 sur 28 | 12 | 92 % | 94 % | kills sur un ADC ou un mid, presque seul, après 14 min (comparé à son poste) +3.14, part de ses parties en top -2.74, part de ses parties en ADC -2.38 |
| plongeur | 36 | 32 sur 36 | 19 | 87 % | 93 % | où il meurt après 14 min (0 = chez lui, 1 = base adverse) (comparé à son poste) +0.80, dégâts encaissés et atténués par minute +1.58, dégâts aux bâtiments par minute (comparé à son poste) +1.01 |
| attrapeur | 29 | 27 sur 29 | 17 | 89 % | 98 % | kills à deux sur un ennemi isolé +1.56, temps de contrôle infligé +1.15, nombre de sorts de contrôle (Data Dragon) +0.75 |
| tank | 20 | 18 sur 20 | 16 | 90 % | 94 % | part des dégâts encaissés par l'équipe -1.46, dégâts encaissés et atténués par minute +5.32, kills sur un ADC ou un mid, presque seul, après 14 min (comparé à son poste) -0.96 |
| hp | 45 | pas encore de choix du propriétaire | | | 99 % | règle : encaisse par minute ≥ moyenne + 0.5 écart-type, sans être tank |
| bloqueur | 39 | 33 sur 39 | 8 | 92 % | 99 % | temps de contrôle infligé +1.33, dégâts encaissés et atténués par minute (comparé à son poste) +1.07, dégâts aux bâtiments par minute (comparé à son poste) -1.01 |
| dueliste | 43 | 41 sur 43 | 12 | 92 % | 96 % | solo kills (comparé à son poste) +1.98, seul sur une lane de côté à 20, 25 et 30 min +1.91, dégâts encaissés et atténués par minute +1.66 |
| splitpusher | 25 | 25 sur 25 | 10 | 94 % | 90 % | seul sur une lane de côté à 20, 25 et 30 min (comparé à son poste) +2.81, nombre de sorts de protection (Data Dragon) +1.29, part de ses parties en top +1.20 |
| teamfighter | 112 | 94 sur 111 | 7 | 86 % | 88 % | kills et assists en combat d'équipe (part des kills de son équipe en combat) (comparé à son poste) +3.25, kills par combat (comparé à son poste) -0.82, dégâts par minute +0.59 |

Ce que l'algorithme voit autrement que le propriétaire (note sans avoir vu ses choix ; ses choix restent appliqués) :

- **carry** : en plus de tes choix : Zyra 63, Urgot 55, Zilean 55, Bard 54, Shyvana 54 ; tes oui qu'il ne voit pas : Cassiopeia 18, Kindred 26, Vladimir 27, Viego 29, Viktor 34, Azir 37, Fiddlesticks 38, Orianna 45, Brand 46
- **enchanteur** : en plus de tes choix : Senna 67 ; tes oui qu'il ne voit pas : aucun
- **assassin** : en plus de tes choix : Annie 80, Aurora 78, Xerath 76, Azir 67, Kindred 66, Graves 65, Hecarim 62, Bel'Veth 57, Senna 57, Vel'Koz 57, Lux 55 ; tes oui qu'il ne voit pas : Sylas 29, Zoe 40
- **plongeur** : en plus de tes choix : Dr. Mundo 99, Illaoi 99, Sion 99, Rengar 85, Xin Zhao 77, Bel'Veth 70, Talon 70, K'Sante 68, Kalista 68, Ekko 67, Rell 64, Taric 63, Poppy 60, Briar 58, Jarvan IV 56, Aatrox 53, Leona 52, Kayn bleu 51, Sylas 51 ; tes oui qu'il ne voit pas : Pantheon 18, Vi 40, Urgot 45, Mordekaiser 48
- **attrapeur** : en plus de tes choix : Maokai 99, Zyra 91, Braum 89, Neeko 82, Galio 81, Poppy 79, Taric 78, Briar 74, Fiddlesticks 74, Ashe 60, Lissandra 59, Karma 58, Taliyah 55 ; tes oui qu'il ne voit pas : Tahm Kench 27, Vi 43
- **tank** : en plus de tes choix : Galio 96, Alistar 89, Shyvana 84, Poppy 83, Singed 76, Nunu & Willump 67, Renekton 66, Kled 64, Zaahen 60, Garen 59, Urgot 59, Volibear 58, Taric 57, Jarvan IV 52, Trundle 52, Ambessa 51 ; tes oui qu'il ne voit pas : Mordekaiser 17, Maokai 42
- **bloqueur** : en plus de tes choix : Swain 96, Briar 79, Aurelion Sol 77, Lissandra 69, Cassiopeia 66, Lillia 58, Sylas 53 ; tes oui qu'il ne voit pas : Lulu 22, Syndra 25, Pyke 27, Vi 39, Rek'Sai 41, Gnar 46
- **dueliste** : en plus de tes choix : Rengar 96, Yorick 84, Dr. Mundo 83, Talon 82, Katarina 80, Tahm Kench 80, Zed 79, Kayn bleu 74, Pantheon 59, LeBlanc 58, Fizz 57, Jayce 54 ; tes oui qu'il ne voit pas : Aurora 11, Nocturne 35
- **splitpusher** : en plus de tes choix : Shen 97, Zaahen 93, Kassadin 85, Hecarim 81, Bard 68, Gangplank 67, Vayne 56, Nocturne 54, Taric 54 ; tes oui qu'il ne voit pas : aucun
- **teamfighter** : en plus de tes choix : Alistar 96, Akshan 91, Ashe 87, Jhin 80, Locke 76, Zoe 70, Renekton 52 ; tes oui qu'il ne voit pas : Darius 5, Neeko 5, Viego 10, Brand 15, Syndra 20, Azir 21, Gragas 25, Vel'Koz 27, Vladimir 29, Master Yi 32, Mel 33, Tahm Kench 33, Zaahen 37, Graves 45, Varus 46, Fiddlesticks 49, Veigar 49
