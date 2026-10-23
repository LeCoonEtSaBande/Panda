# Biais de draft : résultats du 23/10/2026

## L'échantillon

- **15 249 parties figées** le 23/10 à 13h17 (dernière partie 8022307599), noté dans `analyse/echantillon_fige.json`.
- Figé **pendant une collecte en cours**, à ta demande. Toutes les parties qui arrivent après servent au contrôle : personne ne les a regardées.
- Rangs : Émeraude et Diamant seulement (pas de Gold), patchs 16.20 et 16.21.
- Contrôle des données : rien d'anormal.
  - 10 joueurs par partie, mêmes champions que `parties.csv`, 4 parties sans timeline.
  - 168 parties de moins de 15 min écartées des analyses de durée, d'or et de timing.
  - 1 393 parties sont aussi dans l'archive du 22/10. Elles sont écartées quand on compare les deux.
  - Les kills des événements collent au total Riot, sauf quand une tour ou un sbire achève un champion (exécution). C'est une différence de comptage chez Riot, pas un défaut des données.

## Trouvé sur les 15 249 parties

| | Résultat | Verdict |
|---|---|---|
| **B1. Compo early** | Une compo plus early que l'adverse (à champions de force égale) gagne **53 % des parties de 20 min, mais seulement 46 % de celles de 38 min**. | Net sur l'échantillon. **À confirmer** sur les parties suivantes. |
| **C1. Avance en or à 15 min** | 1 000 or d'avance à un seul poste donne : adc 63 %, jungle 62 %, mid 62 %, top 60 %, support 55 %. L'avance du top et surtout du support se convertit moins bien. | Net sur l'échantillon. **À confirmer** sur les parties suivantes. |
| **E2. Cycle des types au top** | Le cycle prévu (distance > combattant > front > distance) est **à l'envers** sur l'or à 10 min. En brut, le combattant prend l'avantage sur le top à distance et sur le front, et le top à distance l'emporte sur le front. | Sens contraire de l'hypothèse, donc **exploratoire**. À revoir sur les parties suivantes. |

Pour B1 et C1 :
- Le rapport de fin de collecte les retestera tout seul sur les parties arrivées après l'échantillon, dès qu'il y en a 3 000 (lignes « confirmation » de `resultats/biais_tests.csv`).
- Ils disent comment une partie tourne, pas quel jungler prendre. Une compo early doit finir vite. Une avance du support ou du top compte moins qu'une avance en jungle, en mid ou en adc.

## Ne donne rien (testé, pas de différence)

Chaque fois, le jungler ou l'équipe gagne entre 48 et 51 %, contre 50 % sinon.

- **A.** 2 assassins ou plus contre une compo sans peel : 50,5 %. Pas retrouvé sur l'archive non plus.
- **B2.** Un jungler early ne compense pas des lanes tardives, et l'inverse non plus.
- **C2.** Un jungler early ne convertit pas mieux son avance en or qu'un jungler tardif.
- **D.** Un jungler tardif ne perd pas davantage contre un jungler envahisseur, ni en profil de champion ni en camps réellement volés.
- **E1.** Pas de cycle des types au top sur la victoire.
- **G.** Jungler counter-engage contre une compo engage : 50 % (catalogue) et 49 % (mesuré). L'ancienne piste à surveiller (54 %) n'est pas retrouvée. Avec le catalogue, la marge reste large (45 à 56 %) ; avec la définition mesurée, elle va de 46 à 52 % et exclut les 54 %.

## L'ancien résultat « confirmé » ne tient plus

**F. Jungler AD dans une équipe avec au plus 1 coéquipier AP.**

- Sur les nouvelles parties, ce jungler gagne **50 %**, contre 50 % sinon. C'est vrai avec le catalogue comme avec les dégâts réels.
- L'archive donnait 45 %. La marge des nouvelles parties (46 à 54 %) exclut presque cet écart.
- L'archive le montre toujours (47 % avec les dégâts réels), et encore 46 % en ne gardant que l'Émeraude et le Diamant. Ce n'est donc pas une question de rang.
- **Conclusion** : probablement un faux positif de l'archive. Ne t'en sers plus comme règle de draft.

## Catégories mesurées contre le catalogue

Les fichiers sont dans `resultats/categories_mesurees.csv` et `resultats/categories_groupes.csv` : 245 champions-postes à 100 parties ou plus. Le catalogue n'a pas été modifié.

- **Les champions forment un continuum, pas des familles nettes.** Le meilleur découpage fait 4 groupes : enchanteurs (peel), poke et carries à distance, assassins et split, front et engage. Même ce découpage colle mal (silhouette de 0,18 sur 1).
- **Le counter-engage se mesure mal.** Kills en infériorité numérique et kills en réponse à un engage varient peu d'un champion à l'autre. Les champions Counter-engage du catalogue sont à peine au-dessus de la moyenne. À prendre avec prudence.
- **35 désaccords nets de style.** Le champion fait moins que la moyenne de son poste dans le style que le catalogue lui donne. Exemples :
  - Engage peu mesuré : Jarvan IV jungle, Gwen, Malphite, Olaf, Vladimir.
  - Counter-engage peu mesuré : Anivia, Shen top, Galio mid, Orianna.
  - Poke peu mesuré : Jhin, Ashe, Twisted Fate.
  - 28 autres désaccords sont légers.
- **17 désaccords de dégâts.** Les tanks dits AP au catalogue font en réalité des dégâts mixtes (Cho'Gath, Malphite jungle, Sejuani). Kog'Maw est AP en mid et mixte en adc. Corki est AD. Ornn est AP.
- **Ton pool, profils mesurés en jungle :**

| Champion | Parties | Profil mesuré | Accord avec le catalogue |
|---|---|---|---|
| Viego | 1 276 | pick, classé avec les carries | oui |
| Kayn rouge | 535 | front et engage | engage à peine moyen, désaccord léger |
| Kayn bleu | 421 | pick et split, gros envahisseur | oui |
| Fiddlesticks | 359 | engage, peu de front, dégâts 92 % magiques | counter-engage juste moyen |
| Ivern | 252 | peel de très loin le plus fort des junglers, n'envahit pas | oui |
| Skarner | 158 | front et engage | counter-engage juste moyen |

**Pas classés à partir de leurs propres stats** (moins de 100 parties en jungle) : Dr. Mundo (88), Maokai (72), Morgana (40), Urgot (3).

## Pistes exploratoires pour ton pool

Ces pistes sont hors de la liste d'hypothèses. 73 tests ont été faits, 5 pistes sortent. Le hasard seul en ferait sortir 3 ou 4 : **aucune n'est fiable pour l'instant.**

| Piste | Ce jungler | Les autres junglers |
|---|---|---|
| Ivern contre une équipe avec 2 engage ou plus | 63 % (81 parties) | 47 % |
| Fiddlesticks avec 2 assassins ou plus dans son équipe | 57 % (106) | 41 % |
| Kayn rouge avec 3 AP ou plus dans son équipe | 43 % (184) | 52 % |
| Ivern avec 3 AP ou plus dans son équipe | 43 % (68) | 55 % |
| Ivern avec 2 assassins ou plus dans son équipe | 63 % (63) | 48 % |

Elles sont figées dans `explorations/pistes_a_confirmer.json`. Elles seront retestées telles quelles sur les parties suivantes avec `python3 analyse/explorations/pistes_pool.py --confirmation`.

## Conseils de draft, aujourd'hui

1. **Aucune règle de compo ne justifie de changer de jungler pour l'instant.** Choisis sur ta maîtrise et la force du champion dans le patch. Les effets de compo testés sont nuls ou trop petits pour se voir sur 15 000 parties.
2. **N'écarte plus un jungler AD parce que ton équipe manque d'AP** : ça ne se vérifie plus.
3. **Si ta compo est très early, joue pour finir avant 30 min.** Passé 32 min, elle perd l'avantage (à confirmer ce soir).
4. **Les pistes « Ivern contre engage » et « Fiddle avec des assassins alliés »** méritent d'être suivies. Ne les applique pas encore comme des règles.
5. **Les données sont Émeraude-Diamant.** En Gold, les effets peuvent différer.

## Combien de parties encore

- **B1 et C1** : le rapport de ce soir (environ 5 000 parties de plus) suffit pour les confirmer ou non.
- **Pistes du pool** : avec des écarts de 8 à 15 % et des cas rares, il faut environ **20 000 à 35 000 parties de plus**. Kayn rouge : environ 20 000. Ivern contre engage : environ 35 000.
- **Counter-engage contre engage (G)** : avec la définition mesurée, un écart de 54 % est déjà exclu (marge de 46 à 52 %). Avec celle du catalogue, les cas sont rares (520). Pour trancher, il faut environ **4 fois plus de cas**, soit environ 45 000 parties de plus.
- **Jungler AD et AP (F)** : pour trancher un petit effet de 47 % contre 50 %, il faut environ **30 000 parties de plus**.

## Fichiers

- `analyse/hypotheses.json` : les 13 hypothèses, écrites et poussées avant tout test.
- `analyse/controle.py`, `analyse/categories.py`, `analyse/biais.py` : appelés par `rapport.py`. Chacun peut être sauté sans faire échouer le rapport.
- `analyse/explorations/` : confirmation sur l'archive et pistes du pool, lancées en local seulement.
