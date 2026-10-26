"""Classification des champions en 10 types, à partir de nos parties et des champions de référence du propriétaire.

Les types (non exclusifs : un champion peut en avoir plusieurs) :
    carry, enchanteur, assassin, plongeur, attrapeur, tank, bloqueur, dueliste, splitpusher, teamfighter.

Comment :
1. Pour chaque champion à chaque poste (au moins 150 parties), des mesures tirées des parties : part des dégâts de
   l'équipe, dégâts encaissés, soins et boucliers sur les alliés, contrôle infligé, solo kills, position à 20, 25 et
   30 min (seul sur une lane de côté), kills sur les ADC et mids, participation aux combats d'équipe…
2. Pour chaque type, une régression logistique sur quelques mesures choisies, apprise sur les références du
   propriétaire (analyse/types/references.csv) contre tous les autres champions. Note de 0 à 100 ; type proposé à 70.
3. Analyse à deux tas : les mesures et le modèle viennent de A ; on vérifie sur B (jamais vu) que les notes sont les
   mêmes, et on retrouve chaque référence sans l'avoir montrée au modèle.
4. Les choix du propriétaire (analyse/types/validations.csv, venus de la page « Types des champions ») passent avant
   le calcul. Le catalogue unifié reçoit le résultat : « oui » dans la colonne de chaque type retenu.

    python3 analyse/types/classer.py              (après analyse/preparer.sh)

Écrit analyse/types/resultats/notes.csv, analyse/types/resultats/types.md, et les colonnes des types de
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
SEUIL = 70
MIN_PARTIES = 150
POSTES = ("top", "jgl", "mid", "adc", "sup")

# Les mesures de chaque type (choisies avec le propriétaire, 26/10/2026).
MESURES = {
    "carry": ["part_degats", "dpm", "or_min", "part_subis", "encaisse_min"],
    "enchanteur": ["soins_allies_min", "boucliers_allies_min"],
    "assassin": ["assassin", "part_carry", "part_subis", "encaisse_min"],
    "plongeur": ["part_carry", "carry_tf_10", "encaisse_min", "part_subis"],
    "attrapeur": ["pick_kill", "immob_kill", "cc_min"],
    "tank": ["encaisse_min", "part_subis", "part_degats"],
    "bloqueur": ["cc_min", "immob_min", "sauve", "encaisse_min"],
    "dueliste": ["solo", "en_inferiorite"],
    "splitpusher": ["seul_cote"],
    "teamfighter": ["presence_tf_poste", "td_par_combat", "kills_par_combat", "cc_min"],
}
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
}


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
    pres = pd.concat([k[k.tf][["match", "participant", "combat"]],
                      e[e.tf][["match", "victime", "combat"]].rename(columns={"victime": "participant"})]).drop_duplicates()
    pres = pres.groupby(["match", "participant"]).size().rename("combats").reset_index()
    return par.merge(vict, on=["match", "participant"], how="outer").merge(pres, on=["match", "participant"], how="outer").fillna(0)


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
    f = f.merge(combats(e, j), on=["match", "participant"], how="left").fillna({c: 0 for c in ("td", "tf_n", "sur_carry", "carry_tf", "assassin", "kills_tf", "morts_tf", "combats")})
    f["tf_10"] = f.tf_n / (f.minutes / 10)
    f["carry_tf_10"] = f.carry_tf / (f.minutes / 10)
    return f


def par_champion(f):
    """Moyennes par champion et par poste (au moins 150 parties), et mesures de combat rapportées aux totaux."""
    moy = ["part_degats", "part_subis", "encaisse_min", "soins_allies_min", "boucliers_allies_min", "cc_min", "immob_min", "batiments_min",
           "solo", "pick_kill", "immob_kill", "sauve", "en_inferiorite", "dpm", "or_min", "seul_cote", "assassin", "tf_10", "carry_tf_10"]
    g = f.groupby(["champion", "poste"])
    a = g[moy].mean()
    a["n"] = g.size()
    s = g[["td", "sur_carry", "kills_tf", "tf_n", "combats"]].sum()
    a["part_carry"] = s.sur_carry / s.td.where(s.td > 0)
    a["td_par_combat"] = s.tf_n / s.combats.where(s.combats > 0)
    a["kills_par_combat"] = s.kills_tf / s.combats.where(s.combats > 0)
    a = a.reset_index()
    a["presence_tf_poste"] = a.tf_10 / a.groupby("poste").tf_10.transform("mean")
    return a[a.n >= MIN_PARTIES].reset_index(drop=True).fillna(0)


# --- Modèle par type ------------------------------------------------------------------------------------------------

def normaliser(a, ref=None):
    """Mesures centrées-réduites (logarithme pour les mesures très étalées), avec la moyenne et l'écart-type de `ref`."""
    ref = a if ref is None else ref
    z = pd.DataFrame(index=a.index)
    for c in {m for ms in MESURES.values() for m in ms}:
        v, r = a[c], ref[c]
        if c in LOG:
            v, r = np.log1p(v.clip(lower=0)), np.log1p(r.clip(lower=0))
        z[c] = (v - r.mean()) / (r.std() or 1)
    return z


def apprendre(z, y, mesures):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000).fit(z[mesures].values, y)


def lire_references():
    refs = defaultdict(set)
    with open(REFERENCES, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            refs[l["type"]].add(l["champion"])
    return refs


def lire_validations():
    """{(champion, type): "oui" | "non"} : les choix du propriétaire, prioritaires sur le calcul."""
    if not VALIDATIONS.exists():
        return {}
    with open(VALIDATIONS, encoding="utf-8", newline="") as f:
        return {(l["champion"], l["type"]): l["choix"] for l in csv.DictReader(f, delimiter=";") if l.get("choix") in ("oui", "non")}


def note_champion(a, colonne):
    """Note d'un champion, tous postes confondus : moyenne des notes de ses postes, pondérée par les parties."""
    return a.groupby("champion").apply(lambda g: float(np.average(g[colonne], weights=g.n)), include_groups=False)


def classer(a_A, a_B, a_tout, refs):
    """Notes de 0 à 100 par type : modèle appris sur A, vérifié sur B, appliqué à toutes les parties."""
    z_A, z_B, z_T = normaliser(a_A), normaliser(a_B, a_A), normaliser(a_tout, a_A)
    bilan, notes = {}, pd.DataFrame({"champion": a_tout.champion, "poste": a_tout.poste, "n": a_tout.n})
    for t in TYPES:
        ms = MESURES[t]
        y = a_A.champion.isin(refs[t]).astype(int).values
        if y.sum() < 2:
            bilan[t] = {"erreur": "moins de 2 références"}
            continue
        m = apprendre(z_A, y, ms)
        # Chaque référence retrouvée sans l'avoir vue (le modèle appris sans elle, sur A).
        sans_voir = {}
        for c in sorted(refs[t]):
            masque = (a_A.champion != c).values
            if masque.all():
                continue
            mm = apprendre(z_A[masque], y[masque], ms)
            sans_voir[c] = round(100 * float(mm.predict_proba(z_A[~masque][ms].values)[:, 1].max()))
        # Vérification sur B : mêmes notes et mêmes décisions que sur A ?
        n_A = pd.Series(100 * m.predict_proba(z_A[ms].values)[:, 1], index=a_A.champion + "|" + a_A.poste)
        n_B = pd.Series(100 * m.predict_proba(z_B[ms].values)[:, 1], index=a_B.champion + "|" + a_B.poste)
        communs = n_A.index.intersection(n_B.index)
        accord = float(np.corrcoef(n_A[communs], n_B[communs])[0, 1]) if len(communs) > 5 else float("nan")
        meme = float(np.mean((n_A[communs] >= SEUIL) == (n_B[communs] >= SEUIL))) if len(communs) else float("nan")
        notes[t] = 100 * m.predict_proba(z_T[ms].values)[:, 1]
        bilan[t] = {"poids": {c: round(float(w), 2) for c, w in zip(ms, m.coef_[0])}, "references_sans_voir": sans_voir,
                    "accord_A_B": round(accord, 3), "meme_decision_A_B": round(meme, 3), "postes_compares": int(len(communs))}
    return notes, bilan


def main():
    regle = commun.lire_decoupage()
    j, t, e = lire(commun.dossier_donnees())
    f = mesures_joueurs(j, t, e)
    tas = {m: commun.tas_ab(m, regle) for m in f.match.unique()}
    f["tas"] = f.match.map(tas)
    a_A, a_B, a_T = par_champion(f[f.tas == "A"]), par_champion(f[f.tas == "B"]), par_champion(f)
    refs = lire_references()
    notes, bilan = classer(a_A, a_B, a_T, refs)

    # Note par champion (tous postes), puis décision : choix du propriétaire, sinon le calcul (70 et plus).
    par_champ = {t: note_champion(notes, t) for t in TYPES if t in notes}
    postes = notes.groupby("champion").apply(lambda g: ", ".join(f"{p} {int(n)}" for p, n in sorted(zip(g.poste, g.n), key=lambda x: -x[1])),
                                             include_groups=False)
    validations = lire_validations()
    RESULTATS.mkdir(parents=True, exist_ok=True)
    with open(RESULTATS / "notes.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";", lineterminator="\n")
        w.writerow(["champion", "postes", "parties"] + list(TYPES))
        for c in sorted(par_champ["carry"].index, key=str.lower):
            w.writerow([c, postes[c], int(notes[notes.champion == c].n.sum())] + [round(par_champ[t][c]) if t in par_champ else "" for t in TYPES])

    with open(CATALOGUE, encoding="utf-8", newline="") as fi:
        lecteur = csv.DictReader(fi, delimiter=";")
        entete, lignes = lecteur.fieldnames, list(lecteur)
    for l in lignes:
        c = l["champion"]
        valide = any((c, t) in validations for t in TYPES)
        for t in TYPES:
            choix = validations.get((c, t))
            calcul = t in par_champ and c in par_champ[t].index and par_champ[t][c] >= SEUIL
            l[t] = "oui" if (choix == "oui" or (choix is None and calcul)) else ""
        l["source"] = "validé" if valide else ("calcul" if c in par_champ["carry"].index else "pas assez de parties")
    with open(CATALOGUE, "w", encoding="utf-8", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=entete, delimiter=";", lineterminator="\n")
        w.writeheader(); w.writerows(lignes)

    (RESULTATS / "types.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    texte = ["# Types des champions", "",
             f"- Parties : A {int((f.tas == 'A').sum() / 10)}, B {int((f.tas == 'B').sum() / 10)} environ (parties de 15 min et plus) ; "
             f"postes avec au moins {MIN_PARTIES} parties. Type proposé à partir de {SEUIL} sur 100.",
             f"- Choix du propriétaire appliqués : {len(validations)}.", "",
             "| Type | Champions | Références retrouvées sans les voir | Même décision sur A et B | Mesures (poids) |", "|---|---|---|---|---|"]
    for t in TYPES:
        b = bilan.get(t, {})
        if "poids" not in b:
            texte.append(f"| {t} | — | {b.get('erreur', '')} | | |")
            continue
        sv = b["references_sans_voir"]
        rates = [f"{c} {v}" for c, v in sv.items() if v < SEUIL]
        nb = int((par_champ[t] >= SEUIL).sum())
        texte.append(f"| {t} | {nb} | {sum(v >= SEUIL for v in sv.values())} sur {len(sv)}{' (ratées : ' + ', '.join(rates) + ')' if rates else ''} | "
                     f"{100 * b['meme_decision_A_B']:.0f} % | " + ", ".join(f"{LIBELLES[m]} {w:+.2f}" for m, w in b["poids"].items()) + " |")
    (RESULTATS / "types.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
