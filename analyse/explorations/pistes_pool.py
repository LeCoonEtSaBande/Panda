"""Exploration (hors liste d'hypothèses) : situations où un jungler du pool gagne plus ou moins que
les autres junglers dans la même situation. À lancer en local :

    python3 analyse/explorations/pistes_pool.py                 # exploration sur l'échantillon figé
    python3 analyse/explorations/pistes_pool.py --confirmation  # retest des pistes sur les parties suivantes

Tout ce qui sort de l'exploration est EXPLORATOIRE : les pistes retenues (p < 0,05 avant correction)
sont écrites dans pistes_a_confirmer.json, puis retestées telles quelles, sans rien changer, sur les
parties arrivées après l'échantillon figé (option --confirmation).

Modèle, pour chaque jungler J du pool à 100 parties ou plus et chaque situation S :
victoire ~ jungler (effet fixe) + rang + S + S × J, deux lignes par partie, erreurs groupées par partie.
Le terme S × J dit si J profite (ou souffre) de S plus que les autres junglers.
"""

import csv
import json
import math
import sys
import warnings
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import biais  # noqa: E402
import categories  # noqa: E402
import echantillon  # noqa: E402

POOL = ("Fiddlesticks", "Ivern", "Dr. Mundo", "Kayn rouge", "Kayn bleu", "Viego", "Morgana", "Urgot", "Maokai", "Skarner")
PISTES = ICI / "pistes_a_confirmer.json"


def situations(t):
    """Situations (0/1) vues de « nous ». Les comptes viennent des profils mesurés."""
    return {
        "eux : 2 engage ou plus": t["eux_engage"] >= 2,
        "eux : 2 assassins ou plus": t["eux_assassins"] >= 2,
        "eux : aucun peel": t["eux_peel"] == 0,
        "eux : 3 AP ou plus": t["eux_ap_mesure"] >= 3,
        "eux : au plus 1 AP": t["eux_ap_mesure"] <= 1,
        "eux : jungler envahisseur": t["eux_jgl_envahisseur"] == 1,
        "eux : jungler tardif": t["eux_jgl_tardif"] == 1,
        "nous : 2 engage ou plus": t["nous_engage"] >= 2,
        "nous : 2 assassins ou plus": t["nous_assassins"] >= 2,
        "nous : aucun peel": t["nous_peel"] == 0,
        "nous : 2 peel ou plus": t["nous_peel"] >= 2,
        "nous : au plus 1 AP (hors jungle)": t["nous_ap_mesure"] <= 1,
        "nous : 3 AP ou plus (hors jungle)": t["nous_ap_mesure"] >= 3,
    }


def tester(deux, fiches, jungler, nom, s):
    import pandas as pd

    s = s.astype(float)
    j = (deux["nous_jgl"] == jungler).astype(float)
    X = pd.concat([biais.fe_jungle(deux, fiches), biais.fe_rang(deux),
                   pd.DataFrame({"situation": s, "test": s * j})], axis=1)
    m = biais.logit(deux["victoire"].astype(float), X, pd.factorize(deux["match"])[0])
    v = deux["victoire"]
    dedans = v[(j == 1) & (s == 1)]
    dehors = v[(j == 1) & (s == 0)]
    autres_dedans = v[(j == 0) & (s == 1)]
    autres_dehors = v[(j == 0) & (s == 0)]
    return {
        "jungler": jungler, "situation": nom, "parties_dedans": len(dedans), "parties_dehors": len(dehors),
        "winrate_dedans": dedans.mean() if len(dedans) else float("nan"),
        "winrate_dehors": dehors.mean() if len(dehors) else float("nan"),
        "autres_dedans": autres_dedans.mean(), "autres_dehors": autres_dehors.mean(),
        "coef": float(m.params["test"]), "p": float(m.pvalues["test"]),
    }


def ecrire(chemin, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(["jungler", "situation", "parties_dedans", "winrate_dedans", "parties_dehors", "winrate_dehors",
                           "autres_junglers_dedans", "autres_junglers_dehors", "effet_base_50", "p", "q_bh"])
        for r in lignes:
            ecrivain.writerow([
                r["jungler"], r["situation"], r["parties_dedans"], f"{100 * r['winrate_dedans']:.1f}",
                r["parties_dehors"], f"{100 * r['winrate_dehors']:.1f}", f"{100 * r['autres_dedans']:.1f}",
                f"{100 * r['autres_dehors']:.1f}", f"{100 / (1 + math.exp(-r['coef'])):.1f}", f"{r['p']:.4f}",
                f"{r.get('q', float('nan')):.4f}",
            ])


def main():
    warnings.filterwarnings("ignore")
    matchs, suite = echantillon.decouper()
    t, j, profils = categories.calculer(matchs)
    confirmation = "--confirmation" in sys.argv
    if confirmation:
        pistes = json.loads(PISTES.read_text(encoding="utf-8"))
        v, fiches = biais.preparer(suite, profils)
        print(f"Confirmation sur {len(suite)} parties arrivées après l'échantillon figé.")
    else:
        v, fiches = biais.preparer(matchs, profils, j, croise=True, t=t)
    deux = biais.deux_lignes(v)
    cas = situations(deux)
    lignes = []
    if confirmation:
        for piste in pistes["pistes"]:
            r = tester(deux, fiches, piste["jungler"], piste["situation"], cas[piste["situation"]])
            r["meme_sens"] = (r["coef"] > 0) == (piste["coef"] > 0)
            lignes.append(r)
    else:
        effectifs = deux["nous_jgl"].value_counts()
        for jungler in POOL:
            if effectifs.get(jungler, 0) < categories.MINIMUM or (jungler, "jgl") not in fiches:
                print(f"{jungler} : {effectifs.get(jungler, 0)} parties en jungle, pas exploré (moins de {categories.MINIMUM}).")
                continue
            for nom, s in cas.items():
                lignes.append(tester(deux, fiches, jungler, nom, s))
    q = biais.benjamini_hochberg([r["p"] for r in lignes]) if lignes else []
    for r, qq in zip(lignes, q):
        r["q"] = qq
    lignes.sort(key=lambda r: r["p"])
    nom = "pistes_confirmation.csv" if confirmation else "pistes_pool.csv"
    ecrire(ICI / nom, lignes)
    if not confirmation:
        retenues = [{"jungler": r["jungler"], "situation": r["situation"], "coef": r["coef"], "p": r["p"]}
                    for r in lignes if r["p"] < 0.05]
        PISTES.write_text(json.dumps({
            "regle": "Pistes exploratoires à p < 0,05 (avant correction) sur l'échantillon figé, à retester telles quelles.",
            "echantillon_fige": echantillon.lire_fige()["N"] if echantillon.lire_fige() else None,
            "pistes": retenues,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(lignes)} tests exploratoires, {len(retenues)} pistes retenues pour confirmation.")
    for r in lignes[:15]:
        print(f"{r['jungler']:12s} {r['situation']:38s} {100 * r['winrate_dedans']:5.1f} % ({r['parties_dedans']}) "
              f"contre {100 * r['winrate_dehors']:5.1f} % ; p = {r['p']:.4f} ; q = {r['q']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
