"""Point 3 : la dynamique des lanes attendue d'après la draft, et ce qu'elle change pour le jungler.

Étape 1, « quelles lanes seront devant ou derrière en or à 15 minutes » :
  pour chaque lane (top, jungle, mid, bot), on prédit l'écart d'or à 15 min à partir des seuls champions
  de la draft (modèle des contres : force de lane de chaque champion + effet propre de la paire, voir
  analyse/contres/contres.py). La prédiction d'une partie ne vient jamais d'un modèle qui l'a vue :
  sur A, en 5 rotations ; sur B, un modèle appris sur tout A. On mesure ensuite, sur B, si la prédiction
  tient : corrélation avec l'écart réel, et part des lanes annoncées devant qui le sont vraiment.

Étape 2, « que faut-il jouer en conséquence » :
  le taux de victoire d'une catégorie de jungler (groupes teamfight du catalogue unifié) change-t-il selon
  les lanes alliées annoncées devant ou derrière ? Régression logistique, en plus de la force des champions :
  effet de 1 000 or annoncés sur chaque lane, et sa variation selon la catégorie du jungler. Appris sur A,
  jugé sur B. C n'est jamais lu.

    python3 analyse/lanes/dynamique.py
"""

import csv
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

import contres  # noqa: E402
import commun  # noqa: E402
import bloc2_compos as bloc2  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402

RESULTATS = ICI / "resultats"
# Catégories de jungler (groupes teamfight) de l'ancien catalogue, figé le 24/10/2026 : ganks et envahir ont été confirmés avec elles.
CATALOGUE = ICI.parent / "catalogues" / "ancien_catalogue_2026-10-24.csv"
LANES = ("top", "jgl", "mid", "bot")
NOM = {"top": "top", "jgl": "jungle", "mid": "mid", "bot": "bot"}
GROUPES = ("Engage (tanks)", "Engage (bruisers)", "Supports tanks", "Pick (assassins)", "Poke (artilleurs)",
           "Carrys", "Disengage (enchanteurs)")


# --- Étape 1 : prédire l'or des lanes -----------------------------------------------------------

class ModeleLanes:
    """Modèle des contres appris sur des parties : prédit l'écart d'or à 15 min de chaque lane."""

    def __init__(self, lignes_par_lane):
        self.m = {}
        for lane, postes in contres.LANES.items():
            lignes = lignes_par_lane[lane]
            forces, cote, residu, _, _ = contres.forces_de_lane(lignes, postes)
            paires = {}
            for poste in postes:
                p, _, _, _ = contres.effets_de_paires(lignes, residu, poste)
                paires[poste] = {k: e["specifique"] for k, e in p.items()}
            self.m[lane] = (postes, forces, cote, paires)

    def predire(self, draft, lane):
        postes, forces, cote, paires = self.m[lane]
        total = cote
        for poste in postes:
            a, b = draft[f"b_{poste}"], draft[f"r_{poste}"]
            total += forces.get((a, poste), 0.0) - forces.get((b, poste), 0.0) + paires[poste].get((a, b), 0.0)
        return total


def lire_catalogue():
    with open(CATALOGUE, encoding="utf-8", newline="") as f:
        return {l["champion"]: l["groupe_teamfight"] for l in csv.DictReader(f, delimiter=";")}


def main():
    donnees = contres.dossier_donnees()
    regle = commun.lire_decoupage()
    table = commun.drafts_ab(regle, donnees)   # toutes les parties, A et B (pas de C : analyse de nos parties)
    table = table[table["tas"].isin(["A", "B"])].reset_index(drop=True)
    tas = dict(zip(table["match"], table["tas"]))
    lignes, _ = contres.lire(donnees)
    # Seules les parties de A et B (Émeraude-Diamant) ; C n'est jamais lu.
    lignes = {lane: [l for l in ls if tas.get(l["match"]) in ("A", "B")] for lane, ls in lignes.items()}
    reel = {lane: {l["match"]: l["or"] for l in ls} for lane, ls in lignes.items()}

    # Prédictions hors échantillon : 5 rotations sur A, modèle de tout A pour B.
    matchs_a = sorted(m for m, t in tas.items() if t == "A")
    pli = {m: i % 5 for i, m in enumerate(np.random.default_rng(3).permutation(matchs_a))}
    pred = {lane: {} for lane in LANES}
    drafts = {r["match"]: r for r in table.to_dict("records")}
    for f in range(6):
        if f < 5:
            apprendre = {lane: [l for l in ls if tas[l["match"]] == "A" and pli[l["match"]] != f] for lane, ls in lignes.items()}
            cibles = [m for m in matchs_a if pli[m] == f]
        else:
            apprendre = {lane: [l for l in ls if tas[l["match"]] == "A"] for lane, ls in lignes.items()}
            cibles = [m for m, t in tas.items() if t == "B"]
        modele = ModeleLanes(apprendre)
        for m in cibles:
            for lane in LANES:
                pred[lane][m] = modele.predire(drafts[m], lane)
        print(f"Rotation {f + 1}/6 faite.", flush=True)

    RESULTATS.mkdir(parents=True, exist_ok=True)
    # Prédictions gardées pour envahir.py : une ligne par partie de A et B.
    import gzip
    with gzip.open(RESULTATS / "predictions.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(["match", "tas"] + [f"or_{lane}" for lane in LANES])
        for m, t_ in sorted(tas.items()):
            if all(m in pred[lane] for lane in LANES):
                w.writerow([m, t_] + [f"{pred[lane][m]:.0f}" for lane in LANES])
    texte = ["# Dynamique des lanes d'après la draft", "",
             f"- Parties : A = {sum(t == 'A' for t in tas.values())}, B = {sum(t == 'B' for t in tas.values())} "
             "(Émeraude-Diamant). Prédictions toujours faites par un modèle qui n'a pas vu la partie.", "",
             "## Étape 1 : la draft annonce-t-elle quelles lanes seront devant en or à 15 min ?", "",
             "| Lane | Corrélation prédit / réel (B) | Écart réel moyen quand la draft annonce +500 or ou plus | "
             "Lanes annoncées devant (+500) qui le sont vraiment | Part des parties annoncées à ±500 |",
             "|---|---|---|---|---|"]
    etape1 = {}
    for lane in LANES:
        ms = [m for m in reel[lane] if tas[m] == "B" and m in pred[lane]]
        p = np.array([pred[lane][m] for m in ms]); r = np.array([reel[lane][m] for m in ms])
        corr = float(np.corrcoef(p, r)[0, 1])
        fort = np.abs(p) >= 500
        signe = np.sign(p[fort])
        ecart = float(np.mean(signe * r[fort])) if fort.any() else math.nan
        juste = float(np.mean(np.sign(r[fort]) == signe)) if fort.any() else math.nan
        etape1[lane] = {"correlation": corr, "ecart_annonce_500": ecart, "justes_500": juste, "part_500": float(fort.mean())}
        texte.append(f"| {NOM[lane]} | {corr:.2f} | {ecart:+.0f} or | {100 * juste:.0f} % | {100 * fort.mean():.0f} % |")
    texte.append("")

    # --- Étape 2 : catégorie du jungler × lanes annoncées ---------------------------------------
    groupe = lire_catalogue()
    index = bloc2.Index(table)
    lignes_a = np.where(table["tas"] == "A")[0]; lignes_b = np.where(table["tas"] == "B")[0]
    force = bloc3.Force(index, lignes_a)
    dec_a, (dec_b,) = force.decalages(lignes_a, [lignes_b])
    y = index.y

    def caracteristiques(rangs):
        cols, noms = [], []
        P = {lane: np.array([pred[lane].get(table["match"][i], 0.0) for i in rangs]) / 1000 for lane in ("top", "mid", "bot", "jgl")}
        gb = np.array([groupe.get(table["b_jgl"][i], "") for i in rangs]); gr = np.array([groupe.get(table["r_jgl"][i], "") for i in rangs])
        for lane in ("top", "mid", "bot", "jgl"):
            cols.append(P[lane]); noms.append(("toutes", lane))
        for g in GROUPES:
            for lane in ("top", "mid", "bot"):
                # Vu du jungler de la catégorie g : ses lanes annoncées devant (+) ou derrière (-). Côté bleu,
                # ses lanes valent +P ; côté rouge, -P, et son effet compte avec le signe opposé : -(-P) = +P.
                cols.append(P[lane] * ((gb == g).astype(float) + (gr == g)))
                noms.append((g, lane))
        return np.column_stack(cols), noms

    Xa, noms = caracteristiques(lignes_a); Xb, _ = caracteristiques(lignes_b)
    meilleur = None
    for lam in (3.0, 10.0, 30.0, 100.0, 300.0):
        pli2 = np.arange(len(lignes_a)) % 5
        gains = []
        for f in range(5):
            beta, _ = bloc3.logistique(Xa[pli2 != f], y[lignes_a][pli2 != f], dec_a[pli2 != f], lam=lam)
            gains.append(bloc3.perte_log(y[lignes_a][pli2 == f], bloc3.sigmoide(dec_a[pli2 == f]))
                         - bloc3.perte_log(y[lignes_a][pli2 == f], bloc3.sigmoide(dec_a[pli2 == f] + Xa[pli2 == f] @ beta)))
        if meilleur is None or np.mean(gains) > meilleur[0]:
            meilleur = (float(np.mean(gains)), lam)
    lam = meilleur[1]
    beta, _ = bloc3.logistique(Xa, y[lignes_a], dec_a, lam=lam)
    seulement_lanes = len([n for n in noms if n[0] == "toutes"])
    beta0, _ = bloc3.logistique(Xa[:, :seulement_lanes], y[lignes_a], dec_a, lam=lam)
    perte = lambda d, X, b: bloc3.perte_log(y[lignes_b], bloc3.sigmoide(d + (X @ b if X is not None else 0)))
    gain_lanes = 1000 * (perte(dec_b, None, None) - perte(dec_b, Xb[:, :seulement_lanes], beta0))
    gain_complet = 1000 * (perte(dec_b, None, None) - perte(dec_b, Xb, beta))
    texte += ["## Étape 2 : quelle catégorie de jungler profite des lanes fortes ?", "",
              f"- Jugement sur B (millièmes de perte log, plus haut = mieux) : lanes annoncées seules {gain_lanes:+.3f} ; "
              f"avec la catégorie du jungler {gain_complet:+.3f}. La différence mesure ce qu'apporte la catégorie.", "",
              "Effet de 1 000 or annoncés en faveur de tes lanes, en points de victoire (à force de champions égale) :", "",
              "| Jungler | top | mid | bot |", "|---|---|---|---|"]
    effet = {n: b for n, b in zip(noms, beta)}
    for g in ("toutes",) + GROUPES:
        cases = []
        for lane in ("top", "mid", "bot"):
            b = effet[("toutes", lane)] + (effet.get((g, lane), 0.0) if g != "toutes" else 0.0)
            cases.append(f"{100 * (bloc3.sigmoide(np.array([b]))[0] - 0.5):+.1f}")
        texte.append(f"| {'tous (moyenne)' if g == 'toutes' else g} | " + " | ".join(cases) + " |")
    texte.append("")
    # Nombre de parties par catégorie de jungler (dans A).
    nb = defaultdict(int)
    for i in lignes_a:
        nb[groupe.get(table["b_jgl"][i], "")] += 1; nb[groupe.get(table["r_jgl"][i], "")] += 1
    texte += ["Junglers par catégorie dans A : " + ", ".join(f"{g} {nb[g]}" for g in GROUPES), ""]
    (RESULTATS / "dynamique.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    (RESULTATS / "dynamique.json").write_text(json.dumps({"etape1": etape1, "lambda": lam, "gain_lanes_B": gain_lanes,
                                                           "gain_complet_B": gain_complet,
                                                           "effets": {f"{g}|{l}": float(b) for (g, l), b in effet.items()}},
                                                          ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
