"""Ce qui suit un recuit, dans le bouton « 4 · Recuit » : préparer la confirmation sur C, puis poser un nouveau gel.

    python3 analyse/recuit/apres_recuit.py preparer --piste teamfight [--minimum 5000]
        Trouve le fichier du recuit qui vient de tourner, compte les parties C (collectées après le gel, jamais lues)
        et, s'il y en a assez, écrit la liste des effets à tester un par un (fixée AVANT de lire C) dans
        analyse/recuit/resultats/effets_a_confirmer.json. Écrit dans $GITHUB_OUTPUT : confirmer=true|false, fichier=…

    python3 analyse/recuit/apres_recuit.py nouveau-gel --raison "…"
        C vient d'être lu : il est « consommé ». Pose un nouveau gel à la dernière partie de parties.csv (même graine :
        chaque partie garde son tas A ou B) ; les parties collectées ensuite formeront le prochain C.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ICI = Path(__file__).resolve().parent
ANALYSE = ICI.parent
sys.path.insert(0, str(ANALYSE))
sys.path.insert(0, str(ANALYSE / "base"))
sys.path.insert(0, str(ANALYSE / "export"))
sys.path.insert(0, str(ANALYSE / "contres"))

import commun  # noqa: E402

RESULTATS = ICI / "resultats"
EFFETS = RESULTATS / "effets_a_confirmer.json"


def sortie_github(**valeurs):
    chemin = os.environ.get("GITHUB_OUTPUT")
    texte = "".join(f"{k}={v}\n" for k, v in valeurs.items())
    if chemin:
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(texte)
    print(texte, end="")


def resume(texte):
    chemin = os.environ.get("GITHUB_STEP_SUMMARY")
    if chemin:
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(texte + "\n")
    print(texte)


def effets_styles(recuit):
    """Recuit n° 3 : les effets du meilleur réglage qui vont dans le même sens sur A et sur B (au moins 300 parties de B,
    1,5 point d'écart à 50 % sur B). Fixés avant de lire C ; testés un par un sur C dans le sens de B."""
    sortie = []
    for b in recuit["palmares"][0]["biais"]:
        ta, tb = b["taux_A"], b["taux_B"]
        if ta == ta and tb == tb and b["parties_B"] >= 300 and (ta - 0.5) * (tb - 0.5) > 0 and abs(tb - 0.5) >= 0.015:
            sortie.append({"nom": b["nom"], "taux_A": ta, "taux_B": tb, "parties_A": b["parties_A"], "parties_B": b["parties_B"]})
    return sortie


def preparer(piste, minimum):
    numero = 3 if piste.startswith("styles") else 2
    pointeur = RESULTATS / f"dernier_recuit{numero}_{piste}.json"
    if not pointeur.exists():
        resume("Pas de recuit trouvé : rien à confirmer.")
        return sortie_github(confirmer="false", fichier="")
    fichier = json.loads(pointeur.read_text(encoding="utf-8"))["fichier"]
    regle = commun.lire_decoupage()
    table = commun.drafts(regle, commun.dossier_donnees())
    nb_c = int((table["tas"] == "C").sum())
    if nb_c < minimum:
        resume(f"Recuit {fichier} enregistré. **Pas de confirmation** : seulement {nb_c} parties C (il en faut {minimum}). "
               f"Lance une ou deux collectes (bouton 1), puis relance ce bouton.")
        return sortie_github(confirmer="false", fichier=fichier)
    # Les effets à tester un par un, fixés avant de lire C : ceux du recuit qui tiennent sur A et sur B.
    effets = []
    if piste == "teamfight":
        import exporter
        effets = exporter.teamfight()["effets"]
    elif piste.startswith("styles"):
        effets = effets_styles(json.loads((RESULTATS / fichier).read_text(encoding="utf-8")))
    EFFETS.write_text(json.dumps({piste: {"effets": effets}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    resume(f"Recuit {fichier} enregistré ; confirmation sur {nb_c} parties C, {len(effets)} effets testés un par un.")
    return sortie_github(confirmer="true", fichier=fichier)


def nouveau_gel(raison):
    ancien = commun.lire_decoupage()
    precedent = (f"Gel n° {ancien.get('version')} (position {ancien.get('gel', {}).get('position')}, dernier match "
                 f"{ancien.get('gel', {}).get('dernier_match')}) : son C a servi à {raison}.")
    regle, _ = commun.proposer_gel(commun.dossier_donnees(), part_b=ancien["part_B"], graine=ancien["graine"],
                                   version=int(ancien.get("version", 3)) + 1, precedent=precedent)
    regle["valide"] = True
    regle["commentaire"] = (f"Posé automatiquement le {datetime.now(ZoneInfo('Europe/Paris')):%d/%m/%Y} après {raison}. "
                            "Même graine : chaque partie garde son tas A ou B ; C repart de zéro.")
    commun.DECOUPAGE.write_text(json.dumps(regle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    resume(f"C consommé : nouveau gel n° {regle['version']} à la partie {regle['gel']['position']}. Les prochaines collectes forment le nouveau C.")


def main():
    parser = argparse.ArgumentParser()
    sous = parser.add_subparsers(dest="action", required=True)
    p = sous.add_parser("preparer")
    p.add_argument("--piste", required=True, choices=("scenarios", "teamfight", "styles", "styles_libre"))
    p.add_argument("--minimum", type=int, default=5000)
    g = sous.add_parser("nouveau-gel")
    g.add_argument("--raison", required=True)
    args = parser.parse_args()
    if args.action == "preparer":
        preparer(args.piste, args.minimum)
    else:
        nouveau_gel(args.raison)
    return 0


if __name__ == "__main__":
    sys.exit(main())
