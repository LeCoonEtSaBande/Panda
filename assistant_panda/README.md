# Assistant Draft

Une page HTML autonome (`Assistant Draft - DL - <date>.html`, à la racine de la branche `assistant`) : elle s'ouvre sans connexion, depuis le bureau.

**Télécharger** : sur GitHub, branche `assistant`, cliquer sur le fichier, puis sur le bouton « Download raw file » (flèche vers le bas, en haut à droite du fichier). Le fichier fait environ 2 Mo : GitHub ne l'affiche pas, et un « Enregistrer sous » de la page GitHub donne une page vide.

**Régénérer** : workflow « Générer l'assistant Panda ». À lancer après un passage Lolalytics (nouveau patch) ou quand des collectes ont ajouté des parties.

## Ce qu'elle fait

- **Mon équipe à gauche**, dans l'ordre de la draft : un poste (un seul de chaque) et un champion par ligne.
- **L'équipe adverse à droite** : le champion seulement ; le poste est deviné (part de ses parties à chaque poste, Lolalytics) et se change à la main.
- Saisie : quelques lettres suffisent, la liste propose les champions correspondants (sans accent ni majuscule). Entrée ou Tab valide.
- **Profils** (onglet Profils) : une personne par profil, avec les postes qu'elle joue et ses champions à chaque poste. En haut de la draft : le profil et le poste joué (« Je joue »).
- **Mémoire** : la page retient, dans le navigateur, les profils, le dernier profil, le dernier poste, la draft en cours et la case « tous les champions ». À la réouverture, tout est comme à la dernière utilisation (même navigateur ; avec Chrome ou Edge, une nouvelle version téléchargée retrouve aussi les profils ; avec Firefox, l'ouvrir depuis le même dossier que l'ancienne).
- **Quel champion prendre** à son poste (son pool, ou tous les champions du poste) : force du patch, contre son adversaire direct, contre le reste de leur équipe (à moitié), effets d'équipe (groupes teamfight). Adversaire direct inconnu : moyenne sur ses champions probables, « sûr en blind » ou non, et les champions à éviter s'ils peuvent encore être pris.
- **Dégâts** sous chaque équipe : part physique, magique et brute (dégâts moyens de chaque champion à son poste), et l'alerte quand une équipe est presque toute physique ou toute magique (elle gagne moins dans nos parties, à force égale ; compté dans le score des candidats dès que 4 champions sont connus). Le tempo de chaque équipe (plutôt early ou late).
- **Selon la durée** : la chance de gagner avant 20 min, à 20-25, 25-30, 30-35 et après 35 min, due au seul tempo des deux compos, avec le conseil qui va avec (finir vite ou temporiser).
- **Comment jouer** avec le champion recommandé (ou le sien, ou celui sur lequel on clique) : pour chaque lane, l'écart d'or attendu à 15 min et la chance d'être devant ; la chance que le gank de son jungler finisse en kill avant 15 min, et celle du jungler adverse ; le matchup Lolalytics. En jungle : lanes avec ou sans prio, meilleure lane à ganker, lane exposée, envahir à 5, 10, 15 et 20 min. En lane : sa chance d'être devant, le risque de gank adverse, l'aide de son jungler.

- **Valider la compo** : quand les 10 champions sont entrés. La page passe au récapitulatif : le plan en quelques lignes (tempo, lanes devant ou derrière, où ganker et quand envahir, ou ta lane et le risque de gank, dégâts adverses, leurs ultimes qui contrôlent), une carte simplifiée de la Faille avec chaque lane, et chaque champion avec ses styles du catalogue et ses contrôles. « Nouvelle draft » repart de zéro pour la partie suivante.
- **Un poste sans champion dans le profil** = tous les champions de ce poste sont proposés.
- **Seulement ce qui est confirmé** sur nos parties jamais vues (tas C) : force du patch et contres (Lolalytics), or à 15 min par lane, ganks, envahir à 15 min pour les junglers Engage (tanks et bruisers), early/late, mix de dégâts. Les effets du recuit teamfight, non confirmés, ont été retirés (24/10/2026).

## D'où viennent les chiffres

| Chiffre | Source |
|---|---|
| Force du patch, contres, matchups de lane, poste deviné | Lolalytics, Platine et plus, tous serveurs (branche `scraping`) |
| Or à 15 min, chance d'être devant | nos parties Émeraude-Diamant avec timeline (`analyse/contres`, `analyse/lanes/dynamique.py`) |
| Ganks réussis | nos parties (`analyse/lanes/ganks.py`) |
| Dégâts par type, early / late | Lolalytics (page de chaque champion, `profils.csv`), sinon nos parties ; effets vérifiés sur nos parties (`analyse/lanes/duree_degats.py`) |
| Contrôles des sorts | Data Dragon (descriptions officielles, `sorts.py`, rafraîchi à chaque génération) |
| Envahir | `analyse/lanes/envahir.py` (5 à 20 min, à écart d’or égal ; seules les minutes et catégories confirmées sur C sont affichées) : ce que font les junglers qui gagnent, pas une cause prouvée |

`construire.py` assemble tout dans `modele.html`.
