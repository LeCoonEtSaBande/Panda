# Proposition de catégories de champions (23/10/2026)

Classification **par champion, tous postes confondus**, faite uniquement sur la façon de jouer : aucune victoire n'entre dedans. Elle sert de base à un second catalogue. Le catalogue actuel n'est pas modifié.

- **Données** : les 15 249 parties de l'échantillon figé, parties de 15 min ou plus.
- **Champions classés** : 174, tous ceux qui ont au moins 100 parties, tous postes réunis.
- **Couverture du pool** : tout le pool est classé, y compris Dr. Mundo, Maokai, Morgana et Urgot, grâce à leurs parties aux autres postes.
- **Script** : `analyse/classification.py`, appelé par le rapport.
- **Fichiers** (`analyse/resultats/`) :
  - `classification_champions.csv` : groupe, netteté, groupe le plus proche, tous les indicateurs ;
  - `classification_groupes.csv` : portrait de chaque groupe et stabilité de chaque nombre de groupes ;
  - `classification_axes.csv` : les grands axes ;
  - `classification_catalogue.csv` : croisement avec le catalogue.

## Ce qui est mesuré

Chaque indicateur est comparé à la moyenne du poste où le champion est joué. Un support fait moins de dégâts qu'un adc, et ce n'est pas un style. Les indicateurs sont ensuite moyennés sur ses postes.

| Famille | Indicateurs |
|---|---|
| Dégâts faits | volume par minute, part des dégâts de l'équipe, dégâts par kill ou assistance (beaucoup de dégâts sans kill = poke), part faite avant 15 min |
| Dégâts encaissés | volume, part de l'équipe, part atténuée (vraie résistance), soin sur soi |
| Kills | kills, morts, assistances, part des takedowns où il porte le coup final, solo kills, kills « burst » (presque seul, victime vidée d'un coup), kills près d'une tour ennemie |
| CC | temps de CC, nombre d'immobilisations, part de CC dur dans le CC total, immobilisations suivies d'un kill allié |
| Avant ou après | dans chaque combat reconstitué (kills à moins de 15 s et 3 000 unités) : s'il est sur le premier kill (il ouvre), sur les kills de fin (il nettoie), s'il meurt en premier, s'il tue en réponse à un mort allié, s'il tue en infériorité numérique |
| Soins et boucliers | soins et boucliers sur les alliés, alliés sauvés de la mort |
| Skillshots | touchés et esquivés |
| Split | dégâts aux bâtiments, distance à ses coéquipiers |

**Limite sur « CC avant ou après les dégâts ».** Riot ne donne pas l'ordre exact des sorts. La colonne « avant ou après » en est l'approximation : est-ce qu'il agit au début du combat ou à la fin, est-ce que ses CC mènent à un kill allié. Pour avoir le vrai ordre, il faudrait collecter le détail des dégâts reçus par chaque victime (qui, quel sort, dans quel ordre). C'est un changement de `collecte.py` à décider.

Le **type de dégâts** (physique, magique, vrai) est gardé **à part**, comme une étiquette AD / AP / mixte. Sinon, il coupe tout en deux (les AP d'un côté, les AD de l'autre) et cache la façon de jouer.

## Résultat : 7 groupes

Les champions forment un continuum : les groupes ne sont pas des îlots bien séparés. Mais ils sont **stables**. En retirant les parties au hasard 20 fois, on retrouve les mêmes groupes (accord de 0,70 sur 1).

| Nombre de groupes | Stabilité (1 = toujours les mêmes) |
|---|---|
| 4 ou 5 | environ 0,8 |
| 6 et 7 | environ 0,7 |
| 8 et plus | 0,6 ou moins |

Au-delà de 7, les groupes changent selon les parties tirées : on découpe du bruit.

Une astérisque (*) marque un champion à cheval entre deux groupes, avec le groupe voisin entre parenthèses. C'est le cas d'environ 7 % des champions.

### 1. Enchanteurs (10)
- **Profil** : soignent, mettent des boucliers, sauvent des alliés de la mort. Font très peu de dégâts et meurent peu. Leurs dégâts sont faits tôt.
- **Champions** : Soraka, Milio, Lulu, Ivern, Yuumi, Zilean, Janna, Nami, Orianna, Karma* (→ Contrôle à distance).
- **Catalogue** : correspond au « Disengage ». C'est la catégorie la plus nette.

### 2. Tanks protecteurs (23)
- **Profil** : encaissent en résistant (beaucoup de dégâts atténués), immobilisent souvent, font beaucoup d'assistances et très peu de coups finaux ou de dégâts.
- **Champions** : Galio, Sejuani, Braum, Shen, Taric, Ornn, K'Sante, Rammus, Nunu & Willump, Skarner, Amumu, Rakan, Alistar, Malphite, Zac, Thresh, Rell, Singed, Nautilus, Renata Glasc, Twisted Fate, Jarvan IV, Leona* (→ Combattants à contrôle).
- **Catalogue** : mélange « Engage » (12) et « Counter-engage » (8). Les données ne séparent pas ces deux styles chez les tanks.

### 3. Combattants à contrôle (31)
- **Profil** : encaissent une grosse part des dégâts de l'équipe, se soignent eux-mêmes, et leurs CC mènent à des kills alliés.
- **Champions** : Cho'Gath, Aatrox, Swain, Zaahen, Xin Zhao, Kled, Tahm Kench, Udyr, Rek'Sai, Xayah, Hecarim, Ryze, Lillia, Maokai, Sylas, Shyvana, Blitzcrank, Nocturne, Poppy, Kayn rouge, Lee Sin, Anivia, Cassiopeia, Sion, Bard, Aphelios, Vi, Dr. Mundo* (→ Tueurs autonomes), Wukong* (→ Plongeurs), Ekko* (→ Tueurs autonomes), Gragas* (→ Contrôle à distance).
- **Catalogue** : surtout « Engage » (17). C'est le groupe le plus flou : il disparaît si on passe à 6 groupes.

### 4. Plongeurs (31)
- **Profil** : ouvrent les combats (premier kill), portent le coup final, font des solo kills, tuent sous la tour ennemie, s'éloignent de l'équipe et meurent souvent. Peu d'assistances.
- **Champions** : Draven, Volibear, Yone, Yasuo, Jax, Irelia, Samira, Elise, Pyke, Diana, Briar, Tristana, Camille, Trundle, Kalista, Fizz, Vayne, Sett, Darius, Pantheon, Rengar, Mordekaiser, Tryndamere, Qiyana, Viego, Bel'Veth, Nilah, Warwick, Renekton, Garen* (→ Tueurs autonomes), Ambessa* (→ Combattants à contrôle).
- **Dégâts** : 24 AD sur 31.
- **Catalogue** : surtout « Engage » (14), avec des « Pick ». Mélange de bruisers et d'adc agressifs : ce qui les réunit, c'est d'aller chercher le combat.

### 5. Tueurs autonomes (31)
- **Profil** : portent le coup final, tuent en burst presque seuls, tuent même en infériorité numérique, jouent loin de l'équipe (split) et se soignent. Presque **aucun CC**.
- **Champions** : Corki, Gwen, Akshan, Talon, Kassadin, Zed, Naafiri, Kai'Sa, Katarina, Ezreal, Olaf, Akali, Vladimir, Kha'Zix, Twitch, Miss Fortune, Yorick, Zeri, Nidalee, Illaoi, Lucian, Yunara, Locke, Graves, Kayle, Master Yi, Nasus, Kindred, Sivir, Kayn bleu, Fiora.
- **Catalogue** : « Pick » (11) et beaucoup de champions sans style (11). Assassins et hypercarries ensemble : des champions qui tuent sans dépendre d'un CC allié.

### 6. Contrôle à distance (36)
- **Profil** : beaucoup de CC qui mène à des kills, des dégâts corrects, encaissent très peu, restent groupés. Meurent souvent en premier quand ils sont attrapés.
- **Champions** : Syndra, Taliyah, Veigar, Zoe, Lux, Kennen, Vex, Jayce, Quinn, Ziggs, Gnar, Seraphine, Evelynn, Malzahar, Ahri, Ashe, Mel, Azir, Annie, Shaco, Varus, Hwei, Urgot, Jinx, Viktor, Xerath, Aurelion Sol, Morgana, Caitlyn, Fiddlesticks, Neeko, Jhin, Sona* (→ Combattants à contrôle), Riven* (→ Combattants à contrôle), Lissandra* (→ Combattants à contrôle), LeBlanc* (→ Plongeurs).
- **Catalogue** : surtout « Poke » (19). Mages de contrôle et adc « utilitaires » (Ashe, Jhin, Varus, Caitlyn, Jinx).

### 7. Artilleurs (12)
- **Profil** : énormes dégâts qui finissent rarement en kill. Agissent **après** le début du combat (en réponse à un mort allié, sur les kills de fin), presque jamais en ouverture. Leurs dégâts viennent tard dans la partie. Peu de résistance.
- **Champions** : Karthus, Brand, Teemo, Zyra, Kog'Maw, Heimerdinger, Vel'Koz, Rumble, Gangplank, Aurora, Senna, Smolder.
- **Catalogue** : « Poke » (11 sur 12). Le catalogue est bien retrouvé ici.

## Comparaison avec le catalogue

- **Retrouvés** : Enchanteurs = Disengage ; Artilleurs = Poke ; Tanks protecteurs et Combattants à contrôle = Engage.
- **Nouveaux** :
  - les **Tueurs autonomes** (assassins et hypercarries sans CC) ;
  - les **Plongeurs** (ceux qui ouvrent le combat et tuent seuls) ;
  - le **Contrôle à distance**, qui regroupe mages de contrôle et adc utilitaires.
- **Introuvable : le Counter-engage.** Ses champions se répartissent entre les tanks (8), les combattants (4) et le contrôle à distance (3). Aucun indicateur ne les distingue. Soit les données ne le captent pas, soit c'est une affaire de timing des sorts (voir la limite sur le CC).
- **Accord global** avec le style principal du catalogue : faible, 0,14 sur 1, où 0 = hasard. Les deux classifications se recoupent sur les extrêmes (enchanteurs, artilleurs, tanks), pas au milieu.

## Ton pool

| Champion | Parties (postes) | Groupe proposé | Netteté | Groupe le plus proche | Catalogue |
|---|---|---|---|---|---|
| Ivern | 308 (jgl 80 %) | Enchanteurs | très net | Tanks protecteurs | Disengage |
| Skarner | 182 (jgl 86 %) | Tanks protecteurs | très net | Combattants à contrôle | Counter-engage |
| Maokai | 365 (sup 59 %, top 22 %, jgl 20 %) | Combattants à contrôle | net | Tanks protecteurs | Counter-engage |
| Kayn rouge | 560 (jgl 95 %) | Combattants à contrôle | net | Plongeurs | Engage |
| Dr. Mundo | 678 (top 87 %) | Combattants à contrôle | à cheval | Tueurs autonomes | sans style |
| Viego | 1 263 (jgl) | Plongeurs | net | Contrôle à distance | Pick |
| Kayn bleu | 421 (jgl) | Tueurs autonomes | moyen | Plongeurs | Pick |
| Fiddlesticks | 479 (jgl 75 %) | Contrôle à distance | net | Combattants à contrôle | Counter-engage |
| Morgana | 610 (sup 86 %) | Contrôle à distance | net | Artilleurs | Disengage |
| Urgot | 509 (top) | Contrôle à distance | très net | Combattants à contrôle | Engage |

Ton pool couvre 5 groupes sur 7. Il n'a aucun Artilleur. Il n'a aucun Tueur autonome à part Kayn bleu.

## Prochaines étapes

1. **Toi** : regarde si ces groupes te parlent. Tu peux les renommer, en fusionner, ou déplacer des champions à cheval. C'est la base du second catalogue.
2. **Ensuite** : mesurer l'impact de ces groupes en draft (compo contre compo, jungler selon la compo), avec des hypothèses fixées avant de regarder et un contrôle sur les parties qui arrivent.
3. **Option** : collecter le détail des dégâts reçus par victime, pour mesurer vraiment « CC avant ou après les dégâts » et retenter de trouver le counter-engage.
