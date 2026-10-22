"""Règle qui range une compo de 5 à partir du catalogue."""

import csv
from pathlib import Path

CATALOGUE = Path(__file__).resolve().parent.parent / "Catalogue.csv"

STYLES = ("Engage", "Pick", "Poke", "Counter-engage", "Disengage")
POINTS_PRINCIPAL = 2
POINTS_SECONDAIRE = 1
SEUIL_PRINCIPAL = 3
SEUIL_SECONDAIRE = 2
SEUIL_DEGATS = 4


def charger_catalogue(chemin=CATALOGUE):
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lignes = list(csv.reader(fichier, delimiter=";"))
    entete = lignes[1]
    catalogue = {}
    for ligne in lignes[2:]:
        fiche = dict(zip(entete, ligne))
        catalogue[fiche["Champion"]] = {
            "principal": fiche["Style principal"],
            "secondaire": fiche["Style secondaire"],
            "tanky": fiche["Tanky"],
            "carry": fiche["Carry"] == "oui",
            "split": fiche["Split"] == "oui",
            "degats": fiche["Dégâts"],
        }
    return catalogue


def _choisir(scores, principaux, seuil, exclu=None):
    candidats = [s for s in STYLES if s != exclu and scores[s] >= seuil]
    if not candidats:
        return ""
    return max(candidats, key=lambda s: (scores[s], principaux[s], -STYLES.index(s)))


def etiqueter(champions, catalogue):
    """Étiquettes d'une équipe. Les champions absents du catalogue sont ignorés."""
    fiches = [catalogue[nom] for nom in champions if nom in catalogue]
    scores = dict.fromkeys(STYLES, 0)
    principaux = dict.fromkeys(STYLES, 0)
    for fiche in fiches:
        if fiche["principal"]:
            scores[fiche["principal"]] += POINTS_PRINCIPAL
            principaux[fiche["principal"]] += 1
        if fiche["secondaire"]:
            scores[fiche["secondaire"]] += POINTS_SECONDAIRE

    principal = _choisir(scores, principaux, SEUIL_PRINCIPAL)
    secondaire = _choisir(scores, principaux, SEUIL_SECONDAIRE, exclu=principal) if principal else ""

    tanky = {f["tanky"] for f in fiches}
    front = "HP+" if "HP+" in tanky else "HP" if "HP" in tanky else ""

    disengage = any("Disengage" in (f["principal"], f["secondaire"]) for f in fiches)
    ad = sum(f["degats"] in ("AD", "Hybride") for f in fiches)
    ap = sum(f["degats"] in ("AP", "Hybride") for f in fiches)
    if ad >= SEUIL_DEGATS and ap < SEUIL_DEGATS:
        degats = "AD"
    elif ap >= SEUIL_DEGATS and ad < SEUIL_DEGATS:
        degats = "AP"
    else:
        degats = "mixte"

    return {
        "principal": principal,
        "secondaire": secondaire,
        "assassin": any(f["principal"] == "Pick" for f in fiches),
        "front": front,
        "protect": any(f["carry"] for f in fiches) and disengage,
        "side": any(f["split"] for f in fiches),
        "degats": degats,
        "scores": scores,
    }


def correspond(etiquettes, condition):
    """Une condition liste des étiquettes. Une liste de valeurs vaut « l'une d'elles »."""
    for cle, attendu in condition.items():
        valeur = etiquettes[cle]
        if isinstance(attendu, list):
            if valeur not in attendu:
                return False
        elif valeur != attendu:
            return False
    return True
