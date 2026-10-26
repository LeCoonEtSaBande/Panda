"""Exporte, pour l'assistant de draft, ce que les analyses ont appris de nos parties.

Écrit analyse/export/assistant_donnees.json :
- catalogue : les 10 types de chaque champion (catalogue unifié), son identifiant Riot, et sa catégorie de jungler
  de l'ancien catalogue (seulement pour les ganks et envahir) ;
- sorts : les sorts de chaque champion par catégorie exclusive (contrôle, déplacement, protection), d'après Data Dragon ;
- lanes : le modèle des contres sur toutes les parties avec timeline (force de lane de chaque champion
  à chaque poste, effet propre des paires vues au moins 10 fois, écart-type de l'or à 15 min), pour
  annoncer l'écart d'or attendu à 15 min et la probabilité d'être devant ;
- ganks : le modèle des ganks réussis avant 15 min (ganks.py) ;
- teamfight : le réglage du recuit teamfight (poids des postes, seuil) et les effets qui tiennent sur A
  et sur B (même sens, au moins 1,5 point sur B, 300 parties sur B) ;
- envahir_minutes : l'effet d'envahir à 5, 10, 15 et 20 min à écart d'or égal, par catégorie, sur A et sur B (envahir.py).

    python3 analyse/export/exporter.py      (après lanes/dynamique.py, envahir.py, ganks.py et duree_degats.py)
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

CATALOGUE = ANALYSE / "catalogues" / "catalogue_unifie.csv"          # les 10 types (classification) et l'identifiant Riot
ANCIEN = ANALYSE / "catalogues" / "ancien_catalogue_2026-10-24.csv"  # catégories de jungler des ganks et d'envahir
ULTIMES = ANALYSE / "catalogues" / "ultimes_a_surveiller.csv"       # ultimes à surveiller, relus à la main
NOTES = ANALYSE / "types" / "resultats" / "notes.csv"                # notes de chaque type, et « fragile »
STYLES_AFFICHES = 2                                                   # en plus de Carry ou Enchanteur
SORTS = ANALYSE / "catalogues" / "sorts.csv"                         # sorts par catégorie (Data Dragon)
LANES_RES = ANALYSE / "lanes" / "resultats"
RECUIT_RES = ANALYSE / "recuit" / "resultats"
CONFIRMATION_RES = ANALYSE / "confirmation" / "resultats"
SORTIE = ICI / "assistant_donnees.json"


MIX_IMPOSE = {"magique < 20 %": -3.0, "magique > 70 %": -3.0}   # points de victoire, choix du propriétaire

TYPES = ("carry", "enchanteur", "assassin", "plongeur", "attrapeur", "tank", "bloqueur", "dueliste", "splitpusher", "teamfighter")


def catalogue():
    """Pour chaque champion : ses types et sa catégorie de jungler de l'ancien catalogue (« groupe », seulement pour les
    ganks et envahir, confirmés avec ces catégories).
    - « tous » : tous ses types du catalogue unifié ;
    - « types » : ceux que l'assistant affiche : Carry ou Enchanteur s'il l'est, plus ses deux autres types les mieux notés
      (notes de analyse/types/resultats/notes.csv), choix du propriétaire du 26/10/2026 ;
    - « fragile » : il encaisse peu (notes.csv) ; l'assistant en fait une cible même s'il n'est ni carry ni enchanteur."""
    notes = {}
    if NOTES.exists():
        with open(NOTES, encoding="utf-8", newline="") as f:
            notes = {l["champion"]: l for l in csv.DictReader(f, delimiter=";")}
    note = lambda c, t: float((notes.get(c) or {}).get(t) or 0)
    sortie = {}
    with open(CATALOGUE, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            c, tous = l["champion"], [t for t in TYPES if l.get(t) == "oui"]
            cible = [t for t in ("carry", "enchanteur") if t in tous]
            autres = sorted((t for t in tous if t not in cible), key=lambda t: (-note(c, t), TYPES.index(t)))[:STYLES_AFFICHES]
            sortie[c] = {"types": cible + autres, "tous": tous, "id": l.get("id_riot", ""), "groupe": "",
                         "fragile": (notes.get(c) or {}).get("fragile") == "oui" and "tank" not in tous}
    if ANCIEN.exists():
        with open(ANCIEN, encoding="utf-8", newline="") as f:
            for l in csv.DictReader(f, delimiter=";"):
                sortie.setdefault(l["champion"], {"types": [], "tous": [], "id": "", "groupe": "", "fragile": False})["groupe"] = l["groupe_teamfight"]
    return sortie


def ultimes():
    """Les ultimes à surveiller que les catégories de sorts ne voient pas seules (combinaisons avec un passif, grosses zones
    de dégâts, repoussements), relus à la main : {champion: raison} (catalogues/ultimes_a_surveiller.csv)."""
    if not ULTIMES.exists():
        return {}
    with open(ULTIMES, encoding="utf-8", newline="") as f:
        return {l["champion"]: l["raison"] for l in csv.DictReader(f, delimiter=";")}


def sorts():
    """Sorts par catégorie exclusive (contrôle, déplacement, protection), d'après Data Dragon : {champion: [[touche, nom, catégorie, détail]]}."""
    if not SORTS.exists():
        return {}
    sortie = {}
    with open(SORTS, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            sortie.setdefault(l["champion"], []).append([l["touche"], l["sort"], l["categorie"], l["detail"]])
    return sortie


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
    fichiers = sorted(RECUIT_RES.glob("recuit2_teamfight_*.json"))
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


def confirmation_c():
    """Ce qui a été confirmé sur C (parties jamais vues). L'assistant n'affiche que ça : sans fichier de confirmation,
    un bloc est considéré comme non confirmé."""
    lire = lambda chemin: json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else None
    ok = lambda d: bool(d) and d.get("verdict") == "confirmé"
    # Analyses de nos parties : la vérification sur B (toutes les parties, recalculée à chaque génération) passe avant
    # l'ancienne confirmation sur C du 24/10/2026, qui ne sert plus que si B n'a pas été calculé.
    gen = lire(CONFIRMATION_RES / "verification_B.json") or lire(CONFIRMATION_RES / "confirmation_C.json") or {}
    dd = lire(CONFIRMATION_RES / "verification_B_duree_degats.json") or lire(CONFIRMATION_RES / "confirmation_C_duree_degats.json") or {}
    recuits = sorted(CONFIRMATION_RES.glob("confirmation_C_recuit2_teamfight_*.json"))
    rec = lire(recuits[-1]) if recuits else None
    lola = {t["nom"]: ok(t) for t in gen.get("lolalytics", {}).get("tests", [])}
    return {
        "parties_C": gen.get("lolalytics", {}).get("parties"),
        "mesure": gen.get("mesure", "C"),
        "force": lola.get("Force du patch", False),
        "contre_direct": lola.get("Contre de l'adversaire direct", False),
        "contres_autres": lola.get("Contres des autres adversaires", False),
        "lanes": bool(gen.get("lanes")) and all(ok(d) for d in gen["lanes"].values()),
        "ganks": bool(gen.get("ganks")) and all(ok(t) for t in gen["ganks"]["tests"]),
        "envahir": [[t["minute"], t["groupe"]] for t in gen.get("envahir", {}).get("tests", []) if ok(t)],
        "tempo": ok(dd.get("late")),
        "mix": [titre for titre, m in dd.get("mix", {}).items() if ok(m)],
        "teamfight": {"recuit": rec["recuit"] if rec else None,
                      "effets": [e["nom"] for e in (rec or {}).get("effets", []) if ok(e)]},
    }


def duels():
    """Duels (lanes/duels.py), analyse à deux tas : appris sur A, vérifié sur B. Rien si le modèle d'ensemble ne tient
    pas sur B. Un champion dont la force n'est pas vérifiée sur B compte comme un champion moyen de son poste : sa force
    ET son évolution avec la minute valent 0 (avant le 26/10/2026, l'évolution restait : il n'était pas vraiment moyen).
    L'évolution avec la minute n'est gardée que si elle est vérifiée sur B. Or et niveau : avance sur la normale du poste."""
    modele = LANES_RES / "duels.json"
    if not modele.exists():
        return None
    m = json.loads(modele.read_text(encoding="utf-8"))
    if "verification_B" not in m or "postes" not in m:
        return None
    ensemble, minute = (t["verdict"] == "vérifié" for t in m["verification_B"]["ensemble"])
    if not ensemble:
        return None
    verifies = {ch for ch, v in m["champions"].items() if v.get("verdict_B") == "vérifié"}
    return {"or_1000": m["coef_or_1000"], "niveau": m["coef_niveau"], "minute_ref": m["minute_reference"],
            "postes": {p: [round(v["effet"], 4), round(v["pente_10min"], 4) if minute else 0.0] for p, v in m["postes"].items()},
            "champions": {ch: [round(v["force"], 4), round(v["pente_10min"], 4) if minute else 0.0] if ch in verifies else [0.0, 0.0]
                          for ch, v in m["champions"].items() if v["duels"] >= 150},
            "confirmes": sorted(verifies), "duels": m["duels"]}


def main():
    conf = confirmation_c()
    tf = teamfight()
    # Effets du recuit : seulement ceux confirmés sur C, et seulement si la confirmation porte sur ce recuit.
    garder = set(conf["teamfight"]["effets"]) if conf["teamfight"]["recuit"] == tf["recuit"] else set()
    tf["effets"] = [e for e in tf["effets"] if e["nom"] in garder]
    dd = (json.loads((LANES_RES / "duree_degats.json").read_text(encoding="utf-8"))
          if (LANES_RES / "duree_degats.json").exists() else None)
    if dd:
        dd["mix"] = {k: dict(m, tient=m["tient"] and k in conf["mix"]) for k, m in dd["mix"].items()}
        # Choix du propriétaire (26/10/2026) : une équipe presque toute AD (moins de 20 % de magique) ou toute AP (plus de
        # 70 %) compte toujours −3 points, même si l'effet n'est qu'« à surveiller » sur B (−4 à −5 points mesurés).
        for k, pts in MIX_IMPOSE.items():
            if k in dd["mix"]:
                dd["mix"][k].update(tient=True, AB=math.log((0.5 + pts / 100) / (0.5 - pts / 100)), impose=True)
        if not conf["tempo"]:
            dd["coef_late"]["retenu"] = 0.0
    envm = json.loads((LANES_RES / "envahir.json").read_text(encoding="utf-8"))
    for m, s in envm.items():
        s["confirme_C"] = [g for mm, g in conf["envahir"] if str(mm) == str(m)]
    donnees = {
        "date": datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M"),
        "catalogue": catalogue(),
        "sorts": sorts(),
        "ultimes": ultimes(),
        "lanes": lanes(),
        "ganks": json.loads((LANES_RES / "ganks_modele.json").read_text(encoding="utf-8")),
        "teamfight": tf,
        "envahir_minutes": envm,
        # Mix de dégâts et early / late (lanes/duree_degats.py), filtrés par la confirmation sur C.
        "duree_degats": dd,
        "confirmation_C": conf,
        "duels": duels(),
    }
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Export : {SORTIE} ({SORTIE.stat().st_size // 1024} Ko) ; {donnees['lanes']['parties']} parties pour les lanes, "
          f"{len(donnees['teamfight']['effets'])} effets teamfight confirmés sur C ; confirmation : {conf}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
