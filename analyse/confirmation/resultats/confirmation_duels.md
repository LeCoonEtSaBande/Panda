# Confirmation des duels (tous les champions)

- Découpage propre aux duels, fixé avant calcul : A = les 28067 premières parties de parties.csv, C = les 14034 dernières (à partir de 8022301461). Duels : A 341871, C 173134.
- Le modèle de lanes/duels.py est rejoué tel quel, appris sur A, mesuré sur C.

## Ensemble

- Champions + minute + or + niveau, mieux que or + niveau seuls : gain 19.6 millièmes sur C, **confirmé**.
- Évolution avec la minute, mieux que sans : gain 6.3 millièmes sur C, **confirmé**.

## Chaque champion (accord des forces A / C : 0.94)

| Champion | À or égal sur A | Sur C | Duels A | Duels C | Verdict |
|---|---|---|---|---|---|
| Zac | 67 % | 62 % | 1458 | 657 | confirmé |
| Warwick | 66 % | 61 % | 4025 | 2120 | confirmé |
| Tahm Kench | 66 % | 67 % | 2568 | 1297 | confirmé |
| Wukong | 65 % | 65 % | 4947 | 2330 | confirmé |
| Pyke | 65 % | 66 % | 2762 | 1393 | confirmé |
| Leona | 64 % | 58 % | 972 | 475 | confirmé |
| Akali | 64 % | 61 % | 11596 | 5691 | confirmé |
| Blitzcrank | 64 % | 60 % | 1376 | 756 | confirmé |
| Nasus | 64 % | 61 % | 3367 | 1661 | confirmé |
| Mordekaiser | 63 % | 62 % | 8182 | 3869 | confirmé |
| Amumu | 63 % | 58 % | 923 | 477 | confirmé |
| Thresh | 63 % | 56 % | 2339 | 1084 | confirmé |
| Sejuani | 63 % | 64 % | 1038 | 574 | confirmé |
| Fiddlesticks | 62 % | 63 % | 1596 | 804 | confirmé |
| Nautilus | 62 % | 61 % | 1536 | 764 | confirmé |
| Poppy | 62 % | 56 % | 1770 | 663 | confirmé |
| Evelynn | 62 % | 60 % | 2112 | 868 | confirmé |
| Sylas | 62 % | 59 % | 10543 | 5386 | confirmé |
| Rek'Sai | 61 % | 57 % | 784 | 352 | confirmé |
| Lee Sin | 61 % | 60 % | 4085 | 2047 | confirmé |
| Shyvana | 61 % | 61 % | 2397 | 1379 | confirmé |
| Briar | 61 % | 62 % | 3671 | 1984 | confirmé |
| Rengar | 61 % | 63 % | 4194 | 2405 | confirmé |
| Cho'Gath | 60 % | 58 % | 6042 | 3179 | confirmé |
| Kayn rouge | 60 % | 60 % | 1877 | 1002 | confirmé |
| Bard | 60 % | 57 % | 1415 | 708 | confirmé |
| Skarner | 59 % | 58 % | 522 | 263 | confirmé |
| Yuumi | 59 % | 57 % | 471 | 258 | rien |
| Vi | 59 % | 56 % | 2096 | 1024 | confirmé |
| K'Sante | 59 % | 58 % | 2685 | 1282 | confirmé |
| Xin Zhao | 59 % | 59 % | 1446 | 796 | confirmé |
| Urgot | 59 % | 58 % | 3855 | 2118 | confirmé |
| Nocturne | 59 % | 58 % | 1794 | 964 | confirmé |
| Rammus | 58 % | 57 % | 541 | 267 | à surveiller |
| Elise | 58 % | 60 % | 2991 | 1663 | confirmé |
| Morgana | 57 % | 51 % | 1461 | 778 | rien |
| Diana | 57 % | 57 % | 5629 | 2959 | confirmé |
| Swain | 57 % | 54 % | 2391 | 1183 | confirmé |
| Udyr | 56 % | 64 % | 1538 | 806 | confirmé |
| Master Yi | 56 % | 56 % | 4717 | 2386 | confirmé |
| Pantheon | 56 % | 60 % | 6199 | 3697 | confirmé |
| Camille | 56 % | 54 % | 7045 | 3196 | confirmé |
| Nunu & Willump | 56 % | 51 % | 1437 | 683 | rien |
| Neeko | 56 % | 58 % | 968 | 460 | confirmé |
| Rell | 56 % | 61 % | 642 | 299 | confirmé |
| Bel'Veth | 55 % | 51 % | 1637 | 856 | rien |
| Alistar | 55 % | 55 % | 826 | 438 | rien |
| Garen | 55 % | 52 % | 9852 | 4962 | confirmé |
| Kha'Zix | 55 % | 57 % | 5539 | 3056 | confirmé |
| Illaoi | 55 % | 55 % | 3310 | 1650 | confirmé |
| Gwen | 55 % | 52 % | 4593 | 2009 | rien |
| Hecarim | 55 % | 57 % | 3013 | 1689 | confirmé |
| Gragas | 54 % | 51 % | 3820 | 2106 | rien |
| Yone | 54 % | 52 % | 22344 | 11414 | confirmé |
| Darius | 54 % | 55 % | 9549 | 5375 | confirmé |
| Jax | 54 % | 53 % | 6961 | 3828 | confirmé |
| Ambessa | 54 % | 56 % | 4002 | 2001 | confirmé |
| Katarina | 54 % | 54 % | 9605 | 4931 | confirmé |
| Renekton | 54 % | 54 % | 7046 | 3738 | confirmé |
| Vel'Koz | 54 % | 54 % | 3960 | 2237 | confirmé |
| Talon | 54 % | 50 % | 6858 | 3094 | rien |
| Fizz | 54 % | 55 % | 5469 | 2856 | confirmé |
| Aatrox | 54 % | 55 % | 6274 | 3171 | confirmé |
| Maokai | 54 % | 52 % | 845 | 325 | rien |
| Vex | 54 % | 52 % | 3245 | 1557 | rien |
| LeBlanc | 54 % | 55 % | 6904 | 3495 | confirmé |
| Jarvan IV | 54 % | 53 % | 3511 | 1795 | confirmé |
| Zaahen | 54 % | 52 % | 4203 | 1983 | rien |
| Kassadin | 53 % | 52 % | 4209 | 2368 | rien |
| Annie | 53 % | 50 % | 2480 | 1272 | rien |
| Viego | 53 % | 55 % | 4905 | 2663 | confirmé |
| Sett | 53 % | 54 % | 9053 | 4866 | confirmé |
| Olaf | 53 % | 52 % | 4570 | 2357 | confirmé |
| Kayn bleu | 53 % | 53 % | 2100 | 1141 | rien |
| Yasuo | 53 % | 51 % | 13798 | 7123 | rien |
| Anivia | 53 % | 52 % | 2723 | 1228 | rien |
| Trundle | 53 % | 52 % | 2169 | 1155 | rien |
| Malphite | 53 % | 53 % | 7124 | 3511 | confirmé |
| Lillia | 52 % | 51 % | 2419 | 1224 | rien |
| Shaco | 52 % | 52 % | 3652 | 1728 | rien |
| Naafiri | 52 % | 52 % | 2313 | 971 | rien |
| Shen | 52 % | 51 % | 3937 | 2191 | rien |
| Taric | 52 % | 33 % | 256 | 100 | rien |
| Vladimir | 52 % | 52 % | 5859 | 3145 | rien |
| Ornn | 52 % | 50 % | 4014 | 1776 | rien |
| Volibear | 52 % | 52 % | 7381 | 3772 | confirmé |
| Ekko | 51 % | 51 % | 9650 | 5030 | rien |
| Zoe | 51 % | 52 % | 3415 | 1533 | rien |
| Cassiopeia | 51 % | 55 % | 2108 | 1068 | confirmé |
| Locke | 51 % | 52 % | 11057 | 6021 | confirmé |
| Dr. Mundo | 51 % | 45 % | 3296 | 1774 | rien |
| Aurora | 51 % | 48 % | 3970 | 1981 | rien |
| Senna | 51 % | 47 % | 2279 | 1231 | rien |
| Rumble | 50 % | 49 % | 1543 | 753 | rien |
| Riven | 50 % | 48 % | 3454 | 1937 | rien |
| Kled | 50 % | 55 % | 2512 | 1115 | rien |
| Irelia | 50 % | 51 % | 9779 | 4824 | rien |
| Braum | 49 % | 50 % | 654 | 326 | rien |
| Sona | 49 % | 57 % | 657 | 321 | rien |
| Lux | 49 % | 49 % | 5798 | 2960 | rien |
| Yorick | 49 % | 51 % | 2306 | 1260 | rien |
| Qiyana | 49 % | 51 % | 10029 | 4619 | rien |
| Fiora | 49 % | 50 % | 7568 | 3713 | rien |
| Azir | 49 % | 48 % | 1768 | 945 | rien |
| Vayne | 49 % | 48 % | 3500 | 1549 | rien |
| Galio | 48 % | 46 % | 2375 | 1143 | confirmé |
| Akshan | 48 % | 49 % | 4407 | 1858 | rien |
| Rakan | 48 % | 56 % | 606 | 329 | rien |
| Kindred | 48 % | 49 % | 1480 | 730 | rien |
| Heimerdinger | 48 % | 47 % | 1974 | 927 | rien |
| Kennen | 48 % | 53 % | 2823 | 1576 | rien |
| Zed | 48 % | 47 % | 11965 | 5360 | confirmé |
| Mel | 48 % | 47 % | 2545 | 1359 | à surveiller |
| Nidalee | 47 % | 54 % | 1562 | 751 | rien |
| Nami | 47 % | 51 % | 3013 | 1514 | rien |
| Graves | 47 % | 46 % | 2911 | 1633 | confirmé |
| Samira | 47 % | 45 % | 1950 | 1025 | confirmé |
| Brand | 47 % | 51 % | 2042 | 1036 | rien |
| Seraphine | 47 % | 47 % | 2175 | 1094 | rien |
| Lissandra | 46 % | 44 % | 4292 | 2233 | confirmé |
| Karma | 46 % | 46 % | 2055 | 1023 | à surveiller |
| Renata Glasc | 46 % | 47 % | 427 | 221 | rien |
| Viktor | 46 % | 44 % | 7968 | 3742 | confirmé |
| Ahri | 45 % | 48 % | 10930 | 5717 | confirmé |
| Gnar | 45 % | 47 % | 4062 | 1826 | confirmé |
| Twitch | 45 % | 42 % | 4527 | 2361 | confirmé |
| Janna | 45 % | 48 % | 2273 | 1081 | rien |
| Tryndamere | 45 % | 48 % | 4240 | 2090 | rien |
| Kog'Maw | 44 % | 46 % | 2400 | 1281 | confirmé |
| Ryze | 44 % | 46 % | 1519 | 847 | confirmé |
| Kayle | 43 % | 42 % | 3759 | 1974 | confirmé |
| Jayce | 43 % | 42 % | 5774 | 2666 | confirmé |
| Lulu | 43 % | 44 % | 2714 | 1400 | confirmé |
| Hwei | 43 % | 39 % | 4665 | 2245 | confirmé |
| Corki | 42 % | 42 % | 1861 | 903 | confirmé |
| Varus | 42 % | 47 % | 2880 | 1530 | confirmé |
| Zyra | 42 % | 41 % | 2008 | 1005 | confirmé |
| Gangplank | 42 % | 43 % | 6098 | 3390 | confirmé |
| Kai'Sa | 42 % | 43 % | 8714 | 4328 | confirmé |
| Xerath | 42 % | 40 % | 4932 | 2583 | confirmé |
| Veigar | 41 % | 43 % | 3499 | 1618 | confirmé |
| Aphelios | 41 % | 43 % | 3346 | 1727 | confirmé |
| Orianna | 41 % | 42 % | 2857 | 1412 | confirmé |
| Teemo | 41 % | 42 % | 6127 | 3321 | confirmé |
| Syndra | 41 % | 40 % | 9113 | 4734 | confirmé |
| Xayah | 41 % | 40 % | 2837 | 1431 | confirmé |
| Quinn | 40 % | 44 % | 2667 | 1359 | confirmé |
| Milio | 40 % | 39 % | 1421 | 663 | confirmé |
| Ezreal | 40 % | 41 % | 4486 | 2107 | confirmé |
| Aurelion Sol | 40 % | 36 % | 1945 | 938 | confirmé |
| Tristana | 40 % | 40 % | 6357 | 3176 | confirmé |
| Malzahar | 39 % | 41 % | 4181 | 2314 | confirmé |
| Ivern | 39 % | 46 % | 706 | 274 | rien |
| Sion | 39 % | 37 % | 4524 | 2086 | confirmé |
| Lucian | 38 % | 37 % | 3698 | 1812 | confirmé |
| Nilah | 38 % | 36 % | 453 | 245 | confirmé |
| Zilean | 38 % | 37 % | 1311 | 655 | confirmé |
| Draven | 37 % | 38 % | 3194 | 1570 | confirmé |
| Kalista | 37 % | 35 % | 2032 | 1000 | confirmé |
| Singed | 36 % | 38 % | 2956 | 1320 | confirmé |
| Taliyah | 36 % | 36 % | 2653 | 1340 | confirmé |
| Zeri | 35 % | 31 % | 1977 | 1081 | confirmé |
| Jhin | 35 % | 34 % | 7336 | 3819 | confirmé |
| Ziggs | 35 % | 34 % | 1440 | 720 | confirmé |
| Smolder | 35 % | 32 % | 2853 | 1547 | confirmé |
| Miss Fortune | 34 % | 32 % | 3529 | 1792 | confirmé |
| Caitlyn | 34 % | 34 % | 6107 | 3250 | confirmé |
| Yunara | 34 % | 34 % | 4410 | 2086 | confirmé |
| Ashe | 33 % | 33 % | 2718 | 1480 | confirmé |
| Soraka | 32 % | 27 % | 1435 | 658 | confirmé |
| Twisted Fate | 31 % | 32 % | 3007 | 1424 | confirmé |
| Jinx | 31 % | 30 % | 6386 | 3307 | confirmé |
| Karthus | 30 % | 30 % | 2447 | 1071 | confirmé |
| Sivir | 29 % | 26 % | 2134 | 1026 | confirmé |

