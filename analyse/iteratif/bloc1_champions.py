"""Bloc 1 : le catalogue à l'instant T (chaque champion dans un groupe, plus ses capacités).

Deux façons de faire, choisies par le paramètre « mode » :
- « catalogue » : le catalogue actuel (Catalogue.csv). Groupe = style principal ; style secondaire
  gardé à part ; option « separer_tanks » qui sépare les Engage HP+ (tanks) des autres Engage.
  C'est le point de départ (itération 0).
- « mesure » : la classification mesurée sur les timelines (comme classification.py), avec des
  paramètres variables : poids de chaque famille d'indicateurs, nombre d'axes, nombre de groupes.

Dans les deux modes, le recuit peut aussi DÉPLACER des champions (paramètre « deplacements ») :
c'est ainsi que le catalogue évolue au fil des itérations. Un champion peut aller dans n'importe quel
groupe ; « voisin » (le groupe le plus proche du sien, ou son style secondaire dans le catalogue) est
proposé en priorité par le recuit.

Capacités de chaque champion (mesurées sur l'échantillon figé, quel que soit le mode) :
- cc : temps de CC et immobilisations (standardisés) ;
- front : dégâts encaissés et part atténuée (standardisés) ;
- magique : part de dégâts magiques (0 à 1).

Les mesures par champion viennent de champions_mesures.csv, préparé une fois par :
    python3 analyse/iteratif/bloc1_champions.py --preparer
(lit les timelines et les événements de l'échantillon figé ; aucune victoire n'y entre).
"""

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

import commun  # noqa: F401  (règle sys.path)
import classification
from regle import CATALOGUE, STYLES, charger_catalogue

ICI = Path(__file__).resolve().parent
MESURES = ICI / "champions_mesures.csv"

# Familles d'indicateurs de classification.py, dont le recuit fait varier les poids.
FAMILLES = {
    "degats": ["degats_min", "part_degats_equipe", "degats_par_takedown", "part_degats_avant_15"],
    "encaisse": ["subis_min", "part_encaisses_equipe", "part_attenuee", "soin_sur_soi_min"],
    "kills": ["kills_min", "morts_min", "assists_min", "part_coup_final", "solo_kills_min",
              "part_kills_burst", "part_kills_sous_tour"],
    "cc": ["cc_min", "immobilisations_min", "part_cc_dur", "cc_puis_kill_min"],
    "moment": ["part_ouvre_combat", "part_finit_combat", "part_premier_mort", "part_en_reponse", "part_en_inferiorite"],
    "soutien": ["soins_allies_min", "boucliers_allies_min", "sauvetages_min"],
    "skillshots": ["skillshots_min", "esquives_min"],
    "split": ["batiments_min", "distance_equipe"],
}
assert sorted(i for l in FAMILLES.values() for i in l) == sorted(classification.STYLE)


@dataclass
class Catalogue:
    """Catalogue à l'instant T. `groupe[c]` : indice 0..k-1 ; `secondaire[c]` : indice ou -1."""
    noms: list
    groupe: dict
    secondaire: dict
    capacites: dict = field(default_factory=dict)
    membres_texte: dict = field(default_factory=dict)
    voisin: dict = field(default_factory=dict)   # groupe vers lequel un champion peut être déplacé

    @property
    def k(self):
        return len(self.noms)


# --- Mesures par champion -------------------------------------------------------------------

def preparer_mesures(chemin=MESURES):
    """Calcule les indicateurs par champion sur l'échantillon figé et les écrit (une fois)."""
    import echantillon
    from tables import charger

    matchs, _ = echantillon.decouper(commun.dossier_donnees())
    t = charger(matchs, commun.dossier_donnees())
    j = classification.indicateurs_joueurs(t)
    del t
    p = classification.profils(j)
    colonnes = ["champion", "parties", "postes", "poste_principal"] + classification.NOMS
    p[colonnes].to_csv(chemin, sep=";", index=False, float_format="%.6g")
    return p


def lire_mesures(chemin=MESURES):
    import pandas as pd

    if not Path(chemin).exists():
        preparer_mesures(chemin)
    return pd.read_csv(chemin, sep=";")


def standardiser(mesures):
    """Z-scores des indicateurs de style (manquants remplacés par la moyenne)."""
    import numpy as np

    X = mesures[classification.STYLE].to_numpy(dtype=float)
    moyenne = np.nanmean(X, axis=0)
    X = np.where(np.isnan(X), moyenne, X)
    ecart = X.std(axis=0)
    ecart[ecart == 0] = 1
    return (X - X.mean(axis=0)) / ecart


def capacites(mesures):
    """{champion: (cc, front, magique)} : cc et front standardisés, magique en part."""
    Z = standardiser(mesures)
    col = {nom: i for i, nom in enumerate(classification.STYLE)}
    sortie = {}
    for i, champion in enumerate(mesures["champion"]):
        cc = (Z[i, col["cc_min"]] + Z[i, col["immobilisations_min"]]) / 2
        front = (Z[i, col["subis_min"]] + Z[i, col["part_attenuee"]]) / 2
        magique = mesures["part_magique"].iloc[i]
        sortie[champion] = (float(cc), float(front), float(magique if magique == magique else 0.5))
    return sortie


# --- Les deux modes -------------------------------------------------------------------------

def depuis_catalogue(params, catalogue=None):
    catalogue = catalogue or charger_catalogue(CATALOGUE)
    noms = list(STYLES) + ["Sans style"]
    if params.get("separer_tanks"):
        noms = ["Engage tank"] + noms
    indice = {nom: i for i, nom in enumerate(noms)}
    groupe, secondaire = {}, {}
    for champion, fiche in catalogue.items():
        principal = fiche["principal"] or "Sans style"
        if params.get("separer_tanks") and principal == "Engage" and fiche["tanky"] == "HP+":
            principal = "Engage tank"
        groupe[champion] = indice[principal]
        secondaire[champion] = indice.get(fiche["secondaire"], -1) if fiche["secondaire"] else -1
    # Kayn : le catalogue a Kayn rouge et Kayn bleu, comme les données.
    return noms, groupe, secondaire


def depuis_mesures(params, mesures):
    import numpy as np

    Z = standardiser(mesures)
    poids = np.ones(Z.shape[1])
    for famille, indicateurs in FAMILLES.items():
        for nom in indicateurs:
            poids[classification.STYLE.index(nom)] = params["familles"][famille]
    X = classification.axes_principaux(Z * poids, params["nb_axes"])
    etiquettes = classification.kmeans(X, params["k"], essais=8, graine=0)
    noms_groupes = classification.nommer(Z, etiquettes)
    vus, noms = {}, []
    for g in sorted(set(etiquettes)):
        nom = noms_groupes[g]
        if "à nommer" in nom:
            nom = f"Groupe {g}"
        if nom in vus:
            nom = f"{nom} {g}"
        vus[nom] = True
        noms.append(nom)
    groupe = {c: int(g) - 1 for c, g in zip(mesures["champion"], etiquettes)}
    # Voisin : le centre de groupe le plus proche après le sien (seul déplacement autorisé).
    centres = np.array([X[etiquettes == g].mean(axis=0) for g in sorted(set(etiquettes))])
    distances = ((X[:, None, :] - centres[None]) ** 2).sum(axis=2)
    voisin = {}
    for i, c in enumerate(mesures["champion"]):
        d = distances[i].copy()
        d[groupe[c]] = np.inf
        voisin[c] = int(d.argmin())
    return noms, groupe, {c: -1 for c in groupe}, voisin


def construire(params, mesures, catalogue=None):
    """Bloc 1 : renvoie le Catalogue à l'instant T pour ces paramètres."""
    if params["mode"] == "catalogue":
        noms, groupe, secondaire = depuis_catalogue(params, catalogue)
        # Dans le catalogue, un champion ne peut passer que vers son style secondaire.
        voisin = {c: s for c, s in secondaire.items() if s >= 0}
    else:
        noms, groupe, secondaire, voisin = depuis_mesures(params, mesures)
    for champion, cible in params.get("deplacements", {}).items():
        if champion in groupe and 0 <= cible < len(noms):
            groupe[champion] = cible
    membres = {}
    for champion, g in sorted(groupe.items()):
        membres.setdefault(noms[g], []).append(champion)
    return Catalogue(noms=noms, groupe=groupe, secondaire=secondaire, capacites=capacites(mesures),
                     membres_texte={n: ", ".join(m) for n, m in membres.items()}, voisin=voisin)


def ecrire(cat, chemin):
    """Écrit le catalogue à l'instant T (une ligne par champion)."""
    with open(chemin, "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(["champion", "groupe", "groupe_secondaire", "cc", "front", "part_magique"])
        for champion in sorted(cat.groupe):
            cc, front, magique = cat.capacites.get(champion, ("", "", ""))
            sec = cat.secondaire.get(champion, -1)
            ecrivain.writerow([champion, cat.noms[cat.groupe[champion]], cat.noms[sec] if sec >= 0 else "",
                               f"{cc:.3f}" if cc != "" else "", f"{front:.3f}" if front != "" else "",
                               f"{magique:.3f}" if magique != "" else ""])


if __name__ == "__main__":
    if "--preparer" in sys.argv:
        p = preparer_mesures()
        print(f"Mesures préparées : {len(p)} champions -> {MESURES}")
