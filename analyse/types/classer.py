"""Classification des champions en 10 types, apprise sur les choix du propriétaire.

Les types (non exclusifs : un champion peut en avoir plusieurs) :
    carry, enchanteur, assassin, plongeur, attrapeur, tank, bloqueur, dueliste, splitpusher, teamfighter.

Comment (version 4, 26/10/2026) :
1. Pour chaque champion, des mesures tirées des parties (moyenne de ses postes, pondérée par les parties) : part des
   dégâts et de l'or, dégâts encaissés, soins et boucliers sur les alliés, contrôle infligé, solo kills, position à 20,
   25 et 30 min, où il meurt, kills sur les ADC et mids, kills et assists en combat d'équipe… ; chacune aussi comparée
   aux champions de son poste (suffixe _p) ; la part de ses parties à chaque poste ; et ses sorts (Data Dragon).
2. Les choix du propriétaire (analyse/types/validations.csv, venus de la page « Types des champions ») : pour chaque
   champion revu, les 10 types en oui ou non. Plus ses champions de référence (references.csv), comptés oui.
3. Pour chaque type, une régression logistique sur 1 à 3 mesures, choisies parmi celles qui ont du sens pour ce type :
   la combinaison qui retrouve le mieux ses choix sans les avoir vus (on retire chaque champion revu, on apprend sur les
   autres, on le reclasse). Note de 0 à 100 ; type proposé à partir de 50, 3 au plus par champion (les mieux notés),
   au moins un.
4. Deux tas : les mesures de l'apprentissage viennent de A ; on vérifie que B donne les mêmes décisions.
5. Un champion revu garde ses choix ; les autres prennent le calcul. Le catalogue unifié reçoit le résultat.

    python3 analyse/types/classer.py              (après analyse/preparer.sh)

Écrit analyse/types/resultats/notes.csv, analyse/types/resultats/types.md et .json, et les colonnes des types de
analyse/catalogues/catalogue_unifie.csv.
"""

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ICI = Path(__file__).resolve().parent
ANALYSE = ICI.parent
sys.path.insert(0, str(ANALYSE))
sys.path.insert(0, str(ANALYSE / "base"))

import lecture  # noqa: E402
import commun  # noqa: E402

TYPES = ("carry", "enchanteur", "assassin", "plongeur", "attrapeur", "tank", "bloqueur", "dueliste", "splitpusher", "teamfighter")
REFERENCES = ICI / "references.csv"
VALIDATIONS = ICI / "validations.csv"
RESULTATS = ICI / "resultats"
CATALOGUE = ANALYSE / "catalogues" / "catalogue_unifie.csv"
SEUIL = 50
MAX_TYPES = 3      # champion pas encore revu : 3 types au plus (les mieux notés)
FRAGILE = -0.5     # fragile : dégâts encaissés et atténués par minute à plus d'un demi-écart-type sous la moyenne des champions
MIN_PARTIES = 150
POSTES = ("top", "jgl", "mid", "adc", "sup")
SORTS = ANALYSE / "catalogues" / "sorts.csv"
REFUS = set()      # (champion, type) refusés exprès par le propriétaire (validations.csv), rempli par main()

# Les mesures de chaque type et la régularisation (C), choisies le 26/10/2026 sur les 173 champions revus par le
# propriétaire : la combinaison de 1 à 3 mesures (parmi celles qui ont du sens pour le type) qui retrouve le mieux ses
# choix sans les avoir vus (justesse 87 à 99 % selon le type, voir resultats/types.md).
MESURES = {
    "carry": (["part_adc", "or_min_p", "profondeur_p"], 0.3),
    "enchanteur": (["sauve", "encaisse_min_p"], 3.0),
    "assassin": (["assassin_p", "part_top", "part_adc"], 3.0),
    "plongeur": (["profondeur_p", "encaisse_min", "batiments_min_p"], 0.3),
    "attrapeur": (["pick_kill", "cc_min", "n_controle"], 0.3),
    "tank": (["part_subis", "encaisse_min", "assassin_p"], 3.0),
    "bloqueur": (["cc_min", "encaisse_min_p", "batiments_min_p"], 0.3),
    "dueliste": (["solo_p", "seul_cote", "encaisse_min"], 1.0),
    "splitpusher": (["seul_cote_p", "n_protection", "part_top"], 1.0),
    "teamfighter": (["kp_combat_p", "kills_par_combat_p", "dpm"], 3.0),
}
# Les mesures de base, chacune aussi comparée aux champions de son poste (suffixe _p).
BASE = ["part_degats", "part_subis", "encaisse_min", "soins_allies_min", "boucliers_allies_min", "cc_min", "immob_min",
        "batiments_min", "solo", "pick_kill", "immob_kill", "sauve", "en_inferiorite", "dpm", "or_min", "seul_cote", "assassin",
        "tf_10", "carry_tf_10", "profondeur", "part_carry", "td_par_combat", "kills_par_combat", "kp_combat"]
# Mesures très étalées (beaucoup de zéros, quelques très grandes valeurs) : comparées en logarithme.
LOG = {"soins_allies_min", "boucliers_allies_min", "batiments_min", "solo", "assassin", "sauve", "pick_kill", "immob_kill",
       "en_inferiorite", "encaisse_min", "dpm"}
LIBELLES = {
    "part_degats": "part des dégâts de l'équipe", "dpm": "dégâts par minute", "or_min": "or par minute",
    "part_subis": "part des dégâts encaissés par l'équipe", "encaisse_min": "dégâts encaissés et atténués par minute",
    "soins_allies_min": "soins sur les alliés", "boucliers_allies_min": "boucliers sur les alliés",
    "assassin": "kills sur un ADC ou un mid, presque seul, après 14 min", "part_carry": "part de ses kills sur un ADC ou un mid",
    "carry_tf_10": "kills sur ADC ou mid en combat d'équipe", "pick_kill": "kills à deux sur un ennemi isolé",
    "immob_kill": "contrôle puis kill avec un allié", "cc_min": "temps de contrôle infligé", "immob_min": "immobilisations par minute",
    "sauve": "alliés sauvés de la mort", "solo": "solo kills", "en_inferiorite": "kills en infériorité numérique",
    "seul_cote": "seul sur une lane de côté à 20, 25 et 30 min", "presence_tf_poste": "présence en combat d'équipe (comparée à son poste)",
    "td_par_combat": "participations par combat", "kills_par_combat": "kills par combat",
    "profondeur": "où il meurt après 14 min (0 = chez lui, 1 = base adverse)",
    "seul_cote_poste": "seul sur une lane de côté, comparé aux champions de son poste",
    "kp_combat": "kills et assists en combat d'équipe (part des kills de son équipe en combat)",
    "tf_10": "kills et assists en combat d'équipe, par 10 minutes",
    "part_adc": "part de ses parties en ADC", "part_sup": "part de ses parties en support",
    "n_protection": "nombre de sorts de protection (Data Dragon)", "n_controle": "nombre de sorts de contrôle (Data Dragon)",
    "part_top": "part de ses parties en top", "batiments_min": "dégâts aux bâtiments par minute",
}


def libelle(m):
    return LIBELLES.get(m[:-2], m) + " (comparé à son poste)" if m.endswith("_p") and m[:-2] in LIBELLES else LIBELLES.get(m, m)


# --- Lecture ---------------------------------------------------------------------------------------------------

def nombre(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def lire(donnees):
    matchs = lecture.matchs_avec_details(donnees)
    duree = {d["match"]: nombre(d["duree_s"]) for d in lecture.lire_details("details_parties", donnees, matchs=matchs)}
    cols = ["kills", "deaths", "assists", "or_gagne", "degats_physiques_champions", "degats_magiques_champions", "degats_vrais_champions",
            "degats_subis", "degats_attenues", "soins_allies", "boucliers_allies", "temps_cc_inflige", "degats_batiments",
            "teamDamagePercentage", "damageTakenOnTeamPercentage", "enemyChampionImmobilizations", "immobilizeAndKillWithAlly",
            "pickKillWithAlly", "soloKills", "outnumberedKills", "saveAllyFromDeath", "damagePerMinute", "goldPerMinute"]
    j = pd.DataFrame([{"match": l["match"], "participant": int(l["participant"]), "equipe": l["equipe"], "poste": l["poste"],
                       "champion": l["champion"], **{c: nombre(l[c]) for c in cols}}
                      for l in lecture.lire_details("joueurs", donnees, matchs=matchs)])
    j["minutes"] = j["match"].map(duree) / 60
    t = pd.DataFrame([{"match": l["match"], "participant": int(l["participant"]),
                       **{f"{a}_{m}": nombre(l[f"{a}_{m}"]) for m in (20, 25, 30) for a in ("x", "y")}}
                      for l in lecture.lire_details("timeline_joueurs", donnees, matchs=matchs)])
    e = pd.DataFrame([{"match": l["match"], "t_ms": nombre(l["t_ms"]), "participant": int(nombre(l["participant"]) or 0),
                       "victime": int(nombre(l["victime"])) if l["victime"] else 0, "assistants": l["assistants"],
                       "x": nombre(l["x"]), "y": nombre(l["y"])}
                      for l in lecture.lire_details("evenements", donnees, matchs=matchs) if l["type"] == "CHAMPION_KILL"])
    return j, t, e


# --- Mesures par joueur et par partie -----------------------------------------------------------------------------

def seul_sur_le_cote(t, j):
    """Part des relevés à 20, 25 et 30 min où le joueur est sur une lane de côté, hors base, à plus de 4 000 unités de
    tout allié."""
    pos = t.merge(j[["match", "participant", "equipe"]], on=["match", "participant"])
    parts = []
    for m in (20, 25, 30):
        d = pos[["match", "participant", "equipe", f"x_{m}", f"y_{m}"]].rename(columns={f"x_{m}": "x", f"y_{m}": "y"}).dropna()
        g = d.merge(d, on=["match", "equipe"], suffixes=("", "_a"))
        g = g[g.participant != g.participant_a]
        g["dist"] = np.hypot(g.x - g.x_a, g.y - g.y_a)
        d = d.merge(g.groupby(["match", "participant"]).dist.min().rename("dmin").reset_index(), on=["match", "participant"])
        cote = ((d.x < 3500) & (d.y > 4500)) | ((d.y > 11500) & (d.x < 10500)) | ((d.x > 11500) & (d.y < 10500)) | ((d.y < 3500) & (d.x > 4500))
        base = (np.hypot(d.x - 500, d.y - 500) < 3500) | (np.hypot(d.x - 14300, d.y - 14300) < 3500)
        d["seul"] = (cote & ~base & (d.dmin > 4000)).astype(float)
        parts.append(d[["match", "participant", "seul"]])
    return pd.concat(parts).groupby(["match", "participant"]).seul.mean().rename("seul_cote").reset_index()


def combats(e, j):
    """Mesures tirées des kills : combats d'équipe (au moins 3 kills enchaînés à moins de 20 s et 2 500 unités),
    kills sur les ADC et les mids."""
    e = e.sort_values(["match", "t_ms"]).reset_index(drop=True)
    num = np.zeros(len(e), int); g = 0; pm, pt, px, py = None, -1e9, 0.0, 0.0
    for i, (m, t, x, y) in enumerate(zip(e.match, e.t_ms, e.x, e.y)):
        if m != pm or t - pt > 20000 or math.hypot(x - px, y - py) > 2500:
            g += 1
        num[i] = g; pm, pt, px, py = m, t, x, y
    e["combat"] = num
    e["tf"] = e.combat.map(e.groupby("combat").size()) >= 3
    equipe = j.set_index(["match", "participant"]).equipe
    poste = j.set_index(["match", "participant"]).poste
    e["poste_v"] = [poste.get((m, v)) for m, v in zip(e.match, e.victime)]
    lignes = []
    for m, c, p, a, tf, pv, t in zip(e.match, e.combat, e.participant, e.assistants, e.tf, e.poste_v, e.t_ms):
        aides = [int(float(q)) for q in a.split("|")] if isinstance(a, str) and a else []
        carry = pv in ("adc", "mid")
        if p > 0:
            lignes.append((m, p, c, tf, 1, carry, carry and len(aides) <= 1 and t >= 14 * 60000))
        for q in aides:
            lignes.append((m, q, c, tf, 0, carry, False))
    k = pd.DataFrame(lignes, columns=["match", "participant", "combat", "tf", "kill", "carry", "assassin"])
    k["tf_n"] = k.tf.astype(int); k["carry_tf"] = (k.carry & k.tf).astype(int)
    k["kill_tf"] = (k.kill.astype(bool) & k.tf).astype(int)
    par = k.groupby(["match", "participant"]).agg(td=("tf", "size"), tf_n=("tf_n", "sum"), sur_carry=("carry", "sum"),
                                                  carry_tf=("carry_tf", "sum"), assassin=("assassin", "sum"), kills_tf=("kill_tf", "sum")).reset_index()
    vict = e[e.tf].groupby(["match", "victime"]).combat.nunique().rename("morts_tf").reset_index().rename(columns={"victime": "participant"})
    # Où il meurt après 14 min : distance de sa propre base, de 0 (chez lui) à 1 (la base adverse).
    d = e[(e.t_ms >= 14 * 60000) & (e.victime > 0)].copy()
    base = np.where([equipe.get((m, v)) == "b" for m, v in zip(d.match, d.victime)], 500.0, 14300.0)
    d["profondeur"] = np.clip(np.hypot(d.x - base, d.y - base) / 19500, 0, 1)
    prof = d.groupby(["match", "victime"]).profondeur.mean().reset_index().rename(columns={"victime": "participant"})
    pres = pd.concat([k[k.tf][["match", "participant", "combat"]],
                      e[e.tf][["match", "victime", "combat"]].rename(columns={"victime": "participant"})]).drop_duplicates()
    pres = pres.groupby(["match", "participant"]).size().rename("combats").reset_index()
    # Kills de son équipe en combat d'équipe : l'équipe du tueur, ou l'équipe opposée à la victime (tué par une tour…).
    eq_v = np.array([equipe.get((m, v)) for m, v in zip(e.match, e.victime)])
    eq_k = np.array([equipe.get((m, p)) if p > 0 else None for m, p in zip(e.match, e.participant)])
    e["eq_tueur"] = np.where(eq_k != None, eq_k, np.where(eq_v == "b", "r", "b"))  # noqa: E711
    kills_eq = e[e.tf].groupby(["match", "eq_tueur"]).size().rename("kills_tf_equipe").reset_index().rename(columns={"eq_tueur": "equipe"})
    sortie = par.merge(vict, on=["match", "participant"], how="outer").merge(pres, on=["match", "participant"], how="outer").fillna(0)
    sortie["equipe"] = [equipe.get((m, p)) for m, p in zip(sortie.match, sortie.participant)]
    sortie = sortie.merge(kills_eq, on=["match", "equipe"], how="left").fillna({"kills_tf_equipe": 0}).drop(columns="equipe")
    return sortie.merge(prof, on=["match", "participant"], how="left")


def mesures_joueurs(j, t, e):
    j = j[j.minutes >= 15].copy()
    mn = j.minutes
    f = j[["match", "participant", "equipe", "poste", "champion"]].copy()
    f["part_degats"] = j.teamDamagePercentage
    f["part_subis"] = j.damageTakenOnTeamPercentage
    f["encaisse_min"] = (j.degats_subis + j.degats_attenues) / mn
    f["soins_allies_min"] = j.soins_allies / mn
    f["boucliers_allies_min"] = j.boucliers_allies / mn
    f["cc_min"] = j.temps_cc_inflige / mn
    f["immob_min"] = j.enemyChampionImmobilizations / mn
    f["batiments_min"] = j.degats_batiments / mn
    f["solo"] = j.soloKills
    f["pick_kill"] = j.pickKillWithAlly
    f["immob_kill"] = j.immobilizeAndKillWithAlly
    f["sauve"] = j.saveAllyFromDeath
    f["en_inferiorite"] = j.outnumberedKills
    f["dpm"] = j.damagePerMinute
    f["or_min"] = j.goldPerMinute
    f["minutes"] = mn
    f = f.merge(seul_sur_le_cote(t, j), on=["match", "participant"], how="left")
    f = f.merge(combats(e, j), on=["match", "participant"], how="left").fillna({c: 0 for c in ("td", "tf_n", "sur_carry", "carry_tf", "assassin", "kills_tf", "morts_tf", "combats", "kills_tf_equipe")})
    f["tf_10"] = f.tf_n / (f.minutes / 10)
    f["carry_tf_10"] = f.carry_tf / (f.minutes / 10)
    return f


def par_champion(f):
    """Moyennes par champion et par poste (au moins 150 parties), et mesures de combat rapportées aux totaux."""
    moy = ["part_degats", "part_subis", "encaisse_min", "soins_allies_min", "boucliers_allies_min", "cc_min", "immob_min", "batiments_min",
           "solo", "pick_kill", "immob_kill", "sauve", "en_inferiorite", "dpm", "or_min", "seul_cote", "assassin", "tf_10", "carry_tf_10", "profondeur"]
    g = f.groupby(["champion", "poste"])
    a = g[moy].mean()
    a["n"] = g.size()
    s = g[["td", "sur_carry", "kills_tf", "tf_n", "combats", "kills_tf_equipe"]].sum()
    a["part_carry"] = s.sur_carry / s.td.where(s.td > 0)
    a["td_par_combat"] = s.tf_n / s.combats.where(s.combats > 0)
    a["kills_par_combat"] = s.kills_tf / s.combats.where(s.combats > 0)
    # Kills et assists en combat d'équipe : part des kills de son équipe en combat où il a un kill ou une assist.
    a["kp_combat"] = s.tf_n / s.kills_tf_equipe.where(s.kills_tf_equipe > 0)
    a = a.reset_index()
    a["presence_tf_poste"] = a.tf_10 / a.groupby("poste").tf_10.transform("mean")
    a = a[a.n >= MIN_PARTIES].copy()
    a["seul_cote_poste"] = (a.seul_cote - a.groupby("poste").seul_cote.transform("mean")) / a.groupby("poste").seul_cote.transform("std")
    return a[a.n >= MIN_PARTIES].reset_index(drop=True).fillna(0)


# --- Modèle par type ------------------------------------------------------------------------------------------------

def table_champions(a):
    """Une ligne par champion : ses mesures (moyenne de ses postes pondérée par les parties), chacune aussi comparée aux
    champions de son poste (_p), la part de ses parties à chaque poste, et ses sorts."""
    a = a.copy()
    for c in BASE:
        v = np.log1p(a[c].clip(lower=0)) if c in LOG else a[c]
        a[c] = v
        a[c + "_p"] = (v - v.groupby(a.poste).transform("mean")) / v.groupby(a.poste).transform("std")
    cols = BASE + [c + "_p" for c in BASE]
    x = a.groupby("champion").apply(lambda d: pd.Series(np.average(d[cols], axis=0, weights=d.n), index=cols), include_groups=False)
    parts = a.pivot_table(index="champion", columns="poste", values="n", aggfunc="sum").fillna(0)
    parts = parts.div(parts.sum(axis=1), axis=0).reindex(columns=list(POSTES), fill_value=0).add_prefix("part_")
    x = x.join(parts)
    if SORTS.exists():
        with open(SORTS, encoding="utf-8", newline="") as f:
            sorts = list(csv.DictReader(f, delimiter=";"))
        for c in x.index:
            mes = [s_ for s_ in sorts if s_["champion"] == c]
            x.loc[c, "n_controle"] = sum(s_["categorie"] == "controle" for s_ in mes)
            x.loc[c, "n_deplacement"] = sum(s_["categorie"] == "deplacement" for s_ in mes)
            x.loc[c, "n_protection"] = sum(s_["categorie"] == "protection" for s_ in mes)
    return x.fillna(0)


def apprendre(X, y, C):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=C, class_weight="balanced", max_iter=1000).fit(X, y)


def lire_references():
    refs = defaultdict(set)
    with open(REFERENCES, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            refs[l["type"]].add(l["champion"])
    return refs


def lire_validations():
    """{champion: {type: True | False}} : les choix du propriétaire, champion par champion (10 types pour un champion revu).
    « oui » ; « non » = refusé exprès ; case vide = pas coché, compté non aussi."""
    if not VALIDATIONS.exists():
        return {}
    v = defaultdict(dict)
    with open(VALIDATIONS, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            v[l["champion"]][l["type"]] = l.get("choix") == "oui"
    return dict(v)


def lire_refus():
    """{(champion, type)} refusés exprès par le propriétaire : jamais montrés comme « vu en plus par les parties »."""
    if not VALIDATIONS.exists():
        return set()
    with open(VALIDATIONS, encoding="utf-8", newline="") as f:
        return {(l["champion"], l["type"]) for l in csv.DictReader(f, delimiter=";") if l.get("choix") == "non"}


def classer(x_A, x_B, x_tout, validations, refs):
    """Notes de 0 à 100 par type : appris sur les choix du propriétaire (mesures du tas A), vérifié sur B."""
    ref = x_A.mean(), x_A.std().replace(0, 1)
    z = lambda x: (x - ref[0]) / ref[1]
    z_A, z_B, z_T = z(x_A), z(x_B), z(x_tout)
    notes, bilan = pd.DataFrame(index=x_tout.index), {}
    for t in TYPES:
        ms, C = MESURES[t]
        revus = [c for c in z_A.index if c in validations and t in validations[c]]
        y = np.array([validations[c][t] for c in revus], dtype=int)
        extra = [c for c in sorted(refs.get(t, ())) if c in z_A.index and c not in validations]
        X = np.vstack([z_A.loc[revus, ms].values] + ([z_A.loc[extra, ms].values] if extra else []))
        Y = np.concatenate([y, np.ones(len(extra), int)])
        if len(set(Y)) < 2:
            bilan[t] = {"erreur": "il faut des oui et des non"}
            continue
        # Chaque champion revu reclassé sans l'avoir vu.
        sans_voir = np.zeros(len(revus))
        for i in range(len(revus)):
            garde = np.ones(len(Y), bool); garde[i] = False
            sans_voir[i] = apprendre(X[garde], Y[garde], C).predict_proba(X[i:i + 1])[0, 1]
        d = sans_voir >= SEUIL / 100
        tp, fp, fn = int((d & (y == 1)).sum()), int((d & (y == 0)).sum()), int((~d & (y == 1)).sum())
        m = apprendre(X, Y, C)
        n_A = pd.Series(m.predict_proba(z_A[ms].values)[:, 1], index=z_A.index)
        n_B = pd.Series(m.predict_proba(z_B[ms].values)[:, 1], index=z_B.index)
        communs = n_A.index.intersection(n_B.index)
        notes[t] = 100 * m.predict_proba(z_T[ms].values)[:, 1]
        bilan[t] = {"poids": {c: round(float(w), 2) for c, w in zip(ms, m.coef_[0])}, "C": C, "revus": len(revus),
                    "oui_retrouves": tp, "oui": int(y.sum()), "faux_oui": fp, "justesse": round(float((d == y).mean()), 3),
                    "erreurs": [c for c, dd, yy in zip(revus, d, y) if dd != yy],
                    "en_plus": sorted([[c, round(100 * v)] for c, v, yy in zip(revus, sans_voir, y) if v >= SEUIL / 100 and not yy and (c, t) not in REFUS],
                                     key=lambda x: -x[1]),
                    "en_moins": sorted([[c, round(100 * v)] for c, v, yy in zip(revus, sans_voir, y) if v < SEUIL / 100 and yy], key=lambda x: x[1]),
                    "meme_decision_A_B": round(float(np.mean((n_A[communs] >= SEUIL / 100) == (n_B[communs] >= SEUIL / 100))), 3)}
    return notes, bilan


def main():
    regle = commun.lire_decoupage()
    j, t, e = lire(commun.dossier_donnees())
    f = mesures_joueurs(j, t, e)
    tas = {m: commun.tas_ab(m, regle) for m in f.match.unique()}
    f["tas"] = f.match.map(tas)
    a_A, a_B, a_T = par_champion(f[f.tas == "A"]), par_champion(f[f.tas == "B"]), par_champion(f)
    x_A, x_B, x_T = table_champions(a_A), table_champions(a_B), table_champions(a_T)
    validations, refs = lire_validations(), lire_references()
    REFUS.update(lire_refus())
    notes, bilan = classer(x_A, x_B, x_T, validations, refs)

    postes = a_T.groupby("champion").apply(lambda g: ", ".join(f"{p} {int(n)}" for p, n in sorted(zip(g.poste, g.n), key=lambda x: -x[1])),
                                           include_groups=False)
    parties = a_T.groupby("champion").n.sum()
    # Fragile : encaisse peu (dégâts subis et atténués par minute, en logarithme), comparé à tous les champions.
    encaisse = (x_T["encaisse_min"] - x_T["encaisse_min"].mean()) / x_T["encaisse_min"].std()
    RESULTATS.mkdir(parents=True, exist_ok=True)
    with open(RESULTATS / "notes.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";", lineterminator="\n")
        w.writerow(["champion", "postes", "parties", "revu", "fragile", "encaisse_z"] + list(TYPES))
        for c in sorted(notes.index, key=str.lower):
            w.writerow([c, postes[c], int(parties[c]), "oui" if c in validations else "", "oui" if encaisse[c] < FRAGILE else "",
                        round(float(encaisse[c]), 2)] + [round(notes[t][c]) if t in notes else "" for t in TYPES])

    with open(CATALOGUE, encoding="utf-8", newline="") as fi:
        lecteur = csv.DictReader(fi, delimiter=";")
        entete, lignes = lecteur.fieldnames, list(lecteur)
    for l in lignes:
        c = l["champion"]
        if c in validations:
            for t in TYPES:
                l[t] = "oui" if validations[c].get(t) else ""
        elif c in notes.index:
            # Ses types : ceux à 50 ou plus, les MAX_TYPES meilleurs ; au moins un (le mieux noté).
            n = notes.loc[c].sort_values(ascending=False)
            imposes = [t for t in TYPES if c in refs.get(t, ())]        # ses types de référence restent
            garde = imposes + [t for t in n.index if n[t] >= SEUIL and t not in imposes][:max(0, MAX_TYPES - len(imposes))]
            garde = garde or [n.index[0]]
            for t in TYPES:
                l[t] = "oui" if t in garde else ""
        else:
            for t in TYPES:
                l[t] = ""
        l["source"] = "validé" if c in validations else ("calcul" if c in notes.index else "pas assez de parties")
    with open(CATALOGUE, "w", encoding="utf-8", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=entete, delimiter=";", lineterminator="\n")
        w.writeheader(); w.writerows(lignes)

    (RESULTATS / "types.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    texte = ["# Types des champions", "",
             f"- Appris sur les choix du propriétaire : {len(validations)} champions revus (10 types chacun), plus ses références ; "
             f"mesures du tas A, vérifiées sur B. Un champion revu garde ses choix ; un autre prend les types à {SEUIL} sur 100 ou plus ({MAX_TYPES} au plus, au moins un).",
             f"- L'assistant affiche Carry ou Enchanteur, plus les deux autres styles les mieux notés de chaque champion ; « fragile » (cible même sans être carry ni enchanteur) : "
             f"encaisse par minute à plus d'un demi-écart-type sous la moyenne des champions ({sum(encaisse < FRAGILE)} champions).",
             f"- Parties de 15 min et plus : A {int((f.tas == 'A').sum() / 10)}, B {int((f.tas == 'B').sum() / 10)} environ ; postes avec au moins {MIN_PARTIES} parties.", "",
             "| Type | Champions retenus | Ses oui retrouvés sans les voir | Faux oui | Justesse sans les voir | Même décision A et B | Mesures (poids) |",
             "|---|---|---|---|---|---|---|"]
    for t in TYPES:
        b = bilan.get(t, {})
        if "poids" not in b:
            texte.append(f"| {t} | — | {b.get('erreur', '')} | | | | |")
            continue
        nb = sum(1 for l in lignes if l[t] == "oui")
        texte.append(f"| {t} | {nb} | {b['oui_retrouves']} sur {b['oui']} | {b['faux_oui']} | {100 * b['justesse']:.0f} % | "
                     f"{100 * b['meme_decision_A_B']:.0f} % | " + ", ".join(f"{libelle(m)} {w:+.2f}" for m, w in b["poids"].items()) + " |")
    texte += ["", "Ce que l'algorithme voit autrement que le propriétaire (note sans avoir vu ses choix ; ses choix restent appliqués) :", ""]
    for t in TYPES:
        b = bilan.get(t, {})
        if "en_plus" not in b:
            continue
        texte.append(f"- **{t}** : en plus de tes choix : {', '.join(f'{c} {n}' for c, n in b['en_plus']) or 'aucun'} ; "
                     f"tes oui qu'il ne voit pas : {', '.join(f'{c} {n}' for c, n in b['en_moins']) or 'aucun'}")
    (RESULTATS / "types.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
