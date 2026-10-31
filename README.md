# Panda — branche `assistant` : l'Assistant Draft

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Une page HTML autonome (`Assistant Draft - DL - <date>.html`, à la racine de la branche `assistant`) : elle s'ouvre sans connexion, depuis le bureau.

**Télécharger** : sur GitHub, branche `assistant`, cliquer sur le fichier, puis sur le bouton « Download raw file » (flèche vers le bas, en haut à droite du fichier). Le fichier fait environ 4 Mo : GitHub ne l'affiche pas, et un « Enregistrer sous » de la page GitHub donne une page vide.

**Régénérer** : bouton « 5 · Générer l'assistant Draft » (sur `main`). À lancer après un passage Lolalytics (nouveau patch) ou quand des collectes ont ajouté des parties.

## Ce qu'elle fait

- **Mon équipe à gauche**, dans l'ordre de la draft : un poste (un seul de chaque) et un champion par ligne.
- **L'équipe adverse à droite** : le champion seulement ; le poste est deviné (part de ses parties à chaque poste, Lolalytics) et se change à la main.
- Saisie : quelques lettres suffisent, la liste propose les champions correspondants (sans accent ni majuscule). Entrée ou Tab valide.
- **En haut**, à droite des onglets : la version de l'assistant (V 2.1, 30/10/2026) et le nombre de parties de nos analyses (au survol : le patch Lolalytics et la date du calcul).
- **Profils** (onglet Profils) : une personne par profil, avec les postes qu'elle joue et ses champions à chaque poste. En haut de la draft : le profil et le poste joué (« Je joue »).
  Au premier lancement (ou si le navigateur a tout oublié), deux profils de départ : **Lee** (jungle : Briar, Darius, Dr. Mundo, Fiddlesticks, Gwen, Ivern, Kayn bleu, Viego, Lee Sin) et **All** (jungle, tous les champions du poste). Des profils déjà enregistrés dans le navigateur ne sont pas touchés.
- **Manuel** (onglet Manuel, 30/10/2026) : « Le petit manuel du forestier », l'arbre de décision du jungler, écrit par le propriétaire : les teamfights à éviter, puis le plan en early (full clear → botlane, priorité ?, gank possible ?, drake si gratuit, reset), en mid (farmer à côté des alliés les plus forts, ganks seulement sur free kills en powerspike ou cibles isolées / low HP) et en late (jouer autour des objectifs ou à l'opposé). Texte fixe, sans calcul.
- **Mémoire** : la page retient, dans le navigateur, les profils, le dernier profil, le dernier poste, la draft en cours et la case « tous les champions ». À la réouverture, tout est comme à la dernière utilisation (même navigateur ; avec Chrome ou Edge, une nouvelle version téléchargée retrouve aussi les profils ; avec Firefox, l'ouvrir depuis le même dossier que l'ancienne).
- **Pendant la draft**, la page ne montre que les deux équipes et **quel champion prendre** ; tout le reste vient au récapitulatif.
- **Chance de gagner** (27/10/2026) : pour chaque candidat, en grand, ta chance de gagner la partie avec lui, d'après toute la draft connue (force du patch, contres et synergie de Lolalytics, avec les poids appris sur nos parties, tas A), et dessous ce qu'il ajoute en points par rapport à la draft sans ton pick ; les candidats sont classés là-dessus. Vérifiée sur les 18 086 parties du tas B, jamais vues : une draft annoncée à 57 % y gagne 56 % du temps, à 1 point près dans chaque tranche. La draft ne décide pas tout : la plupart des parties sont annoncées entre 40 et 60 %, et le pronostic trouve le bon gagnant 56 fois sur 100. Elle est aussi en tête du plan, au récapitulatif.
- **Quel champion prendre** à son poste (son pool, ou tous les champions du poste) : force du patch, contre son adversaire direct, contre le reste de leur équipe (à moitié), **synergie avec chacun de ses alliés déjà choisis** (Lolalytics, comptée à 52 % : le poids mesuré sur nos parties, vérifié sur B le 27/10/2026), mix de dégâts de l'équipe, et le 1 contre 1 à or égal contre son adversaire direct. Adversaire direct inconnu : moyenne sur ses champions probables, « sûr en blind » ou non, et les champions à éviter s'ils peuvent encore être pris.
- **Dégâts** sous chaque équipe, en trois parts : **AD** (physiques), **AP** (magiques) et **Bruts** (ni l'armure ni la résistance magique ne les réduisent), d'après les dégâts moyens de chaque champion à son poste, et l'alerte quand une équipe est presque toute AD (moins de 20 % d'AP) ou toute AP (plus de 70 %) : −3 points, compté dans le score des candidats dès que 4 champions sont connus. C'est un choix du propriétaire (26/10/2026) : sur nos parties, l'effet mesuré (−4 à −5 points) n'est qu'« à surveiller » sur B. Le tempo de chaque équipe (plutôt early ou late).
- **Tes duels** : le 1 contre 1 de ton champion contre **chacun des 5 champions adverses**, chacun avec l'or et le niveau habituels de son poste (un support a moins d'or qu'un top : c'est compté), à 8 et à 25 min, avec le sens de l'évolution (mieux en mieux en vert, stable en gris, moins en moins en rouge). Vert à 55 % ou plus, rouge à 45 % ou moins. « Approximatif » quand la force en duel d'un des deux n'est pas vérifiée sur nos parties (tas B) : il compte alors comme un champion moyen de son poste. Au récapitulatif, sous le plan ; à 8 et 25 min aussi dans « Quel champion prendre ». En bas de chaque carte, le nombre de duels de l'adversaire mesurés dans nos parties ; sous les cartes, les tiens.
- Sous les duels, quelques lignes : en jungle, lanes avec ou sans prio, meilleure lane à ganker, lane exposée ; en lane, sa chance d'être devant, le risque de gank adverse, l'aide de son jungler.
- **Valider la compo** : quand les 10 champions sont entrés. La page passe au récapitulatif, dans cet ordre (« Nouvelle draft » repart de zéro pour la partie suivante) :
  1. À gauche, **le plan** : la chance de victoire d'après la draft, le tempo (early ou late, et la chance de gagner avant 20 min et après 35 min), les dégâts adverses et ce qu'il faut surveiller : leurs ultimes qui changent un combat (contrôle fort, ou relus à la main dans `analyse/catalogues/ultimes_a_surveiller.csv` : combinaison avec un passif comme la Rafale de Fiddlesticks et sa Terreur, grosse zone de dégâts, repoussement) et ceux qui sauvent un allié. Dessous, **tes duels** et les lignes sur les ganks. À droite, **la carte à 15 minutes** : chaque lane est une jauge, bleue depuis ta base (« Nous »), rouge depuis la leur (« Eux ») ; le point blanc montre jusqu'où la lane pousse à 15 min (sa chance d'être devant). Ton équipe est toujours en bleu : côté rouge, ta base est simplement en haut à droite. Dessous, la jauge de la jungle.
  2. **Atteindre leurs cibles** et **Protéger vos cibles** (voir plus bas) ; le bloc qui correspond à ton rôle vient en premier (un enchanteur ou un bloqueur commence par protéger).
  3. **Les rôles** : les deux équipes en tableau horizontal (la leur en haut). Au-dessus de chaque nom, son étiquette : 🎯 **cible** (Carry, Enchanteur, ou champion fragile), 💀 **menace** pour vos cibles (Assassin, Plongeur, Attrapeur), 💚 **tank**, 🛡️ **protecteur** (Bloqueur) ; deux au plus. Sous le nom, ses rôles, chacun avec son émoticône : 🎯 Carry, ✨ Enchanteur, 🗡️ Assassin, 🤿 Plongeur, 🪝 Attrapeur, 💚 Tank, 🛡️ Bloqueur, ⚔️ Dueliste, ♜ Splitpusher, 🧑‍🤝‍🧑 Teamfighter, et HP (un demi-cœur vert : encaisse beaucoup sans être un tank). Un champion garde tous ses styles dans le catalogue ; l'assistant affiche Carry, Tank et HP s'il l'est, plus ses **deux autres styles principaux** (les mieux notés). Les cibles, menaces et protecteurs se décident sur tous ses types.
- **Un poste sans champion dans le profil** = tous les champions de ce poste sont proposés.
- **Seulement ce qui a passé sa vérification** : force du patch et contres (Lolalytics, vérifiés aussi sur nos parties) ; pour nos parties (or à 15 min par lane, ganks, early/late, mix de dégâts, duels, types), appris sur le tas A et affiché seulement si c'est vérifié sur le tas B, recalculé à chaque génération sur toutes les parties. Les effets du recuit n'entrent que confirmés sur C.

### La logique des deux blocs

Les **cibles** : les carrys, les enchanteurs et les autres champions **fragiles** (ceux qui encaissent le moins par minute, d'après nos parties : la plupart des mages, des ADC et des assassins).

**Atteindre leurs cibles** (vu par exemple de Darius, qui veut prendre un reset sur une cible fragile) :
- en haut, **leurs cibles**, chacune avec **sa fuite** (sorts de déplacement), ce qui **la protège elle-même** (bouclier, invulnérabilité, mur contre les projectiles…) et **ses contrôles** ;
- en dessous, **qui les protège** : les bloqueurs et enchanteurs de leur équipe, avec leurs contrôles et leurs protections ; le support est « à côté » de son ADC ;
- la lecture, en deux consignes : **va sur** la cible la plus accessible (le moins d'obstacles : fuites, protections et contrôles, un protecteur à côté compte double), avec ses fuites, ses protections et les contrôles auxquels faire attention ; **évite** la plus protégée **tant que** ceux qui peuvent la sauver (son support à côté en bot, et ceux qui ont un sort pour protéger un allié) ont encore ces sorts, nommés.

**Protéger vos cibles** (vu par exemple d'Ivern, qui reste près de son carry) :
- en haut, **vos cibles**, chacune avec sa fuite, ce qui la protège elle-même et ses contrôles ;
- en dessous, **qui les protège** : vos bloqueurs et enchanteurs avec leurs contrôles et leurs protections, et les boucliers et soins pour les alliés des autres ;
- puis **leurs menaces** (assassin, puis plongeur, puis attrapeur) : **comment il arrive** (sa mobilité) ou **comment il attrape** (ses contrôles) ;
- la lecture : si c'est toi la cible la plus fragile, **attention** (ne te mets pas en avant) ; puis **protège** (si tu es protecteur) ou **reste près de** la cible la plus fragile qui n'est pas toi (le moins de fuites et de protections ; un carry d'abord à égalité), et **garde** ton meilleur contrôle de base (Q, W ou E avant l'ultime, le plus fort d'abord) pour la menace principale, avec le sort par lequel elle arrive.

Les types viennent des choix du propriétaire, classés par les notes de nos parties (branche `analyse`, `analyse/types/`), les sorts de Data Dragon (`analyse/catalogues/sorts.csv`). Ce sont des descriptions des champions : elles ne prédisent pas la victoire, elles n'ont donc pas de tas C.

## La surcouche en jeu (lancée par le lien client)

Pendant une partie, le lien client ouvre une petite fenêtre au bord droit de l'écran (`assistant/surcouche.py`), par-dessus le jeu. Elle disparaît hors partie. Le jeu doit être en **« Fenêtré sans bordure »** (une fenêtre ne peut pas passer par-dessus le plein écran). On la déplace en tirant son bandeau du haut ; elle retient sa place.

- **En haut** : le prochain dragon (le Dragon ancien après une âme) et le Héraut, avec leur compte à rebours ; **bip et texte orange 1 min 30 avant**. Tout est lu par le jeu lui-même (dragons et Héraut tués, par toi ou par eux) : rien à faire.
- **Or des objets** : total de chaque équipe, puis, pour chaque adversaire, l'or dépensé dans ses objets (prix Data Dragon, consommables exclus), comme dans le tableau des scores.
- **Saut éclair (F)** de chaque adversaire : **clic quand il flash**, le compte à rebours démarre (reclic : remis à zéro). La recharge tient compte de ses Bottes de lucidité ioniennes ou de sa Lucidité pourpre (lues dans ses objets, même achetées après) et de Perspicacité cosmique, **supposée dès qu'il a l'arbre Inspiration** (marquée ✦ : le jeu ne donne pas les petites runes des autres ; le sort revient au pire un peu plus tôt qu'annoncé). **On retire 10 secondes** : le temps de voir le flash et de cliquer.
- **Sablier de Zhonya (Z)** : seulement chez ceux qui l'ont ; même principe (Perspicacité cosmique comptée, 10 secondes retirées).
- **Valeurs du patch** (recharges, hâte, timers, prix) : `lolalytics/valeurs_jeu.json` de la branche `scraping`, refait à chaque passage du bouton « 2 · Lolalytics » et téléchargé au lancement (copie gardée à côté du programme pour jouer sans connexion ; à défaut, valeurs vérifiées le 31/10/2026).
- Source : l'interface officielle de Riot pendant une partie (Live Client Data API, sur ton PC seulement). Rien n'est lu dans la mémoire du jeu, rien n'est envoyé au jeu. Les timers d'ultimes ennemis sont interdits par Riot depuis 2025 : il n'y en a pas. Les timers de sorts d'invocateur manuels sont tolérés à ce jour mais à l'étude chez Riot ; le Zhonya est un timer d'objet manuel, même zone.
- Sans surcouche : lancer le lien client avec `--sans-surcouche`.

## Voir les picks du client League automatiquement

- Sous Windows : télécharger `Assistant Draft - Lien client.exe` (même endroit que la page, bouton « Download raw file »), le mettre dans le même dossier que la page et le lancer avant de jouer. Une petite fenêtre reste ouverte ; elle ouvre la page, puis la surcouche en jeu pendant les parties.
- Sur Mac, ou si Python est installé : `python3 assistant/lien_client.py`.
- **Version du jeu** : en haut à droite, la page compare la version de ton jeu (lue dans le client) au patch de l'assistant : « Patch 16.21 à jour » en vert, ou, en orange, « Jeu en 16.22, assistant en 16.21 : à mettre à jour » (relancer « Récupérer les stats Lolalytics du patch » puis « Générer l'assistant Draft », et retélécharger la page). Sans lien client, seul le patch de l'assistant est affiché.
- **Côté bleu ou rouge** : lu dans le client pendant la sélection ; sur la carte du récapitulatif, ta base passe en haut à droite côté rouge (ton équipe reste en bleu) (la case « on est côté rouge » reste modifiable à la main).
- La page affiche en haut « Client relié » ; pendant la sélection, elle remplit seule les deux équipes, ton poste et les bans (exclus des propositions). Les **pré-picks de ton équipe** (annonce avant son tour, ou survol pendant son tour) comptent comme des picks tant que le vrai n'est pas verrouillé ; ils s'affichent en pointillés. Ceux de l'équipe adverse ne sont jamais envoyés par le client. Ton propre survol s'affiche dans « Comment jouer ». Elle passe au récapitulatif à la fin de la sélection et repart de zéro à la sélection suivante. Ce que tu tapes dans une case encore vide est gardé.
- Le lien ne fait que **lire** ce que ton client affiche déjà (champions, postes, bans, ton côté, la version du jeu) : jamais le nom ni les stats des autres joueurs, jamais d'action à ta place (règles de Riot pour les applications tierces). L'interface locale du client n'est pas officiellement prise en charge par Riot : elle peut changer avec un patch.
- Windows peut avertir au premier lancement (programme non signé) : « Informations complémentaires » puis « Exécuter quand même ».

## D'où viennent les chiffres

| Chiffre | Source |
|---|---|
| Force du patch, contres, synergie avec les alliés, matchups de lane, poste deviné | Lolalytics, Platine et plus, tous serveurs (branche `scraping`, `lolalytics/<patch>/`) |
| Or à 15 min, chance d'être devant | nos parties Émeraude-Diamant avec timeline (`analyse/contres`, `analyse/lanes/dynamique.py`) |
| Ganks réussis | nos parties (`analyse/lanes/ganks.py`) |
| Dégâts par type, early / late | Lolalytics (page de chaque champion, `profils.csv`), sinon nos parties ; effets vérifiés sur nos parties (`analyse/lanes/duree_degats.py`) |
| 1 contre 1 | nos parties, 515 000 duels (`analyse/lanes/duels.py`), chacun avec l'or habituel de son poste ; forces vérifiées sur B seulement |
| Types des champions | choix du propriétaire (`analyse/types/validations.csv`), classés par les notes de nos parties (`analyse/types/classer.py`) ; « fragile » d'après les dégâts encaissés par minute |
| Sorts (contrôle, protection, déplacement), identifiants des champions | Data Dragon (bouton « Mettre à jour le catalogue (Data Dragon) », `analyse/catalogues/`), corrigés à la main |

`construire.py` assemble tout dans `modele.html`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `Assistant Draft - DL - <date>.html` | La page à télécharger. Un seul fichier à la fois : l'ancien est retiré à chaque génération. |
| `assistant/construire.py` | Assemble les données (Lolalytics, export des analyses avec les types et les sorts) dans `modele.html`. |
| `assistant/modele.html` | La page elle-même (mise en page et calculs), sans données. |
| `assistant/lien_client.py`, `Assistant Draft - Lien client.exe` | Le lien avec le client League (lecture de la sélection) ; l'exécutable Windows est reconstruit par le workflow quand le code change. |
| `assistant/tests/` | Tests du lien client : `python3 -m unittest discover -s assistant/tests`. |

En local : récupérer Lolalytics (branche `scraping`) et l'export des analyses (branche `analyse`, `analyse/export/assistant_donnees.json`), puis
`python3 assistant/construire.py --lolalytics <dossier du patch> --export <assistant_donnees.json>`.
