"""Recuit n° 3 : les règles de compo avec la classification du 27/10/2026 (11 types du catalogue unifié).

Les variables ne viennent que des types des 10 champions de la draft (les deux équipes) : aucun champion ne change
de type (pas de reclassement). Pour chaque équipe et chaque type, un score = somme, sur ses 5 champions, de
« a ce type » × le coefficient du type × le poids du poste, ramenée à des équivalents champions (5 champions = 5).

Ce que le recuit règle :
- le coefficient de chaque type (0,3 à 2 ; 1 au départ) ;
- le poids des postes : jungle, support, les 3 autres lanes ensemble ;
- le seuil « compo X » (score à atteindre, en équivalents champions ; 2 au départ).

Deux pistes :
- « styles » : les 10 scénarios relus avec le propriétaire le 27/10/2026, chacun avec son sens attendu ;
- « styles_libre » : sans scénarios, tous les croisements « type X chez nous contre type Y chez eux », le jungler
  de chaque type contre et avec chaque compo, et les compos de chaque type.
Garde-fou (piste styles) : un réglage qui laisse moins de scénarios étudiables (300 parties de A) qu'au départ est refusé.

Tas : ceux du découpage (A choix des réglages, B jugement, C jamais lu ici). Le catalogue utilisé est figé dans
le résultat (« catalogue_fige ») pour que la confirmation sur C rejoue exactement les mêmes types.

    python3 analyse/recuit/recuit_styles.py --piste styles --minutes 60 --graine 1 [--melanger]
"""

import argparse
import copy
import csv
import sys
import time

import numpy as np

import recuit_pistes as rp
import commun
import bloc2_compos as bloc2
import bloc3_biais as bloc3

TYPES = ("carry", "enchanteur", "assassin", "plongeur", "attrapeur", "tank", "hp", "bloqueur", "dueliste", "splitpusher", "teamfighter")
NOM = {"carry": "Carry", "enchanteur": "Enchanteur", "assassin": "Assassin", "plongeur": "Plongeur", "attrapeur": "Attrapeur",
       "tank": "Tank", "hp": "HP", "bloqueur": "Bloqueur", "dueliste": "Dueliste", "splitpusher": "Splitpusher",
       "teamfighter": "Teamfighter"}
K = {t: i for i, t in enumerate(TYPES)}
CATALOGUE = commun.ANALYSE / "catalogues" / "catalogue_unifie.csv"
NOTES = commun.ANALYSE / "types" / "resultats" / "notes.csv"
PISTES = ("styles", "styles_libre")
BORNES = {"lanes": (0.3, 2.0), "jgl": (0.5, 2.0), "sup": (0.0, 2.0), "seuil": (1.0, 3.0), "coef": (0.3, 2.0)}
DEPART = {"roles": {"lanes": 1.0, "jgl": 1.0, "sup": 1.0}, "seuil": 2.0, "coef": {t: 1.0 for t in TYPES}}
for _p in PISTES:
    rp.DEPART[_p] = DEPART


def lire_catalogue():
    """{champion: [types..., "fragile" s'il l'est]} : tous ses types du catalogue unifié, et « fragile » (notes.csv)."""
    fragiles = set()
    if NOTES.exists():
        with open(NOTES, encoding="utf-8", newline="") as f:
            fragiles = {l["champion"] for l in csv.DictReader(f, delimiter=";") if l.get("fragile") == "oui"}
    with open(CATALOGUE, encoding="utf-8", newline="") as f:
        return {l["champion"]: [t for t in TYPES if l.get(t) == "oui"] + (["fragile"] if l["champion"] in fragiles else [])
                for l in csv.DictReader(f, delimiter=";")}


class Machine(rp.Machine):
    numero = 3

    def __init__(self, table, piste, catalogue):
        self.piste, self.table = piste, table
        self.catalogue_fige = catalogue
        self.index = bloc2.Index(table)
        n = len(self.index.champions)
        self.a = np.zeros((n + 1, len(TYPES)))          # dernière ligne : champion inconnu (aucun type)
        self.fragile = np.zeros(n + 1)
        for i, c in enumerate(self.index.champions):
            for t in catalogue.get(c, []):
                if t in K:
                    self.a[i, K[t]] = 1
            self.fragile[i] = "fragile" in catalogue.get(c, [])
        self.inconnus = [c for c in self.index.champions if c not in catalogue]
        self.lignes_a = np.where(table["tas"] == "A")[0]
        self.lignes_b = np.where(table["tas"] == "B")[0]
        self.pli = bloc3.plis(len(self.lignes_a))
        force = bloc3.Force(self.index, self.lignes_a)
        self.dec_a, (self.dec_b,) = force.decalages(self.lignes_a, [self.lignes_b], pli=self.pli)
        self.lambda_force = force.lam
        self.ya, self.yb = self.index.y[self.lignes_a], self.index.y[self.lignes_b]
        self.mobiles = []
        self.min_scenarios = 0
        self.min_scenarios = self.nb_scenarios(DEPART)
        self.lam = 30.0
        self.lam = max(rp.LAMBDAS, key=lambda l: self._score_rotation(DEPART, l))

    # --- Les variables -------------------------------------------------------------------------------
    def variables(self, params, lignes):
        r = params["roles"]
        poids = np.array([r["lanes"], r["jgl"], r["lanes"], r["lanes"], r["sup"]])
        coef = np.array([params["coef"][t] for t in TYPES])
        seuil = params["seuil"]
        f = {}
        for cote in "br":
            e = self.index.equipes[cote][lignes]                     # (parties, 5 postes) : indices de champions
            a = self.a[e]                                            # (parties, 5, types)
            s = (a * poids[None, :, None]).sum(axis=1) * coef[None, :] * 5 / poids.sum()
            brut = a.sum(axis=1)                                     # nombre de champions de chaque type
            g = lambda *ts: sum(s[:, K[t]] for t in ts)
            f[cote] = {"s": s, "compo": s >= seuil, "brut": brut, "jgl": a[:, 1, :], "adc": a[:, 3, :], "sup": a[:, 4, :],
                       "menace": g("assassin", "plongeur", "attrapeur"), "protecteur": g("bloqueur", "enchanteur"),
                       "front": g("tank", "hp"), "fragiles": self.fragile[e].sum(axis=1)}
        b, rr = f["b"], f["r"]
        cols, vars_ = [], []

        def ajouter(fb, fr, famille, nom, sens=0):
            cols.append(rp.anti(fb, fr))
            vars_.append(rp.Variable(famille, nom, sens))

        if self.piste == "styles":
            # Les 10 scénarios du 27/10/2026, avec le sens attendu.
            ajouter((b["menace"] >= seuil) & (rr["protecteur"] < 1), (rr["menace"] >= seuil) & (b["protecteur"] < 1),
                    "scenario", "Dive : nos menaces contre une équipe sans protecteur", +1)
            ajouter((b["protecteur"] >= seuil) & (rr["menace"] >= seuil), (rr["protecteur"] >= seuil) & (b["menace"] >= seuil),
                    "scenario", "Peel : nos protecteurs contre leurs menaces", +1)
            ajouter((b["front"] >= seuil) & (rr["front"] <= seuil - 1), (rr["front"] >= seuil) & (b["front"] <= seuil - 1),
                    "scenario", "Frontline : Tank et HP contre une équipe qui en a peu", +1)
            sans = lambda x: (x["brut"][:, K["tank"]] == 0) & (x["brut"][:, K["hp"]] <= 1)
            ajouter(sans(b), sans(rr), "scenario", "Sans frontline : aucun Tank et au plus 1 HP", -1)
            protege = lambda x: (x["adc"][:, K["carry"]] == 1) & ((x["sup"][:, K["enchanteur"]] == 1) | (x["sup"][:, K["bloqueur"]] == 1))
            ajouter(protege(b), protege(rr), "scenario", "Carry protégé : Carry ADC avec un support Enchanteur ou Bloqueur", +1)
            ajouter((b["s"][:, K["carry"]] >= seuil) & (rr["menace"] >= seuil), (rr["s"][:, K["carry"]] >= seuil) & (b["menace"] >= seuil),
                    "scenario", "Deux carrys ou plus contre leurs menaces", -1)
            ajouter((b["s"][:, K["teamfighter"]] >= seuil + 1) & (rr["brut"][:, K["splitpusher"]] >= 1),
                    (rr["s"][:, K["teamfighter"]] >= seuil + 1) & (b["brut"][:, K["splitpusher"]] >= 1),
                    "scenario", "Teamfight (3 ou plus) contre splitpush", +1)
            side = lambda x, autre: (x["brut"][:, K["splitpusher"]] >= 1) & (x["brut"][:, K["dueliste"]] >= 1) & (autre["brut"][:, K["dueliste"]] == 0)
            ajouter(side(b, rr), side(rr, b), "scenario", "Side lane : Splitpusher et Dueliste contre une équipe sans Dueliste", +1)
            ajouter((b["fragiles"] >= 3) & (rr["menace"] >= seuil), (rr["fragiles"] >= 3) & (b["menace"] >= seuil),
                    "scenario", "Équipe fragile (3 ou plus) contre leurs menaces", -1)
            ajouter((b["s"][:, K["attrapeur"]] >= seuil) & (rr["fragiles"] >= 3), (rr["s"][:, K["attrapeur"]] >= seuil) & (b["fragiles"] >= 3),
                    "scenario", "Attrapeurs contre une équipe fragile", +1)
            plonge = lambda x: (x["jgl"][:, K["plongeur"]] == 1) | (x["jgl"][:, K["assassin"]] == 1)
            ajouter(plonge(b) & (rr["fragiles"] >= 3), plonge(rr) & (b["fragiles"] >= 3),
                    "scenario", "Jungler Plongeur ou Assassin contre une équipe fragile", +1)
            solide = lambda x: (x["jgl"][:, K["tank"]] == 1) | (x["jgl"][:, K["hp"]] == 1)
            ajouter(solide(b) & (b["s"][:, K["carry"]] >= seuil), solide(rr) & (rr["s"][:, K["carry"]] >= seuil),
                    "scenario", "Jungler Tank ou HP avec deux carrys", +1)
        else:
            # Sans scénarios : tous les croisements des types.
            n = len(TYPES)
            for x in range(n):
                ajouter(b["compo"][:, x], rr["compo"][:, x], "exploration", f"Compo {NOM[TYPES[x]]}")
            for x in range(n):
                for y in range(x + 1, n):
                    ajouter(b["compo"][:, x] & rr["compo"][:, y], rr["compo"][:, x] & b["compo"][:, y], "exploration",
                            f"Compo {NOM[TYPES[x]]} contre compo {NOM[TYPES[y]]}")
            for x in range(n):
                jb, jr = b["jgl"][:, x] == 1, rr["jgl"][:, x] == 1
                for y in range(n):
                    ajouter(jb & rr["compo"][:, y], jr & b["compo"][:, y], "exploration", f"Jungler {NOM[TYPES[x]]} contre compo {NOM[TYPES[y]]}")
                    ajouter(jb & b["compo"][:, y], jr & rr["compo"][:, y], "exploration", f"Jungler {NOM[TYPES[x]]} avec compo alliée {NOM[TYPES[y]]}")
            ajouter(b["fragiles"] >= 3, rr["fragiles"] >= 3, "exploration", "Équipe fragile (3 ou plus)")
        return np.column_stack(cols), vars_

    # --- Les réglages ---------------------------------------------------------------------------------
    def voisin_params(self, params, rng):
        p = copy.deepcopy(params)
        borne = lambda x, nom: min(max(x, BORNES[nom][0]), BORNES[nom][1])
        tirage = rng.random()
        if tirage < 0.30:
            poste = rng.choice(("lanes", "jgl", "sup"))
            p["roles"][poste] = round(borne(p["roles"][poste] + rng.gauss(0, 0.25), poste), 3)
            return p, f"poids {poste}"
        if tirage < 0.45:
            p["seuil"] = round(borne(p["seuil"] + rng.gauss(0, 0.2), "seuil"), 3)
            return p, "seuil"
        t = rng.choice(TYPES)
        p["coef"][t] = round(borne(p["coef"][t] + rng.gauss(0, 0.2), "coef"), 3)
        return p, f"coefficient {NOM[t]}"

    def decrire_params(self, params):
        r = params["roles"]
        return [f"Poids des postes : jungle {r['jgl']:.2f}, support {r['sup']:.2f}, autres lanes {r['lanes']:.2f} ; "
                f"seuil « compo X » : {params['seuil']:.2f} équivalents champions",
                "Coefficients des types : " + ", ".join(f"{NOM[t]} {params['coef'][t]:.2f}" for t in TYPES)]


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
    parser.add_argument("--piste", choices=PISTES, required=True)
    parser.add_argument("--minutes", type=float, default=60)
    parser.add_argument("--graine", type=int, default=1)
    parser.add_argument("--essais", type=int)
    parser.add_argument("--melanger", action="store_true", help="seuil de hasard")
    parser.add_argument("--une-iteration", action="store_true")
    args = parser.parse_args()
    regle = commun.lire_decoupage()
    commun.exiger_validation(regle)
    debut = time.time()
    machine = preparer(args.piste, regle, args.melanger, args.graine)
    print(f"Préparation : {time.time() - debut:.0f} s ; A = {len(machine.lignes_a)}, B = {len(machine.lignes_b)} ; "
          f"régularisation {machine.lam:g} ; scénarios étudiables au départ : {machine.min_scenarios} ; "
          f"champions hors catalogue : {len(machine.inconnus)}.", flush=True)
    if args.une_iteration:
        t = time.time()
        s = machine.evaluer(DEPART)
        ev = machine.juger(DEPART)
        print(f"Départ : {s:.3f} au choix ({time.time() - t:.2f} s), {ev.score:.3f} au jugement, {ev.nb_variables} variables.")
        for b in [b for b in ev.biais if b["famille"] != "exploration"]:
            print(rp.ligne_biais(b))
        for r in ev.rares:
            print(f"- {r['nom']} : trop rare ({r['parties_A']} parties de A)")
        return 0
    palmares, historique, n, essais = rp.recuit(machine, args.minutes, args.graine, essais_max=args.essais)
    chemin = rp.rapport(machine, palmares, historique, n, essais, args.minutes, args.graine, args.melanger)
    print(chemin.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
