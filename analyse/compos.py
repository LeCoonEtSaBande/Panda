"""Compo contre compo : quel style bat quel style ?

Indépendant du jungler. Chaque partie oppose deux compos ; on regarde qui gagne.

- matrice : parties où les deux compos ont un style principal différent, style A contre style B ;
- regression : une partie = une observation (côté bleu), sur les scores continus de style.
  Pour chaque paire de styles (i, j), le terme « i chez nous × j chez eux − j chez nous × i chez eux »
  mesure si i bat j, au-delà de la force propre de chaque style.
"""

import csv
import itertools
import math
import sys
from collections import Counter
from pathlib import Path

from profils import benjamini_hochberg, ecrire_csv, p_valeur
from regle import STYLES, charger_catalogue, etiqueter

ICI = Path(__file__).resolve().parent
PARTIES = ICI / "donnees" / "parties.csv"
RESULTATS = ICI / "resultats"
POSTES = ("top", "jgl", "mid", "adc", "sup")
SANS_STYLE = "sans-style"


def compos(lignes, catalogue):
    """Pour chaque partie : étiquettes bleues, rouges, et si le bleu gagne."""
    resultat = []
    for ligne in lignes:
        equipes = {cote: [ligne[f"{cote}_{poste}"] for poste in POSTES] for cote in ("b", "r")}
        if any(nom not in catalogue for equipe in equipes.values() for nom in equipe):
            continue
        resultat.append({
            "b": etiqueter(equipes["b"], catalogue),
            "r": etiqueter(equipes["r"], catalogue),
            "bleu_gagne": ligne["gagnant"] == "b",
        })
    return resultat


def matrice(parties, minimum=50):
    """Style A contre style B, quand les deux compos ont un style principal différent."""
    paires = Counter()
    victoires = Counter()
    for partie in parties:
        styles = {cote: partie[cote]["principal"] or SANS_STYLE for cote in ("b", "r")}
        if styles["b"] == styles["r"]:
            continue
        a, b = sorted(styles.values())
        gagnant = styles["b"] if partie["bleu_gagne"] else styles["r"]
        paires[(a, b)] += 1
        victoires[(a, b)] += gagnant == a
    lignes = []
    for (a, b), n in paires.items():
        if n < minimum:
            continue
        v = victoires[(a, b)]
        taux = v / n
        z = (taux - 0.5) / math.sqrt(0.25 / n)
        # On écrit toujours le gagnant de la paire en premier.
        if taux < 0.5:
            a, b, v, taux = b, a, n - v, 1 - taux
        lignes.append([a, b, n, v, taux, p_valeur(z)])
    q = benjamini_hochberg([ligne[-1] for ligne in lignes])
    sortie = [[a, b, n, v, f"{100 * t:.1f}", f"{p:.3f}", f"{qq:.3f}"] for (a, b, n, v, t, p), qq in zip(lignes, q)]
    sortie.sort(key=lambda ligne: float(ligne[-1]))
    return sortie


def regression(parties):
    import numpy as np
    import statsmodels.api as sm

    noms, colonnes = [], []
    scores = {cote: np.array([[p[cote]["scores"][s] / 2 for s in STYLES] for p in parties]) for cote in ("b", "r")}
    for i, style in enumerate(STYLES):
        noms.append(f"force {style}")
        colonnes.append(scores["b"][:, i] - scores["r"][:, i])
    for i, j in itertools.combinations(range(len(STYLES)), 2):
        noms.append(f"{STYLES[i]} bat {STYLES[j]}")
        colonnes.append(scores["b"][:, i] * scores["r"][:, j] - scores["b"][:, j] * scores["r"][:, i])
    X = sm.add_constant(np.column_stack(colonnes))
    y = np.array([p["bleu_gagne"] for p in parties], dtype=float)
    modele = sm.Logit(y, X).fit(disp=False, cov_type="HC1")
    lignes = []
    for k, nom in enumerate(noms, start=1):
        b, e = modele.params[k], modele.bse[k]
        lignes.append([nom, b, e, p_valeur(b / e)])
    q = benjamini_hochberg([ligne[-1] for ligne in lignes])
    # Près de 50 %, un coefficient logit b vaut environ b / 4 en probabilité.
    sortie = [
        [nom, f"{25 * b:+.1f}", f"{25 * (b - 1.96 * e):+.1f}", f"{25 * (b + 1.96 * e):+.1f}", f"{p:.3f}", f"{qq:.3f}"]
        for (nom, b, e, p), qq in zip(lignes, q)
    ]
    sortie.sort(key=lambda ligne: float(ligne[-1]))
    return sortie, 25 * modele.params[0]


def main():
    if not PARTIES.exists():
        print("Compos : aucune partie collectée.")
        return 0
    with open(PARTIES, encoding="utf-8", newline="") as fichier:
        lignes = list(csv.DictReader(fichier, delimiter=";"))
    parties = compos(lignes, charger_catalogue())
    RESULTATS.mkdir(exist_ok=True)
    ecrire_csv(
        RESULTATS / "compos_matrice.csv",
        ["gagnant", "perdant", "parties", "victoires", "taux", "p", "q"],
        matrice(parties),
    )
    try:
        sortie, _ = regression(parties)
    except ImportError:
        print("Compos : statsmodels absent, régression sautée.")
    else:
        ecrire_csv(
            RESULTATS / "compos_regression.csv",
            ["effet", "pts_par_champion", "bas_95", "haut_95", "p", "q"],
            sortie,
        )
    print(f"Compos : {len(parties)} parties.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
