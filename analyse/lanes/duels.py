"""Duels de junglers : quand les deux junglers se croisent et que l'un tue l'autre seul, qui gagne, à or égal ?

Un duel = un kill de champion où le tueur et la victime sont les deux junglers, sans assistance, et où seul le
tueur a infligé des dégâts de champion à la victime (nb_sources = 1). On ne voit que les duels qui finissent en
kill : un duel où les deux repartent vivants n'est pas compté.

Pour chaque duel : l'écart d'or (or total gagné, interpolé entre les relevés de la timeline à 5, 10, 15, 20, 25 et
30 min) et l'écart de niveau au moment du kill. Modèle (régression logistique régularisée, une ligne par duel,
du point de vue du jungler bleu) :
    victoire du bleu ~ force en duel du champion bleu − celle du rouge
                       + évolution de cette force avec la minute (certains junglers sont forts tôt, d'autres tard)
                       + écart d'or + écart de niveau
La force en duel « à or et niveau égaux » est donc ce que le champion gagne en plus ou en moins, toutes choses
égales. Appris sur A, vérifié sur B (gain de prédiction par rapport à l'or et au niveau seuls, et accord des forces
apprises séparément sur A et sur B). C (après le gel) n'est pas lu : la confirmation viendra après la prochaine collecte.
Écrit resultats/duels.json et resultats/duels.md.

    python3 analyse/lanes/duels.py
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "contres"))
sys.path.insert(0, str(ICI.parent / "base"))

import lecture  # noqa: E402
import contres  # noqa: E402
import commun  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402
from dynamique import RESULTATS  # noqa: E402

MINUTES = (0, 5, 10, 15, 20, 25, 30)
MINUTE_REF = 13.0          # les évolutions avec le temps sont centrées sur la minute médiane des duels
POOL = ("Fiddlesticks", "Ivern", "Dr. Mundo", "Kayn bleu", "Kayn rouge", "Viego", "Maokai", "Skarner", "Morgana", "Urgot")


def interpoler(releves, t):
    """Valeur à la minute t, interpolée entre les relevés {minute: valeur} ; None si hors des relevés."""
    xs = sorted(m for m, v in releves.items() if v is not None)
    if not xs or t > xs[-1]:
        return None
    for a, b in zip(xs, xs[1:]):
        if a <= t <= b:
            return releves[a] + (releves[b] - releves[a]) * (t - a) / (b - a)
    return releves[xs[0]]


def lire_duels(donnees, tas):
    matchs = {m for m, t in tas.items() if t in ("A", "B")} & lecture.matchs_presents("timeline_joueurs", donnees)
    jungler = {}                                   # (match, participant) -> (equipe, champion)
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        if j["poste"] == "jgl":
            jungler[(j["match"], j["participant"])] = (j["equipe"], j["champion"])
    releves = {}
    for t in lecture.lire_details("timeline_joueurs", donnees, matchs=matchs):
        cle = (t["match"], t["participant"])
        if cle not in jungler:
            continue
        val = lambda col: float(t[col]) if t[col] else None
        releves[cle] = ({0: 500.0, **{m: val(f"or_{m}") for m in MINUTES[1:]}},
                        {0: 1.0, **{m: val(f"niveau_{m}") for m in MINUTES[1:]}})
    duels = []
    for e in lecture.lire_details("evenements", donnees, matchs=matchs):
        if e["type"] != "CHAMPION_KILL" or e["assistants"] or e["nb_sources"] != "1":
            continue
        k, v = (e["match"], e["participant"]), (e["match"], e["victime"])
        if k not in jungler or v not in jungler or k not in releves or v not in releves:
            continue
        minute = float(e["t_ms"]) / 60000
        ok, ov = interpoler(releves[k][0], minute), interpoler(releves[v][0], minute)
        nk, nv = interpoler(releves[k][1], minute), interpoler(releves[v][1], minute)
        if None in (ok, ov, nk, nv):
            continue
        (ek, ck), (_, cv) = jungler[k], jungler[v]
        # Point de vue du jungler bleu.
        if ek == "b":
            duels.append({"match": e["match"], "tas": tas[e["match"]], "bleu": ck, "rouge": cv, "bleu_gagne": 1,
                          "or": ok - ov, "niveau": nk - nv, "minute": minute})
        else:
            duels.append({"match": e["match"], "tas": tas[e["match"]], "bleu": cv, "rouge": ck, "bleu_gagne": 0,
                          "or": ov - ok, "niveau": nv - nk, "minute": minute})
    return duels


def matrice(duels, champions):
    idx = {c: i for i, c in enumerate(champions)}
    n = len(champions)
    X = np.zeros((len(duels), 2 * n + 2))
    for r, d in enumerate(duels):
        temps = (d["minute"] - MINUTE_REF) / 10
        X[r, idx[d["bleu"]]] += 1; X[r, idx[d["rouge"]]] -= 1
        X[r, n + idx[d["bleu"]]] += temps; X[r, n + idx[d["rouge"]]] -= temps
        X[r, 2 * n] = d["or"] / 1000
        X[r, 2 * n + 1] = d["niveau"]
    return X


def apprendre(X, y, lam):
    beta, c = bloc3.logistique(X, y, lam=lam, constante=True)
    return beta, c


def points(b):
    return 100 * (1 / (1 + math.exp(-b)) - 0.5)


def main():
    donnees = contres.dossier_donnees()
    regle = commun.lire_decoupage()
    table = commun.drafts(regle, donnees)
    tas = dict(zip(table["match"], table["tas"]))
    duels = lire_duels(donnees, tas)
    compte = defaultdict(int)
    for d in duels:
        compte[d["bleu"]] += 1; compte[d["rouge"]] += 1
    champions = sorted(compte)
    n = len(champions)
    y = np.array([d["bleu_gagne"] for d in duels], dtype=float)
    a = np.array([d["tas"] == "A" for d in duels]); b = ~a
    X = matrice(duels, champions)
    base = [2 * n, 2 * n + 1]

    # Choix de la régularisation sur A (5 rotations), puis vérification sur B.
    pli = np.random.default_rng(1).integers(0, 5, size=len(duels))
    meilleur = None
    for lam in (3.0, 10.0, 30.0, 100.0):
        pertes = []
        for f in range(5):
            app, note = a & (pli != f), a & (pli == f)
            beta, c = apprendre(X[app], y[app], lam)
            pertes.append(bloc3.perte_log(y[note], bloc3.sigmoide(X[note] @ beta + c)))
        if meilleur is None or np.mean(pertes) < meilleur[0]:
            meilleur = (float(np.mean(pertes)), lam)
    lam = meilleur[1]
    beta_a, c_a = apprendre(X[a], y[a], lam)
    beta_0, c_0 = apprendre(X[a][:, base], y[a], 1.0)
    perte_complet = bloc3.perte_log(y[b], bloc3.sigmoide(X[b] @ beta_a + c_a))
    perte_or = bloc3.perte_log(y[b], bloc3.sigmoide(X[b][:, base] @ beta_0 + c_0))
    # Accord des forces apprises séparément sur A et sur B (champions vus au moins 150 fois dans chaque tas).
    beta_b, _ = apprendre(X[b], y[b], lam)
    na = defaultdict(int); nb = defaultdict(int)
    for d, t in zip(duels, a):
        for c in (d["bleu"], d["rouge"]):
            (na if t else nb)[c] += 1
    assez = [i for i, c in enumerate(champions) if na[c] >= 150 and nb[c] >= 150]
    accord = float(np.corrcoef(beta_a[assez], beta_b[assez])[0, 1]) if len(assez) > 5 else float("nan")
    # Modèle final, sur A + B, pour l'affichage.
    beta, c = apprendre(X, y, lam)
    force = {ch: float(beta[i]) for i, ch in enumerate(champions)}
    pente = {ch: float(beta[n + i]) for i, ch in enumerate(champions)}
    coef_or, coef_niveau = float(beta[2 * n]), float(beta[2 * n + 1])
    sortie = {"duels": len(duels), "duels_A": int(a.sum()), "duels_B": int(b.sum()), "lambda": lam,
              "verification_B": {"perte_or_niveau": perte_or, "perte_complet": perte_complet, "gain_millièmes": 1000 * (perte_or - perte_complet),
                                 "accord_forces_A_B": accord, "champions_compares": len(assez)},
              "coef_or_1000": coef_or, "coef_niveau": coef_niveau, "minute_reference": MINUTE_REF,
              "champions": {ch: {"force": force[ch], "pente_10min": pente[ch], "duels": compte[ch]} for ch in champions}}
    RESULTATS.mkdir(parents=True, exist_ok=True)
    (RESULTATS / "duels.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def proba(c1, c2, minute=MINUTE_REF):
        t = (minute - MINUTE_REF) / 10
        return 1 / (1 + math.exp(-(force[c1] - force[c2] + (pente[c1] - pente[c2]) * t)))

    frequents = sorted((ch for ch in champions if compte[ch] >= 400), key=lambda ch: -compte[ch])
    texte = ["# Duels de junglers à or égal", "",
             f"- {len(duels)} duels (kill d'un jungler par l'autre, seul, sans aide) dans A + B ; A {int(a.sum())}, B {int(b.sum())}.",
             f"- Repères : 1 000 or d'avance = {points(coef_or):+.1f} points de chance de gagner le duel ; 1 niveau d'avance = {points(coef_niveau):+.1f} points.",
             f"- Vérification sur B : le modèle (champions + or + niveau) prédit mieux que l'or et le niveau seuls : "
             f"gain {1000 * (perte_or - perte_complet):.1f} millièmes. Accord des forces apprises séparément sur A et sur B : {accord:.2f} "
             f"({len(assez)} junglers). À confirmer sur C après la prochaine collecte.", "",
             "## Force en duel à or et niveau égaux (à 13 min), contre un jungler moyen", "",
             "| Jungler | Gagne à or égal | Évolution par 10 min | Duels |", "|---|---|---|---|"]
    for ch in sorted(frequents, key=lambda ch: -force[ch]):
        nom = f"**{ch}**" if ch in POOL else ch
        texte.append(f"| {nom} | {50 + points(force[ch]):.0f} % | {points(pente[ch]):+.1f} | {compte[ch]} |")
    texte += ["", "## Ton pool contre les junglers les plus joués (à or et niveau égaux, à 8 et à 15 min)", ""]
    adverses = frequents[:12]
    texte += ["| Ton jungler | " + " | ".join(adverses) + " |", "|---" * (len(adverses) + 1) + "|"]
    for ch in POOL:
        if compte.get(ch, 0) < 150:
            continue
        cases = [f"{100 * proba(ch, e, 8):.0f} / {100 * proba(ch, e, 15):.0f}" if e != ch else "—" for e in adverses]
        texte.append(f"| {ch} | " + " | ".join(cases) + " |")
    texte.append("")
    (RESULTATS / "duels.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
