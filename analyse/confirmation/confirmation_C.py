"""Confirmation sur C de tout ce que l'assistant affiche (sauf mix de dégâts et early/late : lanes/confirmer_duree_degats.py).

Chaque bloc est appris sur A + B (ou vient de Lolalytics), puis mesuré sur C (parties collectées après le gel) :
1. Lolalytics : la force des champions du patch, le contre direct et les autres contres prédisent-ils nos victoires ?
2. Or à 15 min sur chaque lane : la prédiction de la draft (modèle des contres appris sur A + B) suit-elle l'or réel ?
3. Ganks réussis avant 15 min : le modèle (appris sur A + B) prédit-il mieux que la moyenne, et mieux que la seule
   catégorie du jungler ?
4. Envahir à 5, 10, 15 et 20 min, par catégorie de jungler : les effets que l'assistant affiche (même sens sur A et B)
   se retrouvent-ils sur C, mesurés de la même façon (à force de champions et écart d'or égaux) ?
Verdict par test : confirmé (q < 5 % après correction pour le nombre de tests du bloc), à surveiller (p < 5 %), rien.
Écrit confirmation/resultats/confirmation_C.json et .md, lus par l'export de l'assistant.

    python3 analyse/confirmation/confirmation_C.py --lolalytics <dossier du patch>
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
ANALYSE = ICI.parent
for d in ("", "contres", "base", "lanes"):
    sys.path.insert(0, str(ANALYSE / d))

import lecture  # noqa: E402
import contres  # noqa: E402
import commun  # noqa: E402
import bloc2_compos as bloc2  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402
import dynamique  # noqa: E402
import ganks  # noqa: E402
from envahir import zone  # noqa: E402

SORTIE = ICI / "resultats"
POSTES = ("top", "jgl", "mid", "adc", "sup")
POSTES_LOLA = {"top": "top", "jgl": "jgl", "mid": "mid", "adc": "adc", "sup": "sup"}


def phi(z):
    return 0.5 * math.erfc(-z / math.sqrt(2))


def p_unilaterale(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def logit_se(X, y, decalage=None):
    """Régression logistique (avec constante), coefficients et erreurs types."""
    n = len(y)
    decalage = np.zeros(n) if decalage is None else decalage
    beta, c = bloc3.logistique(X, y, decalage, lam=1e-6, constante=True)
    Xc = np.column_stack([np.ones(n), X])
    mu = bloc3.sigmoide(decalage + Xc @ np.concatenate([[c], beta]))
    H = (Xc * (mu * (1 - mu))[:, None]).T @ Xc
    se = np.sqrt(np.diag(np.linalg.inv(H + 1e-9 * np.eye(H.shape[0]))))[1:]
    return beta, se


def verdicts(tests):
    """tests : liste de dicts avec « p » ; ajoute q et verdict (correction de Benjamini-Hochberg sur la liste)."""
    if not tests:
        return tests
    q = bloc3.benjamini_hochberg([t["p"] for t in tests])
    for t, qq in zip(tests, q):
        t["q"] = float(qq)
        t["verdict"] = "confirmé" if qq < 0.05 else ("à surveiller" if t["p"] < 0.05 else "rien")
    return tests


def nom_lola(c):
    return "Kayn" if c in ("Kayn rouge", "Kayn bleu") else c


# --- 1. Lolalytics ----------------------------------------------------------------------------------

def bloc_lolalytics(table, dossier):
    tier, mu = {p: {} for p in POSTES}, {}
    with open(Path(dossier) / "champions.csv", encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            if l["poste"] in tier and l["victoires"]:
                tier[l["poste"]][l["champion"]] = (float(l["victoires"]), int(l["parties"]))
    moy = {p: sum(w * n for w, n in t.values()) / sum(n for _, n in t.values()) for p, t in tier.items()}
    with open(Path(dossier) / "matchups.csv", encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            n = int(l["parties"])
            if n >= 30:
                mu[(l["poste"], l["champion"], l["poste_adversaire"], l["adversaire"])] = float(l["delta_2"]) * n / (n + 300)

    def force(c, p):
        t = tier[p].get(nom_lola(c))
        return (t[0] - moy[p]) * t[1] / (t[1] + 1000) if t else 0.0

    def contre(p, a, q, b):   # points de a (au poste p) contre b (au poste q), moyenne des deux sens
        return 0.5 * (mu.get((p, nom_lola(a), q, nom_lola(b)), 0.0) - mu.get((q, nom_lola(b), p, nom_lola(a)), 0.0))

    c_rows = np.where(table["tas"] == "C")[0]
    X = []
    for i in c_rows:
        b = {p: table[f"b_{p}"][i] for p in POSTES}; r = {p: table[f"r_{p}"][i] for p in POSTES}
        F = sum(force(b[p], p) - force(r[p], p) for p in POSTES)
        direct = sum(contre(p, b[p], p, r[p]) for p in POSTES)
        autres = sum(contre(p, b[p], q, r[q]) for p in POSTES for q in POSTES if p != q)
        X.append((F, direct, autres))
    X = np.array(X) / 100
    y = table["bleu_gagne"].to_numpy()[c_rows].astype(float)
    beta, se = logit_se(X, y)
    noms = ["Force du patch", "Contre de l'adversaire direct", "Contres des autres adversaires"]
    tests = [{"nom": n, "coefficient": float(b), "erreur": float(s), "attendu": 4.0, "p": p_unilaterale(b / s)}
             for n, b, s in zip(noms, beta, se)]
    # Lecture simple : victoires du camp annoncé devant de 3 points ou plus par la force + le contre direct.
    total = (X[:, 0] + X[:, 1]) * 100
    fort = np.abs(total) >= 3
    gagne = float(np.mean(np.where(total[fort] > 0, y[fort], 1 - y[fort]))) if fort.any() else math.nan
    return {"parties": int(len(c_rows)), "tests": verdicts(tests), "annonce_3_points": {"parties": int(fort.sum()), "gagne": gagne}}


# --- 2. Or à 15 min par lane -----------------------------------------------------------------------

def bloc_lanes(lignes, tas):
    ab = {lane: [l for l in ls if tas.get(l["match"]) in ("A", "B")] for lane, ls in lignes.items()}
    c = {lane: [l for l in ls if tas.get(l["match"]) == "C"] for lane, ls in lignes.items()}
    modele = dynamique.ModeleLanes(ab)
    analyse = contres.analyser(ab)
    sortie, tests = {}, []
    for lane, postes in contres.LANES.items():
        s = max(analyse[p]["ecart_type_residu"] for p in postes)
        pred = np.array([modele.predire(l, lane) for l in c[lane]]); reel = np.array([l["or"] for l in c[lane]])
        n = len(pred)
        corr = float(np.corrcoef(pred, reel)[0, 1])
        z = math.atanh(corr) * math.sqrt(n - 3)
        proba = np.array([phi(p / s) for p in pred])
        calib = []
        for a, b in ((0, .35), (.35, .45), (.45, .55), (.55, .65), (.65, 1.01)):
            sel = (proba >= a) & (proba < b)
            if sel.sum():
                calib.append({"annonce": f"{int(100 * a)}-{min(100, int(100 * b))} %", "parties": int(sel.sum()),
                              "annonce_moyenne": float(proba[sel].mean()), "devant_reel": float((reel[sel] > 0).mean())})
        fort = proba >= 0.6
        sortie[lane] = {"parties": n, "correlation": corr, "calibration": calib,
                        "annonce_devant_60": {"parties": int(fort.sum()), "devant_reel": float((reel[fort] > 0).mean()) if fort.any() else None}}
        tests.append({"nom": lane, "correlation": corr, "parties": n, "p": p_unilaterale(z)})
    verdicts(tests)
    for t in tests:
        sortie[t["nom"]].update(p=t["p"], q=t["q"], verdict=t["verdict"])
    return sortie


# --- 3. Ganks ----------------------------------------------------------------------------------------

def bloc_ganks(donnees, tas):
    from scipy import sparse
    from sklearn.linear_model import LogisticRegression
    tas2 = {m: ("A" if t in ("A", "B") else "B") for m, t in tas.items()}   # A = A + B, B = C
    groupe = dynamique.lire_catalogue()
    lignes = ganks.lignes_ganks(donnees, tas2)
    cles = {}
    rangs, colonnes = [], []
    for i, l in enumerate(lignes):
        ks = [("base", groupe.get(l["jungler"], "?"), l["lane"]), ("jungler", l["jungler"], l["lane"])]
        ks += [("allie", p, c) for p, c in l["allies"]] + [("adverse", p, c) for p, c in l["adverses"]]
        for k in ks:
            rangs.append(i); colonnes.append(cles.setdefault(k, len(cles)))
    X = sparse.csr_matrix((np.ones(len(rangs)), (rangs, colonnes)), shape=(len(lignes), len(cles)))
    y = np.array([1 if l["kills"] > 0 else 0 for l in lignes])
    a = np.array([l["tas"] == "A" for l in lignes]); b = ~a
    C = json.loads((ANALYSE / "lanes" / "resultats" / "ganks_modele.json").read_text(encoding="utf-8")).get("C", 0.1)
    base = [v for k, v in cles.items() if k[0] == "base"]
    p_full = LogisticRegression(C=C, max_iter=3000).fit(X[a], y[a]).predict_proba(X[b])[:, 1]
    p_base = LogisticRegression(C=1.0, max_iter=3000).fit(X[a][:, base], y[a]).predict_proba(X[b][:, base])[:, 1]
    p_moy = np.full(b.sum(), y[a].mean())

    def pertes(p, yy):
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -(yy * np.log(p) + (1 - yy) * np.log(1 - p))
    yb = y[b]
    l_full, l_base, l_moy = pertes(p_full, yb), pertes(p_base, yb), pertes(p_moy, yb)
    tests = []
    for nom, d in (("mieux que la moyenne", l_moy - l_full), ("mieux que la seule catégorie du jungler", l_base - l_full)):
        z = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
        tests.append({"nom": nom, "gain": float(d.mean()), "p": p_unilaterale(z)})
    calib = []
    for lo, hi in ((0, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.01)):
        sel = (p_full >= lo) & (p_full < hi)
        if sel.sum():
            calib.append({"annonce": f"{int(100 * lo)}-{min(100, int(100 * hi))} %", "lignes": int(sel.sum()),
                          "annonce_moyenne": float(p_full[sel].mean()), "reel": float(yb[sel].mean())})
    return {"lignes_C": int(b.sum()), "parties_C": int(b.sum() // 6), "tests": verdicts(tests), "calibration": calib}


# --- 4. Envahir ----------------------------------------------------------------------------------------

def bloc_envahir(donnees, table, lignes_lanes):
    affiche = json.loads((ANALYSE / "lanes" / "resultats" / "envahir.json").read_text(encoding="utf-8"))
    tas = dict(zip(table["match"], table["tas"]))
    ab = {lane: [l for l in ls if tas.get(l["match"]) in ("A", "B")] for lane, ls in lignes_lanes.items()}
    modele = dynamique.ModeleLanes(ab)
    lc = np.where(table["tas"] == "C")[0]
    lab = np.where(table["tas"].isin(["A", "B"]))[0]
    index = bloc2.Index(table)
    force = bloc3.Force(index, lab)
    _, (dec_c,) = force.decalages(lab, [lc])
    y = index.y.astype(float)[lc]
    matchs = set(table["match"][lc]) & lecture.matchs_presents("timeline_joueurs", donnees)
    joueur = {}
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        joueur[(j["match"], j["participant"])] = (j["equipe"], j["poste"])
    zones, ors, complet = defaultdict(dict), defaultdict(lambda: defaultdict(float)), defaultdict(int)
    for t in lecture.lire_details("timeline_joueurs", donnees, matchs=matchs):
        e, poste = joueur.get((t["match"], t["participant"]), (None, None))
        if e is None:
            continue
        for m in (5, 10, 15, 20):
            if not t[f"or_{m}"]:
                continue
            ors[(t["match"], m)][e] += float(t[f"or_{m}"])
            complet[(t["match"], m)] += 1
            if poste == "jgl" and t[f"x_{m}"]:
                zones[(t["match"], m)][e] = zone(float(t[f"x_{m}"]), float(t[f"y_{m}"]), e)
    groupe = dynamique.lire_catalogue()
    tests = []
    for m_txt, s in affiche.items():
        m = int(m_txt)
        rangs, lignes = [], []
        for k, i in enumerate(lc):
            match = table["match"][i]
            z = zones.get((match, m), {})
            if complet[(match, m)] != 10 or len(z) != 2:
                continue
            o = ors[(match, m)]
            d = table.iloc[i].to_dict()
            pm, pb = modele.predire(d, "mid"), modele.predire(d, "bot")
            gb, gr = groupe.get(d["b_jgl"], ""), groupe.get(d["r_jgl"], "")
            ib, ir = float(z["b"] == "adverse"), float(z["r"] == "adverse")
            prio_b, prio_r = pm > 200 and pb > 200, pm < -200 and pb < -200
            # Pas de variable « envahit » générale : avec les variables par groupe, elle ferait double emploi.
            x = [(o["b"] - o["r"]) / 1000, ib * prio_b - ir * prio_r]
            x += [ib * (gb == g) - ir * (gr == g) for g in dynamique.GROUPES]
            rangs.append(k); lignes.append(x)
        rangs = np.array(rangs); X = np.array(lignes)
        beta, se = logit_se(X, y[rangs], dec_c[rangs])
        # Les effets que l'assistant affiche : même sens sur A et B, au moins 1 point, 100 junglers qui envahissent.
        for gi, g in enumerate(dynamique.GROUPES):
            d = s["groupes"].get(g)
            if not d or d["envahisseurs"] < 100 or d["A"] * d["B"] <= 0 or min(abs(d["A"]), abs(d["B"])) < 1:
                continue
            sens = 1 if d["A"] > 0 else -1
            b, e = beta[2 + gi], se[2 + gi]
            tests.append({"minute": m, "groupe": g, "A": d["A"], "B": d["B"], "C": 100 * (1 / (1 + math.exp(-b)) - 0.5),
                          "parties_C": int(len(rangs)), "p": p_unilaterale(sens * b / e)})
    return {"tests": verdicts(tests)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lolalytics", required=True)
    args = parser.parse_args()
    donnees = contres.dossier_donnees()
    regle = commun.lire_decoupage()
    commun.exiger_validation(regle)
    table = commun.drafts(regle, donnees).reset_index(drop=True)
    tas = dict(zip(table["match"], table["tas"]))
    print(f"Parties : A {sum(t == 'A' for t in tas.values())}, B {sum(t == 'B' for t in tas.values())}, "
          f"C {sum(t == 'C' for t in tas.values())}.", flush=True)
    sortie = {"lolalytics": bloc_lolalytics(table, args.lolalytics)}
    print("1. Lolalytics fait.", flush=True)
    lignes, _ = contres.lire(donnees)
    sortie["lanes"] = bloc_lanes(lignes, tas)
    print("2. Lanes fait.", flush=True)
    sortie["ganks"] = bloc_ganks(donnees, tas)
    print("3. Ganks fait.", flush=True)
    sortie["envahir"] = bloc_envahir(donnees, table, lignes)
    print("4. Envahir fait.", flush=True)
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / "confirmation_C.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    pc = lambda x: f"{100 * x:.0f} %"
    L = sortie["lolalytics"]
    texte = ["# Confirmation sur C de ce qu'affiche l'assistant", "",
             "Appris sur A + B (ou Lolalytics), mesuré sur C. Confirmé = moins de 5 % de chances d'être un hasard après correction.", "",
             f"## 1. Lolalytics ({L['parties']} parties de C)", "",
             "| Élément | Coefficient sur C (attendu ≈ 4 si les points sont justes) | Verdict |", "|---|---|---|"]
    texte += [f"| {t['nom']} | {t['coefficient']:.1f} ± {t['erreur']:.1f} | {t['verdict']} |" for t in L["tests"]]
    a = L["annonce_3_points"]
    texte += ["", f"- Quand la force + le contre direct donnent 3 points d'avance ou plus à un camp ({a['parties']} parties), "
              f"il gagne {pc(a['gagne'])}.", "", "## 2. Or à 15 min par lane", "",
              "| Lane | Parties | Corrélation prédit / réel | Annoncée devant à 60 % ou plus : devant en vrai | Verdict |", "|---|---|---|---|---|"]
    for lane, d in sortie["lanes"].items():
        f = d["annonce_devant_60"]
        texte.append(f"| {lane} | {d['parties']} | {d['correlation']:.2f} | "
                     f"{pc(f['devant_reel']) if f['devant_reel'] is not None else '—'} ({f['parties']}) | {d['verdict']} |")
    G = sortie["ganks"]
    texte += ["", f"## 3. Ganks réussis avant 15 min ({G['parties_C']} parties de C)", ""]
    texte += [f"- Le modèle prédit {t['nom']} : gain {1000 * t['gain']:.1f} millièmes, **{t['verdict']}**." for t in G["tests"]]
    texte += ["", "| Chance annoncée | Lignes | Annoncé | Réel |", "|---|---|---|---|"]
    texte += [f"| {c['annonce']} | {c['lignes']} | {pc(c['annonce_moyenne'])} | {pc(c['reel'])} |" for c in G["calibration"]]
    texte += ["", "## 4. Envahir (effets affichés par l'assistant)", "",
              "| Minute | Jungler | A | B | C | Verdict |", "|---|---|---|---|---|---|"]
    texte += [f"| {t['minute']} | {t['groupe']} | {t['A']:+.1f} | {t['B']:+.1f} | {t['C']:+.1f} | {t['verdict']} |"
              for t in sortie["envahir"]["tests"]]
    texte.append("")
    (SORTIE / "confirmation_C.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
