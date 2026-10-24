"""Confirmation des duels de junglers (lanes/duels.py) sur un tas C propre aux duels.

Pas de nouvelle collecte prévue : on découpe les parties existantes dans le temps, règles fixées AVANT de lancer :
- apprentissage (A) = les deux premiers tiers de donnees/parties.csv (ordre de collecte) ;
- C = le dernier tiers (les parties les plus récentes : patch plus récent, autres joueurs).
L'archive n'a pas de timeline, donc pas de duels : elle n'intervient pas.
Le modèle de lanes/duels.py est rejoué tel quel (mêmes variables, régularisation choisie sur A par 5 rotations).

Tests fixés à l'avance (seuil 5 %, correction de Benjamini-Hochberg dans chaque famille) :
1. Ensemble : sur C, le modèle complet (champions + évolution avec la minute + or + niveau) prédit-il mieux que
   l'or et le niveau seuls ? (différence de perte log, duel par duel, test unilatéral)
2. Évolution avec la minute : le modèle complet prédit-il mieux sur C que le même modèle sans l'évolution ?
3. Chaque jungler vu au moins 150 fois dans A et 100 fois dans C : sa force à or égal (signe appris sur A) se
   retrouve-t-elle sur C ? (taux de victoire de ses duels sur C, avec la prédiction or + niveau + adversaire comme
   point de départ, test unilatéral dans le sens appris)
Écrit confirmation/decoupage_duels.json (la règle, avant tout calcul) et confirmation/resultats/confirmation_duels.json et .md.

    python3 analyse/confirmation/confirmer_duels.py
"""

import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ICI = Path(__file__).resolve().parent
ANALYSE = ICI.parent
for d in ("", "contres", "base", "lanes"):
    sys.path.insert(0, str(ANALYSE / d))

import contres  # noqa: E402
import commun  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402
import duels as D  # noqa: E402

PART_C = 1 / 3
REGLE = ICI / "decoupage_duels.json"
SORTIE = ICI / "resultats"


def p_unilaterale(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def pertes(y, p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def test_gain(y, p_simple, p_complet):
    d = pertes(y, p_simple) - pertes(y, p_complet)
    return {"gain_millièmes": float(1000 * d.mean()), "p": p_unilaterale(d.mean() / (d.std(ddof=1) / math.sqrt(len(d))))}


def choisir_lambda(X, y, lignes):
    pli = np.random.default_rng(1).integers(0, 5, size=len(y))
    meilleur = None
    for lam in (3.0, 10.0, 30.0, 100.0):
        p = []
        for f in range(5):
            app, note = lignes & (pli != f), lignes & (pli == f)
            beta, c = D.apprendre(X[app], y[app], lam)
            p.append(bloc3.perte_log(y[note], bloc3.sigmoide(X[note] @ beta + c)))
        if meilleur is None or np.mean(p) < meilleur[0]:
            meilleur = (float(np.mean(p)), lam)
    return meilleur[1]


def main():
    donnees = contres.dossier_donnees()
    ordre = commun.ordre_parties(donnees)
    coupure = int(round(len(ordre) * (1 - PART_C)))
    regle = {"regle": "A = les deux premiers tiers de parties.csv (ordre de collecte), C = le dernier tiers ; archive sans duels.",
             "parties": len(ordre), "coupure_position": coupure, "premier_match_C": ordre[coupure],
             "date": datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
             "tests": ["ensemble : complet mieux que or + niveau", "évolution avec la minute", "force de chaque jungler (≥ 150 duels A, ≥ 100 C)"]}
    REGLE.write_text(json.dumps(regle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    position = {m: i for i, m in enumerate(ordre)}
    tas = {m: ("C" if i >= coupure else "A") for m, i in position.items()}
    # lire_duels ne garde que les tas A et B : C est passé sous le nom « B ».
    duels = D.lire_duels(donnees, {m: ("B" if t == "C" else "A") for m, t in tas.items()})
    compte_a, compte_c = defaultdict(int), defaultdict(int)
    for d in duels:
        for c in (d["bleu"], d["rouge"]):
            (compte_a if d["tas"] == "A" else compte_c)[c] += 1
    champions = sorted(set(compte_a) | set(compte_c))
    n = len(champions)
    y = np.array([d["bleu_gagne"] for d in duels], dtype=float)
    a = np.array([d["tas"] == "A" for d in duels]); c = ~a
    X = D.matrice(duels, champions)
    base = [2 * n, 2 * n + 1]
    sans_temps = list(range(n)) + base
    lam = choisir_lambda(X, y, a)
    beta, k = D.apprendre(X[a], y[a], lam)
    beta0, k0 = D.apprendre(X[a][:, base], y[a], 1.0)
    beta1, k1 = D.apprendre(X[a][:, sans_temps], y[a], lam)
    p_complet = bloc3.sigmoide(X[c] @ beta + k)
    p_or = bloc3.sigmoide(X[c][:, base] @ beta0 + k0)
    p_sans_temps = bloc3.sigmoide(X[c][:, sans_temps] @ beta1 + k1)
    ensemble = [dict(nom="Champions + minute + or + niveau, mieux que or + niveau seuls", **test_gain(y[c], p_or, p_complet)),
                dict(nom="Évolution avec la minute, mieux que sans", **test_gain(y[c], p_sans_temps, p_complet))]
    bloc3.benjamini_hochberg  # (deux tests distincts, chacun au seuil de 5 %)
    for t in ensemble:
        t["verdict"] = "confirmé" if t["p"] < 0.05 and t["gain_millièmes"] > 0 else "rien"

    # Force de chaque jungler sur C : ses duels, avec la prédiction « sans lui » comme point de départ.
    idx = {ch: i for i, ch in enumerate(champions)}
    tests = []
    Xc, yc, lignes_c = X[c], y[c], [d for d, t in zip(duels, c) if t]
    for ch in champions:
        if compte_a[ch] < 150 or compte_c[ch] < 100:
            continue
        i = idx[ch]
        x = Xc[:, i]                          # +1 s'il est bleu, −1 s'il est rouge, 0 sinon
        sel = x != 0
        b_sans = beta.copy(); b_sans[i] = 0.0; b_sans[n + i] = 0.0
        depart = Xc[sel] @ b_sans + k
        coef, _ = bloc3.logistique(x[sel][:, None], yc[sel], depart, lam=1e-6)
        mu = bloc3.sigmoide(depart + x[sel] * coef[0])
        erreur = 1 / math.sqrt(max(float(np.sum(mu * (1 - mu) * x[sel] ** 2)), 1e-12))
        sens = 1 if beta[i] > 0 else -1
        tests.append({"jungler": ch, "force_A": float(beta[i]), "force_C": float(coef[0]), "duels_A": compte_a[ch],
                      "duels_C": compte_c[ch], "p": p_unilaterale(sens * coef[0] / erreur)})
    if tests:
        q = bloc3.benjamini_hochberg([t["p"] for t in tests])
        for t, qq in zip(tests, q):
            t["q"] = float(qq)
            t["verdict"] = "confirmé" if qq < 0.05 else ("à surveiller" if t["p"] < 0.05 else "rien")
    accord = float(np.corrcoef([t["force_A"] for t in tests], [t["force_C"] for t in tests])[0, 1]) if len(tests) > 5 else float("nan")
    sortie = {"regle": regle, "duels_A": int(a.sum()), "duels_C": int(c.sum()), "lambda": lam, "ensemble": ensemble,
              "accord_forces_A_C": accord, "junglers": tests}
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / "confirmation_duels.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    pts = lambda b: 100 * (1 / (1 + math.exp(-b)) - 0.5)
    texte = ["# Confirmation des duels de junglers", "",
             f"- Découpage propre aux duels, fixé avant calcul : A = les {coupure} premières parties de parties.csv, "
             f"C = les {len(ordre) - coupure} dernières (à partir de {ordre[coupure]}). Duels : A {int(a.sum())}, C {int(c.sum())}.",
             "- Le modèle de lanes/duels.py est rejoué tel quel, appris sur A, mesuré sur C.", "",
             "## Ensemble", ""]
    texte += [f"- {t['nom']} : gain {t['gain_millièmes']:.1f} millièmes sur C, **{t['verdict']}**." for t in ensemble]
    texte += ["", f"## Chaque jungler (accord des forces A / C : {accord:.2f})", "",
              "| Jungler | À or égal sur A | Sur C | Duels A | Duels C | Verdict |", "|---|---|---|---|---|---|"]
    texte += [f"| {t['jungler']} | {50 + pts(t['force_A']):.0f} % | {50 + pts(t['force_C']):.0f} % | {t['duels_A']} | {t['duels_C']} | {t['verdict']} |"
              for t in sorted(tests, key=lambda t: -t["force_A"])]
    texte.append("")
    (SORTIE / "confirmation_duels.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
