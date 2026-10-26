"""Duels : quand deux champions se croisent seuls et que l'un tue l'autre, qui gagne, à or et niveau égaux ?

Un duel = un kill de champion sans assistance, où seul le tueur a infligé des dégâts de champion à la victime
(nb_sources = 1), à n'importe quel poste (top contre top, mid contre joueur…). On ne voit que les duels qui
finissent en kill : un duel où les deux repartent vivants n'est pas compté. Une tour peut avoir aidé (plongée).

Or et niveau **par rapport à la normale de son poste** (26/10/2026) : un support a toujours moins d'or et de niveaux
qu'un top. Comparer l'or brut des deux champions faisait passer ce retard normal pour une faiblesse « à or égal »,
et donc gonfler la force des supports qui gagnaient malgré lui (Thresh battait 94 % des champions alors qu'il ne
gagne que 24 % de ses duels). Maintenant, pour chaque joueur au moment du kill : son avance d'or = son or moins l'or
moyen de son poste à cette minute (idem pour le niveau). L'écart normal entre postes reste dans le résultat, via un
effet de chaque poste : on lit donc « qui gagne s'ils se croisent seuls, chacun avec l'or habituel de son poste ».

Pour chaque duel : l'avance d'or et de niveau de chacun sur la normale de son poste (or total gagné et niveau,
interpolés entre les relevés de la timeline à 5, 10, 15, 20, 25 et 30 min). Modèle (régression logistique régularisée,
une ligne par duel, du point de vue du champion bleu) :
    victoire du bleu ~ force en duel du champion bleu − celle du rouge
                       + effet du poste du bleu − celui du poste du rouge
                       + évolution de ces forces avec la minute (certains champions sont forts tôt, d'autres tard)
                       + écart des avances d'or + écart des avances de niveau
Analyse à deux tas : appris sur A, vérifié sur B (ensemble du modèle, évolution avec la minute, et force de chaque
champion, avec correction des tests multiples). Seules les forces vérifiées sur B vont dans l'assistant.
Écrit resultats/duels.json et resultats/duels.md.

    python3 analyse/lanes/duels.py
"""

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
import bloc3_biais as bloc3  # noqa: E402
from dynamique import RESULTATS  # noqa: E402

MINUTES = (0, 5, 10, 15, 20, 25, 30)
POSTES = ("top", "jgl", "mid", "adc", "sup")
MINUTE_REF = 13.0          # les évolutions avec le temps sont centrées sur la minute médiane des duels
POOL = ("Fiddlesticks", "Ivern", "Dr. Mundo", "Kayn bleu", "Kayn rouge", "Viego", "Maokai", "Skarner", "Morgana", "Urgot")


def interpoler(releves, t):
    """Valeur à la minute t, interpolée entre les relevés {minute: valeur} ; None si hors des relevés."""
    xs = sorted(m for m, v in releves.items() if v is not None)
    if not xs or t > xs[-1]:
        return None
    for a, b in zip(xs, xs[1:]):
        if a <= t <= b:
            return releves[a] + (releves[b] - releves[a]) * (t - a) / (b - a)
    return releves[xs[0]]


def lire_duels(donnees, tas):
    matchs = {m for m, t in tas.items() if t in ("A", "B")} & lecture.matchs_presents("timeline_joueurs", donnees)
    joueur = {}                                   # (match, participant) -> (equipe, champion, poste)
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        joueur[(j["match"], j["participant"])] = (j["equipe"], j["champion"], j["poste"])
    releves = {}
    for t in lecture.lire_details("timeline_joueurs", donnees, matchs=matchs):
        cle = (t["match"], t["participant"])
        if cle not in joueur:
            continue
        val = lambda col: float(t[col]) if t[col] else None
        releves[cle] = ({0: 500.0, **{m: val(f"or_{m}") for m in MINUTES[1:]}},
                        {0: 1.0, **{m: val(f"niveau_{m}") for m in MINUTES[1:]}})
    # La normale de chaque poste : or et niveau moyens à chaque relevé (toutes les parties lues).
    somme = defaultdict(lambda: [0.0, 0.0, 0])
    for cle, (ors, niveaux) in releves.items():
        p = joueur[cle][2]
        for m in MINUTES[1:]:
            if ors[m] is not None and niveaux[m] is not None:
                s = somme[(p, m)]; s[0] += ors[m]; s[1] += niveaux[m]; s[2] += 1
    normale = {p: ({0: 500.0, **{m: somme[(p, m)][0] / somme[(p, m)][2] for m in MINUTES[1:] if somme[(p, m)][2]}},
                   {0: 1.0, **{m: somme[(p, m)][1] / somme[(p, m)][2] for m in MINUTES[1:] if somme[(p, m)][2]}}) for p in POSTES}
    duels = []
    for e in lecture.lire_details("evenements", donnees, matchs=matchs):
        if e["type"] != "CHAMPION_KILL" or e["assistants"] or e["nb_sources"] != "1":
            continue
        k, v = (e["match"], e["participant"]), (e["match"], e["victime"])
        if k not in joueur or v not in joueur or k not in releves or v not in releves:
            continue
        minute = float(e["t_ms"]) / 60000
        ok, ov = interpoler(releves[k][0], minute), interpoler(releves[v][0], minute)
        nk, nv = interpoler(releves[k][1], minute), interpoler(releves[v][1], minute)
        if None in (ok, ov, nk, nv):
            continue
        (ek, ck, pk), (_, cv, pv) = joueur[k], joueur[v]
        if pk not in normale or pv not in normale:
            continue
        # Avance sur la normale de son poste à cette minute.
        ok -= interpoler(normale[pk][0], minute); ov -= interpoler(normale[pv][0], minute)
        nk -= interpoler(normale[pk][1], minute); nv -= interpoler(normale[pv][1], minute)
        # Point de vue du champion bleu.
        if ek == "b":
            duels.append({"match": e["match"], "tas": tas[e["match"]], "bleu": ck, "rouge": cv, "bleu_gagne": 1,
                          "postes": (pk, pv), "or": ok - ov, "niveau": nk - nv, "minute": minute})
        else:
            duels.append({"match": e["match"], "tas": tas[e["match"]], "bleu": cv, "rouge": ck, "bleu_gagne": 0,
                          "postes": (pv, pk), "or": ov - ok, "niveau": nv - nk, "minute": minute})
    return duels


def colonnes(n):
    """Positions dans la matrice : forces (n), forces × minute (n), postes (5), postes × minute (5), or, niveau."""
    return {"poste": 2 * n, "poste_temps": 2 * n + 5, "or": 2 * n + 10, "niveau": 2 * n + 11, "total": 2 * n + 12}


def matrice(duels, champions):
    """Matrice creuse : force (±1), force × minute, poste (±1), poste × minute, écart des avances d'or (milliers) et de niveau."""
    from scipy import sparse
    idx = {c: i for i, c in enumerate(champions)}
    n = len(champions); col = colonnes(n); ip = {p: i for i, p in enumerate(POSTES)}
    rangs, cols, vals = [], [], []
    for r, d in enumerate(duels):
        temps = (d["minute"] - MINUTE_REF) / 10
        pb, pr = d["postes"]
        cases = [(idx[d["bleu"]], 1.0), (idx[d["rouge"]], -1.0), (n + idx[d["bleu"]], temps), (n + idx[d["rouge"]], -temps),
                 (col["or"], d["or"] / 1000), (col["niveau"], d["niveau"])]
        if pb != pr:
            cases += [(col["poste"] + ip[pb], 1.0), (col["poste"] + ip[pr], -1.0),
                      (col["poste_temps"] + ip[pb], temps), (col["poste_temps"] + ip[pr], -temps)]
        for c, val in cases:
            rangs.append(r); cols.append(c); vals.append(val)
    return sparse.csr_matrix((vals, (rangs, cols)), shape=(len(duels), col["total"]))


def apprendre(X, y, lam):
    """Régression logistique avec pénalité ridge lam (C = 1 / lam) ; renvoie (coefficients, constante)."""
    from sklearn.linear_model import LogisticRegression
    m = LogisticRegression(C=1.0 / lam, max_iter=2000).fit(X, y)
    return m.coef_[0], float(m.intercept_[0])


def points(b):
    return 100 * (1 / (1 + math.exp(-b)) - 0.5)


def p_unilaterale(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def test_gain(y, p_simple, p_complet):
    """Gain de perte logarithmique du modèle complet sur le simple, et sa p-valeur (test apparié unilatéral)."""
    eps = 1e-12
    ls = -(y * np.log(p_simple + eps) + (1 - y) * np.log(1 - p_simple + eps))
    lc = -(y * np.log(p_complet + eps) + (1 - y) * np.log(1 - p_complet + eps))
    d = ls - lc
    z = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
    return {"gain_millièmes": float(1000 * d.mean()), "p": p_unilaterale(z)}


def main():
    donnees = contres.dossier_donnees()
    regle = commun.lire_decoupage()
    table = commun.drafts_ab(regle, donnees)   # toutes les parties, A et B
    tas = dict(zip(table["match"], table["tas"]))
    duels = lire_duels(donnees, tas)
    compte, compte_a, compte_b = defaultdict(int), defaultdict(int), defaultdict(int)
    for d in duels:
        for c in (d["bleu"], d["rouge"]):
            compte[c] += 1; (compte_a if d["tas"] == "A" else compte_b)[c] += 1
    champions = sorted(compte)
    n = len(champions); col = colonnes(n)
    y = np.array([d["bleu_gagne"] for d in duels], dtype=float)
    a = np.array([d["tas"] == "A" for d in duels]); b = ~a
    X = matrice(duels, champions)
    base = list(range(col["poste"], col["total"]))                      # postes + or + niveau, sans les champions
    sans_temps = list(range(n)) + list(range(col["poste"], col["poste_temps"])) + [col["or"], col["niveau"]]

    # Choix de la régularisation sur A (5 rotations).
    pli = np.random.default_rng(1).integers(0, 5, size=len(duels))
    meilleur = None
    for lam in (3.0, 10.0, 30.0, 100.0):
        pertes = []
        for f in range(5):
            app, note = a & (pli != f), a & (pli == f)
            beta, c = apprendre(X[app], y[app], lam)
            pertes.append(bloc3.perte_log(y[note], bloc3.sigmoide(X[note] @ beta + c)))
        if meilleur is None or np.mean(pertes) < meilleur[0]:
            meilleur = (float(np.mean(pertes)), lam)
    lam = meilleur[1]

    # Vérification sur B (jamais vu pendant l'apprentissage) : l'ensemble, puis chaque champion.
    beta_a, c_a = apprendre(X[a], y[a], lam)
    beta_0, c_0 = apprendre(X[a][:, base], y[a], 1.0)
    beta_1, c_1 = apprendre(X[a][:, sans_temps], y[a], lam)
    p_complet = bloc3.sigmoide(X[b] @ beta_a + c_a)
    ensemble = [dict(nom="Champions, mieux que postes + or + niveau seuls", **test_gain(y[b], bloc3.sigmoide(X[b][:, base] @ beta_0 + c_0), p_complet)),
                dict(nom="Évolution avec la minute, mieux que sans", **test_gain(y[b], bloc3.sigmoide(X[b][:, sans_temps] @ beta_1 + c_1), p_complet))]
    for t in ensemble:
        t["verdict"] = "vérifié" if t["p"] < 0.05 and t["gain_millièmes"] > 0 else "rien"
    tests = []
    Xb, yb = X[b], y[b]
    for ch in champions:
        if compte_a[ch] < 150 or compte_b[ch] < 100:
            continue
        i = champions.index(ch)
        x = np.asarray(Xb[:, i].todense()).ravel()          # +1 s'il est bleu, −1 s'il est rouge, 0 sinon
        sel = x != 0
        b_sans = beta_a.copy(); b_sans[i] = 0.0; b_sans[n + i] = 0.0
        depart = Xb[sel] @ b_sans + c_a
        coef, _ = bloc3.logistique(x[sel][:, None], yb[sel], depart, lam=1e-6)
        mu = bloc3.sigmoide(depart + x[sel] * coef[0])
        erreur = 1 / math.sqrt(max(float(np.sum(mu * (1 - mu) * x[sel] ** 2)), 1e-12))
        sens = 1 if beta_a[i] > 0 else -1
        tests.append({"champion": ch, "force_A": float(beta_a[i]), "force_B": float(coef[0]), "duels_A": compte_a[ch],
                      "duels_B": compte_b[ch], "p": p_unilaterale(sens * coef[0] / erreur)})
    for t, q in zip(tests, bloc3.benjamini_hochberg([t["p"] for t in tests]) if tests else []):
        t["q"] = float(q)
        t["verdict"] = "vérifié" if q < 0.05 else ("à surveiller" if t["p"] < 0.05 else "rien")
    accord = float(np.corrcoef([t["force_A"] for t in tests], [t["force_B"] for t in tests])[0, 1]) if len(tests) > 5 else float("nan")

    # Modèle final, sur A + B, pour l'affichage.
    beta, c = apprendre(X, y, lam)
    force = {ch: float(beta[i]) for i, ch in enumerate(champions)}
    pente = {ch: float(beta[n + i]) for i, ch in enumerate(champions)}
    effet_poste = {p_: float(beta[col["poste"] + k]) for k, p_ in enumerate(POSTES)}
    pente_poste = {p_: float(beta[col["poste_temps"] + k]) for k, p_ in enumerate(POSTES)}
    coef_or, coef_niveau = float(beta[col["or"]]), float(beta[col["niveau"]])
    poste = defaultdict(lambda: defaultdict(int))
    for d in duels:
        poste[d["bleu"]][d["postes"][0]] += 1; poste[d["rouge"]][d["postes"][1]] += 1
    verdict = {t["champion"]: t["verdict"] for t in tests}
    sortie = {"duels": len(duels), "duels_A": int(a.sum()), "duels_B": int(b.sum()), "lambda": lam,
              "or_niveau": "avance sur la normale de son poste à cette minute",
              "verification_B": {"ensemble": ensemble, "accord_forces_A_B": accord, "champions": tests},
              "coef_or_1000": coef_or, "coef_niveau": coef_niveau, "minute_reference": MINUTE_REF,
              "postes": {p_: {"effet": effet_poste[p_], "pente_10min": pente_poste[p_]} for p_ in POSTES},
              "champions": {ch: {"force": force[ch], "pente_10min": pente[ch], "duels": compte[ch],
                                 "poste": max(poste[ch], key=poste[ch].get), "verdict_B": verdict.get(ch, "pas assez de duels")}
                            for ch in champions}}
    RESULTATS.mkdir(parents=True, exist_ok=True)
    (RESULTATS / "duels.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    poste_principal = {ch: sortie["champions"][ch]["poste"] for ch in champions}
    nb_verif = sum(1 for t in tests if t["verdict"] == "vérifié")
    texte = ["# Duels, chacun avec l'or et le niveau habituels de son poste", "",
             f"- {len(duels)} duels (un champion tué par un autre, seul, sans aide) ; A {int(a.sum())}, B {int(b.sum())}.",
             f"- Or et niveau : avance de chacun sur la normale de son poste à cette minute. 1 000 or d'avance de plus = {points(coef_or):+.1f} points ; "
             f"1 niveau = {points(coef_niveau):+.1f} points.",
             *[f"- Sur B : {t['nom']} : gain {t['gain_millièmes']:.1f} millièmes, **{t['verdict']}**." for t in ensemble],
             f"- Force de chaque champion vérifiée sur B : {nb_verif} sur {len(tests)} (accord des forces A / B : {accord:.2f}).", "",
             "## Effet du poste (à 13 min), contre la moyenne des postes", "", "| Poste | Effet | Évolution par 10 min |", "|---|---|---|"]
    texte += [f"| {p_} | {points(effet_poste[p_]):+.1f} points | {points(pente_poste[p_]):+.1f} |" for p_ in POSTES]
    texte.append("")
    for p_, titre in (("top", "Top"), ("jgl", "Jungle"), ("mid", "Mid"), ("adc", "ADC"), ("sup", "Support")):
        liste = sorted((ch for ch in champions if poste_principal[ch] == p_ and compte[ch] >= 400), key=lambda ch: -force[ch])
        texte += [f"## {titre} : force en duel, contre un champion moyen de son poste (à 13 min)", "",
                  "| Champion | Gagne | Évolution par 10 min | Duels | Sur B |", "|---|---|---|---|---|"]
        texte += [f"| {'**' + ch + '**' if ch in POOL else ch} | {50 + points(force[ch]):.0f} % | {points(pente[ch]):+.1f} | {compte[ch]} | "
                  f"{sortie['champions'][ch]['verdict_B']} |" for ch in liste]
        texte.append("")
    (RESULTATS / "duels.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
