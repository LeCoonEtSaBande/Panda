# Panda — branche `assistant` : l'Assistant Draft

Projet complet, règles et routine : voir le README de la branche `main`. Tout se fait en français.

Une page HTML autonome (`Assistant Draft - DL - <date>.html`, à la racine de la branche `assistant`) : elle s'ouvre sans connexion, depuis le bureau.

**Télécharger** : sur GitHub, branche `assistant`, cliquer sur le fichier, puis sur le bouton « Download raw file » (flèche vers le bas, en haut à droite du fichier). Le fichier fait environ 2 Mo : GitHub ne l'affiche pas, et un « Enregistrer sous » de la page GitHub donne une page vide.

**Régénérer** : bouton « Générer l'assistant Draft » (sur `main`). À lancer après un passage Lolalytics (nouveau patch) ou quand des collectes ont ajouté des parties.

## Ce qu'elle fait

- **Mon équipe à gauche**, dans l'ordre de la draft : un poste (un seul de chaque) et un champion par ligne.
- **L'équipe adverse à droite** : le champion seulement ; le poste est deviné (part de ses parties à chaque poste, Lolalytics) et se change à la main.
- Saisie : quelques lettres suffisent, la liste propose les champions correspondants (sans accent ni majuscule). Entrée ou Tab valide.
- **Profils** (onglet Profils) : une personne par profil, avec les postes qu'elle joue et ses champions à chaque poste. En haut de la draft : le profil et le poste joué (« Je joue »).
- **Mémoire** : la page retient, dans le navigateur, les profils, le dernier profil, le dernier poste, la draft en cours et la case « tous les champions ». À la réouverture, tout est comme à la dernière utilisation (même navigateur ; avec Chrome ou Edge, une nouvelle version téléchargée retrouve aussi les profils ; avec Firefox, l'ouvrir depuis le même dossier que l'ancienne).
- **Quel champion prendre** à son poste (son pool, ou tous les champions du poste) : force du patch, contre son adversaire direct, contre le reste de leur équipe (à moitié), mix de dégâts de l'équipe, et le 1 contre 1 à or égal contre son adversaire direct. Adversaire direct inconnu : moyenne sur ses champions probables, « sûr en blind » ou non, et les champions à éviter s'ils peuvent encore être pris.
- **Dégâts** sous chaque équipe : part physique, magique et brute (dégâts moyens de chaque champion à son poste), et l'alerte quand une équipe est presque toute physique ou toute magique (elle gagne moins dans nos parties, à force égale ; compté dans le score des candidats dès que 4 champions sont connus). Le tempo de chaque équipe (plutôt early ou late).
- **Selon la durée** : la chance de gagner avant 20 min, à 20-25, 25-30, 30-35 et après 35 min, due au seul tempo des deux compos, avec le conseil qui va avec (finir vite ou temporiser).
- **Comment jouer** avec le champion recommandé (ou le sien, ou celui sur lequel on clique) : pour chaque lane, l'écart d'or attendu à 15 min et la chance d'être devant ; la chance que le gank de son jungler finisse en kill avant 15 min, et celle du jungler adverse ; le matchup Lolalytics. En jungle : lanes avec ou sans prio, meilleure lane à ganker, lane exposée, quand envahir (seulement si c'est confirmé pour ce type de jungler). En lane : sa chance d'être devant, le risque de gank adverse, l'aide de son jungler.

- **Valider la compo** : quand les 10 champions sont entrés. La page passe au récapitulatif : le plan en quelques lignes (tempo, lanes devant ou derrière, où ganker et quand envahir, ou ta lane et le risque de gank, dégâts adverses, leurs ultimes qui contrôlent), une carte simplifiée de la Faille avec chaque lane, et chaque champion avec ses styles du catalogue, son type de dégâts et ses contrôles. « Nouvelle draft » repart de zéro pour la partie suivante.
- **Un poste sans champion dans le profil** = tous les champions de ce poste sont proposés.
- **Seulement ce qui est confirmé** sur nos parties jamais vues (tas C) : force du patch et contres (Lolalytics), or à 15 min par lane, ganks, envahir à 15 min pour les junglers Engage (tanks et bruisers), early/late, mix de dégâts. Les effets du recuit teamfight, non confirmés, ont été retirés (24/10/2026).

## Voir les picks du client League automatiquement

- Sous Windows : télécharger `Assistant Draft - Lien client.exe` (même endroit que la page, bouton « Download raw file »), le mettre dans le même dossier que la page et le lancer avant de jouer. Une petite fenêtre reste ouverte ; elle ouvre la page.
- Sur Mac, ou si Python est installé : `python3 assistant/lien_client.py`.
- La page affiche en haut « Client relié » ; pendant la sélection, elle remplit seule les deux équipes, ton poste et les bans (exclus des propositions). Les **pré-picks de ton équipe** (annonce avant son tour, ou survol pendant son tour) comptent comme des picks tant que le vrai n'est pas verrouillé ; ils s'affichent en pointillés. Ceux de l'équipe adverse ne sont jamais envoyés par le client. Ton propre survol s'affiche dans « Comment jouer ». Elle passe au récapitulatif à la fin de la sélection et repart de zéro à la sélection suivante. Ce que tu tapes dans une case encore vide est gardé.
- Le lien ne fait que **lire** ce que ton client affiche déjà (champions, postes, bans) : jamais le nom ni les stats des autres joueurs, jamais d'action à ta place (règles de Riot pour les applications tierces). L'interface locale du client n'est pas officiellement prise en charge par Riot : elle peut changer avec un patch.
- Windows peut avertir au premier lancement (programme non signé) : « Informations complémentaires » puis « Exécuter quand même ».

## D'où viennent les chiffres

| Chiffre | Source |
|---|---|
| Force du patch, contres, matchups de lane, poste deviné | Lolalytics, Platine et plus, tous serveurs (branche `scraping`, `lolalytics/<patch>/`) |
| Or à 15 min, chance d'être devant | nos parties Émeraude-Diamant avec timeline (`analyse/contres`, `analyse/lanes/dynamique.py`) |
| Ganks réussis | nos parties (`analyse/lanes/ganks.py`) |
| Dégâts par type, early / late | Lolalytics (page de chaque champion, `profils.csv`), sinon nos parties ; effets vérifiés sur nos parties (`analyse/lanes/duree_degats.py`) |
| Contrôles des sorts | Data Dragon (descriptions officielles, `sorts.py`, rafraîchi à chaque génération) |
| Envahir | `analyse/lanes/envahir.py` (5 à 20 min, à écart d’or égal ; seules les minutes et catégories confirmées sur C sont affichées) : ce que font les junglers qui gagnent, pas une cause prouvée |

`construire.py` assemble tout dans `modele.html`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `Assistant Draft - DL - <date>.html` | La page à télécharger. Un seul fichier à la fois : l'ancien est retiré à chaque génération. |
| `assistant/construire.py` | Assemble les données (Lolalytics, export des analyses, contrôles des sorts) dans `modele.html`. |
| `assistant/modele.html` | La page elle-même (mise en page et calculs), sans données. |
| `assistant/sorts.py`, `assistant/sorts.json` | Les contrôles de chaque champion, d'après Data Dragon, rafraîchis à chaque génération. |
| `assistant/lien_client.py`, `Assistant Draft - Lien client.exe` | Le lien avec le client League (lecture de la sélection) ; l'exécutable Windows est reconstruit par le workflow quand le code change. |
| `assistant/tests/` | Tests des contrôles et du lien client : `python3 -m unittest discover -s assistant/tests`. |

En local : récupérer Lolalytics (branche `scraping`) et l'export des analyses (branche `analyse`, `analyse/export/assistant_donnees.json`), puis
`python3 assistant/construire.py --lolalytics <dossier du patch> --export <assistant_donnees.json>`.
