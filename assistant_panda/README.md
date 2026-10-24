# Assistant Panda

Une page HTML autonome (`Assistant_Panda.html`, à la racine de la branche `assistant`) : elle s'ouvre sans connexion, depuis le bureau.

**Régénérer** : workflow « Générer l'assistant Panda ». À lancer après un passage Lolalytics (nouveau patch) ou quand des collectes ont ajouté des parties.

## Ce qu'elle fait

- **Mon équipe à gauche**, dans l'ordre de la draft : un poste (un seul de chaque) et un champion par ligne.
- **L'équipe adverse à droite** : le champion seulement ; le poste est deviné (part de ses parties à chaque poste, Lolalytics) et se change à la main.
- Saisie : quelques lettres suffisent, la liste propose les champions correspondants (sans accent ni majuscule). Entrée ou Tab valide.
- **Quel jungler prendre** (ton pool, ou tous les junglers) : force du patch, contre le jungler adverse, contre leurs laners (à moitié), effets d'équipe (groupes teamfight). Jungler adverse inconnu : moyenne sur ses junglers probables, « sûr en blind » ou non, et les junglers à éviter s'ils peuvent encore être pris.
- **Comment jouer** avec le jungler recommandé (ou le tien, ou celui sur lequel tu cliques) : pour chaque lane, l'écart d'or attendu à 15 min et la chance d'être devant ; la chance que ton gank finisse en kill avant 15 min, et celle du jungler adverse ; le matchup Lolalytics ; l'envahissement à 5 min.

## D'où viennent les chiffres

| Chiffre | Source |
|---|---|
| Force du patch, contres, matchups de lane, poste deviné | Lolalytics, Platine et plus, tous serveurs (branche `scraping`) |
| Or à 15 min, chance d'être devant | nos parties Émeraude-Diamant avec timeline (`analyse/contres`, `analyse/lanes/dynamique.py`) |
| Ganks réussis | nos parties (`analyse/lanes/ganks.py`) |
| Effets d'équipe | recuit teamfight (`analyse/iteratif/recuit_pistes.py`), effets qui tiennent sur A et sur B |
| Envahir | `analyse/lanes/comportement.py` : ce que font les junglers qui gagnent, pas une cause prouvée |

`construire.py` assemble tout dans `modele.html`.
