"""Confirmation des résultats du recuit sur le tas C (parties jamais vues pendant la recherche).

Pour chacun des meilleurs réglages du dernier recuit (ou du fichier donné) :
1. on réapprend tout sur A + B (force des champions et biais), avec ces réglages, sans rien changer ;
2. on mesure sur C : le score (gain de prédiction) et chaque biais, avec son taux de victoire sur C ;
3. chaque biais est testé dans le sens trouvé sur A + B (test unilatéral), puis correction de
   Benjamini-Hochberg sur l'ensemble des biais testés. Confirmé = moins de 5 % de fausses découvertes.

C est lu ici seulement. Une fois qu'on a regardé C pour un recuit, ces parties ne sont plus
« neuves » pour lui : un nouveau recuit devra être confirmé sur des parties encore plus récentes.

    python3 analyse/iteratif/confirmer.py [--fichier recuit_AAAAMMJJ_HHMM.json] [--reglages 1]
    python3 analyse/iteratif/confirmer.py --a-blanc    # essai du code : apprend sur A, mesure sur B, ne lit pas C

Par défaut, un seul réglage (le premier du palmarès) : les suivants en sont en général des copies à un
ou deux champions près, et les tester aussi ne ferait que répéter les mêmes biais.
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import commun
import bloc1_champions as bloc1
import bloc2_compos as bloc2
import bloc3_biais as bloc3
import bloc4_recuit as bloc4

MIN_PARTIES_C = 30


def p_unilaterale(taux, erreur, sens):
    if not (erreur == erreur) or erreur <= 0:
        return 1.0
    z = (taux - 0.5) / erreur * (1 if sens > 0 else -1)
    return 0.5 * math.erfc(z / math.sqrt(2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fichier")
    parser.add_argument("--reglages", type=int, default=1)
    parser.add_argument("--sans-validation", action="store_true")
    parser.add_argument("--a-blanc", action="store_true",
                        help="essai : apprend sur A, mesure sur B, n'écrit rien et ne lit pas C")
    args = parser.parse_args()
    regle = commun.lire_decoupage()
    if not args.sans_validation:
        commun.exiger_validation(regle)
    fichier = args.fichier or json.loads((commun.RESULTATS / "dernier_recuit.json").read_text(encoding="utf-8"))["fichier"]
    recuit = json.loads((commun.RESULTATS / fichier).read_text(encoding="utf-8"))

    table = commun.drafts(regle)
    if args.a_blanc:
        table = table[table["tas"] != "C"].reset_index(drop=True)
        apprentissage, evaluation = ("A",), ("B",)
    else:
        apprentissage, evaluation = ("A", "B"), ("C",)
    nb_c = int(table["tas"].isin(evaluation).sum())
    machine = bloc4.Machine(table, bloc1.lire_mesures(), apprentissage=apprentissage, evaluation=evaluation)
    print(f"Confirmation de {fichier}{' (à blanc, sur B)' if args.a_blanc else ''} : "
          f"apprentissage = {len(machine.lignes_a)} parties, évaluation = {nb_c} parties.")

    resultats, tests = [], []
    for entree in recuit["palmares"][: args.reglages]:
        params = entree["parametres"]
        ev, cat = machine.evaluer(params, avec_biais=True)
        biais = []
        for b in ev.biais:
            if b["genre"].startswith("capacite") or b["parties_B"] < MIN_PARTIES_C or b["taux_A"] != b["taux_A"]:
                continue
            sens = 1 if b["taux_A"] > 0.5 else -1
            b = dict(b, taux_C=b["taux_B"], parties_C=b["parties_B"], erreur_C=b["erreur_B"],
                     taux_AB=b["taux_A"], parties_AB=b["parties_A"])
            b["p"] = p_unilaterale(b["taux_C"], b["erreur_C"], sens)
            biais.append(b)
            tests.append(b)
        resultats.append({"rang": entree["rang"], "score_B_recuit": entree["score_B"], "score_C": ev.score,
                          "parametres": params, "groupes": cat.membres_texte, "biais": biais})

    q = bloc3.benjamini_hochberg([b["p"] for b in tests]) if tests else []
    for b, qq in zip(tests, q):
        b["q"] = qq
        b["verdict"] = "confirmé" if qq < 0.05 else ("à surveiller" if b["p"] < 0.05 else "pas confirmé")

    if args.a_blanc:
        for r in resultats:
            print(f"Réglage {r['rang']} : score {r['score_C']:.3f} sur B")
            for b in sorted(r["biais"], key=lambda b: b["q"])[:10]:
                print(f"  {b['verdict']} — {b['nom']} : {100 * b['taux_C']:.1f} % ({b['parties_C']} parties), q = {b['q']:.3f}")
        print("À blanc : rien n'est écrit.")
        return 0

    date = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M")
    sortie = {"date": date, "recuit": fichier, "parties_C": nb_c, "reglages": resultats}
    chemin = commun.RESULTATS / f"confirmation_{date}.json"
    chemin.write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    lignes = [f"# Confirmation du {date} (recuit {fichier})", "",
              f"- Tout est réappris sur A + B ({len(machine.lignes_a)} parties), puis mesuré sur C ({nb_c} parties jamais vues).",
              "- Score sur C : gain de prédiction par rapport à la seule force des champions (en millièmes). Positif = les biais tiennent.",
              f"- {len(tests)} biais testés, correction pour le nombre de tests. Confirmé = moins de 5 % de chances d'être un hasard, après correction.", ""]
    for r in resultats:
        lignes += [f"## Réglage n° {r['rang']} : score {r['score_B_recuit']:.3f} sur B pendant le recuit, {r['score_C']:.3f} sur C", ""]
        bons = sorted(r["biais"], key=lambda b: b["q"])[:10]
        for b in bons:
            lignes.append(f"- **{b['verdict']}** — {b['nom']} : {100 * b['taux_C']:.1f} % sur C ({b['parties_C']} parties), "
                          f"{100 * b['taux_AB']:.1f} % sur A + B ({b['parties_AB']}), contre 50 % à force de champions égale")
        lignes.append("")
    (commun.RESULTATS / f"confirmation_{date}.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    confirmes = sum(b["verdict"] == "confirmé" for b in tests)
    print(f"Confirmation : {confirmes} biais confirmés sur {len(tests)} testés. Résultats dans {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
