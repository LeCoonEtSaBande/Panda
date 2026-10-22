"""Assemble la page d'assistant en un seul fichier HTML, sans dépendance."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "assistant"
CATALOGUE = RACINE / "Catalogue.csv"
SORTIE = RACINE / "Assistant_draft.html"


def lire_catalogue(chemin=CATALOGUE):
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lignes = list(csv.reader(fichier, delimiter=";"))
    entete = lignes[1]
    catalogue = []
    for ligne in lignes[2:]:
        fiche = dict(zip(entete, ligne))
        catalogue.append({
            "nom": fiche["Champion"],
            "principal": fiche["Style principal"],
            "secondaire": fiche["Style secondaire"],
            "tanky": fiche["Tanky"],
            "carry": fiche["Carry"] == "oui",
            "split": fiche["Split"] == "oui",
            "degats": fiche["Dégâts"],
        })
    return catalogue


def en_js(valeur):
    # « </ » fermerait la balise <script> si un texte le contenait.
    return json.dumps(valeur, ensure_ascii=False).replace("</", "<\\/")


def construire(sortie=SORTIE):
    gabarit = (DOSSIER / "page.html").read_text(encoding="utf-8")
    regle = (DOSSIER / "regle.js").read_text(encoding="utf-8")
    scenarios = json.loads((DOSSIER / "scenarios.json").read_text(encoding="utf-8"))
    catalogue = lire_catalogue()

    noms = {f["nom"] for f in catalogue}
    inconnus = sorted({s["jungle"] for s in scenarios} - noms)
    if inconnus:
        raise SystemExit(f"Scénarios avec un jungle absent du catalogue : {', '.join(inconnus)}")

    page = (
        gabarit.replace("__REGLE__", regle)
        .replace("__CATALOGUE__", en_js(catalogue))
        .replace("__SCENARIOS__", en_js(scenarios))
        .replace("__GENERE_LE__", datetime.now(timezone.utc).strftime("%d/%m/%Y"))
    )
    sortie.write_text(page, encoding="utf-8")
    print(f"{sortie.name} : {len(catalogue)} champions, {len(scenarios)} scénarios, {len(page) // 1024} Ko")


if __name__ == "__main__":
    construire()
