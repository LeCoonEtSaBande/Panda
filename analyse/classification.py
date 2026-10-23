"""Classification des champions, tous postes confondus (proposition pour un second catalogue).

Une ligne par champion (100 parties ou plus, tous postes réunis). On décrit COMMENT il joue, pas
s'il gagne : aucune victoire n'entre dans la classification.

Indicateurs (par joueur et par partie, puis moyenne du champion) :
- dégâts faits : volume par minute, part des dégâts de l'équipe, dégâts par takedown (poke : beaucoup
  de dégâts qui ne finissent pas en kill), part faite avant 15 min ;
- dégâts encaissés : volume, part de l'équipe, part atténuée (vraie résistance), soin sur soi ;
- kills : kills, morts, assistances, part des takedowns où il porte le coup final, solo kills,
  kills « burst » (presque seul, victime vidée d'un coup), kills près d'une tour ennemie (dive) ;
- contrôle (CC) : temps de CC, nombre d'immobilisations, part de CC « dur » (pondéré) dans le CC
  total, immobilisations suivies d'un kill allié (CC qui prépare le kill) ;
- avant ou après : dans les combats (kills à moins de 15 s et 3 000 unités), part de ses takedowns
  sur le PREMIER kill du combat (il ouvre), sur les kills de fin (il nettoie), part de ses morts où il
  est le premier mort (il rentre en premier ou se fait attraper), takedowns en réponse au premier mort
  de son équipe (counter-engage), takedowns en infériorité numérique ;
  (Riot ne donne pas l'ordre exact CC puis dégâts : ces moments dans le combat en sont l'approximation.)
- soins et boucliers sur les alliés, alliés sauvés de la mort ;
- skillshots touchés et esquivés ;
- bâtiments, distance à ses coéquipiers (split) ;
- type de dégâts : parts physique, magique, vraie.

L'effet du poste est retiré : un support a moins d'or et fait moins de dégâts qu'un adc sans que ce
soit un style. Chaque indicateur est comparé à la moyenne du poste où le champion a été joué, puis
moyenné sur ses postes (pondéré par le nombre de parties). Les parts de type de dégâts restent brutes.

Puis : standardisation, 6 axes principaux (ACP, environ 70 % de l'information), k-means. Le type de
dégâts n'entre pas dans les groupes (il les couperait en « AP » et « AD ») : il reste une étiquette à
part. Nombre de groupes : 7 (K_CHOISI), le plus grand dont les groupes restent stables (accord
d'environ 0,70) quand on rééchantillonne les parties ; la stabilité de chaque k est recalculée à
chaque rapport. Les groupes reçoivent le nom du portrait type le plus proche
(PORTRAITS), sinon « à nommer ». Échantillon : l'échantillon figé (echantillon_fige.json).

Sorties (analyse/resultats/) : classification_champions.csv, classification_groupes.csv,
classification_axes.csv, classification_catalogue.csv.
"""

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent
RESULTATS = ICI / "resultats"
MINIMUM = 100
MINIMUM_POSTE = 20
DUREE_MIN = 15
COMBAT_MS = 15_000
COMBAT_DISTANCE = 3_000

# (nom, type) : « volume » = comparé au poste en rapport (log), « part » = en différence, « brut » = tel quel.
INDICATEURS = [
    ("degats_min", "volume", "Dégâts aux champions par minute"),
    ("part_degats_equipe", "part", "Part des dégâts de l'équipe"),
    ("degats_par_takedown", "volume", "Dégâts par kill ou assistance (poke)"),
    ("part_degats_avant_15", "part", "Part des dégâts faite avant 15 min"),
    ("subis_min", "volume", "Dégâts encaissés par minute"),
    ("part_encaisses_equipe", "part", "Part des dégâts encaissés par l'équipe"),
    ("part_attenuee", "part", "Part des dégâts atténuée (résistance)"),
    ("soin_sur_soi_min", "volume", "Soin sur soi par minute"),
    ("kills_min", "volume", "Kills par minute"),
    ("morts_min", "volume", "Morts par minute"),
    ("assists_min", "volume", "Assistances par minute"),
    ("part_coup_final", "part", "Part des takedowns où il porte le coup final"),
    ("solo_kills_min", "volume", "Solo kills par minute"),
    ("part_kills_burst", "part", "Part de ses kills en burst (presque seul)"),
    ("part_kills_sous_tour", "part", "Part de ses kills près d'une tour ennemie (dive)"),
    ("cc_min", "volume", "Temps de CC infligé par minute"),
    ("immobilisations_min", "volume", "Immobilisations par minute"),
    ("part_cc_dur", "part", "CC dur dans le CC total"),
    ("cc_puis_kill_min", "volume", "Immobilisations suivies d'un kill allié par minute"),
    ("part_ouvre_combat", "part", "Part de ses takedowns sur le premier kill d'un combat"),
    ("part_finit_combat", "part", "Part de ses takedowns sur les kills de fin de combat"),
    ("part_premier_mort", "part", "Part de ses morts où il meurt en premier"),
    ("part_en_reponse", "part", "Part de ses takedowns en réponse à un mort allié"),
    ("part_en_inferiorite", "part", "Part de ses takedowns en infériorité numérique"),
    ("soins_allies_min", "volume", "Soins sur les alliés par minute"),
    ("boucliers_allies_min", "volume", "Boucliers sur les alliés par minute"),
    ("sauvetages_min", "volume", "Alliés sauvés de la mort par minute"),
    ("skillshots_min", "volume", "Skillshots touchés par minute"),
    ("esquives_min", "volume", "Skillshots esquivés par minute"),
    ("batiments_min", "volume", "Dégâts aux bâtiments par minute"),
    ("distance_equipe", "volume", "Distance à ses coéquipiers (split)"),
    ("part_physique", "brut", "Part de dégâts physiques"),
    ("part_magique", "brut", "Part de dégâts magiques"),
    ("part_vraie", "brut", "Part de dégâts bruts"),
]
NOMS = [nom for nom, _, _ in INDICATEURS]
# Le type de dégâts (physique, magique, vrai) est gardé à part comme étiquette : sinon il domine les
# groupes (les mages d'un côté, les AD de l'autre) au lieu de la façon de jouer.
STYLE = [nom for nom, genre, _ in INDICATEURS if genre != "brut"]
NB_AXES = 6
K_VALEURS = range(4, 11)
STABILITE_MIN = 0.70
# Nombre de groupes retenu le 23/10/2026 sur l'échantillon figé : 7 est le plus grand k dont les groupes
# restent stables (accord d'environ 0,70 en rééchantillonnant les parties) ; à 8, l'accord tombe à 0,57.
# Fixé ici pour que les groupes ne changent pas d'un rapport à l'autre au gré du hasard du rééchantillonnage.
K_CHOISI = 7
SEUIL_AD = 0.60

# Portraits types pour nommer les groupes : indicateurs attendus nettement au-dessus (+) ou au-dessous (-).
PORTRAITS = {
    "Enchanteurs": {"soins_allies_min": 1, "boucliers_allies_min": 1, "sauvetages_min": 1, "degats_min": -1},
    "Tanks protecteurs": {"part_attenuee": 1, "assists_min": 1, "immobilisations_min": 1, "part_coup_final": -1, "degats_min": -1},
    "Artilleurs": {"part_en_reponse": 1, "degats_par_takedown": 1, "part_degats_equipe": 1, "part_ouvre_combat": -1},
    "Plongeurs": {"part_ouvre_combat": 1, "part_kills_sous_tour": 1, "solo_kills_min": 1, "assists_min": -1},
    "Tueurs autonomes": {"part_coup_final": 1, "part_kills_burst": 1, "cc_min": -1, "immobilisations_min": -1},
    "Combattants à contrôle": {"cc_puis_kill_min": 1, "subis_min": 1, "part_encaisses_equipe": 1, "soins_allies_min": -1},
    "Contrôle à distance": {"cc_min": 1, "degats_min": 1, "subis_min": -1, "distance_equipe": -1},
}
TYPES = {nom: genre for nom, genre, _ in INDICATEURS}
LIBELLES = {nom: libelle for nom, _, libelle in INDICATEURS}


# --- Combats -------------------------------------------------------------------------------

def combats(kills, equipe_de):
    """Compteurs par joueur (match, participant) tirés des combats reconstitués."""
    compteurs = defaultdict(lambda: defaultdict(int))

    def clore(match, combat):
        presents = {"b": set(), "r": set()}
        for _, tueur, victime, assistants, equipe in combat:
            presents[equipe].update(p for p in [tueur, *assistants] if p)
            if victime:
                presents[equipe_de.get((match, victime), "b" if equipe == "r" else "r")].add(victime)
        premiere_equipe_touchee = "r" if combat[0][4] == "b" else "b"
        for rang, (_, tueur, victime, assistants, equipe) in enumerate(combat):
            autre = "r" if equipe == "b" else "b"
            for p in [tueur, *assistants]:
                if not p:
                    continue
                c = compteurs[(match, p)]
                c["takedowns"] += 1
                if len(combat) >= 2:
                    c["takedowns_combat"] += 1
                    if rang == 0:
                        c["ouvre"] += 1
                    if rang >= 2:
                        c["finit"] += 1
                if rang > 0 and equipe == premiere_equipe_touchee:
                    c["reponse"] += 1
                if len(presents[autre]) > len(presents[equipe]):
                    c["inferiorite"] += 1
            if victime:
                c = compteurs[(match, victime)]
                c["morts"] += 1
                if len(combat) >= 2:
                    c["morts_combat"] += 1
                    if rang == 0:
                        c["premier_mort"] += 1

    courant, combat, dernier = None, [], None
    colonnes = ["match", "t_ms", "x", "y", "participant", "victime", "assistants", "equipe"]
    for match, t, x, y, tueur, victime, assistants, equipe in kills.sort_values(["match", "t_ms"])[colonnes].itertuples(index=False):
        tueur = int(tueur) if tueur == tueur else 0
        victime = int(victime) if victime == victime else 0
        assistants = [int(a) for a in str(assistants).split("|") if a and a != "nan"]
        nouveau = (match != courant or dernier is None or t - dernier[0] > COMBAT_MS
                   or (x == x and dernier[1] == dernier[1] and math.hypot(x - dernier[1], y - dernier[2]) > COMBAT_DISTANCE))
        if nouveau and combat:
            clore(courant, combat)
            combat = []
        combat.append((t, tueur, victime, assistants, equipe))
        courant, dernier = match, (t, x, y)
    if combat:
        clore(courant, combat)
    return compteurs


# --- Indicateurs par joueur ----------------------------------------------------------------

def indicateurs_joueurs(t):
    import numpy as np

    j = t.joueurs[t.joueurs["duree_min"] >= DUREE_MIN].copy()
    minutes = j["duree_min"]

    def par_minute(serie):
        return serie / minutes

    def part(numerateur, denominateur):
        return numerateur / denominateur.where(denominateur > 0)

    degats = j[["degats_physiques_champions", "degats_magiques_champions", "degats_vrais_champions"]].sum(axis=1, min_count=1)
    takedowns = j["kills"] + j["assists"]
    j["degats_min"] = par_minute(degats)
    j["part_degats_equipe"] = j["teamDamagePercentage"]
    j["degats_par_takedown"] = degats / (takedowns + 1)
    j["subis_min"] = par_minute(j["degats_subis"])
    j["part_encaisses_equipe"] = j["damageTakenOnTeamPercentage"]
    j["part_attenuee"] = part(j["degats_attenues"], j["degats_attenues"] + j["degats_subis"])
    j["soin_sur_soi_min"] = par_minute((j["soins_total"] - j["soins_allies"]).clip(lower=0))
    j["kills_min"] = par_minute(j["kills"])
    j["morts_min"] = par_minute(j["deaths"])
    j["assists_min"] = par_minute(j["assists"])
    j["part_coup_final"] = part(j["kills"], takedowns)
    j["solo_kills_min"] = par_minute(j["soloKills"])
    j["part_kills_sous_tour"] = part(j["killsNearEnemyTurret"], j["kills"])
    j["cc_min"] = par_minute(j["temps_cc_inflige"])
    j["immobilisations_min"] = par_minute(j["enemyChampionImmobilizations"])
    j["part_cc_dur"] = part(j["temps_cc_inflige"], j["cc_total"])
    j["cc_puis_kill_min"] = par_minute(j["immobilizeAndKillWithAlly"])
    j["soins_allies_min"] = par_minute(j["soins_allies"])
    j["boucliers_allies_min"] = par_minute(j["boucliers_allies"])
    j["sauvetages_min"] = par_minute(j["saveAllyFromDeath"])
    j["skillshots_min"] = par_minute(j["skillshotsHit"])
    j["esquives_min"] = par_minute(j["skillshotsDodged"])
    j["batiments_min"] = par_minute(j["degats_batiments"])
    j["part_physique"] = part(j["degats_physiques_champions"], degats)
    j["part_magique"] = part(j["degats_magiques_champions"], degats)
    j["part_vraie"] = part(j["degats_vrais_champions"], degats)
    j["degats_total"] = degats

    cle = list(zip(j["match"], j["participant"].astype(int)))
    ev = t.evenements
    avec_ev = set(ev["match"]) if ev is not None and len(ev) else set()
    if avec_ev:
        equipe_de = dict(zip(zip(t.joueurs["match"], t.joueurs["participant"].astype(int)), t.joueurs["equipe"]))
        kills = ev[ev["type"] == "CHAMPION_KILL"]
        c = combats(kills, equipe_de)
        present = np.array([m in avec_ev for m, _ in cle])

        def compte(nom):
            return np.where(present, [c[k][nom] if k in c else 0 for k in cle], np.nan)

        tk, tkc, mc = compte("takedowns"), compte("takedowns_combat"), compte("morts_combat")
        with np.errstate(divide="ignore", invalid="ignore"):
            j["part_ouvre_combat"] = np.where(tkc > 0, compte("ouvre") / tkc, np.nan)
            j["part_finit_combat"] = np.where(tkc > 0, compte("finit") / tkc, np.nan)
            j["part_premier_mort"] = np.where(mc > 0, compte("premier_mort") / mc, np.nan)
            j["part_en_reponse"] = np.where(tk > 0, compte("reponse") / tk, np.nan)
            j["part_en_inferiorite"] = np.where(tk > 0, compte("inferiorite") / tk, np.nan)
        # Kills burst : tueur presque seul (au plus un assistant, au plus 2 champions ennemis dans les
        # dégâts reçus) sur une victime qui a pris beaucoup de dégâts juste avant de mourir.
        k = kills[kills["participant"] > 0]
        nb_assistants = k["assistants"].fillna("").astype(str).map(lambda a: len([x for x in a.split("|") if x and x != "nan"]))
        burst = k[(nb_assistants <= 1) & (k["nb_sources"] <= 2) & (k["degats_recus_victime"] >= k["degats_recus_victime"].median())]
        nb_burst = burst.groupby(["match", "participant"]).size()
        nb_burst = {(m, int(p)): n for (m, p), n in nb_burst.items()}
        bursts = np.where(present, [nb_burst.get(k_, 0) for k_ in cle], np.nan)
        j["part_kills_burst"] = np.where(j["kills"] > 0, bursts / j["kills"].where(j["kills"] > 0), np.nan)
    else:
        for nom in ("part_ouvre_combat", "part_finit_combat", "part_premier_mort", "part_en_reponse",
                    "part_en_inferiorite", "part_kills_burst"):
            j[nom] = np.nan

    if t.timeline is not None and len(t.timeline):
        tl = t.timeline.merge(t.joueurs[["match", "participant", "equipe"]], on=["match", "participant"])
        distances = []
        for minute in (15, 20, 25):
            x, y = tl[f"x_{minute}"], tl[f"y_{minute}"]
            g = tl.assign(_x=x, _y=y, _n=x.notna().astype(int)).groupby(["match", "equipe"])
            sx, sy, n = g["_x"].transform("sum"), g["_y"].transform("sum"), g["_n"].transform("sum")
            cx, cy = (sx - x.fillna(0)) / (n - 1), (sy - y.fillna(0)) / (n - 1)
            distances.append(np.hypot(x - cx, y - cy).where((n >= 3) & x.notna()))
        pile = np.column_stack(distances)
        nb = np.isfinite(pile).sum(axis=1)
        tl["distance_equipe"] = np.where(nb > 0, np.nansum(pile, axis=1) / np.maximum(nb, 1), np.nan)
        tl = tl[["match", "participant", "distance_equipe", "degats_champions_15"]]
        j = j.merge(tl, on=["match", "participant"], how="left")
        j["part_degats_avant_15"] = j["degats_champions_15"] / j["degats_total"].where(j["degats_total"] > 0)
    else:
        j["distance_equipe"] = np.nan
        j["part_degats_avant_15"] = np.nan
    return j


# --- Profils par champion, effet du poste retiré ---------------------------------------------

def profils(j, minimum=MINIMUM, minimum_poste=MINIMUM_POSTE):
    """Une ligne par champion : indicateurs bruts (moyenne) et ajustés au poste."""
    import numpy as np
    import pandas as pd

    moyenne_poste = j.groupby("poste")[NOMS].mean()
    par_cp = j.groupby(["champion", "poste"])[NOMS].mean()
    n_cp = j.groupby(["champion", "poste"]).size().rename("n")
    par_cp = par_cp.join(n_cp)
    par_cp = par_cp[par_cp["n"] >= minimum_poste]

    ajuste = pd.DataFrame(index=par_cp.index)
    for nom in NOMS:
        reference = par_cp.index.get_level_values("poste").map(moyenne_poste[nom])
        valeur = par_cp[nom].to_numpy()
        reference = np.asarray(reference, dtype=float)
        if TYPES[nom] == "volume":
            eps = 0.05 * np.nanmedian(moyenne_poste[nom].to_numpy()) + 1e-9
            ajuste[nom] = np.log((valeur + eps) / (reference + eps))
        elif TYPES[nom] == "part":
            ajuste[nom] = valeur - reference
        else:
            ajuste[nom] = valeur
    ajuste["n"] = par_cp["n"]

    lignes = []
    for champion, groupe in ajuste.groupby(level="champion"):
        total = groupe["n"].sum()
        if total < minimum:
            continue
        poids = groupe["n"] / total
        ligne = {"champion": champion, "parties": int(total)}
        for nom in NOMS:
            valeurs = groupe[nom]
            ok = valeurs.notna()
            ligne[nom] = float((valeurs[ok] * poids[ok]).sum() / poids[ok].sum()) if ok.any() else np.nan
        postes = groupe["n"].droplevel("champion").sort_values(ascending=False)
        ligne["postes"] = ", ".join(f"{p} {100 * n / total:.0f} %" for p, n in postes.items())
        ligne["poste_principal"] = postes.index[0]
        lignes.append(ligne)
    sortie = pd.DataFrame(lignes)
    brut = j.groupby("champion")[NOMS].mean()
    for nom in NOMS:
        sortie[f"brut_{nom}"] = sortie["champion"].map(brut[nom])
    return sortie


def standardiser(sortie, colonnes=None):
    import numpy as np

    X = sortie[colonnes or STYLE].to_numpy(dtype=float)
    moyenne = np.nanmean(X, axis=0)
    X = np.where(np.isnan(X), moyenne, X)
    ecart = X.std(axis=0)
    ecart[ecart == 0] = 1
    return (X - X.mean(axis=0)) / ecart


# --- Axes et groupes -------------------------------------------------------------------------

def acp(Z, k=6):
    """Axes principaux : part de variance et poids de chaque indicateur."""
    import numpy as np

    U, S, Vt = np.linalg.svd(Z - Z.mean(axis=0), full_matrices=False)
    variance = S ** 2 / (S ** 2).sum()
    return variance[:k], Vt[:k], U[:, :k] * S[:k]


def silhouette(X, etiquettes):
    import numpy as np

    D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))
    valeurs = []
    for i in range(len(X)):
        meme = etiquettes == etiquettes[i]
        if meme.sum() <= 1:
            valeurs.append(0.0)
            continue
        a = D[i, meme].sum() / (meme.sum() - 1)
        b = min(D[i, etiquettes == g].mean() for g in set(etiquettes) if g != etiquettes[i])
        valeurs.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(valeurs))


def rand_ajuste(a, b):
    """Indice de Rand ajusté : 1 = mêmes groupes, 0 = pas mieux que le hasard."""
    import numpy as np
    from math import comb

    a, b = np.asarray(a), np.asarray(b)
    table = {}
    for x, y in zip(a, b):
        table[(x, y)] = table.get((x, y), 0) + 1
    somme = sum(comb(n, 2) for n in table.values())
    sa = sum(comb(int((a == x).sum()), 2) for x in set(a))
    sb = sum(comb(int((b == y).sum()), 2) for y in set(b))
    total = comb(len(a), 2)
    attendu = sa * sb / total
    maximum = (sa + sb) / 2
    return (somme - attendu) / (maximum - attendu) if maximum != attendu else 1.0


def axes_principaux(Z, nb=NB_AXES):
    import numpy as np

    U, S, _ = np.linalg.svd(Z - Z.mean(axis=0), full_matrices=False)
    return (U * S)[:, :nb]


def kmeans(X, k, essais=50, iterations=300, graine=0):
    """k-means (initialisation k-means++), meilleur de `essais` lancers. Étiquettes 1..k."""
    import numpy as np

    rng = np.random.default_rng(graine)
    meilleur, meilleure_inertie = None, np.inf
    for _ in range(essais):
        centres = [X[rng.integers(len(X))]]
        for _ in range(1, k):
            d = np.min(((X[:, None, :] - np.array(centres)[None]) ** 2).sum(axis=2), axis=1)
            centres.append(X[rng.choice(len(X), p=d / d.sum())])
        centres = np.array(centres)
        for _ in range(iterations):
            etiquettes = ((X[:, None, :] - centres[None]) ** 2).sum(axis=2).argmin(axis=1)
            nouveaux = np.array([X[etiquettes == g].mean(axis=0) if (etiquettes == g).any() else centres[g] for g in range(k)])
            if np.allclose(nouveaux, centres):
                break
            centres = nouveaux
        inertie = ((X - centres[etiquettes]) ** 2).sum()
        if inertie < meilleure_inertie:
            meilleur, meilleure_inertie = etiquettes, inertie
    # Numérotation stable : groupes triés par taille décroissante.
    tailles = sorted(range(k), key=lambda g: -(meilleur == g).sum())
    renumero = {g: i + 1 for i, g in enumerate(tailles)}
    return np.array([renumero[g] for g in meilleur])


def grouper(p, k):
    return kmeans(axes_principaux(standardiser(p)), k)


def ward(Z, k):
    from scipy.cluster.hierarchy import fcluster, linkage

    return fcluster(linkage(Z, method="ward"), k, criterion="maxclust")


def stabilite(j, reference, k_valeurs, tirages=20, graine=1):
    """Pour chaque k : accord moyen (Rand ajusté, 1 = identique) entre les groupes d'origine et ceux
    obtenus en retirant les parties au hasard avec remise."""
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
            scores[k].append(rand_ajuste(origine[k], grouper(p, k)))
    return {k: float(np.mean(v)) for k, v in scores.items()}


def nommer(Z, etiquettes):
    """Donne à chaque groupe le nom du portrait type qui lui ressemble le plus (sans doublon)."""
    import numpy as np

    groupes = sorted(set(etiquettes))
    centres = {g: Z[etiquettes == g].mean(axis=0) for g in groupes}
    scores = []
    for g in groupes:
        for nom, signes in PORTRAITS.items():
            score = np.mean([signe * centres[g][STYLE.index(ind)] for ind, signe in signes.items()])
            scores.append((score, g, nom))
    noms, pris = {}, set()
    for score, g, nom in sorted(scores, reverse=True):
        if g in noms or nom in pris or score < 0.3:
            continue
        noms[g], pris = nom, pris | {nom}
    return {g: noms.get(g, f"Groupe {g} (à nommer)") for g in groupes}


def portrait(Z, etiquettes, n=4):
    """Pour chaque groupe : les indicateurs les plus au-dessus et au-dessous de la moyenne."""
    import numpy as np

    sortie = {}
    for g in sorted(set(etiquettes)):
        centre = Z[etiquettes == g].mean(axis=0)
        ordre = np.argsort(centre)
        hauts = [(STYLE[i], centre[i]) for i in ordre[::-1][:n] if centre[i] > 0.3]
        bas = [(STYLE[i], centre[i]) for i in ordre[:n] if centre[i] < -0.3]
        sortie[g] = (hauts, bas, centre)
    return sortie


# --- Sortie ----------------------------------------------------------------------------------

def _texte(v):
    if isinstance(v, float):
        return "" if math.isnan(v) else f"{v:.4g}"
    return str(v)


def ecrire_csv(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(entete)
        for ligne in lignes:
            ecrivain.writerow([_texte(v) for v in ligne])


def classer(matchs=None, k=K_CHOISI, tirages=20, k_valeurs=K_VALEURS, j=None):
    """Calcule tout. Renvoie un dictionnaire (profils, Z, essais, k, noms, variance, axes)."""
    import numpy as np

    if j is None:
        import lecture
        from tables import charger

        t = charger(matchs, lecture.DONNEES)
        j = indicateurs_joueurs(t)
        del t
    sortie = profils(j)
    Z = standardiser(sortie)
    variance, axes, _ = acp(Z)
    X = axes_principaux(Z)
    stables = stabilite(j, sortie, list(k_valeurs), tirages=tirages) if tirages else {}
    essais = [(kk, silhouette(X, grouper(sortie, kk)), stables.get(kk, float("nan"))) for kk in k_valeurs]
    if k is None:
        # Le plus de groupes possible tant qu'ils restent stables quand on change les parties.
        stables_ok = [e[0] for e in essais if e[2] == e[2] and e[2] >= STABILITE_MIN]
        k = max(stables_ok) if stables_ok else max(essais, key=lambda e: (e[2] if e[2] == e[2] else 0, e[1]))[0]
    etiquettes = grouper(sortie, k)
    sortie["groupe"] = etiquettes
    noms = nommer(Z, etiquettes)
    sortie["nom_groupe"] = sortie["groupe"].map(noms)
    coordonnees = acp(Z)[2]
    for a in range(coordonnees.shape[1]):
        sortie[f"axe{a + 1}"] = coordonnees[:, a]
    # Netteté : distance au centre du 2e groupe le plus proche moins distance au centre de son groupe
    # (dans l'espace des axes). Proche de 0 = champion à cheval entre deux groupes.
    centres = {g: X[etiquettes == g].mean(axis=0) for g in sorted(set(etiquettes))}
    marge, second = [], []
    for i, g in enumerate(etiquettes):
        d = {h: float(np.linalg.norm(X[i] - c)) for h, c in centres.items()}
        autre = min((h for h in d if h != g), key=d.get)
        marge.append(d[autre] - d[g])
        second.append(noms[autre])
    sortie["nettete"] = marge
    sortie["groupe_proche"] = second
    sortie["degats"] = np.where(sortie["part_physique"] >= SEUIL_AD, "AD",
                                np.where(sortie["part_magique"] >= SEUIL_AD, "AP", "mixte"))
    return {"profils": sortie, "Z": Z, "essais": essais, "k": k, "noms": noms, "variance": variance, "axes": axes}


def ecrire(resultat, chemin=RESULTATS):
    import numpy as np

    from regle import charger_catalogue

    sortie, Z, k, noms = resultat["profils"], resultat["Z"], resultat["k"], resultat["noms"]
    chemin = Path(chemin)
    chemin.mkdir(exist_ok=True)
    catalogue = charger_catalogue()
    nb_axes = len(resultat["variance"])
    entete = (["champion", "parties", "postes", "groupe", "nom_groupe", "nettete", "groupe_proche", "degats",
               "part_physique", "part_magique", "part_vraie",
               "catalogue_principal", "catalogue_secondaire", "catalogue_tanky", "catalogue_degats"]
              + [f"z_{n}" for n in STYLE] + [f"axe{a + 1}" for a in range(nb_axes)] + [f"brut_{n}" for n in NOMS])
    tri = sortie.assign(_i=range(len(sortie))).sort_values(["groupe", "nettete"], ascending=[True, False])
    lignes = []
    for _, r in tri.iterrows():
        fiche = catalogue.get(r["champion"], {})
        lignes.append([r["champion"], r["parties"], r["postes"], r["groupe"], r["nom_groupe"], r["nettete"],
                       r["groupe_proche"], r["degats"], r["part_physique"], r["part_magique"], r["part_vraie"],
                       fiche.get("principal", ""), fiche.get("secondaire", ""), fiche.get("tanky", ""), fiche.get("degats", "")]
                      + list(Z[r["_i"]]) + [r[f"axe{a + 1}"] for a in range(nb_axes)] + [r[f"brut_{n}"] for n in NOMS])
    ecrire_csv(chemin / "classification_champions.csv", entete, lignes)

    groupes = []
    for kk, s, st in resultat["essais"]:
        groupes.append(["essai", kk, "choisi" if kk == k else "", f"silhouette {s:.3f}", f"stabilité {st:.2f}"])
    for g, (hauts, bas, _) in portrait(Z, sortie["groupe"].to_numpy()).items():
        membres = tri[tri["groupe"] == g]["champion"].tolist()
        groupes.append(["groupe", g, noms[g], len(membres),
                        "plus : " + ", ".join(f"{LIBELLES[n]} ({v:+.1f})" for n, v in hauts)
                        + " | moins : " + ", ".join(f"{LIBELLES[n]} ({v:+.1f})" for n, v in bas)
                        + " | " + ", ".join(membres)])
    ecrire_csv(chemin / "classification_groupes.csv", ["type", "groupe", "nom", "taille", "detail"], groupes)

    variance, axes = resultat["variance"], resultat["axes"]
    axes_lignes = []
    for a in range(nb_axes):
        ordre = sorted(range(len(STYLE)), key=lambda i: -abs(axes[a][i]))[:8]
        axes_lignes.append([f"axe{a + 1}", f"{100 * variance[a]:.1f} %",
                            ", ".join(f"{LIBELLES[STYLE[i]]} ({axes[a][i]:+.2f})" for i in ordre)])
    ecrire_csv(chemin / "classification_axes.csv", ["axe", "variance", "indicateurs principaux"], axes_lignes)

    # Croisement avec le style principal du catalogue.
    styles = sorted({catalogue.get(c, {}).get("principal", "") or "sans style" for c in sortie["champion"]})
    croise = []
    for g in sorted(noms):
        membres = sortie[sortie["groupe"] == g]["champion"]
        compte = [sum((catalogue.get(c, {}).get("principal", "") or "sans style") == st for c in membres) for st in styles]
        croise.append([noms[g]] + compte)
    principal = [catalogue.get(c, {}).get("principal", "") or "sans style" for c in sortie["champion"]]
    accord = rand_ajuste(sortie["groupe"].to_numpy(), np.array(principal))
    croise.append([f"accord avec le catalogue (Rand ajusté, 1 = identique, 0 = hasard) : {accord:.2f}"] + [""] * len(styles))
    ecrire_csv(chemin / "classification_catalogue.csv", ["groupe"] + styles, croise)


def main():
    try:
        import echantillon

        matchs, _ = echantillon.decouper()
        if not matchs:
            print("Classification : aucune partie.")
            return 0
        resultat = classer(matchs, tirages=20)
        ecrire(resultat)
        print(f"Classification : {len(resultat['profils'])} champions, {resultat['k']} groupes : "
              + ", ".join(resultat["noms"].values()) + ".")
    except ImportError as erreur:
        print(f"Classification : sautée, bibliothèque absente ({erreur}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
