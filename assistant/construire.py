"""Génère l'assistant de draft autonome (« Assistant Draft - DL - <date>.html »), une seule page sans connexion.

Sources :
- Lolalytics (branche scraping, lolalytics/<patch>/) : force des champions du patch à chaque poste, part de leurs
  parties à chaque poste (pour deviner le poste adverse), tous les matchups, dégâts par type, victoires selon la durée ;
- nos analyses (branche analyse, analyse/export/assistant_donnees.json) : catalogue unifié, écart d'or attendu à
  15 min sur chaque lane, ganks réussis avant 15 min, envahir, early/late, mix de dégâts, et la liste de ce qui
  est confirmé sur C (seul affiché) ;
- les sorts par catégorie et les identifiants Riot viennent aussi de l'export (catalogue mis à jour par Data Dragon).

    python3 assistant/construire.py --lolalytics <dossier du patch> --export <assistant_donnees.json>
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
POSTES = ("top", "jgl", "mid", "adc", "sup")


def lire_csv(chemin):
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def nombre(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def duree_degats(dd):
    """Mix de dégâts et early / late (analyse/lanes/duree_degats.py), en version compacte ; None si absent.

    deg[poste][champion] = [part physique, part magique, part brute, dégâts moyens par partie] ;
    late[poste][champion] = points de victoire (en fraction) par 10 min de partie en plus ;
    k = coefficient vérifié sur nos parties ; mix = [[de, à, coefficient]] pour les tranches de part magique qui tiennent.
    """
    if not dd:
        return None
    return {"deg": dd["degats"], "late": dd["late"], "k": round(dd["coef_late"]["retenu"], 3),
            "mix": [[m["de"], m["a"], round(m["AB"], 4), t] for t, m in dd["mix"].items() if m["tient"]],
            "tr": dd["tranches_B"], "parties": dd["parties"], "patch": dd.get("patch_lolalytics")}


def construire(dossier_lola, export, sortie):
    patch = Path(dossier_lola).name
    champions = lire_csv(Path(dossier_lola) / "champions.csv")
    matchups = lire_csv(Path(dossier_lola) / "matchups.csv")
    ex = json.loads(Path(export).read_text(encoding="utf-8"))

    tier = {p: {} for p in POSTES}
    for c in champions:
        wr, n, part, pick = nombre(c["victoires"]), int(c["parties"]), nombre(c["part_du_poste"]) or 0.0, nombre(c["pick"]) or 0.0
        if wr is not None and n > 0:
            tier[c["poste"]][c["champion"]] = [round(wr, 2), n, round(part, 2), round(pick, 2)]
    moyenne = {}
    for p, t in tier.items():
        n = sum(v[1] for v in t.values())
        moyenne[p] = round(sum(v[0] * v[1] for v in t.values()) / n, 2) if n else 50.0

    # Matchups de tous les postes, vus au moins 30 fois, en tableau compact :
    # mu[poste][indice du champion] = [poste adverse, indice de l'adversaire, delta_2 × 10, victoires × 10, parties, ...]
    lola_noms = sorted({m["champion"] for m in matchups} | {m["adversaire"] for m in matchups})
    indice = {n: i for i, n in enumerate(lola_noms)}
    code = {p: i for i, p in enumerate(POSTES)}
    mu = {p: {} for p in POSTES}
    for m in matchups:
        n = int(m["parties"])
        if n < 30 or m["poste"] not in code or m["poste_adversaire"] not in code:
            continue
        mu[m["poste"]].setdefault(indice[m["champion"]], []).extend(
            [code[m["poste_adversaire"]], indice[m["adversaire"]], round(float(m["delta_2"]) * 10), round(float(m["victoires"]) * 10), n])

    noms = sorted(set(ex["catalogue"]) | {c["champion"] for c in champions if c["champion"] != "Kayn"}, key=str.lower)
    lanes = {p: {"f": v["forces"], "p": v["paires"], "s": round(v["ecart_type"]), "k": round(v["pente_victoire"], 4)}
             for p, v in ex["lanes"]["postes"].items()}
    donnees = {
        "meta": {"patch": patch, "export": ex["date"], "parties_lanes": ex["lanes"]["parties"],
                 "parties_ganks": ex["ganks"]["parties"]},
        "noms": noms,
        # Catalogue : [catégorie de jungler de l'ancien catalogue (seulement pour les ganks et envahir), les styles affichés
        # (Carry ou Enchanteur, plus ses deux styles principaux), 1 s'il est fragile (une cible même sans être carry ni enchanteur)].
        "cat": {c: [v.get("groupe", ""), v.get("types", []), 1 if v.get("fragile") else 0] for c, v in ex["catalogue"].items()},
        "tier": tier, "moy": moyenne, "lola": lola_noms, "mu": mu, "lanes": lanes,
        "ganks": ex["ganks"], "tf": ex["teamfight"], "invm": ex.get("envahir_minutes", {}),
        "dd": duree_degats(ex.get("duree_degats")),
        # Ce qui est confirmé sur C (l'export a déjà retiré le reste) et contrôles des sorts (Data Dragon).
        "conf": ex.get("confirmation_C") or {},
        # Sorts par catégorie exclusive (contrôle, déplacement, protection), d'après Data Dragon (branche analyse).
        "sorts": ex.get("sorts") or {},
        # Ultimes à surveiller relus à la main (combinaisons avec un passif, grosses zones) : {champion: raison}.
        "ultis": ex.get("ultimes") or {},
        # Identifiant Riot -> nom (lien client) : Kayn n'a qu'un identifiant pour ses deux formes.
        "ids": {v["id"]: ("Kayn" if c.startswith("Kayn ") else c) for c, v in ex["catalogue"].items() if v.get("id")},
        # Duels : chacun avec l'or habituel de son poste ; forces vérifiées sur B seulement (None si le modèle ne tient pas).
        "duel": ex.get("duels"),
    }
    modele = (ICI / "modele.html").read_text(encoding="utf-8")
    page = modele.replace("__DONNEES__", json.dumps(donnees, ensure_ascii=False, separators=(",", ":")))
    Path(sortie).write_text(page, encoding="utf-8")
    print(f"Assistant : {sortie} ({Path(sortie).stat().st_size // 1024} Ko), patch {patch}, "
          f"{sum(len(v) for v in mu.values())} champions-postes avec matchups.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lolalytics", required=True)
    parser.add_argument("--export", required=True)
    parser.add_argument("--sortie", help="par défaut : « Assistant Draft - DL - <date>.html » à la racine")
    args = parser.parse_args()
    if not args.sortie:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        date = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
        args.sortie = str(ICI.parent / f"Assistant Draft - DL - {date}.html")
    construire(args.lolalytics, args.export, args.sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
