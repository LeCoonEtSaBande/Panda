"""Chargement des données d'un ensemble de parties en tables pandas (via lecture.py uniquement).

    from tables import charger
    t = charger(matchs)          # matchs : liste ordonnée d'identifiants
    t.parties, t.joueurs, t.timeline, t.evenements, t.details

Toutes les valeurs sont converties en nombres ; une case vide devient NaN (absente, pas zéro).
`evenements` ne contient que les CHAMPION_KILL. `joueurs` reçoit en plus : victoire (0/1), duree_min, ordre (rang de la partie dans parties.csv),
pli (0 ou 1 selon la parité du rang, pour la validation croisée), rang (D, E...), patch.
"""

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import lecture

POSTES = ("top", "jgl", "mid", "adc", "sup")
TEXTE = {"match", "equipe", "poste", "champion", "type", "assistants", "detail", "patch", "palier", "gagnant"}


@dataclass
class Tables:
    parties: object
    details: object
    joueurs: object
    timeline: object
    evenements: object


def _nombre(texte):
    if texte == "":
        return math.nan
    try:
        return float(texte)
    except ValueError:
        return math.nan


def _cadre(lignes, colonnes_texte=TEXTE, garder=None, filtre=None):
    """DataFrame construit colonne par colonne en flux (peu de mémoire), valeurs converties au passage.

    `garder` : colonnes à garder (toutes par défaut) ; `filtre` : fonction ligne -> bool.
    """
    import pandas as pd

    colonnes = None
    valeurs = {}
    for ligne in lignes:
        if filtre is not None and not filtre(ligne):
            continue
        if colonnes is None:
            colonnes = [c for c in ligne if garder is None or c in garder]
            valeurs = {c: [] for c in colonnes}
        for c in colonnes:
            texte = ligne[c]
            if c in colonnes_texte or c.endswith(("_ban1", "_ban2", "_ban3", "_ban4", "_ban5")):
                valeurs[c].append(texte)
            else:
                valeurs[c].append(_nombre(texte))
    if colonnes is None:
        return pd.DataFrame(columns=list(garder or []))
    return pd.DataFrame(valeurs)


def lire_parties_csv(chemin, matchs=None):
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lignes = list(csv.DictReader(fichier, delimiter=";"))
    if matchs is not None:
        garder = set(matchs)
        lignes = [ligne for ligne in lignes if ligne["match"] in garder]
    return lignes


def charger(matchs, donnees=lecture.DONNEES, evenements=True, timeline=True):
    """Tables des parties `matchs` (liste ordonnée). L'ordre de la liste donne `ordre` et `pli`."""
    import pandas as pd

    matchs = list(matchs)
    rang_de = {m: i for i, m in enumerate(matchs)}
    ensemble = set(matchs)

    parties = pd.DataFrame(lire_parties_csv(Path(donnees) / "parties.csv", ensemble))
    parties = parties.drop_duplicates("match", keep="last")
    parties["ordre"] = parties["match"].map(rang_de)
    parties = parties.sort_values("ordre").reset_index(drop=True)

    details = _cadre(lecture.lire_details("details_parties", donnees, matchs=ensemble))
    joueurs = _cadre(lecture.lire_details("joueurs", donnees, matchs=ensemble))
    tl = _cadre(lecture.lire_details("timeline_joueurs", donnees, matchs=ensemble)) if timeline else None
    # Seuls les kills de champions servent aux analyses : on ne garde qu'eux.
    ev = _cadre(lecture.lire_details("evenements", donnees, matchs=ensemble),
                filtre=lambda ligne: ligne["type"] == "CHAMPION_KILL") if evenements else None

    infos = parties.set_index("match")
    duree = details.set_index("match")["duree_s"] / 60
    joueurs["victoire"] = (joueurs["equipe"] == joueurs["match"].map(infos["gagnant"])).astype(int)
    joueurs["duree_min"] = joueurs["match"].map(duree)
    joueurs["ordre"] = joueurs["match"].map(rang_de)
    joueurs["pli"] = joueurs["ordre"] % 2
    joueurs["rang"] = joueurs["match"].map(infos["palier"]).str[:1]
    joueurs["patch"] = joueurs["match"].map(infos["patch"])
    return Tables(parties=parties, details=details, joueurs=joueurs, timeline=tl, evenements=ev)
