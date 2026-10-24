"""Génère l'assistant de draft autonome (Assistant_Panda.html), une seule page sans connexion.

Sources :
- Lolalytics (branche scraping, analyse/lolalytics/<patch>/) : force des champions du patch à chaque poste,
  part de leurs parties à chaque poste (pour deviner le poste adverse), matchups du jungler contre chaque
  poste adverse et matchups lane contre lane ;
- nos analyses (branche analyse, analyse/export/assistant_donnees.json) : catalogue unifié (groupes
  teamfight), écart d'or attendu à 15 min sur chaque lane, ganks réussis avant 15 min, effets teamfight,
  envahir à 5 min.

    python3 assistant_panda/construire.py --lolalytics <dossier du patch> --export <assistant_donnees.json>
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

    mu_j, mu_l = {}, {}
    for m in matchups:
        n = int(m["parties"])
        d2, wr = float(m["delta_2"]), float(m["victoires"])
        if m["poste"] == "jgl" and n >= 30:
            mu_j.setdefault(m["champion"], {})[f"{m['poste_adversaire']}|{m['adversaire']}"] = [round(d2, 2), round(wr, 1), n]
        elif m["poste"] == m["poste_adversaire"] and n >= 100:
            mu_l[f"{m['poste']}|{m['champion']}|{m['adversaire']}"] = [round(d2, 2), round(wr, 1), n]

    noms = sorted(set(ex["catalogue"]) | {c["champion"] for c in champions if c["champion"] != "Kayn"}, key=str.lower)
    lanes = {p: {"f": v["forces"], "p": v["paires"], "s": round(v["ecart_type"]), "k": round(v["pente_victoire"], 4)}
             for p, v in ex["lanes"]["postes"].items()}
    donnees = {
        "meta": {"patch": patch, "export": ex["date"], "parties_lanes": ex["lanes"]["parties"],
                 "parties_ganks": ex["ganks"]["parties"]},
        "noms": noms,
        "cat": {c: [v["groupe"], v["tanky"], v["carry"], v["degats"]] for c, v in ex["catalogue"].items()},
        "tier": tier, "moy": moyenne, "mj": mu_j, "ml": mu_l, "lanes": lanes,
        "ganks": ex["ganks"], "tf": ex["teamfight"], "inv": ex["envahir"], "invm": ex.get("envahir_minutes", {}),
    }
    modele = (ICI / "modele.html").read_text(encoding="utf-8")
    page = modele.replace("__DONNEES__", json.dumps(donnees, ensure_ascii=False, separators=(",", ":")))
    Path(sortie).write_text(page, encoding="utf-8")
    print(f"Assistant : {sortie} ({Path(sortie).stat().st_size // 1024} Ko), patch {patch}, "
          f"{len(mu_j)} junglers avec matchups, {len(mu_l)} matchups de lane.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lolalytics", required=True)
    parser.add_argument("--export", required=True)
    parser.add_argument("--sortie", default=str(ICI.parent / "Assistant_Panda.html"))
    args = parser.parse_args()
    construire(args.lolalytics, args.export, args.sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
