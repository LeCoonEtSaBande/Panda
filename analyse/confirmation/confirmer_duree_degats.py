"""Confirmation sur C du mix de dégâts et de l'early / late (profils et sens figés par duree_degats.py sur A + B).

- early / late : coefficient de « écart de pente × durée » sur C, à force de champions égale (force apprise sur A + B) ;
- mix : points de victoire des équipes dans chaque tranche de part magique, sur C, dans le sens mesuré sur A + B.
Écrit confirmation/resultats/confirmation_C_duree_degats.md et .json.

    python3 analyse/confirmation/confirmer_duree_degats.py
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "contres"))
sys.path.insert(0, str(ICI.parent / "base"))
sys.path.insert(0, str(ICI.parent / "lanes"))

import lecture  # noqa: E402
import contres  # noqa: E402
import commun  # noqa: E402
import bloc2_compos as bloc2  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402
from dynamique import RESULTATS as LANES_RES  # noqa: E402
from duree_degats import POSTES, T, TRANCHES_DUREE, points  # noqa: E402

RESULTATS_C = ICI / "resultats"


def coef_et_erreur(x, y, dec):
    """Coefficient d'une seule variable (avec décalage) et son erreur type."""
    b, _ = bloc3.logistique(x[:, None], y, dec, lam=1e-6)
    mu = bloc3.sigmoide(dec + x * b[0])
    return float(b[0]), float(1 / math.sqrt(max(np.sum(mu * (1 - mu) * x * x), 1e-12)))


def p_unilaterale(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def main():
    dd = json.loads((LANES_RES / "duree_degats.json").read_text(encoding="utf-8"))
    donnees = contres.dossier_donnees()
    regle = commun.lire_decoupage()
    commun.exiger_validation(regle)
    table = commun.drafts(regle, donnees).reset_index(drop=True)
    duree = {r["match"]: float(r["duree_s"]) / 60 for r in lecture.lire_details("details_parties", donnees) if r["duree_s"]}
    index = bloc2.Index(table)
    lab = np.where(table["tas"].isin(["A", "B"]))[0]; lc = np.where(table["tas"] == "C")[0]
    force = bloc3.Force(index, lab)
    _, (dec_c,) = force.decalages(lab, [lc])
    y = index.y.astype(float)[lc]
    late, degats = dd["late"], dd["degats"]

    # Early / late
    avec = np.array([table["match"][i] in duree for i in lc])
    S = np.array([sum(late[p].get(table[f"b_{p}"][i], 0.0) for p in POSTES) - sum(late[p].get(table[f"r_{p}"][i], 0.0) for p in POSTES)
                  for i in lc])
    TT = np.array([T(duree.get(table["match"][i], 30.0)) for i in lc])
    b, e = coef_et_erreur((S * TT)[avec], y[avec], dec_c[avec])
    p_late = p_unilaterale(b / e)
    med = float(np.median(np.abs(S[avec])))
    tranches = []
    for a, z in TRANCHES_DUREE:
        sel = np.array([avec[k] and abs(S[k]) > med and a <= duree[table["match"][lc[k]]] < z for k in range(len(lc))])
        if sel.sum():
            gagne = np.where(S[sel] > 0, y[sel], 1 - y[sel])
            tranches.append({"de": a, "a": z, "parties": int(sel.sum()), "late_gagne": round(100 * float(gagne.mean()), 1)})

    # Mix de dégâts
    def part_magique(i, e):
        s = np.zeros(3)
        for p in POSTES:
            d = degats[p].get(table[f"{e}_{p}"][i])
            if d:
                s += np.array(d[:3]) * d[3]
        return s[1] / s.sum() if s.sum() else 0.5
    mag = {e: np.array([part_magique(i, e) for i in lc]) for e in "br"}
    mix = {}
    for titre, m in dd["mix"].items():
        x = (((mag["b"] >= m["de"]) & (mag["b"] < m["a"] + (m["a"] >= 1))).astype(float)
             - ((mag["r"] >= m["de"]) & (mag["r"] < m["a"] + (m["a"] >= 1))).astype(float))
        bm, em = coef_et_erreur(x, y, dec_c)
        sens = -1 if m["AB"] < 0 else 1
        pm = p_unilaterale(sens * bm / em)
        mix[titre] = {"points_AB": round(points(m["AB"]), 1), "points_C": round(points(bm), 1), "equipes_C": int(np.abs(x).sum()), "p": pm}
    tests = [p_late] + [m["p"] for m in mix.values()]
    q = bloc3.benjamini_hochberg(tests)
    verdict = lambda p, qq: "confirmé" if qq < 0.05 else ("à surveiller" if p < 0.05 else "rien")
    sortie = {"parties_C": int(len(lc)), "parties_C_avec_duree": int(avec.sum()),
              "late": {"coef_C": b, "erreur_C": e, "coef_AB": dd["coef_late"]["AB"], "p": p_late, "q": float(q[0]),
                       "verdict": verdict(p_late, q[0]), "tranches_C": tranches},
              "mix": {t: dict(m, q=float(qq), verdict=verdict(m["p"], qq)) for (t, m), qq in zip(mix.items(), q[1:])}}
    (RESULTATS_C / "confirmation_C_duree_degats.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    L = sortie["late"]
    texte = ["# Confirmation sur C : early / late et mix de dégâts", "",
             f"- Profils et sens figés sur A + B (duree_degats.py, profils {', '.join(f'{k} {v}' for k, v in dd['sources'].items())}). "
             f"Mesuré sur C : {len(lc)} parties, dont {int(avec.sum())} avec durée. Force des champions apprise sur A + B.", "",
             f"## Early / late : **{L['verdict']}**", "",
             f"- Coefficient sur C {b:.2f} (± {e:.2f}), sur A + B {dd['coef_late']['AB']:.2f}.",
             f"- Sur C, quand une équipe est nettement plus late (écart au-dessus de la médiane, {med:.2f}) :", "",
             "| Durée | Parties | L'équipe late gagne |", "|---|---|---|"]
    texte += [f"| {t['de']}-{t['a'] if t['a'] < 999 else '…'} min | {t['parties']} | {t['late_gagne']} % |" for t in tranches]
    texte += ["", "## Mix de dégâts", "", "| Part magique | Sur A + B | Sur C | Équipes de C | Verdict |", "|---|---|---|---|---|"]
    texte += [f"| {t} | {m['points_AB']:+.1f} | {m['points_C']:+.1f} | {m['equipes_C']} | {m['verdict']} |" for t, m in sortie["mix"].items()]
    texte.append("")
    (RESULTATS_C / "confirmation_C_duree_degats.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
