"""Tests des hypothèses fixées à l'avance dans hypotheses.json (tâche 2).

Les profils de champion (peel, assassin, engage, timing, dégâts réels...) viennent de categories.py,
calculés sur l'échantillon figé seulement. Les tests tournent :
- sur l'échantillon figé (c'est là que les hypothèses sont cherchées) ;
- sur les parties arrivées après (confirmation), dès qu'il y en a assez.

Sortie : analyse/resultats/biais_tests.csv. pandas et statsmodels sont nécessaires ; sinon, sauté.

Les fonctions de construction des variables n'ont besoin que des champions et du gagnant pour les
hypothèses A1, D1, E1, F1, F2, G1, G2 : elles servent aussi, en local, à confirmer sur l'archive
(script explorations/confirmer_archives.py).
"""

import csv
import json
import math
import sys
from pathlib import Path

import categories
from regle import charger_catalogue, etiqueter

ICI = Path(__file__).resolve().parent
RESULTATS = ICI / "resultats"
HYPOTHESES = ICI / "hypotheses.json"
POSTES = ("top", "jgl", "mid", "adc", "sup")
CONFIRMATION_MIN = 3000
DUREE_CENTRE = 28.0
CHAMPION_ONLY = ("A1", "D1", "E1", "F1", "F2", "G1", "G2")


def invlogit(x):
    return 1 / (1 + math.exp(-x))


def p_valeur(z):
    return math.erfc(abs(z) / math.sqrt(2))


def benjamini_hochberg(p):
    ordre = sorted(range(len(p)), key=lambda i: p[i])
    q = [1.0] * len(p)
    minimum = 1.0
    for rang in range(len(ordre), 0, -1):
        i = ordre[rang - 1]
        minimum = min(minimum, p[i] * len(p) / rang)
        q[i] = minimum
    return q


# --- Profils utilisés ----------------------------------------------------------------------

def table_profils(profils):
    """{(champion, poste): fiche} à partir de la sortie de categories.profils()."""
    fiches = {}
    for ligne in profils.to_dict("records"):
        fiches[(ligne["champion"], ligne["poste"])] = ligne
    return fiches


def timing_croise(j, profils):
    """Timing calculé sur l'autre pli : {pli de la partie: {(champion, poste): (timing, tardif)}}.

    Pour une partie du pli 0, on utilise le timing mesuré sur les parties du pli 1, et inversement.
    Seuls les champions qui ont un profil (100 parties ou plus) en reçoivent un.
    """
    connus = set(zip(profils["champion"], profils["poste"]))
    sortie = {}
    for pli in (0, 1):
        autre = j[j["pli"] != pli]
        scores = categories.scores_timing(autre, minimum=1)
        scores = scores[[cle in connus for cle in scores.index]]
        jungle = scores[[p == "jgl" for _, p in scores.index]]["timing"].dropna()
        seuil = jungle.quantile(0.25) if len(jungle) else -1
        sortie[pli] = {
            cle: (valeur, int(cle[1] == "jgl" and valeur <= seuil))
            for cle, valeur in scores["timing"].dropna().items()
        }
    return sortie


# --- Variables par partie ------------------------------------------------------------------

def variables_parties(parties, fiches, catalogue, timing=None, plis=None):
    """Une ligne par partie avec, pour chaque côté, les variables des hypothèses (champions seuls).

    `timing` : dict pli -> {(champion, poste): (timing, tardif)} pour la validation croisée ;
    sinon, le timing complet des fiches.
    """
    import pandas as pd

    lignes = []
    for partie in parties.to_dict("records"):
        ligne = {"match": partie["match"], "rang": str(partie["palier"])[:1], "bleu_gagne": int(partie["gagnant"] == "b")}
        pli = plis.get(partie["match"]) if plis is not None else None
        for cote in ("b", "r"):
            champions = {poste: partie[f"{cote}_{poste}"] for poste in POSTES}
            f = {poste: fiches.get((nom, poste)) for poste, nom in champions.items()}

            def drapeau(poste, cle):
                return int(bool(f[poste]) and f[poste].get(cle, 0) == 1)

            def tim(poste):
                cle = (champions[poste], poste)
                if timing is not None and pli is not None:
                    # timing[pli] a été mesuré sur les parties de l'AUTRE pli (voir timing_croise).
                    return timing[pli].get(cle, (0.0, 0))
                fiche = f[poste]
                if not fiche or fiche.get("timing") != fiche.get("timing"):
                    return (0.0, 0)
                return (fiche["timing"], int(fiche.get("jungler_tardif", 0)))

            ligne[f"{cote}_assassins"] = sum(drapeau(p, "pick_mesure") for p in POSTES)
            ligne[f"{cote}_peel"] = sum(drapeau(p, "peel_mesure") for p in POSTES)
            ligne[f"{cote}_engage"] = sum(drapeau(p, "engage_mesure") for p in POSTES)
            ligne[f"{cote}_timing_lanes"] = sum(tim(p)[0] for p in POSTES if p != "jgl")
            ligne[f"{cote}_timing_jgl"] = tim("jgl")[0]
            ligne[f"{cote}_jgl_tardif"] = tim("jgl")[1]
            ligne[f"{cote}_jgl_envahisseur"] = drapeau("jgl", "jungler_envahisseur")
            ligne[f"{cote}_jgl_counter"] = drapeau("jgl", "counter-engage_mesure")
            fj = f["jgl"]
            ligne[f"{cote}_jgl_ad_mesure"] = int(bool(fj) and fj["part_physique"] >= categories.SEUIL_AD)
            ligne[f"{cote}_ap_mesure"] = sum(
                int(bool(f[p]) and f[p]["part_magique"] >= categories.SEUIL_AP_COEQUIPIER) for p in POSTES if p != "jgl")
            ligne[f"{cote}_type_top"] = (f["top"] or {}).get("type_top", "") or ""
            # Catalogue (réplications F1 et G1).
            dans_catalogue = all(nom in catalogue for nom in champions.values())
            ligne[f"{cote}_catalogue_ok"] = int(dans_catalogue)
            if dans_catalogue:
                ligne[f"{cote}_jgl_ad_catalogue"] = int(catalogue[champions["jgl"]]["degats"] == "AD")
                ligne[f"{cote}_ap_catalogue"] = sum(
                    catalogue[nom]["degats"] in ("AP", "Hybride") for p, nom in champions.items() if p != "jgl")
                ligne[f"{cote}_jgl_counter_catalogue"] = int(catalogue[champions["jgl"]]["principal"] == "Counter-engage")
                ligne[f"{cote}_engage_catalogue"] = int(etiqueter(list(champions.values()), catalogue)["principal"] == "Engage")
            ligne[f"{cote}_jgl"] = champions["jgl"]
            for poste in POSTES:
                ligne[f"{cote}_{poste}"] = champions[poste]
        lignes.append(ligne)
    return pd.DataFrame(lignes)


def ajouter_details(v, t):
    """Durée, écarts d'or par poste (bleu - rouge) à 10 et 15 min, invasion réelle des junglers."""
    import numpy as np

    duree = t.details.set_index("match")["duree_s"] / 60
    v["duree_min"] = v["match"].map(duree)
    if t.timeline is not None and len(t.timeline):
        tl = t.timeline.merge(t.joueurs[["match", "participant", "equipe", "poste"]], on=["match", "participant"])
        for minute in (10, 15):
            pivot = tl.pivot_table(index="match", columns=["equipe", "poste"], values=f"or_{minute}", aggfunc="first")
            for poste in POSTES:
                if ("b", poste) in pivot.columns and ("r", poste) in pivot.columns:
                    ecart = (pivot[("b", poste)] - pivot[("r", poste)]) / 1000
                    v[f"or{minute}_{poste}"] = v["match"].map(ecart)
    else:
        for minute in (10, 15):
            for poste in POSTES:
                v[f"or{minute}_{poste}"] = np.nan
    jungle = t.joueurs[t.joueurs["poste"] == "jgl"].set_index(["match", "equipe"])["enemyJungleMonsterKills"]
    duree_j = t.joueurs[t.joueurs["poste"] == "jgl"].set_index(["match", "equipe"])["duree_min"]
    par_minute = (jungle / duree_j).to_dict()
    for cote in ("b", "r"):
        v[f"{cote}_invasion_reelle"] = [par_minute.get((m, cote), np.nan) for m in v["match"]]
    return v


# --- Modèles -------------------------------------------------------------------------------

def effets_fixes_compos(v, fiches):
    """Effets fixes champion à son poste, +1 côté bleu, -1 côté rouge (rares regroupés par poste)."""
    import numpy as np
    import pandas as pd

    colonnes = {}
    for poste in POSTES:
        for cote, signe in (("b", 1.0), ("r", -1.0)):
            noms = v[f"{cote}_{poste}"].map(lambda nom, poste=poste: nom if (nom, poste) in fiches else "rare")
            for nom in noms.unique():
                cle = f"fe|{poste}|{nom}"
                colonnes.setdefault(cle, np.zeros(len(v)))
                colonnes[cle] += signe * (noms == nom).to_numpy()
    fe = pd.DataFrame(colonnes, index=v.index)
    fe = fe.loc[:, fe.abs().sum() > 0]
    # Une colonne de référence par poste est retirée (la somme des colonnes d'un poste vaut 0).
    for poste in POSTES:
        cols = [c for c in fe.columns if c.split("|")[1] == poste]
        if cols:
            fe = fe.drop(columns=max(cols, key=lambda c: fe[c].abs().sum()))
    return fe


def logit(y, X, groupes=None):
    import statsmodels.api as sm

    X = sm.add_constant(X, has_constant="add")
    modele = sm.Logit(y, X)
    if groupes is not None:
        return modele.fit(disp=False, maxiter=300, method="newton", cov_type="cluster", cov_kwds={"groups": groupes})
    return modele.fit(disp=False, maxiter=300, method="newton", cov_type="HC1")


def deux_lignes(v):
    """Deux lignes par partie : chaque équipe (« nous ») face à l'autre (« eux »)."""
    import pandas as pd

    tables = []
    for nous, eux in (("b", "r"), ("r", "b")):
        t = pd.DataFrame({"match": v["match"], "rang": v["rang"]})
        t["victoire"] = v["bleu_gagne"] if nous == "b" else 1 - v["bleu_gagne"]
        for colonne in v.columns:
            if colonne.startswith(f"{nous}_"):
                t["nous_" + colonne[2:]] = v[colonne]
            elif colonne.startswith(f"{eux}_"):
                t["eux_" + colonne[2:]] = v[colonne]
        signe = 1 if nous == "b" else -1
        for colonne in v.columns:
            if colonne.startswith(("or10_", "or15_")):
                t[colonne] = signe * v[colonne]
        if "duree_min" in v:
            t["duree_min"] = v["duree_min"]
        tables.append(t)
    return pd.concat(tables, ignore_index=True)


def fe_jungle(t, fiches, colonne="nous_jgl", prefixe="j"):
    import pandas as pd

    noms = t[colonne].map(lambda nom: nom if (nom, "jgl") in fiches else "rare")
    return pd.get_dummies(noms, prefix=prefixe, drop_first=True, dtype=float)


def fe_rang(t):
    import pandas as pd

    return pd.get_dummies(t["rang"], prefix="rang", drop_first=True, dtype=float)


def resultat(hid, n, coef, erreur, p, texte, brut="", sens=None):
    """Ligne de résultat commune."""
    return {"id": hid, "n": int(n), "coef": coef, "erreur": erreur, "p": p, "texte": texte, "brut": brut, "sens": sens}


def winrate(serie):
    return f"{100 * serie.mean():.1f} %" if len(serie) else "-"


def tests(v, fiches, avec_details=True, exclure=(), seulement=None):
    """Lance les tests possibles sur la table de parties `v`. Renvoie une liste de résultats."""
    import numpy as np
    import pandas as pd

    sortie = []
    attendus = {h["id"]: h["sens_attendu"] for h in json.loads(HYPOTHESES.read_text(encoding="utf-8"))["hypotheses"]}

    def voulu(hid):
        return seulement is None or hid in seulement

    def sens_ok(hid, coef):
        attendu = attendus.get(hid, "")
        if attendu.startswith("positif"):
            return coef > 0
        if attendu.startswith("négatif"):
            return coef < 0
        return None

    fe = effets_fixes_compos(v, fiches)
    y = v["bleu_gagne"].astype(float)

    # A1 : 2 assassins ou plus contre une compo sans peel.
    if voulu("A1"):
        a_b, a_r = (v["b_assassins"] >= 2).astype(float), (v["r_assassins"] >= 2).astype(float)
        np_b, np_r = (v["b_peel"] == 0).astype(float), (v["r_peel"] == 0).astype(float)
        X = pd.concat([fe, pd.DataFrame({"assassins": a_b - a_r, "sans_peel": np_b - np_r,
                                         "test": a_b * np_r - a_r * np_b})], axis=1)
        m = logit(y, X)
        b, e = m.params["test"], m.bse["test"]
        dedans_b, dedans_r = (a_b * np_r * (1 - a_r * np_b)) == 1, (a_r * np_b * (1 - a_b * np_r)) == 1
        dedans = pd.concat([y[dedans_b], 1 - y[dedans_r]])
        autres_b = (a_b == 1) & ~dedans_b
        autres_r = (a_r == 1) & ~dedans_r
        autres = pd.concat([y[autres_b], 1 - y[autres_r]])
        p_avec = invlogit(b / 2)
        sortie.append(resultat("A1", m.nobs, b, e, m.pvalues["test"],
            f"À force de champions égale, une équipe à 2 assassins ou plus contre une compo sans peel gagne environ "
            f"{100 * p_avec:.1f} % au lieu de 50 %.",
            f"Brut : 2 assassins+ contre sans peel {winrate(dedans)} ({len(dedans)} cas) ; 2 assassins+ contre une compo avec peel {winrate(autres)} ({len(autres)} cas).",
            sens_ok("A1", b)))

    # E1 : cycle des types au top.
    if voulu("E1"):
        types = {cote: v[f"{cote}_type_top"] for cote in ("b", "r")}
        d = {c: (types[c] == "distance").astype(float) for c in "br"}
        c_ = {c: (types[c] == "combattant").astype(float) for c in "br"}
        f_ = {c: (types[c] == "front").astype(float) for c in "br"}
        cycle = (d["b"] * c_["r"] - c_["b"] * d["r"]) + (c_["b"] * f_["r"] - f_["b"] * c_["r"]) + (f_["b"] * d["r"] - d["b"] * f_["r"])
        connus = (types["b"] != "") & (types["r"] != "")
        X = pd.concat([fe, pd.DataFrame({"test": cycle})], axis=1)[connus]
        m = logit(y[connus], X)
        b, e = m.params["test"], m.bse["test"]
        brut = []
        for gagnant, perdant in (("distance", "combattant"), ("combattant", "front"), ("front", "distance")):
            cas_b = (types["b"] == gagnant) & (types["r"] == perdant)
            cas_r = (types["r"] == gagnant) & (types["b"] == perdant)
            serie = pd.concat([y[cas_b], 1 - y[cas_r]])
            brut.append(f"{gagnant} contre {perdant} : {winrate(serie)} ({len(serie)})")
        sortie.append(resultat("E1", m.nobs, b, e, m.pvalues["test"],
            f"À force de champions égale, le type « favorable » du cycle gagne environ {100 * invlogit(b):.1f} % au lieu de 50 %.",
            "Brut (sans contrôle des champions) : " + " ; ".join(brut), sens_ok("E1", b)))

    deux = deux_lignes(v)
    groupes = pd.factorize(deux["match"])[0]
    fej, fer = fe_jungle(deux, fiches), fe_rang(deux)
    yy = deux["victoire"].astype(float)

    # D1 : jungler tardif contre jungler envahisseur (profils de champion).
    if voulu("D1"):
        fee = fe_jungle(deux, fiches, "eux_jgl", "e")
        test = (deux["nous_jgl_tardif"] * deux["eux_jgl_envahisseur"]).astype(float)
        X = pd.concat([fej, fee, fer, pd.DataFrame({"test": test})], axis=1)
        m = logit(yy, X, groupes)
        b, e = m.params["test"], m.bse["test"]
        tardif = deux["nous_jgl_tardif"] == 1
        sortie.append(resultat("D1", m.nobs, b, e, m.pvalues["test"],
            f"À force de junglers égale, un jungler tardif face à un jungler envahisseur gagne environ "
            f"{100 * invlogit(b):.1f} % au lieu de 50 %.",
            f"Brut : jungler tardif contre envahisseur {winrate(yy[tardif & (deux['eux_jgl_envahisseur'] == 1)])} "
            f"({int((tardif & (deux['eux_jgl_envahisseur'] == 1)).sum())}) ; contre les autres {winrate(yy[tardif & (deux['eux_jgl_envahisseur'] == 0)])} "
            f"({int((tardif & (deux['eux_jgl_envahisseur'] == 0)).sum())}).",
            sens_ok("D1", b)))

    # F1 et F2 : équilibre des dégâts.
    for hid, ad, ap, filtre in (
        ("F1", "nous_jgl_ad_catalogue", "nous_ap_catalogue", deux["nous_catalogue_ok"] == 1),
        ("F2", "nous_jgl_ad_mesure", "nous_ap_mesure", deux["nous_jgl"].notna()),
    ):
        if not voulu(hid):
            continue
        garder = filtre & ~deux["match"].isin(set(exclure)) if hid == "F1" else filtre
        sous = deux[garder]
        peu = (sous[ap] <= 1).astype(float)
        X = pd.concat([fe_jungle(sous, fiches), fe_rang(sous),
                       pd.DataFrame({"peu_ap": peu, "test": peu * sous[ad].astype(float)})], axis=1)
        m = logit(sous["victoire"].astype(float), X, pd.factorize(sous["match"])[0])
        b, e = m.params["test"], m.bse["test"]
        cas = (sous[ad] == 1) & (peu == 1)
        hors = (sous[ad] == 1) & (peu == 0)
        sortie.append(resultat(hid, m.nobs, b, e, m.pvalues["test"],
            f"À force de jungler égale, un jungler AD avec au plus un coéquipier AP gagne environ {100 * invlogit(b):.1f} % "
            f"au lieu de 50 % (comparé à un jungler non AD dans la même situation).",
            f"Brut : jungler AD avec au plus 1 AP {winrate(sous['victoire'][cas])} ({int(cas.sum())}) ; jungler AD avec 2 AP ou plus "
            f"{winrate(sous['victoire'][hors])} ({int(hors.sum())}).",
            sens_ok(hid, b)))

    # G1 et G2 : jungler counter-engage contre compo engage.
    for hid, jg, adv, filtre in (
        ("G1", "nous_jgl_counter_catalogue", "eux_engage_catalogue", (deux["nous_catalogue_ok"] == 1) & (deux["eux_catalogue_ok"] == 1)),
        ("G2", "nous_jgl_counter", None, deux["nous_jgl"].notna()),
    ):
        if not voulu(hid):
            continue
        garder = filtre & ~deux["match"].isin(set(exclure)) if hid == "G1" else filtre
        sous = deux[garder]
        engage = sous[adv].astype(float) if adv else (sous["eux_engage"] >= 2).astype(float)
        X = pd.concat([fe_jungle(sous, fiches), fe_rang(sous),
                       pd.DataFrame({"engage_adverse": engage, "test": engage * sous[jg].astype(float)})], axis=1)
        m = logit(sous["victoire"].astype(float), X, pd.factorize(sous["match"])[0])
        b, e = m.params["test"], m.bse["test"]
        ce = sous[jg] == 1
        sortie.append(resultat(hid, m.nobs, b, e, m.pvalues["test"],
            f"À force de jungler égale, un jungler counter-engage contre une compo engage gagne environ {100 * invlogit(b):.1f} % "
            f"au lieu de 50 % (comparé à un autre jungler contre la même compo).",
            f"Brut : jungler counter-engage contre engage {winrate(sous['victoire'][ce & (engage == 1)])} ({int((ce & (engage == 1)).sum())}) ; "
            f"contre les autres compos {winrate(sous['victoire'][ce & (engage == 0)])} ({int((ce & (engage == 0)).sum())}).",
            sens_ok(hid, b)))

    if not avec_details:
        return sortie

    # Tests qui ont besoin de la durée et de l'or : parties de 15 min ou plus.
    longues = v["duree_min"] >= categories.DUREE_MIN

    if voulu("B1"):
        timing = v["b_timing_lanes"] + v["b_timing_jgl"] - v["r_timing_lanes"] - v["r_timing_jgl"]
        ecart_type = timing[longues].std()
        z = timing / ecart_type
        duree = (v["duree_min"] - DUREE_CENTRE) / 10
        X = pd.concat([fe, pd.DataFrame({"duree": duree, "test": z * duree})], axis=1)[longues]
        m = logit(y[longues], X)
        b, e = m.params["test"], m.bse["test"]
        court, long_ = (20 - DUREE_CENTRE) / 10, (38 - DUREE_CENTRE) / 10
        sortie.append(resultat("B1", m.nobs, b, e, m.pvalues["test"],
            f"À force de champions égale, l'équipe dont la compo est plus early d'un cran (1 écart type) gagne environ "
            f"{100 * invlogit(b * court):.1f} % des parties de 20 min et {100 * invlogit(b * long_):.1f} % de celles de 38 min.",
            f"{int((~longues).sum())} parties de moins de 15 min écartées.", sens_ok("B1", b)))

    deux_l = deux[deux["duree_min"] >= categories.DUREE_MIN]
    g_l = pd.factorize(deux_l["match"])[0]
    yl = deux_l["victoire"].astype(float)

    if voulu("B2"):
        zj = (deux_l["nous_timing_jgl"] - deux_l["nous_timing_jgl"].mean()) / deux_l["nous_timing_jgl"].std()
        zl = (deux_l["nous_timing_lanes"] - deux_l["nous_timing_lanes"].mean()) / deux_l["nous_timing_lanes"].std()
        X = pd.concat([fe_jungle(deux_l, fiches), fe_rang(deux_l), pd.DataFrame({"lanes": zl, "test": zj * zl})], axis=1)
        m = logit(yl, X, g_l)
        b, e = m.params["test"], m.bse["test"]
        sortie.append(resultat("B2", m.nobs, b, e, m.pvalues["test"],
            f"Écart entre un jungler early et un jungler tardif (2 écarts types) : avec des lanes tardives, l'early gagne environ "
            f"{100 * invlogit(-2 * b):.1f} % contre 50 % ; avec des lanes early, {100 * invlogit(2 * b):.1f} % contre 50 % "
            f"(hors force propre du jungler).", "", sens_ok("B2", b)))

    or_cols = [f"or15_{p}" for p in POSTES]
    if voulu("C1") and all(c in v for c in or_cols):
        ok = longues & v[or_cols].notna().all(axis=1)
        X = pd.concat([fe, v[or_cols]], axis=1)[ok]
        m = logit(y[ok], X)
        # Test : les 5 pentes sont égales (4 contraintes).
        contraintes = np.zeros((4, len(m.params)))
        for k in range(4):
            contraintes[k, m.params.index.get_loc(or_cols[k])] = 1
            contraintes[k, m.params.index.get_loc(or_cols[k + 1])] = -1
        wald = m.wald_test(contraintes, scalar=True)
        p = float(wald.pvalue)
        pentes = " ; ".join(f"{p_[5:]} {100 * invlogit(m.params[p_]):.1f} %" for p_ in or_cols)
        meilleur = max(or_cols, key=lambda c: m.params[c])
        sortie.append(resultat("C1", m.nobs, float(m.params[meilleur] - m.params["or15_top"]), float("nan"), p,
            f"Équipe avec 1 000 or d'avance à 15 min à un seul poste, tout le reste égal : {pentes}.",
            "Test : les cinq postes convertissent pareil.", None))

    if voulu("C2") and all(c in deux_l for c in or_cols):
        ok = deux_l[or_cols].notna().all(axis=1)
        sous = deux_l[ok]
        zj = (sous["nous_timing_jgl"] - sous["nous_timing_jgl"].mean()) / sous["nous_timing_jgl"].std()
        X = pd.concat([fe_jungle(sous, fiches), fe_rang(sous), sous[or_cols],
                       pd.DataFrame({"test": zj * sous["or15_jgl"]})], axis=1)
        m = logit(sous["victoire"].astype(float), X, pd.factorize(sous["match"])[0])
        b, e = m.params["test"], m.bse["test"]
        base = m.params["or15_jgl"]
        sortie.append(resultat("C2", m.nobs, b, e, m.pvalues["test"],
            f"1 000 or d'avance du jungler à 15 min : environ {100 * invlogit(base + b):.1f} % de victoire pour un jungler "
            f"early (1 écart type), {100 * invlogit(base - b):.1f} % pour un jungler tardif.", "", sens_ok("C2", b)))

    if voulu("D2"):
        ok = deux_l["eux_invasion_reelle"].notna()
        sous = deux_l[ok]
        zi = (sous["eux_invasion_reelle"] - sous["eux_invasion_reelle"].mean()) / sous["eux_invasion_reelle"].std()
        X = pd.concat([fe_jungle(sous, fiches), fe_rang(sous),
                       pd.DataFrame({"invasion": zi, "test": zi * sous["nous_jgl_tardif"].astype(float)})], axis=1)
        m = logit(sous["victoire"].astype(float), X, pd.factorize(sous["match"])[0])
        b, e = m.params["test"], m.bse["test"]
        a = m.params["invasion"]
        sortie.append(resultat("D2", m.nobs, b, e, m.pvalues["test"],
            f"Quand le jungler adverse vole beaucoup de camps (1 écart type au-dessus), un jungler tardif gagne environ "
            f"{100 * invlogit(a + b):.1f} %, un autre jungler {100 * invlogit(a):.1f} % (base 50 %).",
            "Attention : qui gagne envahit plus ; l'effet peut aller dans les deux sens.", sens_ok("D2", b)))

    if voulu("E2") and "or10_top" in v:
        import statsmodels.api as sm

        types = {cote: v[f"{cote}_type_top"] for cote in ("b", "r")}
        d = {c: (types[c] == "distance").astype(float) for c in "br"}
        c_ = {c: (types[c] == "combattant").astype(float) for c in "br"}
        f_ = {c: (types[c] == "front").astype(float) for c in "br"}
        cycle = (d["b"] * c_["r"] - c_["b"] * d["r"]) + (c_["b"] * f_["r"] - f_["b"] * c_["r"]) + (f_["b"] * d["r"] - d["b"] * f_["r"])
        ok = longues & v["or10_top"].notna() & (types["b"] != "") & (types["r"] != "")
        X = sm.add_constant(pd.concat([fe, pd.DataFrame({"test": cycle})], axis=1)[ok], has_constant="add")
        m = sm.OLS(v.loc[ok, "or10_top"], X).fit(cov_type="HC1")
        b, e = m.params["test"], m.bse["test"]
        sortie.append(resultat("E2", m.nobs, b, e, m.pvalues["test"],
            f"À force de champions égale, le top du type « favorable » a environ {1000 * b:+.0f} or à 10 min sur son vis-à-vis.",
            "", sens_ok("E2", b)))
    return sortie


def verdicts(sortie):
    """q-valeurs (Benjamini-Hochberg sur l'ensemble) et verdict provisoire."""
    q = benjamini_hochberg([r["p"] for r in sortie])
    for r, qq in zip(sortie, q):
        r["q"] = qq
        bon_sens = r["sens"] is not False
        if qq < 0.05 and bon_sens:
            r["verdict"] = "significatif"
        elif (qq < 0.10 or r["p"] < 0.05) and bon_sens:
            r["verdict"] = "à surveiller"
        elif r["p"] < 0.05 and not bon_sens:
            r["verdict"] = "sens contraire"
        else:
            r["verdict"] = "rien"
    return sortie


def lignes_csv(echantillon_nom, sortie):
    return [[
        echantillon_nom, r["id"], r["n"], f"{r['coef']:+.4f}",
        "" if r["erreur"] != r["erreur"] else f"{r['erreur']:.4f}",
        f"{r['p']:.4f}", f"{r.get('q', float('nan')):.4f}", r.get("verdict", ""),
        "" if r["sens"] is None else ("oui" if r["sens"] else "non"), r["texte"], r["brut"],
    ] for r in sortie]


ENTETE = ["echantillon", "hypothese", "observations", "coefficient_logit", "erreur", "p", "q_bh", "verdict",
          "sens_attendu", "lecture", "chiffres_bruts"]


def preparer(matchs, profils_fige, j_fige=None, croise=False, donnees=None, t=None):
    """Table de parties prête pour tests() à partir d'une liste de parties (ou de tables déjà chargées)."""
    import lecture
    from tables import charger

    if t is None:
        t = charger(matchs, donnees or lecture.DONNEES)
    fiches = table_profils(profils_fige)
    timing = plis = None
    if croise and j_fige is not None:
        timing = timing_croise(j_fige, profils_fige)
        plis = dict(zip(t.parties["match"], t.parties["ordre"] % 2))
    v = variables_parties(t.parties, fiches, charger_catalogue(), timing, plis)
    v = ajouter_details(v, t)
    return v, fiches


def main():
    try:
        import pandas  # noqa: F401
        import statsmodels  # noqa: F401
    except ImportError as erreur:
        print(f"Biais : sauté, bibliothèque absente ({erreur}).")
        return 0
    import echantillon

    fige = echantillon.lire_fige()
    if not fige:
        print("Biais : pas d'échantillon figé (analyse/echantillon_fige.json), tests sautés.")
        return 0
    matchs, suite = echantillon.decouper()
    t, j, profils = categories.calculer(matchs)
    exclure = fige.get("communs_archive", [])
    v, fiches = preparer(matchs, profils, j, croise=True, t=t)
    del t
    lignes = lignes_csv("fige", verdicts(tests(v, fiches, exclure=exclure)))
    if len(suite) >= CONFIRMATION_MIN:
        vs, _ = preparer(suite, profils)
        lignes += lignes_csv("confirmation", verdicts(tests(vs, fiches)))
        print(f"Biais : confirmation sur {len(suite)} parties arrivées après l'échantillon figé.")
    else:
        print(f"Biais : {len(suite)} parties après l'échantillon figé, il en faut {CONFIRMATION_MIN} pour confirmer.")
    RESULTATS.mkdir(exist_ok=True)
    with open(RESULTATS / "biais_tests.csv", "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(ENTETE)
        ecrivain.writerows(lignes)
    print(f"Biais : {len(lignes)} tests écrits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
