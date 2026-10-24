"""Les champions forts et faibles du patch, à chaque poste (surtout la jungle).

Lit analyse/donnees_patch/<patch>/parties.csv (collecte_patch.py) et écrit dans
analyse/resultats_patch/<patch>/ :
- champions.csv : un champion par ligne et par poste ;
- champions_jungle.md : le résumé lisible (jungle d'abord, puis le meilleur et le pire des autres postes).

Deux taux par champion et par poste :
- brut : sa part de victoires, avec une marge d'erreur (intervalle à 95 %) ;
- corrigé : sa force une fois retirée celle des 9 autres champions de la partie (régression logistique
  régularisée, un coefficient par champion et par poste). C'est le taux de victoire qu'il aurait contre
  une draft moyenne. Un champion souvent joué avec ou contre des champions forts n'est ainsi ni avantagé
  ni pénalisé.
Verdict : « fort » si le taux corrigé atteint 51,5 % et que sa marge d'erreur reste au-dessus de 50 % ;
« faible » dans l'autre sens ; « dans la moyenne » sinon ; « pas assez de parties » sous parties_min.

    python3 analyse/patch/champions_forts.py [--patch 16.21]
"""

import argparse
import configparser
import csv
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
DONNEES_PATCH = ICI.parent / "donnees_patch"
RESULTATS_PATCH = ICI.parent / "resultats_patch"
POSTES = ("top", "jgl", "mid", "adc", "sup")
NOMS_POSTES = {"top": "Top", "jgl": "Jungle", "mid": "Mid", "adc": "ADC", "sup": "Support"}
POOL = ("Fiddlesticks", "Ivern", "Dr. Mundo", "Kayn bleu", "Kayn rouge", "Viego", "Morgana", "Urgot", "Maokai", "Skarner")
LAMBDAS = (3.0, 10.0, 30.0, 100.0)
SEUIL_FORT = 0.515


def lire_parties(chemin):
    vus, lignes = set(), []
    with open(chemin, encoding="utf-8", newline="") as fichier:
        for l in csv.DictReader(fichier, delimiter=";"):
            if l["match"] not in vus:
                vus.add(l["match"])
                lignes.append(l)
    return lignes


def sigmoide(x):
    return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def logistique(X, y, lam, iterations=30):
    """Ridge logistique par Newton ; la première colonne (constante) n'est pas pénalisée."""
    beta = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], lam)
    pen[0] = 1e-6
    for _ in range(iterations):
        mu = sigmoide(X @ beta)
        h = (X * (mu * (1 - mu))[:, None]).T @ X + np.diag(pen)
        pas = np.linalg.solve(h, X.T @ (y - mu) - pen * beta)
        beta += pas
        if np.max(np.abs(pas)) < 1e-7:
            break
    return beta, h


def wilson(v, n):
    if n == 0:
        return float("nan"), float("nan")
    p, z = v / n, 1.96
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - demi, centre + demi


def analyser(parties, parties_min):
    cles = sorted({(l[f"{c}_{p}"], p) for l in parties for c in "br" for p in POSTES})
    col = {k: i + 1 for i, k in enumerate(cles)}
    n = len(parties)
    X = np.zeros((n, len(cles) + 1))
    X[:, 0] = 1.0          # avantage du côté bleu
    y = np.array([1.0 if l["gagnant"] == "b" else 0.0 for l in parties])
    for i, l in enumerate(parties):
        for p in POSTES:
            X[i, col[(l[f"b_{p}"], p)]] += 1
            X[i, col[(l[f"r_{p}"], p)]] -= 1
    # Régularisation choisie par validation croisée (5 plis).
    pli = np.arange(n) % 5
    np.random.default_rng(0).shuffle(pli)
    meilleur = None
    for lam in LAMBDAS:
        perte = 0.0
        for f in range(5):
            beta, _ = logistique(X[pli != f], y[pli != f], lam)
            mu = np.clip(sigmoide(X[pli == f] @ beta), 1e-9, 1 - 1e-9)
            perte -= np.sum(y[pli == f] * np.log(mu) + (1 - y[pli == f]) * np.log(1 - mu))
        if meilleur is None or perte < meilleur[0]:
            meilleur = (perte, lam)
    lam = meilleur[1]
    beta, h = logistique(X, y, lam)
    erreur = np.sqrt(np.diag(np.linalg.inv(h)))

    stats = {k: [0, 0] for k in cles}
    for l in parties:
        for c in "br":
            gagne = l["gagnant"] == c
            for p in POSTES:
                s = stats[(l[f"{c}_{p}"], p)]
                s[0] += 1
                s[1] += gagne
    lignes = []
    for k in cles:
        nb, v = stats[k]
        b, e = beta[col[k]], erreur[col[k]]
        corrige, bas, haut = sigmoide(b), sigmoide(b - 1.96 * e), sigmoide(b + 1.96 * e)
        if nb < parties_min:
            verdict = "pas assez de parties"
        elif corrige >= SEUIL_FORT and bas > 0.5:
            verdict = "fort"
        elif corrige <= 1 - SEUIL_FORT and haut < 0.5:
            verdict = "faible"
        else:
            verdict = "dans la moyenne"
        bb, bh = wilson(v, nb)
        lignes.append({"champion": k[0], "poste": k[1], "parties": nb, "part_jeu": nb / n,
                       "victoires_brut": v / nb if nb else float("nan"), "brut_bas": bb, "brut_haut": bh,
                       "victoires_corrige": float(corrige), "corrige_bas": float(bas), "corrige_haut": float(haut),
                       "verdict": verdict})
    return lignes, lam, float(sigmoide(beta[0]))


def pc(x):
    return "—" if x != x else f"{100 * x:.1f} %"


def ecrire(patch, parties, lignes, lam, bleu, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    champs = list(lignes[0])
    with open(dossier / "champions.csv", "w", encoding="utf-8", newline="") as fichier:
        w = csv.DictWriter(fichier, fieldnames=champs, delimiter=";", lineterminator="\n")
        w.writeheader()
        for l in sorted(lignes, key=lambda l: (l["poste"], -l["victoires_corrige"])):
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in l.items()})

    rangs = {}
    for l in parties:
        rangs[l["palier"][:1]] = rangs.get(l["palier"][:1], 0) + 1
    texte = [f"# Champions forts du patch {patch}", "",
             f"- {len(parties)} parties du patch {patch} ("
             + ", ".join(f"{ {'D': 'Diamant', 'E': 'Émeraude', 'P': 'Platine'}.get(r, r)} {n}" for r, n in sorted(rangs.items())) + ").",
             "- **Taux corrigé** : le taux de victoire du champion contre une draft moyenne, une fois retirée la force "
             "des 9 autres champions de la partie. **Brut** : sa part de victoires, sans correction.",
             "- Entre crochets : la marge d'erreur (95 %). **Fort** : corrigé à 51,5 % ou plus, marge au-dessus de 50 %. "
             "**Faible** : l'inverse.",
             f"- Côté bleu : {pc(bleu)} de victoires à draft égale. Régularisation : {lam:g}.", ""]

    def tableau(selection):
        if not selection:
            return []
        lignes_t = ["| Champion | Parties | Corrigé | Brut | Verdict |", "|---|---|---|---|---|"]
        for l in selection:
            lignes_t.append(f"| {l['champion']} | {l['parties']} | {pc(l['victoires_corrige'])} "
                            f"[{pc(l['corrige_bas'])} ; {pc(l['corrige_haut'])}] | {pc(l['victoires_brut'])} | {l['verdict']} |")
        return lignes_t

    jungle = sorted([l for l in lignes if l["poste"] == "jgl"], key=lambda l: -l["victoires_corrige"])
    juges = [l for l in jungle if l["verdict"] != "pas assez de parties"]
    texte += ["## Ton pool en jungle", ""] + tableau([l for l in jungle if l["champion"] in POOL]) + [""]
    texte += ["## Junglers forts", ""] + (tableau([l for l in juges if l["verdict"] == "fort"]) or ["Aucun."]) + [""]
    texte += ["## Junglers faibles", ""] + (tableau([l for l in juges if l["verdict"] == "faible"][::-1]) or ["Aucun."]) + [""]
    texte += ["## Tous les junglers jugés (au moins assez de parties)", ""] + tableau(juges) + [""]
    for p in ("top", "mid", "adc", "sup"):
        poste = sorted([l for l in lignes if l["poste"] == p and l["verdict"] != "pas assez de parties"],
                       key=lambda l: -l["victoires_corrige"])
        forts = [l for l in poste if l["verdict"] == "fort"][:8]
        faibles = [l for l in poste if l["verdict"] == "faible"][::-1][:8]
        texte += [f"## {NOMS_POSTES[p]} : forts et faibles", ""]
        texte += (tableau(forts + faibles) if forts or faibles else ["Aucun champion nettement fort ou faible."]) + [""]
    (dossier / "champions_jungle.md").write_text("\n".join(texte) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch")
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(ICI / "patch.ini", encoding="utf-8")
    parties_min = config["analyse"].getint("parties_min", 100)
    patch = args.patch or (DONNEES_PATCH / "dernier_patch.txt").read_text(encoding="utf-8").strip()
    chemin = DONNEES_PATCH / patch / "parties.csv"
    if not chemin.exists():
        print(f"Aucune partie pour le patch {patch}.")
        return 0
    parties = lire_parties(chemin)
    if len(parties) < 200:
        print(f"Patch {patch} : seulement {len(parties)} parties, analyse sautée.")
        return 0
    lignes, lam, bleu = analyser(parties, parties_min)
    ecrire(patch, parties, lignes, lam, bleu, RESULTATS_PATCH / patch)
    forts = [l["champion"] for l in lignes if l["poste"] == "jgl" and l["verdict"] == "fort"]
    print(f"Patch {patch} : {len(parties)} parties ; junglers forts : {', '.join(forts) or 'aucun'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
