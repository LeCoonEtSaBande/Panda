"""Catégorisation mesurée des champions, poste par poste (tâche 1).

Pour chaque champion à son poste (au moins 100 parties de 15 min ou plus dans l'échantillon figé),
des indicateurs tirés des joueurs, de la timeline et des événements, rapportés à la moyenne du poste.
Les indicateurs sont regroupés en familles (engage, pick, poke, peel, counter-engage, front, split) ;
le score d'une famille est la moyenne des indicateurs standardisés dans le poste (0 = moyenne du
poste, +1 = un écart type au-dessus). Puis classification hiérarchique (Ward) sur les 7 familles, nombre
de groupes choisi par le coefficient de silhouette, et comparaison avec le catalogue.

Sorties (analyse/resultats/) :
- categories_mesurees.csv : une ligne par champion et poste ;
- categories_groupes.csv : les groupes (taille, familles dominantes) et la silhouette de chaque k essayé.

Le catalogue n'est jamais modifié : les désaccords sont présentés au propriétaire.
pandas, numpy et scipy sont nécessaires ; sans eux, l'analyse est sautée.
"""

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

from regle import charger_catalogue

ICI = Path(__file__).resolve().parent
RESULTATS = ICI / "resultats"
POSTES = ("top", "jgl", "mid", "adc", "sup")
MINIMUM = 100
DUREE_MIN = 15
# Reconstitution des combats : deux kills appartiennent au même combat s'ils sont à moins de 15 s
# et à moins de 3 000 unités l'un de l'autre (la carte fait environ 15 000 unités de côté).
COMBAT_MS = 15_000
COMBAT_DISTANCE = 3_000
SEUIL_AD = 0.60
SEUIL_AP_COEQUIPIER = 0.40

# Champions qui attaquent à distance (ceux qui changent de forme sont classés selon la forme
# qu'ils utilisent le plus en lane : Gnar, Jayce, Kayle, Nidalee, Elise à distance).
# Liste écrite à la main le 23/10/2026, à vérifier par le propriétaire.
DISTANCE = frozenset("""
Ahri|Akshan|Anivia|Annie|Aphelios|Ashe|Aurelion Sol|Aurora|Azir|Bard|Brand|Caitlyn|Cassiopeia|Corki|
Draven|Elise|Ezreal|Fiddlesticks|Gnar|Graves|Heimerdinger|Hwei|Ivern|Janna|Jayce|Jhin|Jinx|Kai'Sa|
Kalista|Karma|Karthus|Kayle|Kennen|Kindred|Kog'Maw|LeBlanc|Lissandra|Lucian|Lulu|Lux|Malzahar|Mel|
Milio|Miss Fortune|Morgana|Nami|Neeko|Nidalee|Orianna|Quinn|Rakan|Renata Glasc|Ryze|Samira|Senna|
Seraphine|Sivir|Smolder|Sona|Soraka|Swain|Syndra|Taliyah|Teemo|Thresh|Tristana|Twisted Fate|Twitch|
Urgot|Varus|Vayne|Veigar|Vel'Koz|Vex|Viktor|Vladimir|Xayah|Xerath|Yunara|Yuumi|Zeri|Ziggs|Zilean|Zoe|Zyra
""".replace("\n", "").split("|"))

# Familles et indicateurs (tous orientés : plus haut = plus de la famille).
FAMILLES = {
    "engage": ["cc_inflige_min", "immobilisations_min", "immobilise_et_tue_min", "repousse_et_tue_min", "part_degats_encaisses"],
    "pick": ["pick_kills_min", "solo_kills_min", "kills_burst_min"],
    "poke": ["degats_sur_subis", "degats_par_participation", "skillshots_min"],
    "peel": ["sauvetages_min", "soins_allies_min", "boucliers_allies_min", "soins_boucliers_effectifs_min", "cc_par_degat_subi"],
    # Parts plutôt que volumes : sinon les champions qui tuent beaucoup en général (assassins)
    # passeraient pour counter-engage.
    "counter-engage": ["part_kills_en_inferiorite", "part_takedowns_combats_en_inferiorite", "part_takedowns_en_reponse"],
    "front": ["degats_subis_min", "degats_attenues_min"],
    "split": ["degats_batiments_min", "solo_kills_min", "distance_equipe"],
}
STYLES_MESURES = {"engage": "Engage", "pick": "Pick", "poke": "Poke", "peel": "Disengage", "counter-engage": "Counter-engage"}
INDICATEURS = list(dict.fromkeys(i for liste in FAMILLES.values() for i in liste))


# --- Indicateurs par joueur ---------------------------------------------------------------

def _par_minute(joueurs, colonne):
    return joueurs[colonne] / joueurs["duree_min"]


def combats(evenements, equipe_de):
    """Pour chaque joueur (match, participant) : takedowns dans des combats où son équipe était
    moins nombreuse. Un combat = kills enchaînés à moins de COMBAT_MS et COMBAT_DISTANCE.
    Les présents d'un combat sont les tueurs, assistants et victimes de ses kills."""
    kills = evenements[evenements["type"] == "CHAMPION_KILL"].sort_values(["match", "t_ms"])
    credit = defaultdict(int)
    reponse = defaultdict(int)

    def clore(match, combat):
        presents = {"b": set(), "r": set()}
        for _, tueur, victime, assistants, equipe in combat:
            for p in [tueur, *assistants]:
                if p:
                    presents[equipe].add(p)
            if victime:
                presents[equipe_de.get((match, victime), "b" if equipe == "r" else "r")].add(victime)
        # L'équipe qui perd le premier mort du combat est celle qui s'est fait engager (ou attraper) :
        # ses takedowns qui suivent sont une réponse, c'est-à-dire du counter-engage.
        engagee = combat[0][4]
        engagee = "r" if engagee == "b" else "b"
        for rang, (_, tueur, _, assistants, equipe) in enumerate(combat):
            autre = "r" if equipe == "b" else "b"
            if len(presents[autre]) > len(presents[equipe]):
                for p in [tueur, *assistants]:
                    if p:
                        credit[(match, p)] += 1
            if rang > 0 and equipe == engagee:
                for p in [tueur, *assistants]:
                    if p:
                        reponse[(match, p)] += 1

    courant_match, combat, dernier = None, [], None
    for ligne in kills[["match", "t_ms", "x", "y", "participant", "victime", "assistants", "equipe"]].itertuples(index=False):
        match, t, x, y, tueur, victime, assistants, equipe = ligne
        tueur = int(tueur) if tueur == tueur else 0
        victime = int(victime) if victime == victime else 0
        assistants = [int(a) for a in str(assistants).split("|") if a and a != "nan"]
        nouveau = (
            match != courant_match or dernier is None or t - dernier[0] > COMBAT_MS
            or (x == x and dernier[1] == dernier[1] and math.hypot(x - dernier[1], y - dernier[2]) > COMBAT_DISTANCE)
        )
        if nouveau and combat:
            clore(courant_match, combat)
            combat = []
        combat.append((t, tueur, victime, assistants, equipe))
        courant_match, dernier = match, (t, x, y)
    if combat:
        clore(courant_match, combat)
    return credit, reponse


def indicateurs_joueurs(t):
    """Une ligne par joueur (parties de 15 min ou plus) avec tous les indicateurs."""
    import numpy as np

    j = t.joueurs[t.joueurs["duree_min"] >= DUREE_MIN].copy()
    j["cc_inflige_min"] = _par_minute(j, "temps_cc_inflige")
    j["immobilisations_min"] = _par_minute(j, "enemyChampionImmobilizations")
    j["immobilise_et_tue_min"] = _par_minute(j, "immobilizeAndKillWithAlly")
    j["repousse_et_tue_min"] = _par_minute(j, "knockEnemyIntoTeamAndKill")
    j["part_degats_encaisses"] = j["damageTakenOnTeamPercentage"]
    j["pick_kills_min"] = _par_minute(j, "pickKillWithAlly")
    j["solo_kills_min"] = _par_minute(j, "soloKills")
    degats = j[["degats_physiques_champions", "degats_magiques_champions", "degats_vrais_champions"]].sum(axis=1, min_count=1)
    j["degats_champions"] = degats
    j["degats_sur_subis"] = degats / j["degats_subis"].where(j["degats_subis"] > 0)
    j["degats_par_participation"] = degats / (j["kills"] + j["assists"] + 1)
    j["skillshots_min"] = _par_minute(j, "skillshotsHit")
    j["sauvetages_min"] = _par_minute(j, "saveAllyFromDeath")
    j["soins_allies_min"] = _par_minute(j, "soins_allies")
    j["boucliers_allies_min"] = _par_minute(j, "boucliers_allies")
    j["soins_boucliers_effectifs_min"] = _par_minute(j, "effectiveHealAndShielding")
    j["cc_par_degat_subi"] = j["temps_cc_inflige"] / (j["degats_subis"].where(j["degats_subis"] > 0) / 1000)
    j["part_kills_en_inferiorite"] = j["outnumberedKills"] / j["kills"].where(j["kills"] > 0)
    j["degats_subis_min"] = _par_minute(j, "degats_subis")
    j["degats_attenues_min"] = _par_minute(j, "degats_attenues")
    j["degats_batiments_min"] = _par_minute(j, "degats_batiments")

    cle = list(zip(j["match"], j["participant"].astype(int)))
    if t.evenements is not None and len(t.evenements):
        ev = t.evenements
        avec_ev = set(ev["match"])
        equipe_de = dict(zip(zip(t.joueurs["match"], t.joueurs["participant"].astype(int)), t.joueurs["equipe"]))
        credit, reponse = combats(ev, equipe_de)
        # Kills « burst » : tueur presque seul (au plus un assistant, au plus 2 champions ennemis
        # dans les dégâts reçus) sur une victime qui a pris beaucoup de dégâts juste avant de mourir.
        kills = ev[(ev["type"] == "CHAMPION_KILL") & (ev["participant"] > 0)].copy()
        nb_assistants = kills["assistants"].fillna("").astype(str).map(lambda a: len([x for x in a.split("|") if x and x != "nan"]))
        seuil = kills["degats_recus_victime"].median()
        burst = kills[(nb_assistants <= 1) & (kills["nb_sources"] <= 2) & (kills["degats_recus_victime"] >= seuil)]
        nb_burst = burst.groupby(["match", "participant"]).size().to_dict()
        present = np.array([m in avec_ev for m, _ in cle])
        j["takedowns_combats_en_inferiorite_min"] = np.where(present, [credit.get(k, 0) for k in cle], np.nan) / j["duree_min"]
        j["takedowns_en_reponse_min"] = np.where(present, [reponse.get(k, 0) for k in cle], np.nan) / j["duree_min"]
        j["kills_burst_min"] = np.where(present, [nb_burst.get((m, float(p)), nb_burst.get((m, p), 0)) for m, p in cle], np.nan) / j["duree_min"]
        takedowns = (j["kills"] + j["assists"]).where(lambda s: s > 0)
        j["part_takedowns_combats_en_inferiorite"] = j["takedowns_combats_en_inferiorite_min"] * j["duree_min"] / takedowns
        j["part_takedowns_en_reponse"] = j["takedowns_en_reponse_min"] * j["duree_min"] / takedowns
    else:
        j["part_takedowns_combats_en_inferiorite"] = np.nan
        j["part_takedowns_en_reponse"] = np.nan
        j["takedowns_combats_en_inferiorite_min"] = np.nan
        j["takedowns_en_reponse_min"] = np.nan
        j["kills_burst_min"] = np.nan

    if t.timeline is not None and len(t.timeline):
        tl = t.timeline.merge(t.joueurs[["match", "participant", "equipe", "poste"]], on=["match", "participant"])
        distances = []
        for minute in (15, 20, 25):
            x, y = tl[f"x_{minute}"], tl[f"y_{minute}"]
            groupe = tl.assign(_x=x, _y=y, _n=x.notna().astype(int)).groupby(["match", "equipe"])
            sx, sy, n = groupe["_x"].transform("sum"), groupe["_y"].transform("sum"), groupe["_n"].transform("sum")
            cx, cy = (sx - x.fillna(0)) / (n - 1), (sy - y.fillna(0)) / (n - 1)
            d = np.hypot(x - cx, y - cy).where((n >= 3) & x.notna())
            distances.append(d)
        pile = np.column_stack(distances)
        nb = np.isfinite(pile).sum(axis=1)
        tl["distance_equipe"] = np.where(nb > 0, np.nansum(pile, axis=1) / np.maximum(nb, 1), np.nan)
        for minute in (10, 15):
            adverse = tl[["match", "poste", "equipe", f"or_{minute}"]].copy()
            adverse["equipe"] = adverse["equipe"].map({"b": "r", "r": "b"})
            adverse = adverse.rename(columns={f"or_{minute}": f"or_adverse_{minute}"})
            tl = tl.merge(adverse, on=["match", "poste", "equipe"], how="left")
            tl[f"avance_or_{minute}"] = tl[f"or_{minute}"] - tl[f"or_adverse_{minute}"]
        j = j.merge(tl[["match", "participant", "distance_equipe", "avance_or_10", "avance_or_15"]],
                    on=["match", "participant"], how="left")
    else:
        j["distance_equipe"] = np.nan
        j["avance_or_10"] = np.nan
        j["avance_or_15"] = np.nan

    j["invasion_min"] = _par_minute(j, "enemyJungleMonsterKills")
    j["kills_lanes_tot_jungle"] = j["killsOnLanersEarlyJungleAsJungler"]
    return j


# --- Profils par champion et poste ---------------------------------------------------------

def scores_timing(j, minimum=MINIMUM):
    """Winrate par tranche de durée et score de timing (winrate 15-25 min moins winrate > 32 min)."""
    import pandas as pd

    j = j[j["duree_min"] >= DUREE_MIN]
    tranche = pd.cut(j["duree_min"], [DUREE_MIN, 25, 32, 1e9], right=False, labels=["moins25", "25_32", "plus32"])
    wr = j.assign(tranche=tranche).pivot_table(index=["champion", "poste"], columns="tranche", values="victoire",
                                               aggfunc="mean", observed=False, dropna=False)
    wr = wr.reindex(columns=["moins25", "25_32", "plus32"])
    wr.columns = [f"winrate_{c}" for c in wr.columns]
    n = j.groupby(["champion", "poste"]).size().rename("parties")
    sortie = wr.join(n)
    sortie["timing"] = sortie["winrate_moins25"] - sortie["winrate_plus32"]
    return sortie[sortie["parties"] >= minimum]


def profils(j, catalogue=None, minimum=MINIMUM):
    """Profil de chaque champion à son poste : moyennes, ratios au poste, scores de famille."""
    import numpy as np
    import pandas as pd

    groupes = j.groupby(["champion", "poste"])
    moyennes = groupes[INDICATEURS].mean()
    n = groupes.size().rename("parties")
    moyennes = moyennes.join(n)
    moyennes = moyennes[moyennes["parties"] >= minimum].copy()
    moyennes["winrate"] = groupes["victoire"].mean()
    sommes = groupes[["degats_physiques_champions", "degats_magiques_champions", "degats_vrais_champions"]].sum()
    total = sommes.sum(axis=1)
    moyennes["part_physique"] = sommes["degats_physiques_champions"] / total
    moyennes["part_magique"] = sommes["degats_magiques_champions"] / total
    moyennes["part_vraie"] = sommes["degats_vrais_champions"] / total
    moyennes["avance_or_10"] = groupes["avance_or_10"].mean()
    moyennes["avance_or_15"] = groupes["avance_or_15"].mean()
    devant = j[j["avance_or_15"] > 0].groupby(["champion", "poste"])["victoire"].mean()
    derriere = j[j["avance_or_15"] < 0].groupby(["champion", "poste"])["victoire"].mean()
    moyennes["winrate_devant_15"] = devant
    moyennes["winrate_derriere_15"] = derriere
    moyennes["snowball"] = devant - derriere
    moyennes["invasion_min"] = groupes["invasion_min"].mean()
    moyennes["kills_lanes_tot_jungle"] = groupes["kills_lanes_tot_jungle"].mean()
    moyennes = moyennes.join(scores_timing(j, minimum).drop(columns="parties"), how="left")

    # Moyenne du poste : tous les joueurs du poste (y compris champions rares).
    moyenne_poste = j.groupby("poste")[INDICATEURS].mean()
    sortie = moyennes.reset_index()
    for indicateur in INDICATEURS:
        reference = sortie["poste"].map(moyenne_poste[indicateur])
        sortie[f"ratio_{indicateur}"] = sortie[indicateur] / reference.where(reference != 0)
        # Standardisation dans le poste, entre champions à 100 parties ou plus.
        par_poste = sortie.groupby("poste")[indicateur]
        ecart = par_poste.transform("std")
        sortie[f"z_{indicateur}"] = (sortie[indicateur] - par_poste.transform("mean")) / ecart.where(ecart > 0)
    for famille, liste in FAMILLES.items():
        sortie[f"score_{famille}"] = sortie[[f"z_{i}" for i in liste]].mean(axis=1, skipna=True)

    # Invasion (junglers) : moyenne standardisée des deux indicateurs, parmi les junglers.
    jungle = sortie["poste"] == "jgl"
    sortie["score_invasion"] = np.nan
    if jungle.any():
        z = []
        for colonne in ("invasion_min", "kills_lanes_tot_jungle"):
            valeurs = sortie.loc[jungle, colonne]
            z.append((valeurs - valeurs.mean()) / valeurs.std())
        sortie.loc[jungle, "score_invasion"] = pd.concat(z, axis=1).mean(axis=1)

    # Quart supérieur de chaque famille dans le poste (utilisé par les hypothèses).
    for famille in FAMILLES:
        seuil = sortie.groupby("poste")[f"score_{famille}"].transform(lambda s: s.quantile(0.75))
        sortie[f"{famille}_mesure"] = (sortie[f"score_{famille}"] >= seuil).astype(int)
    if jungle.any():
        seuil_invasion = sortie.loc[jungle, "score_invasion"].quantile(0.75)
        seuil_tardif = sortie.loc[jungle, "timing"].quantile(0.25)
        sortie["jungler_envahisseur"] = (jungle & (sortie["score_invasion"] >= seuil_invasion)).astype(int)
        sortie["jungler_tardif"] = (jungle & (sortie["timing"] <= seuil_tardif)).astype(int)
    else:
        sortie["jungler_envahisseur"] = 0
        sortie["jungler_tardif"] = 0
    top = sortie["poste"] == "top"
    seuil_front = sortie.loc[top, "score_front"].quantile(2 / 3) if top.any() else np.inf
    sortie["type_top"] = ""
    sortie.loc[top, "type_top"] = np.where(
        sortie.loc[top, "champion"].isin(DISTANCE), "distance",
        np.where(sortie.loc[top, "score_front"] >= seuil_front, "front", "combattant"),
    )
    sortie["distance"] = sortie["champion"].isin(DISTANCE).astype(int)
    sortie["degats_mesures"] = np.where(sortie["part_physique"] >= SEUIL_AD, "AD",
                                        np.where(sortie["part_magique"] >= SEUIL_AD, "AP", "mixte"))
    styles = list(STYLES_MESURES)
    sortie["style_mesure"] = sortie[[f"score_{s}" for s in styles]].idxmax(axis=1).str.removeprefix("score_").map(STYLES_MESURES)
    if catalogue is not None:
        comparer_catalogue(sortie, catalogue)
    return sortie


def comparer_catalogue(sortie, catalogue):
    import numpy as np

    fiche = sortie["champion"].map(lambda nom: catalogue.get(nom, {}))
    sortie["catalogue_principal"] = fiche.map(lambda f: f.get("principal", ""))
    sortie["catalogue_secondaire"] = fiche.map(lambda f: f.get("secondaire", ""))
    sortie["catalogue_degats"] = fiche.map(lambda f: f.get("degats", ""))
    sortie["catalogue_tanky"] = fiche.map(lambda f: f.get("tanky", ""))
    sortie["catalogue_split"] = fiche.map(lambda f: "oui" if f.get("split") else "non")
    # Désaccord de style : le champion fait MOINS que la moyenne de son poste dans la famille que le
    # catalogue lui donne en style principal. Le style mesuré le plus fort est donné à côté.
    famille_de = {v: k for k, v in STYLES_MESURES.items()}
    sortie["score_style_catalogue"] = [
        sortie.at[i, f"score_{famille_de[p]}"] if p in famille_de else np.nan
        for i, p in zip(sortie.index, sortie["catalogue_principal"])
    ]
    sortie["desaccord_style"] = np.where(
        sortie["catalogue_principal"] == "", "sans style au catalogue",
        np.where(sortie["score_style_catalogue"] < -0.25, "oui",
                 np.where(sortie["score_style_catalogue"] < 0, "léger", "non")))
    correspondance = {"AD": "AD", "AP": "AP", "Hybride": "mixte"}
    sortie["desaccord_degats"] = [
        "non" if correspondance.get(c, c) == m else "oui" for m, c in zip(sortie["degats_mesures"], sortie["catalogue_degats"])
    ]
    sortie["desaccord_front"] = np.where(
        ((sortie["catalogue_tanky"] == "HP+") & (sortie["score_front"] < 0))
        | ((sortie["catalogue_tanky"] == "") & (sortie["front_mesure"] == 1)), "oui", "non")
    sortie["desaccord_split"] = np.where(
        ((sortie["catalogue_split"] == "oui") & (sortie["score_split"] < 0))
        | ((sortie["catalogue_split"] == "non") & (sortie["split_mesure"] == 1)), "oui", "non")
    sortie["desaccord"] = np.where((sortie["desaccord_style"] == "oui") | (sortie["desaccord_degats"] == "oui"), "oui", "non")


# --- Groupes -------------------------------------------------------------------------------

def silhouette(X, etiquettes):
    import numpy as np

    distances = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))
    valeurs = []
    for i in range(len(X)):
        meme = etiquettes == etiquettes[i]
        if meme.sum() <= 1:
            valeurs.append(0.0)
            continue
        a = distances[i, meme].sum() / (meme.sum() - 1)
        b = min(distances[i, etiquettes == k].mean() for k in set(etiquettes) if k != etiquettes[i])
        valeurs.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(valeurs))


def regrouper(sortie, k_min=4, k_max=10):
    """Ward sur les 7 scores de famille. k = meilleure silhouette entre k_min et k_max."""
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage

    colonnes = [f"score_{f}" for f in FAMILLES]
    X = sortie[colonnes].fillna(0.0).to_numpy()
    X = (X - X.mean(axis=0)) / X.std(axis=0)
    arbre = linkage(X, method="ward")
    essais = []
    for k in range(k_min, min(k_max, len(X) - 1) + 1):
        etiquettes = fcluster(arbre, k, criterion="maxclust")
        essais.append((k, silhouette(X, etiquettes)))
    k_choisi = max(essais, key=lambda e: e[1])[0]
    etiquettes = fcluster(arbre, k_choisi, criterion="maxclust")
    sortie["groupe"] = etiquettes
    libelles = {}
    for g in sorted(set(etiquettes)):
        centre = sortie.loc[sortie["groupe"] == g, colonnes].mean()
        dominantes = [c.removeprefix("score_") for c in centre.sort_values(ascending=False).index[:2] if centre[c] > 0.2]
        libelles[g] = " + ".join(dominantes) if dominantes else "moyen partout"
    sortie["groupe_libelle"] = sortie["groupe"].map(libelles)
    return essais, k_choisi, libelles


# --- Sortie --------------------------------------------------------------------------------

COLONNES_SORTIE = (
    ["champion", "poste", "parties", "winrate", "groupe", "groupe_libelle", "style_mesure",
     "catalogue_principal", "catalogue_secondaire", "score_style_catalogue", "desaccord_style",
     "degats_mesures", "catalogue_degats", "desaccord_degats", "part_physique", "part_magique", "part_vraie",
     "catalogue_tanky", "desaccord_front", "catalogue_split", "desaccord_split", "desaccord"]
    + [f"score_{f}" for f in FAMILLES]
    + [f"{f}_mesure" for f in FAMILLES]
    + ["winrate_moins25", "winrate_25_32", "winrate_plus32", "timing", "avance_or_10", "avance_or_15",
       "winrate_devant_15", "winrate_derriere_15", "snowball", "score_invasion", "jungler_tardif",
       "jungler_envahisseur", "distance", "type_top"]
    + [f"ratio_{i}" for i in INDICATEURS]
)


def _texte(valeur):
    if isinstance(valeur, float):
        if math.isnan(valeur):
            return ""
        return f"{valeur:.4g}" if abs(valeur) < 1000 else f"{valeur:.0f}"
    return str(valeur)


def ecrire(sortie, essais, k_choisi, libelles, chemin=RESULTATS):
    chemin = Path(chemin)
    chemin.mkdir(exist_ok=True)
    tri = sortie.sort_values(["poste", "groupe", "champion"])
    with open(chemin / "categories_mesurees.csv", "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(COLONNES_SORTIE)
        for ligne in tri[COLONNES_SORTIE].itertuples(index=False):
            ecrivain.writerow([_texte(v) for v in ligne])
    with open(chemin / "categories_groupes.csv", "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(["type", "groupe", "valeur", "detail"])
        for k, s in essais:
            ecrivain.writerow(["silhouette", k, f"{s:.3f}", "choisi" if k == k_choisi else ""])
        for g, libelle in libelles.items():
            membres = sortie[sortie["groupe"] == g]
            exemples = ", ".join(f"{c} ({p})" for c, p in membres.sort_values("parties", ascending=False)[["champion", "poste"]].head(8).itertuples(index=False))
            ecrivain.writerow(["groupe", g, len(membres), f"{libelle} : {exemples}"])


def calculer(matchs, donnees=None):
    """Tables, indicateurs par joueur et profils pour une liste ordonnée de parties."""
    import lecture
    from tables import charger

    t = charger(matchs, donnees or lecture.DONNEES)
    j = indicateurs_joueurs(t)
    sortie = profils(j, charger_catalogue())
    return t, j, sortie


def main():
    try:
        import echantillon

        matchs, _ = echantillon.decouper()
        if not matchs:
            print("Catégories : aucune partie.")
            return 0
        t, j, sortie = calculer(matchs)
        essais, k, libelles = regrouper(sortie)
        ecrire(sortie, essais, k, libelles)
        courtes = int((t.joueurs.groupby("match")["duree_min"].first() < DUREE_MIN).sum())
        print(f"Catégories : {len(matchs)} parties ({courtes} de moins de 15 min écartées), "
              f"{len(sortie)} champions-postes, {k} groupes, {int((sortie['desaccord'] == 'oui').sum())} désaccords.")
    except ImportError as erreur:
        print(f"Catégories : sauté, bibliothèque absente ({erreur}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
