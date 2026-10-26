# Panda — branche `assistant` : l'Assistant Draft

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Une page HTML autonome (`Assistant Draft - DL - <date>.html`, à la racine de la branche `assistant`) : elle s'ouvre sans connexion, depuis le bureau.

**Télécharger** : sur GitHub, branche `assistant`, cliquer sur le fichier, puis sur le bouton « Download raw file » (flèche vers le bas, en haut à droite du fichier). Le fichier fait environ 2 Mo : GitHub ne l'affiche pas, et un « Enregistrer sous » de la page GitHub donne une page vide.

**Régénérer** : bouton « 5 · Générer l'assistant Draft » (sur `main`). À lancer après un passage Lolalytics (nouveau patch) ou quand des collectes ont ajouté des parties.

## Ce qu'elle fait

- **Mon équipe à gauche**, dans l'ordre de la draft : un poste (un seul de chaque) et un champion par ligne.
- **L'équipe adverse à droite** : le champion seulement ; le poste est deviné (part de ses parties à chaque poste, Lolalytics) et se change à la main.
- Saisie : quelques lettres suffisent, la liste propose les champions correspondants (sans accent ni majuscule). Entrée ou Tab valide.
- **Profils** (onglet Profils) : une personne par profil, avec les postes qu'elle joue et ses champions à chaque poste. En haut de la draft : le profil et le poste joué (« Je joue »).
- **Mémoire** : la page retient, dans le navigateur, les profils, le dernier profil, le dernier poste, la draft en cours et la case « tous les champions ». À la réouverture, tout est comme à la dernière utilisation (même navigateur ; avec Chrome ou Edge, une nouvelle version téléchargée retrouve aussi les profils ; avec Firefox, l'ouvrir depuis le même dossier que l'ancienne).
- **Quel champion prendre** à son poste (son pool, ou tous les champions du poste) : force du patch, contre son adversaire direct, contre le reste de leur équipe (à moitié), mix de dégâts de l'équipe, et le 1 contre 1 à or égal contre son adversaire direct. Adversaire direct inconnu : moyenne sur ses champions probables, « sûr en blind » ou non, et les champions à éviter s'ils peuvent encore être pris.
- **Dégâts** sous chaque équipe, en trois parts : **AD** (physiques), **AP** (magiques) et **Bruts** (ni l'armure ni la résistance magique ne les réduisent), d'après les dégâts moyens de chaque champion à son poste, et l'alerte quand une équipe est presque toute physique ou toute magique (elle gagne moins dans nos parties, à force égale ; compté dans le score des candidats dès que 4 champions sont connus). Le tempo de chaque équipe (plutôt early ou late).
- **Selon la durée** : la chance de gagner avant 20 min, à 20-25, 25-30, 30-35 et après 35 min, due au seul tempo des deux compos, avec le conseil qui va avec (finir vite ou temporiser).
- **Tes duels** : le 1 contre 1 de ton champion contre **chacun des 5 champions adverses**, chacun avec l'or et le niveau habituels de son poste (un support a moins d'or qu'un top : c'est compté), à 8, 15 et 25 min, avec le sens de l'évolution (de mieux en mieux, de moins en moins). Vert à 55 % ou plus, rouge à 45 % ou moins. « Approximatif » quand la force en duel d'un des deux n'est pas vérifiée sur nos parties (tas B) : il compte alors comme un champion moyen de son poste. Dans « Comment jouer » et dans le récapitulatif.
- **Comment jouer** avec le champion recommandé (ou le sien, ou celui sur lequel on clique) : pour chaque lane, l'écart d'or attendu à 15 min et la chance d'être devant ; la chance que le gank de son jungler finisse en kill avant 15 min, et celle du jungler adverse ; le matchup Lolalytics. En jungle : lanes avec ou sans prio, meilleure lane à ganker, lane exposée, quand envahir (seulement si c'est confirmé pour ce type de jungler). En lane : sa chance d'être devant, le risque de gank adverse, l'aide de son jungler.

- **Valider la compo** : quand les 10 champions sont entrés. La page passe au récapitulatif, dans cet ordre (« Nouvelle draft » repart de zéro pour la partie suivante) :
  1. **Le plan** en quelques lignes : tempo, lanes devant ou derrière, où ganker et quand envahir (ou ta lane et le risque de gank), dégâts adverses, leurs ultimes qui contrôlent.
  2. **Qui est qui** : les deux équipes en tableau horizontal (la leur en haut). Au-dessus de chaque nom, son étiquette : 🎯 **cible prioritaire** (Carry, Enchanteur), 💀 **menace** pour vos cibles (Assassin, Plongeur, Attrapeur), 💚 **tank**, 🛡️ **protecteur** (Bloqueur) ; deux au plus. Puis ses types : 🎯 Carry, ✨ Enchanteur, 🗡️ Assassin, 🤿 Plongeur, 🪝 Attrapeur, 💚 Tank, 🛡️ Bloqueur, ⚔️ Dueliste, ♜ Splitpusher, 👥 Teamfighter. Puis ses sorts, **chacun rangé une seule fois** : tout le monde a ses **contrôles** ; une cible a en plus sa **protection** et sa **fuite** ; un assassin ou un plongeur, sa **mobilité**.
  3. **Atteindre leurs cibles** et **Protéger vos cibles** (voir plus bas) ; le bloc qui correspond à ton rôle vient en premier (un enchanteur ou un bloqueur commence par protéger).
  4. **Sur la carte** : chaque lane est une jauge, bleue depuis ta base, rouge depuis la leur ; le point blanc montre jusqu'où la lane pousse à 15 min (sa chance d'être devant). Ton équipe est toujours en bleu : côté rouge, ta base est simplement en haut à droite. Dessous, la jauge de la jungle et les ganks réussis avant 15 min, pour ton jungler et le leur, sur chaque lane.
  5. **Tes duels** contre chacun des 5 adversaires.
- **Un poste sans champion dans le profil** = tous les champions de ce poste sont proposés.
- **Seulement ce qui a passé sa vérification** : force du patch et contres (Lolalytics) ; confirmés sur nos parties jamais vues (tas C) : or à 15 min par lane, ganks, envahir à 15 min pour les junglers Engage (tanks et bruisers, catégories de l'ancien catalogue), early/late, mix de dégâts ; vérifiés sur le tas B : duels et types. Les effets du recuit teamfight, non confirmés, ont été retirés (24/10/2026).

### La logique des deux blocs

**Atteindre leurs cibles** (vu par exemple de Darius, qui veut prendre un reset sur une cible fragile) :
- pour chaque cible prioritaire adverse : **sa fuite** (sorts de déplacement), **sa protection** (bouclier, invulnérabilité, mur contre les projectiles…), **ses contrôles pour se défendre** (la cage de Veigar, le E de Syndra), et **qui la protège** : les bloqueurs et enchanteurs de son équipe, avec leurs contrôles et leurs protections ; le support compte comme « à côté » de son ADC ;
- la lecture : la **cible la plus accessible** est celle qui a le moins d'obstacles (fuites et protections, ses contrôles à moitié, un protecteur à côté compte double) ; la plus protégée est nommée avec ce qu'il faut faire tomber avant d'y aller.

**Protéger vos cibles** (vu par exemple d'Ivern, qui reste près de son carry) :
- pour chaque menace adverse (assassin, puis plongeur, puis attrapeur) : **comment il arrive** (sa mobilité) ou **comment il attrape** (ses contrôles) ;
- **vos protections** : les boucliers et soins pour les alliés de votre équipe, et les contrôles de vos protecteurs ;
- la lecture : **reste près de** votre cible la plus fragile (le moins de fuites et de protections ; l'ADC d'abord à égalité), et **garde** ton meilleur contrôle de base (Q, W ou E avant l'ultime, le plus fort d'abord) pour la menace principale, avec le sort par lequel elle arrive.

Les types viennent de la classification de nos parties (branche `analyse`, `analyse/types/`), les sorts de Data Dragon (`analyse/catalogues/sorts.csv`). Ce sont des descriptions des champions : elles ne prédisent pas la victoire, elles n'ont donc pas de tas C.

## Voir les picks du client League automatiquement

- Sous Windows : télécharger `Assistant Draft - Lien client.exe` (même endroit que la page, bouton « Download raw file »), le mettre dans le même dossier que la page et le lancer avant de jouer. Une petite fenêtre reste ouverte ; elle ouvre la page.
- Sur Mac, ou si Python est installé : `python3 assistant/lien_client.py`.
- **Version du jeu** : en haut à droite, la page compare la version de ton jeu (lue dans le client) au patch de l'assistant : « Patch 16.21 à jour » en vert, ou, en orange, « Jeu en 16.22, assistant en 16.21 : à mettre à jour » (relancer « Récupérer les stats Lolalytics du patch » puis « Générer l'assistant Draft », et retélécharger la page). Sans lien client, seul le patch de l'assistant est affiché.
- **Côté bleu ou rouge** : lu dans le client pendant la sélection ; sur la carte du récapitulatif, ta base passe en haut à droite côté rouge (ton équipe reste en bleu) (la case « on est côté rouge » reste modifiable à la main).
- La page affiche en haut « Client relié » ; pendant la sélection, elle remplit seule les deux équipes, ton poste et les bans (exclus des propositions). Les **pré-picks de ton équipe** (annonce avant son tour, ou survol pendant son tour) comptent comme des picks tant que le vrai n'est pas verrouillé ; ils s'affichent en pointillés. Ceux de l'équipe adverse ne sont jamais envoyés par le client. Ton propre survol s'affiche dans « Comment jouer ». Elle passe au récapitulatif à la fin de la sélection et repart de zéro à la sélection suivante. Ce que tu tapes dans une case encore vide est gardé.
- Le lien ne fait que **lire** ce que ton client affiche déjà (champions, postes, bans, ton côté, la version du jeu) : jamais le nom ni les stats des autres joueurs, jamais d'action à ta place (règles de Riot pour les applications tierces). L'interface locale du client n'est pas officiellement prise en charge par Riot : elle peut changer avec un patch.
- Windows peut avertir au premier lancement (programme non signé) : « Informations complémentaires » puis « Exécuter quand même ».

## D'où viennent les chiffres

| Chiffre | Source |
|---|---|
| Force du patch, contres, matchups de lane, poste deviné | Lolalytics, Platine et plus, tous serveurs (branche `scraping`, `lolalytics/<patch>/`) |
| Or à 15 min, chance d'être devant | nos parties Émeraude-Diamant avec timeline (`analyse/contres`, `analyse/lanes/dynamique.py`) |
| Ganks réussis | nos parties (`analyse/lanes/ganks.py`) |
| Dégâts par type, early / late | Lolalytics (page de chaque champion, `profils.csv`), sinon nos parties ; effets vérifiés sur nos parties (`analyse/lanes/duree_degats.py`) |
| 1 contre 1 | nos parties, 515 000 duels (`analyse/lanes/duels.py`), chacun avec l'or habituel de son poste ; forces vérifiées sur B seulement |
| Types des champions | nos parties (`analyse/types/classer.py`), appris sur les références du propriétaire, vérifiés sur B |
| Sorts (contrôle, protection, déplacement), identifiants des champions | Data Dragon (bouton « Mettre à jour le catalogue (Data Dragon) », `analyse/catalogues/`), corrigés à la main |
| Envahir | `analyse/lanes/envahir.py` (5 à 20 min, à écart d’or égal ; seules les minutes et catégories confirmées sur C sont affichées) : ce que font les junglers qui gagnent, pas une cause prouvée |

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
