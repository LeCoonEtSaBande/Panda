"""Bilan de fin de collecte : combien de parties, de quels patchs et paliers, avec ou sans détails.

Lancé par enregistrer.sh --rapport à la fin de chaque collecte ; écrit collecte/bilan.md.
Bibliothèque standard seulement ; ne fait jamais échouer l'enregistrement des données.

    python3 collecte/bilan.py
"""

import csv
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

import lecture  # noqa: E402

SORTIE = ICI / "bilan.md"


def volume_details(donnees=None):
    """Parties de parties.csv avec détails et avec timeline."""
    try:
        donnees = donnees or lecture.DONNEES
        avec_details = lecture.matchs_avec_details(donnees)
        avec_timeline = avec_details & lecture.matchs_presents("timeline_joueurs", donnees)
        return [["avec_details", len(avec_details)], ["avec_timeline", len(avec_timeline)]]
    except Exception as erreur:  # noqa: BLE001
        print(f"Volume des détails : sauté ({type(erreur).__name__} : {erreur}).")
        return []


def lire(chemin):
    if not chemin.exists():
        return []
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main():
    parties = lire(lecture.DONNEES / "parties.csv")
    ecartees = lire(lecture.DONNEES / "ecartees.csv")
    volume = dict(volume_details())
    date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    lignes = [f"# Bilan de collecte ({date})", "",
              f"- **{len(parties)} parties** dans `donnees/parties.csv`, dont {volume.get('avec_details', '?')} avec détails "
              f"et {volume.get('avec_timeline', '?')} avec timeline.",
              f"- {len(ecartees)} parties écartées (jamais retéléchargées).", "",
              "| Patch | Parties |", "|---|---|"]
    lignes += [f"| {p} | {n} |" for p, n in sorted(Counter(l["patch"] for l in parties).items())]
    lignes += ["", "| Palier | Parties |", "|---|---|"]
    lignes += [f"| {p} | {n} |" for p, n in sorted(Counter(l["palier"] for l in parties).items())]
    lignes += ["", "| Raison d'écart | Parties |", "|---|---|"]
    lignes += [f"| {r} | {n} |" for r, n in sorted(Counter(l["raison"] for l in ecartees).items())]
    SORTIE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"Bilan : {len(parties)} parties.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
