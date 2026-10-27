"""Recuit n° 2 : deux pistes, chacune avec son vocabulaire (catalogue unifié du 24/10/2026).

- Piste « scenarios » : les colonnes du catalogue du propriétaire (style principal et secondaire, tanky,
  carry, dégâts). On note ses 13 scénarios (fixés à l'avance, avec leur sens attendu), chacun aussi
  vu du jungler, plus une famille « exploration » : les autres croisements de ses styles.
- Piste « teamfight » : le groupe teamfight (7 groupes mesurés, relus par le propriétaire) et la
  colonne tanky. Tout y est exploration : compo X contre compo Y, jungler X contre ou avec compo Y,
  compo tanky ou sans tank.

Ce que le recuit règle (le sens des mots) :
- poids des postes dans le score de style d'une compo : jungle, support, les 3 autres lanes ensemble ;
- seuil « compo X » : score à atteindre, en équivalents champions (2 = deux champions du style) ;
- piste scenarios : poids du style secondaire, et au plus 5 champions dont on inverse principal et
  secondaire ;
- piste teamfight : au plus 5 champions déplacés vers leur groupe voisin mesuré.
Garde-fou : un réglage qui laisse moins de scénarios étudiables (300 parties de A) qu'au départ est
refusé, pour que le recuit ne puisse pas « gagner » en faisant disparaître les scénarios.
Fixés : beaucoup d'engage = 3, peel = Counter-engage ou Disengage au support ou au jungler,
tanky = 2 HP+ ou 1 HP+ et 2 HP, sans tank = aucun HP+, full AD / full AP = au plus un champion de
l'autre type (hybride = un demi), carry = colonne Carry.

Tas (decoupage.json, n° 2) :
- A : choix des réglages, score = gain de prédiction en 5 rotations sur A (millièmes de perte log) ;
- B : jugement, lu une seule fois à la fin, pour les meilleurs réglages (appris sur tout A) ;
- C : jamais lu ici.
Seuil de hasard (--melanger) : victoires de A et B tirées au sort selon la seule force des champions.

    python3 analyse/recuit/recuit_pistes.py --piste scenarios --minutes 60 --graine 1 [--melanger]
"""

import argparse
import copy
import csv
import gzip
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "base"))

import commun  # noqa: E402
import bloc2_compos as bloc2  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402

# Styles et groupes teamfight de l'ancien catalogue, figé le 24/10/2026 (le catalogue unifié a maintenant les 10 types).
CATALOGUE_UNIFIE = commun.ANALYSE / "catalogues" / "ancien_catalogue_2026-10-24.csv"
RESULTATS = ICI / "resultats"
STYLES = ("Engage", "Pick", "Poke", "Counter-engage", "Disengage")
COURT = {"Engage": "E", "Pick": "Pi", "Poke": "Po", "Counter-engage": "CE", "Disengage": "D"}
GROUPES = ("Engage (tanks)", "Engage (bruisers)", "Supports tanks", "Pick (assassins)", "Poke (artilleurs)",
           "Carrys", "Disengage (enchanteurs)")
POSTES = bloc2.POSTES                       # top, jgl, mid, adc, sup
MIN_PARTIES = 300                           # une situation doit apparaître dans 300 parties de A
MAX_DEPLACEMENTS = 5
BEAUCOUP_ENGAGE = 3.0
LAMBDAS = (10.0, 30.0, 100.0, 300.0, 1000.0)
TAILLE_PALMARES = 10

DEPART = {
    "scenarios": {"roles": {"lanes": 1.0, "jgl": 1.0, "sup": 1.0}, "seuil": 2.0, "poids_secondaire": 0.5, "echanges": []},
    "teamfight": {"roles": {"lanes": 1.0, "jgl": 1.0, "sup": 1.0}, "seuil": 2.0, "deplacements": {}},
}
BORNES = {"lanes": (0.3, 2.0), "jgl": (0.5, 2.0), "sup": (0.0, 2.0), "seuil": (1.0, 3.0), "poids_secondaire": (0.0, 1.0)}


# --- Catalogue unifié -------------------------------------------------------------------------

def lire_catalogue(chemin=CATALOGUE_UNIFIE):
    with open(chemin, encoding="utf-8", newline="") as fichier:
        return {l["champion"]: l for l in csv.DictReader(fichier, delimiter=";")}


@dataclass
class Tableaux:
    """Le catalogue en tableaux numpy, dans l'ordre des champions de l'index (-1 = inconnu)."""
    principal: np.ndarray
    secondaire: np.ndarray
    tanky: np.ndarray        # 0 non, 1 HP, 2 HP+
    carry: np.ndarray        # 0 / 1
    ap: np.ndarray           # AD 0, AP 1, hybride 0,5
    groupe: np.ndarray
    voisin: np.ndarray       # groupe voisin mesuré (-1 : aucun)


def tableaux(catalogue, champions):
    s = {nom: i for i, nom in enumerate(STYLES)}
    g = {nom: i for i, nom in enumerate(GROUPES)}
    n = len(champions)
    t = Tableaux(*(np.full(n, -1) for _ in range(2)), np.zeros(n, int), np.zeros(n, int), np.full(n, 0.5),
                 np.full(n, -1), np.full(n, -1))
    for i, c in enumerate(champions):
        l = catalogue.get(c)
        if not l:
            continue
        t.principal[i] = s.get(l["style_principal"], -1)
        t.secondaire[i] = s.get(l["style_secondaire"], -1)
        t.tanky[i] = {"HP": 1, "HP+": 2}.get(l["tanky"], 0)
        t.carry[i] = 1 if l["carry"] == "oui" else 0
        t.ap[i] = {"AD": 0.0, "AP": 1.0}.get(l["degats"], 0.5)
        t.groupe[i] = g.get(l["groupe_teamfight"], -1)
        # Voisin : si le propriétaire a changé le groupe, le voisin est le groupe mesuré ; sinon le voisin mesuré.
        mesure, voisin = g.get(l["groupe_teamfight_mesure"], -1), g.get(l["groupe_voisin_mesure"], -1)
        t.voisin[i] = mesure if mesure != t.groupe[i] else voisin
    return t


# --- Variables de situation ---------------------------------------------------------------------

@dataclass
class Variable:
    famille: str      # « scenario », « scenario_jungler » ou « exploration »
    nom: str
    sens: int = 0     # sens attendu (+1 favorable, -1 défavorable), 0 si aucun


def anti(fb, fr):
    """Variable antisymétrique : +1 si le bleu est dans la situation, -1 si c'est le rouge."""
    return fb.astype(float) - fr.astype(float)


def poids_postes(params):
    r = params["roles"]
    return np.array([r["lanes"], r["jgl"], r["lanes"], r["lanes"], r["sup"]])


def scores(code, code2, poids, poids2, equipe, k):
    """Score de chaque catégorie pour une équipe : somme des poids de postes des champions (et du
    secondaire × poids2), ramenée à des équivalents champions (poids moyen 1)."""
    n = equipe.shape[0]
    s = np.zeros((n, k))
    lignes = np.arange(n)
    for r in range(5):
        c = code[equipe[:, r]]
        ok = c >= 0
        np.add.at(s, (lignes[ok], c[ok]), poids[r])
        if code2 is not None and poids2 > 0:
            c = code2[equipe[:, r]]
            ok = c >= 0
            np.add.at(s, (lignes[ok], c[ok]), poids[r] * poids2)
    return s * 5 / poids.sum()


def tanky_flags(t, equipe):
    hpp = (t.tanky[equipe] == 2).sum(axis=1)
    hp = (t.tanky[equipe] == 1).sum(axis=1)
    return (hpp >= 2) | ((hpp >= 1) & (hp >= 2)), hpp == 0


def variables_scenarios(t, index, lignes, params):
    principal, secondaire = t.principal.copy(), t.secondaire.copy()
    for i in params["echanges"]:
        principal[i], secondaire[i] = secondaire[i], principal[i]
    poids = poids_postes(params)
    E, Pi, Po, CE, D = range(5)
    f = {}
    for cote in "br":
        e = index.equipes[cote][lignes]
        s = scores(principal, secondaire, poids, params["poids_secondaire"], e, 5)
        compo = s >= params["seuil"]
        jp, js = principal[e[:, 1]], secondaire[e[:, 1]]
        sp, ss = principal[e[:, 4]], secondaire[e[:, 4]]
        peel = np.isin(jp, (CE, D)) | np.isin(js, (CE, D)) | np.isin(sp, (CE, D)) | np.isin(ss, (CE, D))
        tanky, sans_tank = tanky_flags(t, e)
        ap = t.ap[e].sum(axis=1)
        f[cote] = {"compo": compo, "beaucoup_engage": s[:, E] >= BEAUCOUP_ENGAGE, "peel": peel, "tanky": tanky,
                   "sans_tank": sans_tank, "carry": t.carry[e].max(axis=1) == 1,
                   "full": (ap <= 1) | ((5 - ap) <= 1), "jungler": jp}
    b, r = f["b"], f["r"]
    cols, vars_ = [], []

    def ajouter(fb, fr, famille, nom, sens=0):
        cols.append(anti(fb, fr))
        vars_.append(Variable(famille, nom, sens))

    def duel(x, y, nom, sens, condition_y=None):
        cb = b["compo"][:, y] if condition_y is None else condition_y(r)
        cr = r["compo"][:, y] if condition_y is None else condition_y(b)
        ajouter(b["compo"][:, x] & cb, r["compo"][:, x] & cr, "scenario", nom, sens)
        ajouter((b["jungler"] == x) & cb, (r["jungler"] == x) & cr, "scenario_jungler", f"Jungler {STYLES[x]} : {nom}", sens)

    # Les 13 scénarios du propriétaire (23/10), dans son ordre, avec le sens attendu.
    duel(E, Po, "Engage bat Poke", +1)
    ajouter(b["beaucoup_engage"] & r["compo"][:, D], r["beaucoup_engage"] & b["compo"][:, D], "scenario",
            "Beaucoup d'engage (3) bat Disengage", +1)
    ajouter((b["jungler"] == E) & r["compo"][:, D], (r["jungler"] == E) & b["compo"][:, D], "scenario_jungler",
            "Jungler Engage : Engage bat Disengage", +1)
    duel(CE, E, "Counter-engage bat Engage", +1)
    duel(D, CE, "Disengage bat Counter-engage", +1)
    duel(Po, CE, "Poke bat Counter-engage", +1)
    duel(Po, D, "Poke bat Disengage", +1)
    duel(Pi, D, "Pick bat Disengage", +1)
    duel(CE, Pi, "Counter-engage bat Pick", +1)
    duel(Pi, Po, "Pick bat Poke sans peel", +1, condition_y=lambda autre: autre["compo"][:, Po] & ~autre["peel"])
    duel(Pi, None, "Pick perd contre compo tanky", -1, condition_y=lambda autre: autre["tanky"])
    ajouter(b["full"], r["full"], "scenario", "Compo full AD ou full AP perd", -1)
    ajouter(b["sans_tank"], r["sans_tank"], "scenario", "Compo sans tank perd", -1)
    ajouter(b["peel"] & ~b["carry"], r["peel"] & ~r["carry"], "scenario", "Peel sans carry perd", -1)

    # Exploration : les autres croisements des styles.
    for x in range(5):
        ajouter(b["compo"][:, x], r["compo"][:, x], "exploration", f"Compo {STYLES[x]}")
    for x, y in ((E, Pi), (E, D), (Pi, Po)):
        ajouter(b["compo"][:, x] & r["compo"][:, y], r["compo"][:, x] & b["compo"][:, y], "exploration",
                f"Compo {STYLES[x]} contre compo {STYLES[y]}")
    deja = {(E, Po), (E, D), (CE, E), (D, CE), (Po, CE), (Po, D), (Pi, D), (CE, Pi)}
    for x in range(5):
        for y in range(5):
            if (x, y) not in deja:
                ajouter((b["jungler"] == x) & r["compo"][:, y], (r["jungler"] == x) & b["compo"][:, y], "exploration",
                        f"Jungler {STYLES[x]} contre compo {STYLES[y]}")
            ajouter((b["jungler"] == x) & b["compo"][:, y], (r["jungler"] == x) & r["compo"][:, y], "exploration",
                    f"Jungler {STYLES[x]} avec compo alliée {STYLES[y]}")
    ajouter(b["tanky"], r["tanky"], "exploration", "Compo tanky")
    return np.column_stack(cols), vars_


def variables_teamfight(t, index, lignes, params):
    groupe = t.groupe.copy()
    for i, g in params["deplacements"].items():
        groupe[int(i)] = g
    poids = poids_postes(params)
    G = len(GROUPES)
    f = {}
    for cote in "br":
        e = index.equipes[cote][lignes]
        s = scores(groupe, None, poids, 0, e, G)
        tanky, sans_tank = tanky_flags(t, e)
        f[cote] = {"compo": s >= params["seuil"], "jungler": groupe[e[:, 1]], "tanky": tanky, "sans_tank": sans_tank}
    b, r = f["b"], f["r"]
    cols, vars_ = [], []

    def ajouter(fb, fr, nom):
        cols.append(anti(fb, fr))
        vars_.append(Variable("exploration", nom))

    for x in range(G):
        ajouter(b["compo"][:, x], r["compo"][:, x], f"Compo {GROUPES[x]}")
    for x in range(G):
        for y in range(x + 1, G):
            ajouter(b["compo"][:, x] & r["compo"][:, y], r["compo"][:, x] & b["compo"][:, y],
                    f"Compo {GROUPES[x]} contre compo {GROUPES[y]}")
    for x in range(G):
        for y in range(G):
            ajouter((b["jungler"] == x) & r["compo"][:, y], (r["jungler"] == x) & b["compo"][:, y],
                    f"Jungler {GROUPES[x]} contre compo {GROUPES[y]}")
            ajouter((b["jungler"] == x) & b["compo"][:, y], (r["jungler"] == x) & r["compo"][:, y],
                    f"Jungler {GROUPES[x]} avec compo alliée {GROUPES[y]}")
    ajouter(b["tanky"], r["tanky"], "Compo tanky")
    ajouter(b["sans_tank"], r["sans_tank"], "Compo sans tank")
    for x in range(G):
        ajouter((b["jungler"] == x) & r["tanky"], (r["jungler"] == x) & b["tanky"], f"Jungler {GROUPES[x]} contre compo tanky")
        ajouter((b["jungler"] == x) & r["sans_tank"], (r["jungler"] == x) & b["sans_tank"], f"Jungler {GROUPES[x]} contre compo sans tank")
        ajouter((b["jungler"] == x) & b["sans_tank"], (r["jungler"] == x) & r["sans_tank"], f"Jungler {GROUPES[x]} avec compo alliée sans tank")
    return np.column_stack(cols), vars_


# --- La machine : données préparées une fois --------------------------------------------------

@dataclass
class Evaluation:
    score: float          # gain en millièmes (rotations sur A, ou jugement sur B)
    nb_variables: int
    biais: list
    rares: list = None


class Machine:
    def __init__(self, table, piste, catalogue):
        self.piste = piste
        self.table = table
        self.index = bloc2.Index(table)
        self.t = tableaux(catalogue, self.index.champions)
        self.inconnus = [c for c in self.index.champions if c not in catalogue]
        self.lignes_a = np.where(table["tas"] == "A")[0]
        self.lignes_b = np.where(table["tas"] == "B")[0]
        self.pli = bloc3.plis(len(self.lignes_a))
        force = bloc3.Force(self.index, self.lignes_a)
        self.dec_a, (self.dec_b,) = force.decalages(self.lignes_a, [self.lignes_b], pli=self.pli)
        self.lambda_force = force.lam
        self.ya, self.yb = self.index.y[self.lignes_a], self.index.y[self.lignes_b]
        # Champions qu'on peut changer : un secondaire (scenarios) ou un groupe voisin (teamfight).
        if piste == "scenarios":
            self.mobiles = [i for i in range(len(self.index.champions))
                            if self.t.secondaire[i] >= 0 and self.t.secondaire[i] != self.t.principal[i]]
        else:
            self.mobiles = [i for i in range(len(self.index.champions)) if self.t.voisin[i] >= 0]
        # Garde-fou : un réglage doit laisser au moins autant de scénarios étudiables (300 parties de A)
        # qu'au départ. Sinon le recuit pourrait « gagner » en faisant disparaître les scénarios.
        self.min_scenarios = 0
        self.min_scenarios = self.nb_scenarios(DEPART[piste])
        self.lam = 30.0
        self.lam = max(LAMBDAS, key=lambda l: self._score_rotation(DEPART[piste], l))

    def variables(self, params, lignes):
        fonction = variables_scenarios if self.piste == "scenarios" else variables_teamfight
        return fonction(self.t, self.index, lignes, params)

    def _matrices(self, params):
        Xa, vars_ = self.variables(params, self.lignes_a)
        garder = (Xa != 0).sum(axis=0) >= MIN_PARTIES
        return Xa[:, garder], [v for v, g in zip(vars_, garder) if g], garder

    def nb_scenarios(self, params):
        _, vars_, _ = self._matrices(params)
        return sum(v.famille != "exploration" for v in vars_)

    def _score_rotation(self, params, lam=None):
        lam = self.lam if lam is None else lam
        X, vars_, _ = self._matrices(params)
        if sum(v.famille != "exploration" for v in vars_) < self.min_scenarios:
            return -1e9
        if X.shape[1] == 0:
            return 0.0
        gains = []
        for f in range(bloc3.PLIS):
            app, note = self.pli != f, self.pli == f
            beta, _ = bloc3.logistique(X[app], self.ya[app], self.dec_a[app], lam=lam)
            gains.append(bloc3.perte_log(self.ya[note], bloc3.sigmoide(self.dec_a[note]))
                         - bloc3.perte_log(self.ya[note], bloc3.sigmoide(self.dec_a[note] + X[note] @ beta)))
        return 1000 * float(np.mean(gains))

    def evaluer(self, params):
        """Note de choix : 5 rotations sur A."""
        return self._score_rotation(params)

    def juger(self, params):
        """Note de jugement : appris sur tout A, mesuré sur B (jamais vu pendant la recherche)."""
        tous_a, tous_vars = self.variables(params, self.lignes_a)
        Xa, vars_, garder = self._matrices(params)
        Xb = self.variables(params, self.lignes_b)[0][:, garder]
        # Scénarios trop rares pour être étudiés avec ce réglage : signalés, pas cachés.
        rares = [{"famille": v.famille, "nom": v.nom, "sens_attendu": v.sens, "parties_A": int((tous_a[:, i] != 0).sum())}
                 for i, v in enumerate(tous_vars) if not garder[i] and v.famille != "exploration"]
        beta, _ = bloc3.logistique(Xa, self.ya, self.dec_a, lam=self.lam)
        gain = (bloc3.perte_log(self.yb, bloc3.sigmoide(self.dec_b))
                - bloc3.perte_log(self.yb, bloc3.sigmoide(self.dec_b + Xb @ beta)))
        biais = []
        for i, v in enumerate(vars_):
            ta, na, _ = bloc3.taux_ajuste(Xa[:, i], self.ya, self.dec_a)
            tb, nb, eb = bloc3.taux_ajuste(Xb[:, i], self.yb, self.dec_b)
            biais.append({"famille": v.famille, "nom": v.nom, "sens_attendu": v.sens, "coefficient": float(beta[i]),
                          "taux_A": ta, "parties_A": na, "taux_B": tb, "parties_B": nb, "erreur_B": eb})
        return Evaluation(score=1000 * gain, nb_variables=len(vars_), biais=biais, rares=rares)


# --- Le recuit ----------------------------------------------------------------------------------

def borner(x, nom):
    a, b = BORNES[nom]
    return min(max(x, a), b)


def voisin(params, rng, machine):
    if hasattr(machine, "voisin_params"):       # recuit n° 3 (styles) : ses propres réglages
        return machine.voisin_params(params, rng)
    p = copy.deepcopy(params)
    tirage = rng.random()
    if tirage < 0.35:
        poste = rng.choice(("lanes", "jgl", "sup"))
        p["roles"][poste] = round(borner(p["roles"][poste] + rng.gauss(0, 0.25), poste), 3)
        return p, f"poids {poste}"
    if tirage < 0.50:
        p["seuil"] = round(borner(p["seuil"] + rng.gauss(0, 0.2), "seuil"), 3)
        return p, "seuil"
    if machine.piste == "scenarios" and tirage < 0.62:
        p["poids_secondaire"] = round(borner(p["poids_secondaire"] + rng.gauss(0, 0.15), "poids_secondaire"), 3)
        return p, "poids du secondaire"
    if not machine.mobiles:
        return p, "rien"
    i = rng.choice(machine.mobiles)
    nom = machine.index.champions[i]
    if machine.piste == "scenarios":
        if i in p["echanges"]:
            p["echanges"].remove(i)
            return p, f"{nom} reprend son style principal"
        if len(p["echanges"]) >= MAX_DEPLACEMENTS:
            p["echanges"].pop(rng.randrange(len(p["echanges"])))
        p["echanges"].append(i)
        p["echanges"].sort()
        return p, f"{nom} : principal et secondaire inversés"
    cle = str(i)
    if cle in p["deplacements"]:
        p["deplacements"].pop(cle)
        return p, f"{nom} revient dans son groupe"
    if len(p["deplacements"]) >= MAX_DEPLACEMENTS:
        p["deplacements"].pop(rng.choice(sorted(p["deplacements"])))
    p["deplacements"][cle] = int(machine.t.voisin[i])
    return p, f"{nom} va dans {GROUPES[machine.t.voisin[i]]}"


def signature(params):
    return hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]


def recuit(machine, minutes, graine=1, journal=print, t0=0.30, t_fin=0.005, essais_max=None):
    rng = random.Random(graine)
    courant = copy.deepcopy(DEPART[machine.piste])
    score_courant = machine.evaluer(courant)
    palmares = {signature(courant): (score_courant, courant)}
    historique, essais = [], []
    debut, duree = time.time(), 60 * minutes
    iteration, sans_progres, meilleur = 0, 0, score_courant
    while time.time() - debut < duree and (essais_max is None or iteration < essais_max):
        iteration += 1
        avance = (time.time() - debut) / duree if essais_max is None else iteration / essais_max
        temperature = t0 * (t_fin / t0) ** avance
        candidat, changement = voisin(courant, rng, machine)
        try:
            score = machine.evaluer(candidat)
        except (np.linalg.LinAlgError, ValueError):
            continue
        accepte = score >= score_courant or rng.random() < math.exp((score - score_courant) / temperature)
        if accepte:
            courant, score_courant = candidat, score
        essais.append((iteration, round(time.time() - debut, 1), round(temperature, 5), round(score, 5), int(accepte),
                       changement, json.dumps(candidat, ensure_ascii=False, sort_keys=True)))
        palmares[signature(candidat)] = (score, candidat)
        if len(palmares) > 5 * TAILLE_PALMARES:
            palmares.pop(min(palmares, key=lambda k: palmares[k][0]))
        if score > meilleur + 1e-9:
            meilleur, sans_progres = score, 0
        else:
            sans_progres += 1
        if sans_progres > 400:
            score_courant, courant = rng.choice(sorted(palmares.values(), key=lambda e: -e[0])[:TAILLE_PALMARES])
            courant, sans_progres = copy.deepcopy(courant), 0
        if iteration % 50 == 0:
            historique.append({"iteration": iteration, "secondes": round(time.time() - debut),
                               "temperature": round(temperature, 4), "courant": round(score_courant, 4),
                               "meilleur": round(meilleur, 4)})
        if iteration % 500 == 0:
            journal(f"{iteration} essais, {round(time.time() - debut)} s : meilleur {meilleur:.3f}, courant {score_courant:.3f}")
    return palmares, historique, iteration, essais


# --- Rapport ------------------------------------------------------------------------------------

def decrire(params, machine):
    if hasattr(machine, "decrire_params"):
        return machine.decrire_params(params)
    r = params["roles"]
    lignes = [f"Poids des postes : jungle {r['jgl']:.2f}, support {r['sup']:.2f}, autres lanes {r['lanes']:.2f} ; "
              f"seuil « compo X » : {params['seuil']:.2f} équivalents champions"]
    if machine.piste == "scenarios":
        lignes.append(f"Poids du style secondaire : {params['poids_secondaire']:.2f}")
        if params["echanges"]:
            lignes.append("Principal et secondaire inversés : " + ", ".join(
                f"{machine.index.champions[i]} ({STYLES[machine.t.secondaire[i]]} devient principal)" for i in params["echanges"]))
    elif params["deplacements"]:
        lignes.append("Champions déplacés : " + ", ".join(
            f"{machine.index.champions[int(i)]} -> {GROUPES[g]}" for i, g in sorted(params["deplacements"].items(), key=lambda e: machine.index.champions[int(e[0])])))
    return lignes


def pourcent(x):
    return "—" if x != x else f"{100 * x:.1f} %"


def ligne_biais(b):
    sens = ""
    if b["sens_attendu"]:
        bon = (b["taux_B"] - 0.5) * b["sens_attendu"] > 0 if b["taux_B"] == b["taux_B"] else False
        sens = " — dans le sens attendu sur B" if bon else " — PAS dans le sens attendu sur B"
    return (f"- {b['nom']} : {pourcent(b['taux_A'])} sur A ({b['parties_A']} parties), {pourcent(b['taux_B'])} sur B "
            f"({b['parties_B']} parties){sens}")


def rapport(machine, palmares, historique, iterations, essais, minutes, graine, melange):
    dossier = RESULTATS
    dossier.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M")
    numero = getattr(machine, "numero", 2)
    base = f"recuit{numero}_{machine.piste}_{date}" + ("_hasard" if melange else "")
    depart = DEPART[machine.piste]
    score_depart, jugement_depart = machine.evaluer(depart), machine.juger(depart)
    meilleurs = sorted(palmares.values(), key=lambda e: -e[0])[:5]
    juges = [(s, p, machine.juger(p)) for s, p in meilleurs]
    sortie = {"date": date, "piste": machine.piste, "minutes": minutes, "graine": graine, "essais": iterations,
              "victoires_tirees_au_sort": melange, "lambda": machine.lam, "lambda_force": machine.lambda_force,
              "tas": {"A": int(len(machine.lignes_a)), "B": int(len(machine.lignes_b))},
              "champions_hors_catalogue": machine.inconnus,
              "catalogue_fige": getattr(machine, "catalogue_fige", None),
              "depart": {"parametres": depart, "score_choix": score_depart, "score_jugement": jugement_depart.score},
              "historique": historique,
              "palmares": [{"rang": i + 1, "score_choix": s, "score_jugement": ev.score, "parametres": p,
                            "description": decrire(p, machine), "biais": ev.biais, "trop_rares": ev.rares}
                           for i, (s, p, ev) in enumerate(juges)]}
    (dossier / f"{base}.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    with gzip.open(dossier / f"{base}_essais.csv.gz", "wt", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(["essai", "secondes", "temperature", "score", "accepte", "changement", "parametres"])
        ecrivain.writerows(essais)
    if not melange:
        (dossier / f"dernier_recuit{numero}_{machine.piste}.json").write_text(
            json.dumps({"fichier": f"{base}.json"}, ensure_ascii=False) + "\n", encoding="utf-8")

    s, p, ev = juges[0]
    lignes = [f"# Recuit n° {numero}, piste {machine.piste}, du {date}" + (" (seuil de hasard)" if melange else ""), "",
              f"- {iterations} réglages essayés en {minutes:g} min (graine {graine}).",
              f"- A (choix) : {len(machine.lignes_a)} parties, notées en 5 rotations. B (jugement) : {len(machine.lignes_b)} "
              "parties, lues une fois à la fin. C n'a pas été lu.",
              "- Score = gain de prédiction par rapport à la seule force des champions, en millièmes. 0 = rien de plus ; "
              "négatif = ce qui a été appris ne tient pas.",
              f"- Départ : {score_depart:.3f} au choix, {jugement_depart.score:.3f} au jugement sur B.",
              f"- **Meilleur réglage : {s:.3f} au choix, {ev.score:.3f} au jugement sur B.**",
              "- À comparer au seuil de hasard (même recuit sur des victoires tirées au sort).", ""]
    if melange:
        lignes += ["Victoires tirées au sort : les taux ci-dessous ne décrivent pas de vraies parties.", ""]
    lignes += ["## Meilleur réglage", ""] + [f"- {x}" for x in decrire(p, machine)] + [""]
    familles = [("scenario", "Tes scénarios"), ("scenario_jungler", "Tes scénarios vus du jungler"), ("exploration", "Exploration")]
    for cle, titre in familles:
        groupe = [b for b in ev.biais if b["famille"] == cle]
        if not groupe and not any(r["famille"] == cle for r in (ev.rares or [])):
            continue
        if cle == "exploration":
            groupe = sorted(groupe, key=lambda b: -abs(b["coefficient"]))[:15]
            titre += " (les 15 effets les plus forts)"
        lignes += [f"## {titre}", ""] + [ligne_biais(b) for b in groupe]
        rares = [r for r in (ev.rares or []) if r["famille"] == cle]
        lignes += [f"- {r['nom']} : trop rare avec ce réglage ({r['parties_A']} parties de A, il en faut {MIN_PARTIES})" for r in rares]
        lignes += [""]
    lignes += ["## Les 5 meilleurs réglages", ""] + [
        f"- n° {i + 1} : {s_:.3f} au choix, {ev_.score:.3f} au jugement" for i, (s_, _, ev_) in enumerate(juges)] + [""]
    (dossier / f"{base}.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return dossier / f"{base}.md"


# --- Lancement ----------------------------------------------------------------------------------

def preparer(piste, regle, melanger=False, graine=0, catalogue=None):
    table = commun.drafts(regle)
    table = table[table["tas"].isin(["A", "B"])].reset_index(drop=True)
    if melanger:
        index = bloc2.Index(table)
        tout = np.arange(len(table))
        force = bloc3.Force(index, tout)
        force.decalages(tout, [])
        beta, c = force.apprendre(tout, force.lam)
        proba = bloc3.sigmoide(force.matrice(tout) @ beta + c)
        table["bleu_gagne"] = (np.random.default_rng(1000 + graine).random(len(table)) < proba).astype(int)
    return Machine(table, piste, catalogue or lire_catalogue())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--piste", choices=("scenarios", "teamfight"), required=True)
    parser.add_argument("--minutes", type=float, default=60)
    parser.add_argument("--graine", type=int, default=1)
    parser.add_argument("--essais", type=int)
    parser.add_argument("--melanger", action="store_true", help="seuil de hasard")
    parser.add_argument("--une-iteration", action="store_true")
    args = parser.parse_args()
    regle = commun.lire_decoupage()
    commun.exiger_validation(regle)
    if regle.get("version", 1) < 2:
        raise SystemExit("Le recuit n° 2 demande le découpage n° 2 (A choix, B jugement).")
    debut = time.time()
    machine = preparer(args.piste, regle, args.melanger, args.graine)
    print(f"Préparation : {time.time() - debut:.0f} s ; A = {len(machine.lignes_a)}, B = {len(machine.lignes_b)} ; "
          f"régularisation {machine.lam:g} ; scénarios étudiables au départ : {machine.min_scenarios} ; "
          f"champions hors catalogue : {len(machine.inconnus)}.")
    if args.une_iteration:
        t = time.time()
        s = machine.evaluer(DEPART[args.piste])
        ev = machine.juger(DEPART[args.piste])
        print(f"Départ : {s:.3f} au choix ({time.time() - t:.2f} s), {ev.score:.3f} au jugement, {ev.nb_variables} variables.")
        for b in [b for b in ev.biais if b["famille"] != "exploration"]:
            print(ligne_biais(b))
        for r in ev.rares:
            print(f"- {r['nom']} : trop rare ({r['parties_A']} parties de A)")
        return 0
    palmares, historique, n, essais = recuit(machine, args.minutes, args.graine, essais_max=args.essais)
    chemin = rapport(machine, palmares, historique, n, essais, args.minutes, args.graine, args.melanger)
    print(chemin.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
