"""Envahir la jungle adverse à 5, 10, 15 et 20 minutes : est-ce que ça va avec plus de victoires,
à écart d'or égal ?

Pour chaque minute M (5, 10, 15, 20), d'après la timeline :
- le jungler « envahit » s'il est dans la jungle adverse (au-delà de la rivière, hors des lanes) ;
- l'écart d'or entre les deux équipes à M.
Plus la partie avance, plus un jungler envahit PARCE QUE son équipe est déjà devant. On compare donc
les junglers qui envahissent à ceux qui ne le font pas, à force de champions égale ET à écart d'or égal
au même moment (régression logistique : force des champions + écart d'or à M + envahit).
Le reste de l'effet est ce que l'invasion « ajoute » ; ça reste une association (le jungler qui envahit
peut aussi être le meilleur joueur), pas une cause prouvée.

Résultats par catégorie de jungler (groupes teamfight) et selon la priorité annoncée par la draft
(mid et bot annoncés devant), appris séparément sur A et sur B pour voir s'ils tiennent.
Seules les parties qui durent au moins M + 1 minutes comptent pour la minute M.

    python3 analyse/lanes/envahir.py      (après dynamique.py)
"""

import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "contres"))
sys.path.insert(0, str(ICI.parent / "iteratif"))

import lecture  # noqa: E402
import contres  # noqa: E402
import commun  # noqa: E402
import bloc2_compos as bloc2  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402
from dynamique import GROUPES, RESULTATS, lire_catalogue  # noqa: E402
from comportement import zone  # noqa: E402

MINUTES = (5, 10, 15, 20)


def points(b):
    return 100 * (1 / (1 + math.exp(-b)) - 0.5)


def main():
    donnees = contres.dossier_donnees()
    table = commun.drafts(commun.lire_decoupage(), donnees)
    table = table[table["tas"].isin(["A", "B"])].reset_index(drop=True)
    pred = {}
    with gzip.open(RESULTATS / "predictions.csv.gz", "rt", encoding="utf-8") as f:
        for l in csv.DictReader(f, delimiter=";"):
            pred[l["match"]] = {k[3:]: float(v) for k, v in l.items() if k.startswith("or_")}
    matchs = set(pred) & lecture.matchs_presents("timeline_joueurs", donnees)
    joueur = {}
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        joueur[(j["match"], j["participant"])] = (j["equipe"], j["poste"])
    zones = defaultdict(dict)                # (match, minute) -> {equipe: zone du jungler}
    ors = defaultdict(lambda: defaultdict(float))   # (match, minute) -> {equipe: or de l'équipe}
    complet = defaultdict(int)
    for t in lecture.lire_details("timeline_joueurs", donnees, matchs=matchs):
        e, poste = joueur.get((t["match"], t["participant"]), (None, None))
        if e is None:
            continue
        for m in MINUTES:
            if not t[f"or_{m}"]:
                continue
            ors[(t["match"], m)][e] += float(t[f"or_{m}"])
            complet[(t["match"], m)] += 1
            if poste == "jgl" and t[f"x_{m}"]:
                zones[(t["match"], m)][e] = zone(float(t[f"x_{m}"]), float(t[f"y_{m}"]), e)
    groupe = lire_catalogue()
    index = bloc2.Index(table)
    la = np.where(table["tas"] == "A")[0]; lb = np.where(table["tas"] == "B")[0]
    force = bloc3.Force(index, la)
    dec_a, (dec_b,) = force.decalages(la, [lb])
    dec = np.zeros(len(table)); dec[la] = dec_a; dec[lb] = dec_b
    y = index.y

    sortie, texte = {}, ["# Envahir la jungle adverse, de 5 à 20 minutes", "",
                         "- Envahir à M min : le jungler est dans la jungle adverse à cet instant (hors rivière et lanes).",
                         "- Effet = points de victoire en plus quand le jungler envahit, **à force de champions égale et à écart d'or "
                         "égal à M min**. Appris séparément sur A et sur B : un effet qui tient a le même signe des deux côtés.",
                         "- Association, pas cause prouvée : un jungler qui envahit peut aussi être un meilleur joueur.", ""]
    for m in MINUTES:
        rangs, lignes = [], []
        for i, match in enumerate(table["match"]):
            z = zones.get((match, m), {})
            if complet[(match, m)] != 10 or len(z) != 2:
                continue
            o = ors[(match, m)]
            gb, gr = groupe.get(table["b_jgl"][i], ""), groupe.get(table["r_jgl"][i], "")
            ib, ir = float(z["b"] == "adverse"), float(z["r"] == "adverse")
            p = pred.get(match, {})
            prio_b = p.get("mid", 0) > 200 and p.get("bot", 0) > 200
            prio_r = p.get("mid", 0) < -200 and p.get("bot", 0) < -200
            x = {"ecart d'or": (o["b"] - o["r"]) / 1000, "envahit": ib - ir,
                 "envahit avec mid et bot annoncés devant": ib * prio_b - ir * prio_r}
            for g in GROUPES:
                x[f"envahit × {g}"] = ib * (gb == g) - ir * (gr == g)
            rangs.append(i); lignes.append(x)
        rangs = np.array(rangs)
        noms = list(lignes[0])
        X = np.array([[l[k] for k in noms] for l in lignes])
        nb_inv = defaultdict(int)
        for l, i in zip(lignes, rangs):
            for e in "br":
                if zones[(table["match"][i], m)][e] == "adverse":
                    nb_inv[groupe.get(table[f"{e}_jgl"][i], "")] += 1
        res = {}
        for tas in ("A", "B"):
            sel = np.array([table["tas"][i] == tas for i in rangs])
            beta, _ = bloc3.logistique(X[sel], y[rangs[sel]], dec[rangs[sel]], lam=10.0)
            res[tas] = dict(zip(noms, beta.tolist()))
        envahisseurs = sum(nb_inv.values())
        sortie[m] = {"parties": int(len(rangs)), "part_envahit": envahisseurs / (2 * len(rangs)),
                     "or_1000": {t: points(res[t]["ecart d'or"]) for t in "AB"},
                     "envahit": {t: points(res[t]["envahit"]) for t in "AB"},
                     "avec_prio": {t: points(res[t]["envahit"] + res[t]["envahit avec mid et bot annoncés devant"]) for t in "AB"},
                     "groupes": {g: {"A": points(res["A"]["envahit"] + res["A"][f"envahit × {g}"]),
                                     "B": points(res["B"]["envahit"] + res["B"][f"envahit × {g}"]), "envahisseurs": nb_inv[g]}
                                 for g in GROUPES}}
        s = sortie[m]
        tient = lambda d: "oui" if d["A"] * d["B"] > 0 and min(abs(d["A"]), abs(d["B"])) >= 1 else "non"
        texte += [f"## À {m} minutes", "",
                  f"- {s['parties']} parties ; {100 * s['part_envahit']:.1f} % des junglers sont dans la jungle adverse.",
                  f"- Repère : 1 000 or d'avance à {m} min = {s['or_1000']['A']:+.1f} points (A), {s['or_1000']['B']:+.1f} (B).",
                  f"- **Envahir, à or égal : {s['envahit']['A']:+.1f} points sur A, {s['envahit']['B']:+.1f} sur B** (tient : {tient(s['envahit'])}).",
                  f"- Envahir avec mid et bot annoncés devant : {s['avec_prio']['A']:+.1f} (A), {s['avec_prio']['B']:+.1f} (B).", "",
                  "| Jungler | A | B | tient | junglers qui envahissent |", "|---|---|---|---|---|"]
        for g, d in s["groupes"].items():
            texte.append(f"| {g} | {d['A']:+.1f} | {d['B']:+.1f} | {tient(d)} | {d['envahisseurs']} |")
        texte.append("")
    (RESULTATS / "envahir.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    (RESULTATS / "envahir.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
