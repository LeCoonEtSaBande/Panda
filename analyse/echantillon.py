"""Échantillon figé : les N premières parties complètes de parties.csv, dans l'ordre du fichier.

Tout le travail d'exploration et de test porte sur cet échantillon. Les parties qui arrivent ensuite
servent de test de confirmation, sur des parties que personne n'a regardées.

    python3 analyse/echantillon.py --figer   # écrit analyse/echantillon_fige.json (une seule fois)

Bibliothèque standard uniquement.
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import lecture

ICI = Path(__file__).resolve().parent
FIGE = ICI / "echantillon_fige.json"
# Lue une seule fois, en local, au moment de figer (jamais par le rapport) : on note quelles parties de
# l'échantillon figé sont aussi dans l'archive, pour que les tests de réplication les écartent.
ARCHIVE = ICI.parent / "archives" / "2026-10-22_avant_details" / "parties.csv"


def ordre_parties(donnees=lecture.DONNEES):
    """Identifiants de parties.csv dans l'ordre du fichier (chronologique), sans doublon."""
    chemin = Path(donnees) / "parties.csv"
    vus, ordre = set(), []
    if not chemin.exists():
        return ordre
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lecteur = csv.reader(fichier, delimiter=";")
        next(lecteur, None)
        for ligne in lecteur:
            if ligne and ligne[0] not in vus:
                vus.add(ligne[0])
                ordre.append(ligne[0])
    return ordre


def parties_completes_ordonnees(donnees=lecture.DONNEES):
    completes = lecture.matchs_avec_details(donnees)
    return [m for m in ordre_parties(donnees) if m in completes]


def lire_fige(chemin=FIGE):
    if not Path(chemin).exists():
        return None
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def decouper(donnees=lecture.DONNEES, chemin=FIGE):
    """(échantillon figé, parties de confirmation), en listes ordonnées de parties complètes.

    L'échantillon est coupé par le nombre N, pas par une date. Sans fichier figé, tout est dans
    l'échantillon et la confirmation est vide.
    """
    completes = parties_completes_ordonnees(donnees)
    fige = lire_fige(chemin)
    if not fige:
        return completes, []
    n = int(fige["N"])
    echantillon, suite = completes[:n], completes[n:]
    if echantillon and echantillon[-1] != fige["dernier_match"]:
        # Ne devrait jamais arriver : la collecte n'écrit qu'en ajout.
        print(f"Échantillon figé : la {n}e partie est {echantillon[-1]}, pas {fige['dernier_match']}.")
    return echantillon, suite


def figer(donnees=lecture.DONNEES, chemin=FIGE):
    if Path(chemin).exists():
        raise SystemExit(f"{chemin} existe déjà : l'échantillon est figé une seule fois.")
    completes = parties_completes_ordonnees(donnees)
    toutes = ordre_parties(donnees)
    communs = []
    if ARCHIVE.exists():
        anciens = set(ordre_parties(ARCHIVE.parent))
        communs = [m for m in completes if m in anciens]
    contenu = {
        "N": len(completes),
        "dernier_match": completes[-1] if completes else "",
        "dernier_match_parties_csv": toutes[-1] if toutes else "",
        "date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "regle": "Les N premières parties complètes (dans parties.csv et details_parties), dans l'ordre de parties.csv.",
        "nb_communs_archive": len(communs),
        "communs_archive": communs,
    }
    Path(chemin).write_text(json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return contenu


if __name__ == "__main__":
    if "--figer" in sys.argv:
        print(json.dumps(figer(), ensure_ascii=False, indent=2))
    else:
        echantillon, suite = decouper()
        print(f"Échantillon figé : {len(echantillon)} parties ; confirmation : {len(suite)} parties.")
