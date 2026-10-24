"""Point 3, étape 3 : envahir ou pas, et de quel côté jouer, selon la draft.

Ce que fait le jungler, mesuré avec sa position à 5 et 10 minutes (timeline) :
- **envahit à 5 min** : il est dans la jungle adverse (au-delà de la rivière, hors des lanes) ;
- **côté joué** à 5 et 10 min : côté top, côté bot ou mid (au-dessus ou au-dessous de la diagonale de la carte).
Ce que la draft annonce (dynamique.py, prédictions hors échantillon) : l'écart d'or attendu à 15 min sur
chaque lane, donc les lanes qui devraient avoir la priorité.

Questions :
1. Envahir à 5 min va-t-il avec plus de victoires, à force de champions égale ? Et cela dépend-il de la
   priorité annoncée du mid et du bot (qui peuvent suivre), du duel de jungle annoncé, et de la catégorie
   du jungler ?
2. Jouer du côté de la lane annoncée la plus forte (top ou bot) va-t-il avec plus de victoires ?
Appris sur A, vérifié sur B. Attention : ce sont des comportements en partie, pas la draft. Un jungler
peut envahir parce que ses lanes ont VRAIMENT la priorité ce jour-là. On regarde tôt (5 et 10 min) pour
limiter cet effet, mais ces résultats disent « ça va avec », pas « ça cause ».

    python3 analyse/lanes/comportement.py     (après dynamique.py)
"""

import csv
import gzip
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

RIVIERE = 14800          # la rivière suit la diagonale x + y ≈ 14 800 (base bleue en bas à gauche)
MARGE = 1200


def zone(x, y, equipe):
    """« adverse » si le joueur est dans la jungle adverse, « allie » dans la sienne, « lane » sur une lane."""
    if x < 2500 or y > 12500 or y < 2500 or x > 12500 or abs(x - y) < 1500:
        return "lane"
    s = x + y
    if equipe == "b":
        return "adverse" if s > RIVIERE + MARGE else ("allie" if s < RIVIERE - MARGE else "riviere")
    return "adverse" if s < RIVIERE - MARGE else ("allie" if s > RIVIERE + MARGE else "riviere")


def cote(x, y):
    if abs(x - y) < 1500:
        return "mid"
    return "top" if y > x else "bot"


def main():
    donnees = contres.dossier_donnees()
    regle = commun.lire_decoupage()
    table = commun.drafts(regle, donnees)
    table = table[table["tas"].isin(["A", "B"])].reset_index(drop=True)
    pred = {}
    with gzip.open(RESULTATS / "predictions.csv.gz", "rt", encoding="utf-8") as f:
        for l in csv.DictReader(f, delimiter=";"):
            pred[l["match"]] = {k[3:]: float(v) for k, v in l.items() if k.startswith("or_")}
    matchs = set(pred)
    jungler = {}
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        if j["poste"] == "jgl":
            jungler[(j["match"], j["participant"])] = j["equipe"]
    pos = defaultdict(dict)
    for t in lecture.lire_details("timeline_joueurs", donnees, matchs=matchs):
        k = (t["match"], t["participant"])
        if k in jungler and t["x_5"] and t["x_10"]:
            e = jungler[k]
            pos[t["match"]][e] = {"zone5": zone(float(t["x_5"]), float(t["y_5"]), e),
                                  "cote5": cote(float(t["x_5"]), float(t["y_5"])), "cote10": cote(float(t["x_10"]), float(t["y_10"]))}
    groupe = lire_catalogue()
    garder = [i for i, m in enumerate(table["match"]) if m in pred and len(pos.get(m, {})) == 2]
    table = table.iloc[garder].reset_index(drop=True)
    index = bloc2.Index(table)
    la = np.where(table["tas"] == "A")[0]; lb = np.where(table["tas"] == "B")[0]
    force = bloc3.Force(index, la)
    dec_a, (dec_b,) = force.decalages(la, [lb])
    y = index.y

    def vue(m, e):
        """Ce que voit le jungler de l'équipe e : ses lanes annoncées (or, positif = devant)."""
        s = 1 if e == "b" else -1
        return {lane: s * pred[m][lane] / 1000 for lane in ("top", "jgl", "mid", "bot")}

    def caracteristiques(rangs):
        noms, cols = [], defaultdict(list)
        for i in rangs:
            m = table["match"][i]
            for e, signe in (("b", 1), ("r", -1)):
                p, z = vue(m, e), pos[m][e]
                inv = 1.0 if z["zone5"] == "adverse" else 0.0
                fort = "top" if p["top"] > p["bot"] else "bot"
                bon_cote = 1.0 if z["cote10"] == fort else 0.0
                g = groupe.get(table[f"{e}_jgl"][i], "")
                valeurs = {"envahit": inv, "envahit × mid annoncé devant": inv * p["mid"],
                           "envahit × bot annoncé devant": inv * p["bot"], "envahit × duel de jungle annoncé": inv * p["jgl"],
                           "joue côté de la lane la plus forte (10 min)": bon_cote,
                           "côté fort × écart entre top et bot annoncés": bon_cote * abs(p["top"] - p["bot"])}
                for gg in GROUPES:
                    valeurs[f"envahit × {gg}"] = inv * (g == gg)
                for k, v in valeurs.items():
                    if e == "b":
                        cols[k].append(v)
                    else:
                        cols[k][-1] -= v
        noms = list(cols)
        return np.column_stack([cols[k] for k in noms]), noms

    Xa, noms = caracteristiques(la); Xb, _ = caracteristiques(lb)
    beta, _ = bloc3.logistique(Xa, y[la], dec_a, lam=30.0)
    perte = lambda d, X: bloc3.perte_log(y[lb], bloc3.sigmoide(d + X))
    gain_b = 1000 * (perte(dec_b, 0) - perte(dec_b, Xb @ beta))

    # Taux bruts (à force de champions égale) : jungler qui envahit contre jungler qui n'envahit pas.
    def taux(rangs, dec, condition):
        res = []
        for i_, i in enumerate(rangs):
            m = table["match"][i]
            for e in "br":
                if condition(m, e, i):
                    gagne = y[i] if e == "b" else 1 - y[i]
                    attendu = bloc3.sigmoide(np.array([dec[i_]]))[0]
                    attendu = attendu if e == "b" else 1 - attendu
                    res.append(gagne - attendu)
        return (0.5 + float(np.mean(res)), len(res)) if res else (math.nan, 0)

    inv = lambda m, e, i: pos[m][e]["zone5"] == "adverse"
    texte = ["# Envahir et choisir son côté, d'après la draft", "",
             f"- Parties avec la position des deux junglers : A = {len(la)}, B = {len(lb)}.",
             f"- Junglers dans la jungle adverse à 5 min : {100 * np.mean([pos[m][e]['zone5'] == 'adverse' for m in table['match'] for e in 'br']):.1f} %.",
             f"- Jugement sur B de l'ensemble des effets ci-dessous : {gain_b:+.3f} millièmes (positif = ils tiennent).",
             "- Ce sont des associations (comportements en partie), pas des causes.", "",
             "## Effets appris sur A (en points de victoire, à force de champions égale)", "", "| Effet | Points |", "|---|---|"]
    for n, b in zip(noms, beta):
        texte.append(f"| {n} | {100 * (bloc3.sigmoide(np.array([b]))[0] - 0.5):+.1f} |")
    texte += ["", "## Envahir à 5 min : taux de victoire à force de champions égale", "",
              "| Situation | A | B |", "|---|---|---|"]
    situations = {
        "tous les junglers qui envahissent": inv,
        "envahit, mid et bot annoncés devant": lambda m, e, i: inv(m, e, i) and vue(m, e)["mid"] > 0.2 and vue(m, e)["bot"] > 0.2,
        "envahit, mid et bot annoncés derrière": lambda m, e, i: inv(m, e, i) and vue(m, e)["mid"] < -0.2 and vue(m, e)["bot"] < -0.2,
        "envahit, duel de jungle annoncé gagné": lambda m, e, i: inv(m, e, i) and vue(m, e)["jgl"] > 0.3,
        "envahit, duel de jungle annoncé perdu": lambda m, e, i: inv(m, e, i) and vue(m, e)["jgl"] < -0.3,
    }
    for gg in GROUPES:
        situations[f"envahit, jungler {gg}"] = (lambda g_: lambda m, e, i: inv(m, e, i) and groupe.get(table[f"{e}_jgl"][i], "") == g_)(gg)
    for nom, cond in situations.items():
        ta, na = taux(la, dec_a, cond); tb, nb = taux(lb, dec_b, cond)
        texte.append(f"| {nom} | {100 * ta:.1f} % ({na}) | {100 * tb:.1f} % ({nb}) |")
    texte.append("")
    (RESULTATS / "comportement.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
