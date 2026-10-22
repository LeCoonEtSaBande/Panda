"""Biais de winrate par profil de jungler.

Étude 1 : le profil du jungler face au style de la compo adverse.
Étude 2 : le profil du jungler avec le style de ses quatre coéquipiers.

Deux lectures pour chaque étude :
- un tableau croisé : winrate du profil dans un cas contre hors de ce cas ;
- une régression logistique qui contrôle la force de chaque champion, le palier et le patch,
  et qui sépare l'effet de la compo adverse de celui de la compo alliée.
"""

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from regle import STYLES, charger_catalogue, correspond, etiqueter

ICI = Path(__file__).resolve().parent
PARTIES = ICI / "donnees" / "parties.csv"
PROFILS = ICI / "profils_jungle.json"
RESULTATS = ICI / "resultats"

POSTES = ("top", "jgl", "mid", "adc", "sup")
SANS_STYLE = "sans-style"
# Un jungler plus rare que ça est regroupé avec les autres junglers rares de son profil
# pour l'effet fixe « champion » de la régression.
JUNGLE_MIN_REGRESSION = 30
VARIABLES = [f"nb_{style}" for style in STYLES] + ["front_HP+", "sans_front"]


def charger_profils(chemin=PROFILS):
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def profil_de(fiche, profils):
    """Premier profil dont la condition correspond à la fiche du catalogue."""
    for profil in profils:
        if correspond(fiche, profil["condition"]):
            return profil["id"]
    return "autre"


def resume_compo(champions, catalogue):
    """Style et variables numériques d'un groupe de champions."""
    etiquettes = etiqueter(champions, catalogue)
    # Un champion qui a ce style en principal compte 1, en secondaire 0,5.
    valeurs = {f"nb_{style}": etiquettes["scores"][style] / 2 for style in STYLES}
    valeurs["front_HP+"] = 1.0 if etiquettes["front"] == "HP+" else 0.0
    valeurs["sans_front"] = 1.0 if etiquettes["front"] == "" else 0.0
    return {
        "style": etiquettes["principal"] or SANS_STYLE,
        "front": etiquettes["front"] or "aucun",
        "valeurs": valeurs,
    }


def observations(lignes, catalogue, profils):
    """Deux observations par partie, une par équipe. La compo alliée exclut le jungler."""
    resultat = []
    for ligne in lignes:
        equipes = {cote: [ligne[f"{cote}_{poste}"] for poste in POSTES] for cote in ("b", "r")}
        if any(nom not in catalogue for equipe in equipes.values() for nom in equipe):
            continue
        for cote, autre in (("b", "r"), ("r", "b")):
            jungle = ligne[f"{cote}_jgl"]
            coequipiers = [nom for poste, nom in zip(POSTES, equipes[cote]) if poste != "jgl"]
            resultat.append({
                "match": ligne["match"],
                "patch": ligne["patch"],
                "rang": ligne["palier"][:1],
                "jungle": jungle,
                "profil": profil_de(catalogue[jungle], profils),
                "victoire": ligne["gagnant"] == cote,
                "adverse": resume_compo(equipes[autre], catalogue),
                "allie": resume_compo(coequipiers, catalogue),
            })
    return resultat


# --- Statistiques -------------------------------------------------------------------------

def p_valeur(z):
    return math.erfc(abs(z) / math.sqrt(2))


def benjamini_hochberg(p_valeurs):
    """q-valeurs : p corrigées pour le nombre de tests (taux de fausses découvertes)."""
    ordre = sorted(range(len(p_valeurs)), key=lambda i: p_valeurs[i])
    q = [1.0] * len(p_valeurs)
    minimum = 1.0
    for rang in range(len(ordre), 0, -1):
        i = ordre[rang - 1]
        minimum = min(minimum, p_valeurs[i] * len(p_valeurs) / rang)
        q[i] = minimum
    return q


def comparer(dedans, dehors):
    """Écart de winrate dedans / dehors et sa p-valeur (test de deux proportions)."""
    n1, n2 = len(dedans), len(dehors)
    v1, v2 = sum(dedans), sum(dehors)
    p1, p2 = v1 / n1, v2 / n2
    p = (v1 + v2) / (n1 + n2)
    erreur = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) if 0 < p < 1 else 0.0
    z = (p1 - p2) / erreur if erreur else 0.0
    return p1, p2, p_valeur(z)


def pourcent(x):
    return f"{100 * x:.1f}"


# --- Tableaux croisés ---------------------------------------------------------------------

def tableau(obs, cote, minimum):
    """Pour chaque profil et chaque style de la compo (adverse ou alliée), dedans contre dehors."""
    par_profil = defaultdict(list)
    for o in obs:
        par_profil[o["profil"]].append(o)
    lignes = []
    for profil, liste in par_profil.items():
        cas = Counter(o[cote]["style"] for o in liste) + Counter(f"front {o[cote]['front']}" for o in liste)
        for valeur in cas:
            dedans = [o["victoire"] for o in liste if valeur in (o[cote]["style"], f"front {o[cote]['front']}")]
            dehors = [o["victoire"] for o in liste if valeur not in (o[cote]["style"], f"front {o[cote]['front']}")]
            if len(dedans) < minimum or len(dehors) < minimum:
                continue
            taux, taux_hors, p = comparer(dedans, dehors)
            lignes.append([profil, valeur, len(dedans), sum(dedans), taux, taux_hors, p])
    q = benjamini_hochberg([ligne[-1] for ligne in lignes])
    sortie = [
        [profil, valeur, n, v, pourcent(t), pourcent(th), f"{100 * (t - th):+.1f}", f"{p:.3f}", f"{qq:.3f}"]
        for (profil, valeur, n, v, t, th, p), qq in zip(lignes, q)
    ]
    sortie.sort(key=lambda ligne: float(ligne[-1]))
    return sortie


# --- Régression ---------------------------------------------------------------------------

def regression(obs):
    """Logit : victoire ~ champion + rang + patch + profil × (compo adverse) + profil × (compo alliée).

    Pour chaque profil et chaque variable, on donne la pente propre au profil et son écart à la
    pente moyenne de tous les junglers : c'est cet écart qui est un biais du profil.
    Erreurs standard groupées par partie (les deux équipes d'une partie ne sont pas indépendantes).
    """
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm

    effectifs = Counter(o["jungle"] for o in obs)
    profils = sorted({o["profil"] for o in obs})
    lignes = []
    for o in obs:
        ligne = {
            "victoire": float(o["victoire"]),
            "match": o["match"],
            "jungle": o["jungle"] if effectifs[o["jungle"]] >= JUNGLE_MIN_REGRESSION else f"rare {o['profil']}",
            "rang": o["rang"],
            "patch": o["patch"],
        }
        for cote in ("adverse", "allie"):
            for variable in VARIABLES:
                for profil in profils:
                    ligne[f"{cote}|{profil}|{variable}"] = o[cote]["valeurs"][variable] if o["profil"] == profil else 0.0
        lignes.append(ligne)
    table = pd.DataFrame(lignes)
    interactions = [c for c in table.columns if c.count("|") == 2]
    # Une interaction toujours nulle (profil absent, variable jamais présente) ferait une colonne vide.
    interactions = [c for c in interactions if table[c].abs().sum() > 0]
    fixes = pd.get_dummies(table[["jungle", "rang", "patch"]], drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([fixes, table[interactions]], axis=1))
    modele = sm.Logit(table["victoire"], X).fit(
        disp=False, maxiter=200, cov_type="cluster", cov_kwds={"groups": pd.factorize(table["match"])[0]}
    )
    beta, cov = modele.params, modele.cov_params()

    poids = Counter(o["profil"] for o in obs)
    total = sum(poids.values())
    resultats = []
    for cote in ("adverse", "allie"):
        for variable in VARIABLES:
            colonnes = [f"{cote}|{p}|{variable}" for p in profils if f"{cote}|{p}|{variable}" in beta.index]
            moyenne = np.zeros(len(beta))
            for colonne in colonnes:
                profil = colonne.split("|")[1]
                moyenne[beta.index.get_loc(colonne)] = poids[profil] / total
            for colonne in colonnes:
                profil = colonne.split("|")[1]
                contraste = -moyenne.copy()
                contraste[beta.index.get_loc(colonne)] += 1
                ecart = float(contraste @ beta.values)
                erreur = float(math.sqrt(contraste @ cov.values @ contraste))
                resultats.append({
                    "cote": cote, "profil": profil, "variable": variable,
                    "pente": float(beta[colonne]), "ecart": ecart, "erreur": erreur,
                    "p": p_valeur(ecart / erreur) if erreur else 1.0,
                })
    q = benjamini_hochberg([r["p"] for r in resultats])
    # Près de 50 %, un coefficient logit b vaut environ b / 4 en probabilité.
    sortie = []
    for r, qq in zip(resultats, q):
        sortie.append([
            r["cote"], r["profil"], r["variable"],
            f"{25 * r['pente']:+.1f}", f"{25 * r['ecart']:+.1f}",
            f"{25 * (r['ecart'] - 1.96 * r['erreur']):+.1f}", f"{25 * (r['ecart'] + 1.96 * r['erreur']):+.1f}",
            f"{r['p']:.3f}", f"{qq:.3f}",
        ])
    sortie.sort(key=lambda ligne: float(ligne[-1]))
    return sortie, modele.nobs


# --- Sortie -------------------------------------------------------------------------------

def ecrire_csv(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(entete)
        ecrivain.writerows(lignes)


def main(minimum=100):
    if not PARTIES.exists():
        print("Profils : aucune partie collectée.")
        return 0
    with open(PARTIES, encoding="utf-8", newline="") as fichier:
        lignes = list(csv.DictReader(fichier, delimiter=";"))
    catalogue = charger_catalogue()
    profils = charger_profils()
    obs = observations(lignes, catalogue, profils)
    RESULTATS.mkdir(exist_ok=True)

    composition = Counter((o["profil"], o["jungle"]) for o in obs)
    ecrire_csv(
        RESULTATS / "profils_composition.csv", ["profil", "jungle", "observations"],
        sorted(([p, j, n] for (p, j), n in composition.items()), key=lambda l: (l[0], -l[2])),
    )
    entete = ["profil", "{}", "parties", "victoires", "taux", "taux_hors", "ecart", "p", "q"]
    ecrire_csv(RESULTATS / "profils_adverse.csv", [e.format("compo_adverse") for e in entete], tableau(obs, "adverse", minimum))
    ecrire_csv(RESULTATS / "profils_allie.csv", [e.format("compo_alliee") for e in entete], tableau(obs, "allie", minimum))

    try:
        sortie, n = regression(obs)
    except ImportError:
        print("Profils : statsmodels absent, régression sautée (pip install statsmodels).")
    else:
        ecrire_csv(
            RESULTATS / "profils_regression.csv",
            ["compo", "profil", "variable", "pente_pts", "ecart_moyenne_pts", "bas_95", "haut_95", "p", "q"],
            sortie,
        )
        print(f"Profils : régression sur {int(n)} observations.")
    print(f"Profils : {len(obs)} observations, {len(profils)} profils.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
