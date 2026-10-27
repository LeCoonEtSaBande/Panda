"""Confirmation sur C d'un recuit n° 2 (pistes), réglage FIGÉ.

Le meilleur réglage du recuit (celui jugé sur B) est rejoué tel quel, avec le catalogue utilisé pendant le recuit :
- apprentissage sur A + B (tout ce que le recuit a vu), mesure sur C (parties collectées après le gel, jamais lues) ;
- test d'ensemble : le gain de prédiction sur C (par rapport à la seule force des champions) est comparé à n
  tirages où les victoires suivent la seule force des champions (aucun biais de compo) ;
- test un par un des effets retenus pour l'assistant (liste fixée avant de lire C : ceux de l'export), dans le
  sens mesuré sur B, avec correction pour le nombre de tests (Benjamini-Hochberg).
Verdicts : confirmé (q < 5 %), à surveiller (p < 5 % sans correction), rien.

    python3 analyse/confirmation/confirmer_pistes.py --fichier recuit2_teamfight_20261024_0709.json \\
        --catalogue analyse/catalogues/catalogue_unifie_recuit2.csv --effets analyse/export/assistant_donnees.json --hasard 40
"""

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "base"))
sys.path.insert(0, str(ICI.parent / "recuit"))

import commun  # noqa: E402
import bloc2_compos as bloc2  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402
import recuit_pistes as rp  # noqa: E402
import recuit_styles as rs  # noqa: E402


def p_unilaterale(taux, erreur, sens):
    if not erreur or erreur != erreur:
        return 1.0
    z = (taux - 0.5) / erreur * sens
    return 0.5 * math.erfc(z / math.sqrt(2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fichier", required=True)
    parser.add_argument("--catalogue", help="catalogue utilisé pendant le recuit n° 2 (le n° 3 a le sien, figé dans son résultat)")
    parser.add_argument("--effets", help="assistant_donnees.json : effets retenus pour l'assistant, testés un par un")
    parser.add_argument("--hasard", type=int, default=40)
    args = parser.parse_args()
    regle = commun.lire_decoupage()
    commun.exiger_validation(regle)
    recuit = json.loads((rp.RESULTATS / args.fichier).read_text(encoding="utf-8"))
    piste, params = recuit["piste"], recuit["palmares"][0]["parametres"]
    styles = piste.startswith("styles")
    cat = recuit["catalogue_fige"] if styles else rp.lire_catalogue(args.catalogue)
    Fabrique = rs.Machine if styles else rp.Machine

    table = commun.drafts(regle)
    origine = bloc2.Index(table[table["tas"].isin(["A", "B"])].reset_index(drop=True)).champions
    # A + B deviennent l'apprentissage (« A » pour la machine), C devient la mesure (« B » pour la machine).
    table = table.assign(tas=table["tas"].map({"A": "A", "B": "A", "C": "B"})).reset_index(drop=True)
    nouveaux = {c: i for i, c in enumerate(bloc2.Index(table).champions)}
    params = dict(params)
    if "deplacements" in params:   # indices de champions : ceux de l'index A + B, à refaire sur A + B + C
        params["deplacements"] = {str(nouveaux[origine[int(k)]]): g for k, g in params["deplacements"].items()}
    if "echanges" in params:
        params["echanges"] = sorted(nouveaux[origine[i]] for i in params["echanges"])
    if "deplacements" in params:
        noms = bloc2.Index(table).champions
        print("Champions déplacés :", ", ".join(f"{noms[int(k)]} -> {rp.GROUPES[g]}" for k, g in params["deplacements"].items()))
    rp.LAMBDAS = (recuit["lambda"],)
    bloc3.LAMBDAS_FORCE = (recuit["lambda_force"],)
    nb = {t: int((table["tas"] == t).sum()) for t in ("A", "B")}
    print(f"Confirmation de {args.fichier} : apprentissage A + B = {nb['A']} parties, mesure sur C = {nb['B']} parties.", flush=True)

    machine = Fabrique(table, piste, cat)
    ev = machine.juger(params)
    print(f"Gain sur C : {ev.score:.3f} (sur B pendant le recuit : {recuit['palmares'][0]['score_jugement']:.3f})", flush=True)

    # Test d'ensemble : victoires tirées au sort selon la seule force des champions (apprise sur tout), réglage figé.
    index = machine.index
    tout = np.arange(len(table))
    force = bloc3.Force(index, tout)
    beta, c = force.apprendre(tout, machine.lambda_force)
    proba = bloc3.sigmoide(force.matrice(tout) @ beta + c)
    hasard = []
    for s in range(args.hasard):
        t = table.copy()
        t["bleu_gagne"] = (np.random.default_rng(7000 + s).random(len(t)) < proba).astype(int)
        hasard.append(Fabrique(t, piste, cat).juger(params).score)
        print(f"  hasard {s + 1}/{args.hasard} : {hasard[-1]:.3f}", flush=True)
    hasard = np.array(hasard)
    part = float((hasard >= ev.score).mean()) if len(hasard) else None

    # Effets un par un : la liste et le sens sont fixés par l'export (mesurés sur B), avant de lire C.
    tests = []
    if args.effets:
        effets = json.loads(Path(args.effets).read_text(encoding="utf-8"))[piste if styles else "teamfight"]["effets"]
        mesures = {b["nom"]: b for b in ev.biais}
        for e in effets:
            b = mesures.get(e["nom"])
            sens = 1 if e["taux_B"] > 0.5 else -1
            if b is None or b["taux_B"] != b["taux_B"]:
                tests.append({"nom": e["nom"], "taux_B_recuit": e["taux_B"], "absent": True, "p": 1.0})
                continue
            tests.append({"nom": e["nom"], "taux_A_B": b["taux_A"], "parties_A_B": b["parties_A"], "taux_B_recuit": e["taux_B"],
                          "taux_C": b["taux_B"], "parties_C": b["parties_B"], "erreur_C": b["erreur_B"],
                          "p": p_unilaterale(b["taux_B"], b["erreur_B"], sens)})
        q = bloc3.benjamini_hochberg([t["p"] for t in tests]) if tests else []
        for t, qq in zip(tests, q):
            t["q"] = float(qq)
            t["verdict"] = "confirmé" if qq < 0.05 else ("à surveiller" if t["p"] < 0.05 else "rien")

    date = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y%m%d_%H%M")
    base = ICI / "resultats" / f"confirmation_C_{args.fichier.replace('.json', '')}_{date}"
    sortie = {"date": date, "recuit": args.fichier, "catalogue": args.catalogue, "parties_A_B": nb["A"], "parties_C": nb["B"],
              "gain_C": ev.score, "gain_B_recuit": recuit["palmares"][0]["score_jugement"], "hasard": hasard.tolist(),
              "part_hasard_au_moins_aussi_bon": part, "effets": tests}
    base.with_suffix(".json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    verdict = ("confirmé" if part is not None and part < 0.05 and ev.score > 0 else ("à surveiller" if ev.score > 0 else "rien"))
    lignes = [f"# Confirmation sur C du recuit {args.fichier}", "",
              f"- Réglage figé (le meilleur du recuit), catalogue du recuit. Appris sur A + B ({nb['A']} parties), mesuré sur C "
              f"({nb['B']} parties collectées après le gel, jamais lues avant).",
              f"- **Test d'ensemble : {verdict}.** Gain de prédiction sur C {ev.score:.3f} (sur B : {sortie['gain_B_recuit']:.3f}). "
              + (f"Au hasard ({len(hasard)} tirages) : moyenne {hasard.mean():.3f}, maximum {hasard.max():.3f} ; "
               f"{int((hasard >= ev.score).sum())} sur {len(hasard)} font au moins aussi bien." if len(hasard) else "Pas de tirages au hasard."), "",
              "## Les effets de l'assistant, un par un", "",
              "| Effet | Sur B (recuit) | Sur C | Parties de C | Verdict |", "|---|---|---|---|---|"]
    for t in sorted(tests, key=lambda t: t["p"]):
        if t.get("absent"):
            lignes.append(f"| {t['nom']} | {100 * t['taux_B_recuit']:.1f} % | — | trop rare | rien |")
        else:
            lignes.append(f"| {t['nom']} | {100 * t['taux_B_recuit']:.1f} % | {100 * t['taux_C']:.1f} % | {t['parties_C']} | {t['verdict']} |")
    lignes += ["", "Taux = victoires de l'équipe concernée, à force de champions égale (50 % = aucun effet). "
               f"Confirmé : moins de 5 % de chances d'être un hasard après correction pour les {len(tests)} tests.", ""]
    base.with_suffix(".md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
