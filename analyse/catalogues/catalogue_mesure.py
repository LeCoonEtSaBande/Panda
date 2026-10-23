"""Catalogue mesuré « teamfight » : proposition de catalogue de départ pour le recuit.

Différences avec la classification de analyse/classification.py (demandées par le propriétaire le 23/10) :
1. Référence : un champion n'est plus comparé à la moyenne de SON poste (ce qui envoyait par exemple
   Jinx avec les champions « qui font peu de dégâts », parce qu'elle en fait moins que les autres adc),
   mais à la moyenne de la JUNGLE s'il est joué en jungle, et à celle des LANES (top, mid, adc, sup
   ensemble) s'il est joué en lane. Les lanes se tapent dessus en permanence, la jungle non.
2. Période : ce qui fait gagner, ce sont les teamfights. Quand les données le permettent, on ne
   regarde que la partie APRÈS la minute T (15 ou 20) : dégâts aux champions (timeline), kills, morts,
   assistances, rôle dans les combats (événements datés), regroupement avec l'équipe (positions).
   Riot ne donne que le total de la partie pour le reste : dégâts encaissés et atténués, soins,
   boucliers, CC, skillshots, bâtiments. Ces indicateurs-là restent sur toute la partie.
   Seules les parties qui durent au moins T + 5 minutes comptent.

Aucune victoire n'entre dans le calcul. Parties : toutes les parties complètes avec timeline.

    python3 analyse/catalogues/catalogue_mesure.py [--minute 15] [--k 7] [--sans-stabilite]

Sorties dans analyse/catalogues/ : catalogue_mesure_T<minute>_k<groupes>.csv (une ligne par champion) et
catalogue_mesure_T<minute>_k<groupes>.md (groupes, portraits, comparaison avec Catalogue.csv).
"""

import argparse
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import classification as cl  # noqa: E402

REFERENCE = {"top": "lane", "mid": "lane", "adc": "lane", "sup": "lane", "jgl": "jungle"}

# (nom, type, libellé, période) : période « apres » = après la minute T, « partie » = toute la partie.
INDICATEURS = [
    ("degats_min", "volume", "Dégâts aux champions par minute", "apres"),
    ("part_degats_equipe", "part", "Part des dégâts de l'équipe", "apres"),
    ("degats_par_takedown", "volume", "Dégâts par kill ou assistance (poke)", "apres"),
    ("kills_min", "volume", "Kills par minute", "apres"),
    ("morts_min", "volume", "Morts par minute", "apres"),
    ("assists_min", "volume", "Assistances par minute", "apres"),
    ("part_coup_final", "part", "Part des takedowns où il porte le coup final", "apres"),
    ("kills_seul_min", "volume", "Kills sans assistance par minute", "apres"),
    ("part_kills_burst", "part", "Part de ses kills en burst (presque seul)", "apres"),
    ("part_ouvre_combat", "part", "Part de ses takedowns sur le premier kill d'un combat", "apres"),
    ("part_finit_combat", "part", "Part de ses takedowns sur les kills de fin de combat", "apres"),
    ("part_premier_mort", "part", "Part de ses morts où il meurt en premier", "apres"),
    ("part_en_reponse", "part", "Part de ses takedowns en réponse à un mort allié", "apres"),
    ("part_en_inferiorite", "part", "Part de ses takedowns en infériorité numérique", "apres"),
    ("distance_equipe", "volume", "Distance à ses coéquipiers (split)", "apres"),
    ("subis_min", "volume", "Dégâts encaissés par minute", "partie"),
    ("part_encaisses_equipe", "part", "Part des dégâts encaissés par l'équipe", "partie"),
    ("part_attenuee", "part", "Part des dégâts atténuée (résistance)", "partie"),
    ("soin_sur_soi_min", "volume", "Soin sur soi par minute", "partie"),
    ("cc_min", "volume", "Temps de CC infligé par minute", "partie"),
    ("immobilisations_min", "volume", "Immobilisations par minute", "partie"),
    ("part_cc_dur", "part", "CC dur dans le CC total", "partie"),
    ("cc_puis_kill_min", "volume", "Immobilisations suivies d'un kill allié par minute", "partie"),
    ("soins_allies_min", "volume", "Soins sur les alliés par minute", "partie"),
    ("boucliers_allies_min", "volume", "Boucliers sur les alliés par minute", "partie"),
    ("sauvetages_min", "volume", "Alliés sauvés de la mort par minute", "partie"),
    ("skillshots_min", "volume", "Skillshots touchés par minute", "partie"),
    ("esquives_min", "volume", "Skillshots esquivés par minute", "partie"),
    ("batiments_min", "volume", "Dégâts aux bâtiments par minute", "partie"),
    ("part_physique", "brut", "Part de dégâts physiques", "apres"),
    ("part_magique", "brut", "Part de dégâts magiques", "apres"),
]
NOMS = [n for n, _, _, _ in INDICATEURS]
STYLE = [n for n, g, _, _ in INDICATEURS if g != "brut"]
TYPES = {n: g for n, g, _, _ in INDICATEURS}
LIBELLES = {n: l for n, _, l, _ in INDICATEURS}
PERIODE = {n: p for n, _, _, p in INDICATEURS}

# Portraits pour nommer les groupes (indicateurs attendus au-dessus (+1) ou au-dessous (-1) de la moyenne).
PORTRAITS = {
    "Enchanteurs": {"soins_allies_min": 1, "boucliers_allies_min": 1, "sauvetages_min": 1, "degats_min": -1},
    "Tanks d'engage": {"part_attenuee": 1, "subis_min": 1, "immobilisations_min": 1, "part_ouvre_combat": 1, "degats_min": -1},
    "Supports d'engage": {"assists_min": 1, "immobilisations_min": 1, "cc_puis_kill_min": 1, "degats_min": -1, "kills_min": -1},
    "Carrys à distance": {"degats_min": 1, "part_degats_equipe": 1, "part_en_reponse": 1, "cc_min": -1, "immobilisations_min": -1},
    "Artilleurs": {"degats_par_takedown": 1, "skillshots_min": 1, "subis_min": -1, "part_attenuee": -1},
    "Assassins": {"part_coup_final": 1, "part_ouvre_combat": 1, "kills_min": 1, "part_finit_combat": -1},
    "Combattants": {"subis_min": 1, "soin_sur_soi_min": 1, "part_encaisses_equipe": 1, "part_kills_burst": 1, "assists_min": -1},
    "Split-pushers": {"distance_equipe": 1, "batiments_min": 1, "kills_seul_min": 1, "assists_min": -1, "skillshots_min": -1},
    "Contrôle à distance": {"cc_min": 1, "skillshots_min": 1, "subis_min": -1, "part_premier_mort": -1},
}


def indicateurs_joueurs(t, minute=15):
    """Une ligne par joueur et par partie (parties d'au moins minute + 5 min, avec timeline)."""
    import numpy as np

    T = minute
    j = t.joueurs[t.joueurs["duree_min"] >= T + 5].copy()
    tl = t.timeline[["match", "participant", f"degats_champions_{T}", "x_20", "y_20", "x_25", "y_25", "x_30", "y_30"]]
    j = j.merge(tl, on=["match", "participant"], how="inner")
    j["reference"] = j["poste"].map(REFERENCE)
    minutes = j["duree_min"]
    apres = j["duree_min"] - T

    def part(a, b):
        return a / b.where(b > 0)

    total = j[["degats_physiques_champions", "degats_magiques_champions", "degats_vrais_champions"]].sum(axis=1, min_count=1)
    degats_apres = (total - j[f"degats_champions_{T}"]).clip(lower=0)
    j["degats_apres"] = degats_apres
    equipe = j.groupby(["match", "equipe"])["degats_apres"].transform("sum")
    j["degats_min"] = degats_apres / apres
    j["part_degats_equipe"] = part(degats_apres, equipe)
    # Type de dégâts : sur toute la partie (Riot ne le donne pas minute par minute).
    j["part_physique"] = part(j["degats_physiques_champions"], total)
    j["part_magique"] = part(j["degats_magiques_champions"], total)

    # Toute la partie.
    j["subis_min"] = j["degats_subis"] / minutes
    j["part_encaisses_equipe"] = j["damageTakenOnTeamPercentage"]
    j["part_attenuee"] = part(j["degats_attenues"], j["degats_attenues"] + j["degats_subis"])
    j["soin_sur_soi_min"] = (j["soins_total"] - j["soins_allies"]).clip(lower=0) / minutes
    j["cc_min"] = j["temps_cc_inflige"] / minutes
    j["immobilisations_min"] = j["enemyChampionImmobilizations"] / minutes
    j["part_cc_dur"] = part(j["temps_cc_inflige"], j["cc_total"])
    j["cc_puis_kill_min"] = j["immobilizeAndKillWithAlly"] / minutes
    j["soins_allies_min"] = j["soins_allies"] / minutes
    j["boucliers_allies_min"] = j["boucliers_allies"] / minutes
    j["sauvetages_min"] = j["saveAllyFromDeath"] / minutes
    j["skillshots_min"] = j["skillshotsHit"] / minutes
    j["esquives_min"] = j["skillshotsDodged"] / minutes
    j["batiments_min"] = j["degats_batiments"] / minutes

    # Après la minute T : kills, morts, assistances et combats, à partir des événements datés.
    cle = list(zip(j["match"], j["participant"].astype(int)))
    kills = t.evenements[t.evenements["t_ms"] >= T * 60_000]
    equipe_de = dict(zip(zip(t.joueurs["match"], t.joueurs["participant"].astype(int)), t.joueurs["equipe"]))
    c = cl.combats(kills, equipe_de)

    def compte(nom):
        return np.array([c[k][nom] if k in c else 0 for k in cle], dtype=float)

    k_ = kills[kills["participant"] > 0]
    nb_ass = k_["assistants"].fillna("").astype(str).map(lambda a: len([x for x in a.split("|") if x and x != "nan"]))
    nb_kills = k_.groupby(["match", "participant"]).size()
    seuls = k_[nb_ass == 0].groupby(["match", "participant"]).size()
    burst = k_[(nb_ass <= 1) & (k_["nb_sources"] <= 2)
               & (k_["degats_recus_victime"] >= k_["degats_recus_victime"].median())].groupby(["match", "participant"]).size()

    def depuis(serie):
        d = {(m, int(p)): n for (m, p), n in serie.items()}
        return np.array([d.get(k, 0) for k in cle], dtype=float)

    kills_j = depuis(nb_kills)
    tk, tkc, mc = compte("takedowns"), compte("takedowns_combat"), compte("morts_combat")
    morts = compte("morts")
    assists = tk - kills_j
    with np.errstate(divide="ignore", invalid="ignore"):
        j["kills_min"] = kills_j / apres
        j["morts_min"] = morts / apres
        j["assists_min"] = assists / apres
        j["part_coup_final"] = np.where(tk > 0, kills_j / tk, np.nan)
        j["kills_seul_min"] = depuis(seuls) / apres
        j["part_kills_burst"] = np.where(kills_j > 0, depuis(burst) / kills_j, np.nan)
        j["degats_par_takedown"] = degats_apres / (tk + 1)
        j["part_ouvre_combat"] = np.where(tkc > 0, compte("ouvre") / tkc, np.nan)
        j["part_finit_combat"] = np.where(tkc > 0, compte("finit") / tkc, np.nan)
        j["part_premier_mort"] = np.where(mc > 0, compte("premier_mort") / mc, np.nan)
        j["part_en_reponse"] = np.where(tk > 0, compte("reponse") / tk, np.nan)
        j["part_en_inferiorite"] = np.where(tk > 0, compte("inferiorite") / tk, np.nan)

    # Regroupement : distance moyenne aux coéquipiers à 20, 25 et 30 min (toujours après T).
    distances = []
    for m in (20, 25, 30):
        if m < T:
            continue
        x, y = j[f"x_{m}"], j[f"y_{m}"]
        g = j.assign(_x=x, _y=y, _n=x.notna().astype(int)).groupby(["match", "equipe"])
        sx, sy, n = g["_x"].transform("sum"), g["_y"].transform("sum"), g["_n"].transform("sum")
        cx, cy = (sx - x.fillna(0)) / (n - 1), (sy - y.fillna(0)) / (n - 1)
        distances.append(np.hypot(x - cx, y - cy).where((n >= 3) & x.notna()))
    pile = np.column_stack(distances)
    nb = np.isfinite(pile).sum(axis=1)
    j["distance_equipe"] = np.where(nb > 0, np.nansum(pile, axis=1) / np.maximum(nb, 1), np.nan)
    return j


def profils(j, minimum=cl.MINIMUM, minimum_ref=cl.MINIMUM_POSTE):
    """Une ligne par champion : indicateurs comparés à la moyenne de sa référence (jungle ou lanes)."""
    import numpy as np
    import pandas as pd

    moyenne = j.groupby("reference")[NOMS].mean()
    par = j.groupby(["champion", "reference"])[NOMS].mean().join(j.groupby(["champion", "reference"]).size().rename("n"))
    par = par[par["n"] >= minimum_ref]
    ajuste = pd.DataFrame(index=par.index)
    for nom in NOMS:
        ref = np.asarray(par.index.get_level_values("reference").map(moyenne[nom]), dtype=float)
        v = par[nom].to_numpy()
        if TYPES[nom] == "volume":
            eps = 0.05 * np.nanmedian(moyenne[nom].to_numpy()) + 1e-9
            ajuste[nom] = np.log((v + eps) / (ref + eps))
        elif TYPES[nom] == "part":
            ajuste[nom] = v - ref
        else:
            ajuste[nom] = v
    ajuste["n"] = par["n"]
    postes = j.groupby(["champion", "poste"]).size()
    lignes = []
    for champion, g in ajuste.groupby(level="champion"):
        total = g["n"].sum()
        if total < minimum:
            continue
        poids = g["n"] / total
        ligne = {"champion": champion, "parties": int(total)}
        for nom in NOMS:
            ok = g[nom].notna()
            ligne[nom] = float((g[nom][ok] * poids[ok]).sum() / poids[ok].sum()) if ok.any() else np.nan
        p = postes.loc[champion].sort_values(ascending=False)
        ligne["postes"] = ", ".join(f"{q} {100 * n / p.sum():.0f} %" for q, n in p.items() if n / p.sum() >= 0.05)
        ligne["poste_principal"] = p.index[0]
        lignes.append(ligne)
    return pd.DataFrame(lignes)


def standardiser(p):
    return cl.standardiser(p, STYLE)


def grouper(p, k, nb_axes=cl.NB_AXES):
    return cl.kmeans(cl.axes_principaux(standardiser(p), nb_axes), k)


def stabilite(j, reference, k_valeurs, tirages=20, graine=1):
    import numpy as np

    rng = np.random.default_rng(graine)
    matchs = j["match"].unique()
    champions = list(reference["champion"])
    origine = {k: grouper(reference, k) for k in k_valeurs}
    scores = {k: [] for k in k_valeurs}
    for _ in range(tirages):
        tirage = rng.choice(matchs, size=len(matchs), replace=True)
        poids = dict(zip(*np.unique(tirage, return_counts=True)))
        jj = j[j["match"].isin(poids)]
        jj = jj.loc[jj.index.repeat(jj["match"].map(poids))]
        p = profils(jj).set_index("champion").reindex(champions).reset_index()
        p[NOMS] = p[NOMS].fillna(reference[NOMS])
        for k in k_valeurs:
            scores[k].append(cl.rand_ajuste(origine[k], grouper(p, k)))
    return {k: float(np.mean(v)) for k, v in scores.items()}


def nommer(Z, etiquettes):
    import numpy as np

    groupes = sorted(set(etiquettes))
    centres = {g: Z[etiquettes == g].mean(axis=0) for g in groupes}
    scores = sorted(((np.mean([s * centres[g][STYLE.index(i)] for i, s in signes.items()]), g, nom)
                     for g in groupes for nom, signes in PORTRAITS.items()), reverse=True)
    noms, pris = {}, set()
    for score, g, nom in scores:
        if g in noms or nom in pris or score < 0.3:
            continue
        noms[g], pris = nom, pris | {nom}
    return {g: noms.get(g, f"Groupe {g} (à nommer)") for g in groupes}


def charger_joueurs(minute):
    import echantillon
    import lecture
    from tables import charger

    donnees = lecture.DONNEES
    import os
    if os.environ.get("PANDA_DONNEES"):
        donnees = Path(os.environ["PANDA_DONNEES"])
    matchs = echantillon.parties_completes_ordonnees(donnees)
    t = charger(matchs, donnees)
    return indicateurs_joueurs(t, minute), len(matchs)


def main():
    import numpy as np

    from regle import charger_catalogue

    parser = argparse.ArgumentParser()
    parser.add_argument("--minute", type=int, default=15)
    parser.add_argument("--k", type=int)
    parser.add_argument("--sans-stabilite", action="store_true")
    args = parser.parse_args()

    j, nb_matchs = charger_joueurs(args.minute)
    p = profils(j)
    Z = standardiser(p)
    k_valeurs = list(range(5, 12))
    stables = {} if args.sans_stabilite else stabilite(j, p, k_valeurs)
    k = args.k or max([kk for kk in k_valeurs if stables.get(kk, 0) >= cl.STABILITE_MIN] or [7])
    X = cl.axes_principaux(Z)
    et = grouper(p, k)
    noms = nommer(Z, et)
    p["groupe"] = [noms[g] for g in et]
    centres = {g: X[et == g].mean(axis=0) for g in sorted(set(et))}
    proche, nettete = [], []
    for i, g in enumerate(et):
        d = {h: float(np.linalg.norm(X[i] - c)) for h, c in centres.items()}
        autre = min((h for h in d if h != g), key=d.get)
        proche.append(noms[autre])
        nettete.append(d[autre] - d[g])
    p["groupe_proche"], p["nettete"] = proche, nettete
    p["degats"] = np.where(p["part_physique"] >= cl.SEUIL_AD, "AD", np.where(p["part_magique"] >= cl.SEUIL_AD, "AP", "mixte"))

    catalogue = charger_catalogue()
    p["catalogue_principal"] = p["champion"].map(lambda c: catalogue.get(c, {}).get("principal", ""))
    p["catalogue_secondaire"] = p["champion"].map(lambda c: catalogue.get(c, {}).get("secondaire", ""))
    p["catalogue_tanky"] = p["champion"].map(lambda c: catalogue.get(c, {}).get("tanky", ""))
    for i, nom in enumerate(STYLE):
        p[f"z_{nom}"] = Z[:, i]

    base = ICI / f"catalogue_mesure_T{args.minute}_k{k}"
    colonnes = (["champion", "parties", "postes", "groupe", "groupe_proche", "nettete", "degats",
                 "catalogue_principal", "catalogue_secondaire", "catalogue_tanky"] + [f"z_{n}" for n in STYLE])
    p.sort_values(["groupe", "nettete"], ascending=[True, False])[colonnes].to_csv(
        base.with_suffix(".csv"), sep=";", index=False, float_format="%.3f")

    lignes = [f"# Catalogue mesuré « teamfight » (après {args.minute} min, lanes contre jungle)", "",
              f"- {nb_matchs} parties complètes lues, {j['match'].nunique()} gardées (avec timeline et au moins "
              f"{args.minute + 5} min), {len(p)} champions (100 parties ou plus).",
              "- Chaque champion est comparé à la moyenne de la jungle quand il est joué en jungle, à celle des "
              "lanes (top, mid, adc, sup) sinon. Aucune victoire n'entre dans le calcul.",
              f"- Dégâts, kills, morts, assistances, combats et regroupement : après {args.minute} min. "
              "Encaissé, soins, boucliers, CC, skillshots, bâtiments : toute la partie (Riot ne les date pas).", ""]
    if stables:
        lignes += ["Stabilité des groupes quand on change les parties (1 = identiques, 0,70 = seuil retenu) : "
                   + ", ".join(f"{kk} groupes {v:.2f}" for kk, v in stables.items()) + f". Retenu : **{k} groupes**.", ""]
    for g in sorted(set(et)):
        nom = noms[g]
        membres = p[p["groupe"] == nom].sort_values("nettete", ascending=False)
        centre = Z[et == g].mean(axis=0)
        ordre = np.argsort(centre)
        hauts = [f"{LIBELLES[STYLE[i]].lower()} ({centre[i]:+.1f})" for i in ordre[::-1][:4] if centre[i] > 0.3]
        bas = [f"{LIBELLES[STYLE[i]].lower()} ({centre[i]:+.1f})" for i in ordre[:4] if centre[i] < -0.3]
        styles = membres["catalogue_principal"].replace("", "sans style").value_counts()
        lignes += [f"## {nom} ({len(membres)} champions)", "",
                   f"- **Plus que la moyenne** : {', '.join(hauts) or '—'}",
                   f"- **Moins que la moyenne** : {', '.join(bas) or '—'}",
                   f"- Styles de ton catalogue : " + ", ".join(f"{s} {n}" for s, n in styles.items()),
                   f"- Junglers : " + ", ".join(membres[membres["postes"].str.contains("jgl")]["champion"]),
                   "- Membres (du plus net au plus à cheval) : " + ", ".join(
                       f"{r.champion}{' ↔ ' + r.groupe_proche if r.nettete < 0.5 else ''}" for r in membres.itertuples()), ""]
    accord = cl.rand_ajuste(p["groupe"].to_numpy(), p["catalogue_principal"].replace("", "sans style").to_numpy())
    lignes += [f"Accord avec le style principal de ton catalogue : {accord:.2f} (1 = mêmes groupes, 0 = pas mieux que le hasard).", ""]
    base.with_suffix(".md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
