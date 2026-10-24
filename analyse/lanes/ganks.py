"""Les ganks réussis : probabilité qu'un jungler tue au moins une fois sur une lane avant 15 minutes.

« Gank réussi » sur la lane L : un kill de champion avant 15 min dont la victime est un laner adverse de L
(top, mid, ou ADC/support pour la bot) et où le jungler a participé (tueur ou assistant). On ne voit
pas les ganks ratés, seulement ceux qui finissent en kill.

Modèle (régression logistique régularisée), une ligne par partie, par équipe et par lane :
- catégorie du jungler × lane (groupes teamfight du catalogue unifié) : la base ;
- le champion jungler lui-même (certains gankent mieux que leur catégorie) ;
- les laners alliés de la lane (ceux qui aident le gank : CC, dégâts) ;
- les laners adverses de la lane (ceux qui meurent souvent aux ganks).
Appris sur A, vérifié sur B (découpage n° 2). Écrit resultats/ganks.md et resultats/ganks_modele.json,
utilisé par l'assistant.

    python3 analyse/lanes/ganks.py
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

import lecture  # noqa: E402
import contres  # noqa: E402
import commun  # noqa: E402
from dynamique import GROUPES, RESULTATS, lire_catalogue  # noqa: E402

T_MAX = 15 * 60_000
LANE_DU_POSTE = {"top": "top", "mid": "mid", "adc": "bot", "sup": "bot"}
POSTES_DE_LANE = {"top": ("top",), "mid": ("mid",), "bot": ("adc", "sup")}


def lignes_ganks(donnees, tas):
    matchs = {m for m, t in tas.items() if t in ("A", "B")} & lecture.matchs_presents("timeline_joueurs", donnees)
    joueurs = {}
    places = defaultdict(dict)
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        p = int(j["participant"])
        joueurs[(j["match"], p)] = (j["equipe"], j["poste"], j["champion"])
        places[j["match"]][(j["equipe"], j["poste"])] = p
    reussis = defaultdict(int)          # (match, equipe du jungler, lane) -> kills de gank
    for e in lecture.lire_details("evenements", donnees, matchs=matchs):
        if e["type"] != "CHAMPION_KILL" or not e["victime"]:
            continue
        try:
            t = float(e["t_ms"])
        except ValueError:
            continue
        if t >= T_MAX:
            continue
        m = e["match"]
        victime = joueurs.get((m, int(e["victime"])))
        if not victime or victime[1] not in LANE_DU_POSTE:
            continue
        equipe = "r" if victime[0] == "b" else "b"
        jungler = places[m].get((equipe, "jgl"))
        participants = {int(x) for x in [e["participant"], *(e["assistants"] or "").split("|")] if x not in ("", "0")}
        if jungler in participants:
            reussis[(m, equipe, LANE_DU_POSTE[victime[1]])] += 1
    sortie = []
    for m, pl in places.items():
        if len(pl) != 10:
            continue
        for equipe in "br":
            adverse = "r" if equipe == "b" else "b"
            jgl = joueurs[(m, pl[(equipe, "jgl")])][2]
            for lane, postes in POSTES_DE_LANE.items():
                sortie.append({"match": m, "tas": tas[m], "lane": lane, "jungler": jgl,
                               "allies": [(p, joueurs[(m, pl[(equipe, p)])][2]) for p in postes],
                               "adverses": [(p, joueurs[(m, pl[(adverse, p)])][2]) for p in postes],
                               "kills": reussis[(m, equipe, lane)]})
    return sortie


def main():
    from scipy import sparse
    from sklearn.linear_model import LogisticRegression

    donnees = contres.dossier_donnees()
    table = commun.drafts(commun.lire_decoupage(), donnees)
    tas = dict(zip(table["match"], table["tas"]))
    groupe = lire_catalogue()
    lignes = lignes_ganks(donnees, tas)
    cles = {}

    def col(k):
        if k not in cles:
            cles[k] = len(cles)
        return cles[k]

    rangs, colonnes = [], []
    for i, l in enumerate(lignes):
        ks = [("base", groupe.get(l["jungler"], "?"), l["lane"]), ("jungler", l["jungler"], l["lane"])]
        ks += [("allie", p, c) for p, c in l["allies"]] + [("adverse", p, c) for p, c in l["adverses"]]
        for k in ks:
            rangs.append(i); colonnes.append(col(k))
    X = sparse.csr_matrix((np.ones(len(rangs)), (rangs, colonnes)), shape=(len(lignes), len(cles)))
    y = np.array([1 if l["kills"] > 0 else 0 for l in lignes])
    a = np.array([l["tas"] == "A" for l in lignes]); b = ~a

    def perte(p, yy):
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return float(-np.mean(yy * np.log(p) + (1 - yy) * np.log(1 - p)))

    base = [v for k, v in cles.items() if k[0] == "base"]
    meilleur = None
    for C in (0.03, 0.1, 0.3, 1.0):
        mod = LogisticRegression(C=C, max_iter=2000).fit(X[a], y[a])
        pb = perte(mod.predict_proba(X[b])[:, 1], y[b])
        if meilleur is None or pb < meilleur[0]:
            meilleur = (pb, C, mod)
    pb, C, mod = meilleur
    mod0 = LogisticRegression(C=1.0, max_iter=2000).fit(X[a][:, base], y[a])
    pb0 = perte(mod0.predict_proba(X[b][:, base])[:, 1], y[b])
    pmoy = perte(np.full(b.sum(), y[a].mean()), y[b])

    # Probabilité par catégorie et par lane (brute, sur A + B).
    brut = defaultdict(lambda: [0, 0])
    for l, yy in zip(lignes, y):
        k = (groupe.get(l["jungler"], "?"), l["lane"])
        brut[k][0] += 1; brut[k][1] += yy
    coef = {k: float(mod.coef_[0][v]) for k, v in cles.items()}
    modele = {"constante": float(mod.intercept_[0]), "C": C,
              "base": {f"{g}|{lane}": coef.get(("base", g, lane), 0.0) for g in GROUPES for lane in POSTES_DE_LANE},
              "jungler": {f"{c}|{lane}": v for (t, c, lane), v in coef.items() if t == "jungler"},
              "allie": {f"{p}|{c}": v for (t, p, c), v in coef.items() if t == "allie"},
              "adverse": {f"{p}|{c}": v for (t, p, c), v in coef.items() if t == "adverse"},
              "parties": int(len(lignes) // 6)}
    RESULTATS.mkdir(parents=True, exist_ok=True)
    (RESULTATS / "ganks_modele.json").write_text(json.dumps(modele, ensure_ascii=False) + "\n", encoding="utf-8")
    sig = lambda x: 1 / (1 + math.exp(-x))
    texte = ["# Ganks réussis avant 15 minutes", "",
             f"- {len(lignes) // 6} parties (A + B, Émeraude-Diamant, avec timeline). Gank réussi = le jungler participe à un kill "
             "d'un laner adverse de la lane avant 15 min.",
             f"- Vérification sur B (perte log, plus bas = mieux) : sans rien {pmoy:.4f} ; catégorie du jungler et lane {pb0:.4f} ; "
             f"modèle complet (jungler, laners alliés et adverses) {pb:.4f}.", "",
             "## Probabilité d'au moins un gank réussi avant 15 min, par catégorie de jungler", "",
             "| Jungler | top | mid | bot | parties |", "|---|---|---|---|---|"]
    for g in GROUPES:
        n = brut[(g, "top")][0]
        texte.append(f"| {g} | " + " | ".join(f"{100 * brut[(g, l)][1] / max(1, brut[(g, l)][0]):.0f} %" for l in POSTES_DE_LANE) + f" | {n} |")
    texte += ["", "## Les laners qui changent le plus les chances de gank (effet sur la cote, modèle complet)", ""]
    for genre, titre in (("allie", "Alliés qui aident le plus"), ("adverse", "Adversaires qui meurent le plus aux ganks")):
        top = sorted(((v, k) for k, v in coef.items() if k[0] == genre), reverse=True)[:12]
        texte.append(f"- **{titre}** : " + ", ".join(f"{c} ({p}) ×{math.exp(v):.2f}" for v, (_, p, c) in top))
    texte.append("")
    junglers = sorted(((v, k[1], k[2]) for k, v in coef.items() if k[0] == "jungler"), reverse=True)
    texte.append("- **Junglers qui gankent le mieux par rapport à leur catégorie** : " +
                 ", ".join(f"{c} ({lane}) ×{math.exp(v):.2f}" for v, c, lane in junglers[:10]))
    texte.append("")
    (RESULTATS / "ganks.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
