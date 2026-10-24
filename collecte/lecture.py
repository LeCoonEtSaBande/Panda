"""Lecture des fichiers de détails découpés en tranches (bibliothèque standard uniquement).

    from lecture import lire_details
    for ligne in lire_details("joueurs"):
        ...

Chaque dossier de donnees/ (details_parties, joueurs, timeline_joueurs, evenements) est lu
en entier, tranche après tranche. On ne garde que les matchs présents dans parties.csv et dans
details_parties (écrit en dernier, donc détails complets). Si un match a été écrit plusieurs fois
(collecte interrompue puis reprise), seul son dernier bloc de lignes est gardé.
"""

import csv
from pathlib import Path

DONNEES = Path(__file__).resolve().parent.parent / "donnees"
TYPES = ("details_parties", "joueurs", "timeline_joueurs", "evenements")


def tranches(nom, donnees=DONNEES):
    dossier = Path(donnees) / nom
    if not dossier.is_dir():
        return []
    return sorted(dossier.glob(f"{nom}_*.csv"))


def _lignes(nom, donnees):
    """(bloc, entete, ligne) pour chaque ligne complète.

    Un bloc = les lignes d'une écriture d'un match. Une réécriture du même match juste après la
    précédente recommence par la même première ligne : c'est ainsi qu'on la distingue.
    """
    bloc = 0
    for chemin in tranches(nom, donnees):
        with open(chemin, encoding="utf-8", newline="") as fichier:
            lecteur = csv.reader(fichier, delimiter=";")
            entete = next(lecteur, None)
            if not entete:
                continue
            premiere = None
            for ligne in lecteur:
                if len(ligne) != len(entete):
                    continue
                if premiere is None or ligne[0] != premiere[0] or ligne == premiere:
                    bloc += 1
                    premiere = ligne
                yield bloc, entete, ligne


def matchs_presents(nom, donnees=DONNEES):
    """Ensemble des matchs qui ont au moins une ligne complète dans ce dossier."""
    return {ligne[0] for _, _, ligne in _lignes(nom, donnees)}


def matchs_de_parties(donnees=DONNEES):
    chemin = Path(donnees) / "parties.csv"
    if not chemin.exists():
        return set()
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lecteur = csv.reader(fichier, delimiter=";")
        next(lecteur, None)
        return {ligne[0] for ligne in lecteur if ligne}


def matchs_avec_details(donnees=DONNEES):
    """Matchs de parties.csv dont les détails sont complets."""
    return matchs_de_parties(donnees) & matchs_presents("details_parties", donnees)


def lire_details(nom, donnees=DONNEES, matchs=None):
    """Lignes (dictionnaires) du dossier `nom`, dédoublonnées par match (dernier bloc gardé).

    `matchs` restreint la lecture à un ensemble de matchs ; par défaut, ceux de matchs_avec_details().
    """
    if nom not in TYPES:
        raise ValueError(f"Type de détails inconnu : {nom}")
    if matchs is None:
        matchs = matchs_avec_details(donnees)
    dernier = {}
    for bloc, _, ligne in _lignes(nom, donnees):
        if ligne[0] in matchs:
            dernier[ligne[0]] = bloc
    for bloc, entete, ligne in _lignes(nom, donnees):
        if dernier.get(ligne[0]) == bloc:
            yield dict(zip(entete, ligne))
