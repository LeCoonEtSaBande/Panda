"""Exporte, pour l'assistant de draft, ce que les analyses ont appris de nos parties.

Écrit analyse/export/assistant_donnees.json :
- catalogue : le catalogue unifié (groupe teamfight, tanky, carry, dégâts, styles) ;
- lanes : le modèle des contres sur toutes les parties avec timeline (force de lane de chaque champion
  à chaque poste, effet propre des paires vues au moins 10 fois, écart-type de l'or à 15 min), pour
  annoncer l'écart d'or attendu à 15 min et la probabilité d'être devant ;
- ganks : le modèle des ganks réussis avant 15 min (ganks.py) ;
- teamfight : le réglage du recuit teamfight (poids des postes, seuil) et les effets qui tiennent sur A
  et sur B (même sens, au moins 1,5 point sur B, 300 parties sur B) ;
- envahir : les taux de victoire des junglers qui envahissent à 5 min (comportement.py), avec la mise en garde ;
- envahir_minutes : l'effet d'envahir à 5, 10, 15 et 20 min à écart d'or égal, par catégorie, sur A et sur B (envahir.py).

    python3 analyse/export/exporter.py      (après analyse/lanes/ganks.py, comportement.py et envahir.py)
"""

import csv
import json
import math
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

ICI = Path(__file__).resolve().parent
ANALYSE = ICI.parent
sys.path.insert(0, str(ANALYSE))
sys.path.insert(0, str(ANALYSE / "contres"))

import contres  # noqa: E402

CATALOGUE = ANALYSE / "catalogues" / "catalogue_unifie.csv"
LANES_RES = ANALYSE / "lanes" / "resultats"
ITERATIF_RES = ANALYSE / "iteratif" / "resultats"
SORTIE = ICI / "assistant_donnees.json"


def catalogue():
    with open(CATALOGUE, encoding="utf-8", newline="") as f:
        return {l["champion"]: {"groupe": l["groupe_teamfight"], "tanky": l["tanky"], "carry": l["carry"] == "oui",
                                "degats": l["degats"], "principal": l["style_principal"], "secondaire": l["style_secondaire"]}
                for l in csv.DictReader(f, delimiter=";")}


def lanes():
    lignes, matchs = contres.lire(contres.dossier_donnees())
    sortie = contres.analyser(lignes)
    modele = {"parties": len(matchs), "postes": {}}
    for poste, s in sortie.items():
        modele["postes"][poste] = {
            "lane": s["lane"], "ecart_type": s["ecart_type_residu"], "pente_victoire": s["pente"],
            "forces": {c: round(v) for c, v in s["forces"].items() if s["comptes"].get(c, 0) >= 20},
            "paires": {f"{a}|{b}": round(e["specifique"]) for (a, b), e in s["paires"].items()
                       if e["parties"] >= 10 and abs(e["specifique"]) >= 20},
        }
    return modele


MOTIFS = [
    (r"^Compo (.+) contre compo (.+)$", "duel"),
    (r"^Jungler (.+) contre compo tanky$", "jungler_contre_tanky"),
    (r"^Jungler (.+) contre compo sans tank$", "jungler_contre_sans_tank"),
    (r"^Jungler (.+) avec compo alliée sans tank$", "jungler_avec_sans_tank"),
    (r"^Jungler (.+) contre compo (.+)$", "jungler_contre"),
    (r"^Jungler (.+) avec compo alliée (.+)$", "jungler_avec"),
    (r"^Compo tanky$", "tanky"),
    (r"^Compo sans tank$", "sans_tank"),
    (r"^Compo (.+)$", "compo"),
]


def teamfight():
    fichiers = sorted(ITERATIF_RES.glob("recuit2_teamfight_*.json"))
    fichiers = [f for f in fichiers if "hasard" not in f.name and "test" not in f.name]
    d = json.loads(fichiers[-1].read_text(encoding="utf-8"))
    meilleur = d["palmares"][0]
    effets = []
    for b in meilleur["biais"]:
        ta, tb, na, nb = b["taux_A"], b["taux_B"], b["parties_A"], b["parties_B"]
        if not (ta == ta and tb == tb) or nb < 300 or (ta - 0.5) * (tb - 0.5) <= 0 or abs(tb - 0.5) < 0.015:
            continue
        for motif, genre in MOTIFS:
            m = re.match(motif, b["nom"])
            if m:
                groupes = list(m.groups())
                effets.append({"genre": genre, "x": groupes[0] if groupes else None, "y": groupes[1] if len(groupes) > 1 else None,
                               "nom": b["nom"], "taux": (ta * na + tb * nb) / (na + nb), "taux_A": ta, "taux_B": tb,
                               "coefficient": b["coefficient"],
                               "parties": na + nb})
                break
    return {"recuit": fichiers[-1].name, "roles": meilleur["parametres"]["roles"], "seuil": meilleur["parametres"]["seuil"],
            "effets": sorted(effets, key=lambda e: -abs(e["taux"] - 0.5))}


def main():
    donnees = {
        "date": datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M"),
        "catalogue": catalogue(),
        "lanes": lanes(),
        "ganks": json.loads((LANES_RES / "ganks_modele.json").read_text(encoding="utf-8")),
        "teamfight": teamfight(),
        "envahir": json.loads((LANES_RES / "comportement.json").read_text(encoding="utf-8"))["envahir"],
        "envahir_minutes": json.loads((LANES_RES / "envahir.json").read_text(encoding="utf-8")),
    }
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Export : {SORTIE} ({SORTIE.stat().st_size // 1024} Ko) ; {donnees['lanes']['parties']} parties pour les lanes, "
          f"{len(donnees['teamfight']['effets'])} effets teamfight.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
