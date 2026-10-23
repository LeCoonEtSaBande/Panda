"""Bloc 4 : le recuit simulé qui fait varier les paramètres des blocs 1 et 2 pour trouver des biais.

Boucle :
    paramètres -> bloc 1 (catalogue à l'instant T) -> bloc 2 (types de compo) -> bloc 3 (score sur B)
    -> on modifie un peu les paramètres -> on garde le changement s'il améliore le score, ou parfois
       même s'il l'empire (d'autant plus souvent que la « température » est haute, au début) pour
       sortir des optimums locaux -> la température baisse peu à peu.
On repart régulièrement d'un des meilleurs points trouvés, et on garde un palmarès des meilleurs
réglages (optimums locaux différents).

Le recuit n'utilise QUE les tas A (pour apprendre) et B (pour noter). Le tas C n'est jamais lu ici :
c'est confirmer.py qui le lit, une fois, à la fin.

    python3 analyse/iteratif/bloc4_recuit.py --minutes 60 --graine 1
    python3 analyse/iteratif/bloc4_recuit.py --une-iteration      # itération 0 : catalogue actuel

Résultats : analyse/iteratif/resultats/recuit_<date>.json et .md (et dernier_recuit.json).
"""

import argparse
import copy
import hashlib
import json
import math
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import commun
import bloc1_champions as bloc1
import bloc2_compos as bloc2
import bloc3_biais as bloc3

POSTES = bloc2.POSTES
TAILLE_PALMARES = 10

# Paramètres de départ (itération 0) : le catalogue actuel et l'équivalent de la règle actuelle.
DEPART = {
    "mode": "catalogue",
    "separer_tanks": False,
    "poids_secondaire": 0.5,
    "familles": {f: 1.0 for f in bloc1.FAMILLES},
    "nb_axes": 6,
    "k": 7,
    "deplacements": {},
    "roles": {p: 1.0 for p in POSTES},
    "seuil": 0.30,
    "lambda": 5.0,
}

# Bornes de chaque paramètre.
BORNES = {
    "poids_secondaire": (0.0, 1.0),
    "famille": (0.0, 3.0),
    "nb_axes": (3, 10),
    "k": (4, 12),
    "role": (0.0, 2.0),
    "role_jgl": (0.5, 2.0),   # la jungle reste toujours dans l'équation
    "seuil": (0.15, 0.60),
    "lambda": (0.3, 100.0),
    "deplacements_max": 10,
}
# Garde-fous contre un algorithme qui « triche » en faisant un groupe par champion :
# - chaque groupe doit garder au moins TAILLE_MIN_GROUPE champions (sinon le réglage est rejeté) ;
# - au plus 12 groupes, au plus 10 champions déplacés ;
# - une variable de biais n'est gardée que si sa situation apparaît dans au moins 50 parties de A ;
# - le score est mesuré sur B, que l'apprentissage n'a pas vu, et comparé au score que le même recuit
#   atteint sur des victoires mélangées au hasard (option --melanger) : seul l'écart compte.
TAILLE_MIN_GROUPE = 8


def borner(x, bornes):
    return min(max(x, bornes[0]), bornes[1])


def voisin(params, rng, champions):
    """Un petit changement aléatoire des paramètres. Renvoie (nouveaux paramètres, description)."""
    p = copy.deepcopy(params)
    tirage = rng.random()
    if tirage < 0.30:
        poste = rng.choice(POSTES)
        bornes = BORNES["role_jgl"] if poste == "jgl" else BORNES["role"]
        p["roles"][poste] = round(borner(p["roles"][poste] + rng.gauss(0, 0.25), bornes), 3)
        return p, f"poids {poste}"
    if tirage < 0.40:
        p["seuil"] = round(borner(p["seuil"] + rng.gauss(0, 0.04), BORNES["seuil"]), 3)
        return p, "seuil"
    if tirage < 0.48:
        p["lambda"] = round(borner(p["lambda"] * math.exp(rng.gauss(0, 0.4)), BORNES["lambda"]), 3)
        return p, "lambda"
    if tirage < 0.62:
        # Déplacer un champion d'un groupe à l'autre : le catalogue évolue.
        if len(p["deplacements"]) >= BORNES["deplacements_max"] and rng.random() < 0.5:
            p["deplacements"].pop(rng.choice(sorted(p["deplacements"])))
            return p, "retour d'un champion dans son groupe"
        champion = rng.choice(champions)
        k = p["k"] if p["mode"] == "mesure" else (6 + int(p["separer_tanks"]))
        p["deplacements"][champion] = rng.randrange(k)
        return p, f"déplacement de {champion}"
    # Changements du bloc 1 lui-même : les déplacements n'ont plus de sens, on les efface.
    p["deplacements"] = {}
    if tirage < 0.67:
        p["mode"] = "mesure" if p["mode"] == "catalogue" else "catalogue"
        return p, f"mode {p['mode']}"
    if p["mode"] == "catalogue":
        if rng.random() < 0.5:
            p["separer_tanks"] = not p["separer_tanks"]
            return p, "séparer les tanks"
        p["poids_secondaire"] = round(borner(p["poids_secondaire"] + rng.gauss(0, 0.15), BORNES["poids_secondaire"]), 3)
        return p, "poids du secondaire"
    choix = rng.random()
    if choix < 0.6:
        famille = rng.choice(sorted(p["familles"]))
        p["familles"][famille] = round(borner(p["familles"][famille] + rng.gauss(0, 0.4), BORNES["famille"]), 3)
        return p, f"famille {famille}"
    if choix < 0.8:
        p["k"] = int(borner(p["k"] + rng.choice((-1, 1)), BORNES["k"]))
        return p, "nombre de groupes"
    p["nb_axes"] = int(borner(p["nb_axes"] + rng.choice((-1, 1)), BORNES["nb_axes"]))
    return p, "nombre d'axes"


def signature(params):
    return hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]


def signature_bloc1(params):
    cles = ("mode", "separer_tanks", "familles", "nb_axes", "k") if params["mode"] == "mesure" else ("mode", "separer_tanks")
    return json.dumps({c: params[c] for c in cles}, sort_keys=True)


class Machine:
    """Données préparées une fois ; evaluer(params) fait tourner les blocs 1, 2 et 3."""

    def __init__(self, table, mesures, apprentissage=("A",), evaluation=("B",)):
        self.table = table
        self.mesures = mesures
        self.index = bloc2.Index(table)
        # « lignes_a » : parties pour apprendre ; « lignes_b » : parties pour noter.
        # Recuit : A puis B. Confirmation : A + B puis C.
        self.lignes_a = np.where(table["tas"].isin(apprentissage))[0]
        self.lignes_b = np.where(table["tas"].isin(evaluation))[0]
        force = bloc3.Force(self.index, self.lignes_a)
        self.dec_a, (self.dec_b,) = force.decalages(self.lignes_a, [self.lignes_b])
        self.lambda_force = force.lam
        self.cache_bloc1 = {}
        self.champions = sorted(set(mesures["champion"]))

    def catalogue(self, params):
        cle = signature_bloc1(params)
        if cle not in self.cache_bloc1:
            if len(self.cache_bloc1) > 200:
                self.cache_bloc1.clear()
            base = dict(params, deplacements={})
            self.cache_bloc1[cle] = bloc1.construire(base, self.mesures)
        cat = copy.copy(self.cache_bloc1[cle])
        cat.groupe = dict(cat.groupe)
        deplacements = params.get("deplacements", {})
        for champion, cible in deplacements.items():
            if champion in cat.groupe and 0 <= cible < cat.k:
                cat.groupe[champion] = cible
        if deplacements:
            membres = {}
            for champion, g in sorted(cat.groupe.items()):
                membres.setdefault(cat.noms[g], []).append(champion)
            cat.membres_texte = {n: ", ".join(m) for n, m in membres.items()}
        return cat

    def evaluer(self, params, avec_biais=False):
        cat = self.catalogue(params)
        tailles = np.bincount(list(cat.groupe.values()), minlength=cat.k)
        if tailles.min() < TAILLE_MIN_GROUPE:
            return bloc3.Evaluation(score=-1e9, score_a=-1e9, biais=[], nb_variables=0), cat
        compos = bloc2.construire(cat, self.index, params)
        ev = bloc3.evaluer(compos, self.index, self.lignes_a, self.lignes_b, self.dec_a, self.dec_b,
                           params["lambda"], avec_biais=avec_biais)
        return ev, cat


def recuit(machine, minutes, graine=1, depart=None, journal=print, t0=0.30, t_fin=0.005):
    """Recuit simulé pendant `minutes`. Renvoie (palmarès, historique)."""
    rng = random.Random(graine)
    courant = copy.deepcopy(depart or DEPART)
    score_courant = machine.evaluer(courant)[0].score
    palmares = {signature(courant): (score_courant, courant)}
    historique = []
    debut = time.time()
    duree = 60 * minutes
    iteration, sans_progres, meilleur = 0, 0, score_courant
    while time.time() - debut < duree:
        iteration += 1
        avance = (time.time() - debut) / duree
        temperature = t0 * (t_fin / t0) ** avance
        candidat, changement = voisin(courant, rng, machine.champions)
        try:
            score = machine.evaluer(candidat)[0].score
        except (np.linalg.LinAlgError, ValueError):
            continue
        if score >= score_courant or rng.random() < math.exp((score - score_courant) / temperature):
            courant, score_courant = candidat, score
        sig = signature(candidat)
        if len(palmares) < 5 * TAILLE_PALMARES or score > min(s for s, _ in palmares.values()):
            palmares[sig] = (score, candidat)
            if len(palmares) > 5 * TAILLE_PALMARES:
                palmares.pop(min(palmares, key=lambda k: palmares[k][0]))
        if score > meilleur + 1e-9:
            meilleur, sans_progres = score, 0
        else:
            sans_progres += 1
        # Redémarrage depuis un des meilleurs réglages quand on tourne en rond.
        if sans_progres > 400:
            choix = sorted(palmares.values(), key=lambda e: -e[0])[:TAILLE_PALMARES]
            score_courant, courant = rng.choice(choix)
            courant = copy.deepcopy(courant)
            sans_progres = 0
        if iteration % 50 == 0:
            historique.append({"iteration": iteration, "secondes": round(time.time() - debut),
                               "temperature": round(temperature, 4), "courant": round(score_courant, 4),
                               "meilleur": round(meilleur, 4)})
        if iteration % 500 == 0:
            journal(f"{iteration} essais, {round(time.time() - debut)} s : meilleur {meilleur:.3f}, "
                    f"courant {score_courant:.3f} (dernier changement : {changement})")
    return palmares, historique, iteration


def resume_reglage(params, cat):
    roles = ", ".join(f"{p} {params['roles'][p]:.2f}" for p in POSTES)
    texte = [f"Catalogue : {params['mode']}" + (f", {cat.k} groupes, {params['nb_axes']} axes" if params["mode"] == "mesure" else
                                                 (" (tanks séparés)" if params["separer_tanks"] else "")),
             f"Poids des postes : {roles} ; seuil de compo {params['seuil']:.2f} ; régularisation {params['lambda']:.2f}"]
    if params["mode"] == "mesure":
        texte.append("Poids des familles : " + ", ".join(f"{f} {v:.2f}" for f, v in params["familles"].items()))
    if params["deplacements"]:
        texte.append("Champions déplacés : " + ", ".join(f"{c} -> {cat.noms[g]}" for c, g in sorted(params["deplacements"].items()) if g < cat.k))
    return texte


def rapport(machine, palmares, historique, iterations, minutes, graine, dossier=commun.RESULTATS, melange=False):
    """Écrit le JSON complet et un résumé lisible, pour les meilleurs réglages distincts."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M") + ("_hasard" if melange else "")
    depart_ev, _ = machine.evaluer(DEPART)
    meilleurs = sorted(palmares.values(), key=lambda e: -e[0])
    retenus, vus = [], set()
    for score, params in meilleurs:
        ev, cat = machine.evaluer(params, avec_biais=True)
        cle = json.dumps(sorted(cat.groupe.items())) + str(round(score, 2))
        if cle in vus:
            continue
        vus.add(cle)
        retenus.append((params, ev, cat))
        if len(retenus) >= TAILLE_PALMARES:
            break
    sortie = {
        "date": date, "minutes": minutes, "graine": graine, "essais": iterations, "victoires_melangees": melange,
        "tas": {"A": int(len(machine.lignes_a)), "B": int(len(machine.lignes_b))},
        "score_depart": depart_ev.score,
        "historique": historique,
        "palmares": [{
            "rang": i + 1, "score_B": ev.score, "score_A": ev.score_a, "parametres": params,
            "groupes": cat.membres_texte, "biais": ev.biais[:40],
        } for i, (params, ev, cat) in enumerate(retenus)],
    }
    chemin = dossier / f"recuit_{date}.json"
    chemin.write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if not melange:
        (dossier / "dernier_recuit.json").write_text(json.dumps({"fichier": chemin.name}, ensure_ascii=False) + "\n", encoding="utf-8")
    lignes = [f"# Recuit simulé du {date}", "",
              f"- {iterations} réglages essayés en {minutes} min (graine {graine}).",
              f"- Tas : A = {len(machine.lignes_a)} parties pour apprendre, B = {len(machine.lignes_b)} pour noter. C n'a pas été lu.",
              f"- Score = baisse de la perte logarithmique sur B, en millièmes, par rapport à la seule force des champions. "
              f"0 = aucun biais utile.",
              f"- Score du départ (catalogue actuel, règle actuelle) : {depart_ev.score:.3f} sur B ({depart_ev.score_a:.3f} sur A).", ""]
    for i, (params, ev, cat) in enumerate(retenus[:5]):
        lignes += [f"## Réglage n° {i + 1} : score {ev.score:.3f} sur B ({ev.score_a:.3f} sur A)", ""]
        lignes += [f"- {t}" for t in resume_reglage(params, cat)]
        lignes += ["", "Biais les plus forts (à confirmer sur C) :", ""]
        tenus = [b for b in ev.biais if not b["genre"].startswith("capacite") and b["taux_B"] == b["taux_B"]
                 and (b["taux_A"] - 0.5) * (b["taux_B"] - 0.5) > 0][:8]
        lignes += [f"- {bloc3.phrase(b)}" for b in tenus] or ["- aucun biais retrouvé dans le même sens sur A et B"]
        lignes += ["", "Groupes :", ""] + [f"- **{n}** : {m}" for n, m in cat.membres_texte.items()] + [""]
    (dossier / f"recuit_{date}.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return chemin


def preparer(regle=None, melanger=False, graine=0):
    """Données des tas A et B. `melanger` : les victoires sont tirées au hasard (même proportion),
    pour mesurer jusqu'où le recuit monte sur du pur hasard (le seuil à dépasser)."""
    regle = regle or commun.lire_decoupage()
    table = commun.drafts(regle)
    table = table[table["tas"].isin(["A", "B"])].reset_index(drop=True)
    if melanger:
        rng = np.random.default_rng(graine)
        table["bleu_gagne"] = rng.permutation(table["bleu_gagne"].to_numpy())
    return Machine(table, bloc1.lire_mesures())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=60)
    parser.add_argument("--graine", type=int, default=1)
    parser.add_argument("--une-iteration", action="store_true")
    parser.add_argument("--sans-validation", action="store_true", help="essai local avant validation du découpage")
    parser.add_argument("--melanger", action="store_true", help="victoires mélangées : mesure du score atteint par hasard")
    args = parser.parse_args()
    regle = commun.lire_decoupage()
    if not args.sans_validation:
        commun.exiger_validation(regle)
    debut = time.time()
    machine = preparer(regle, melanger=args.melanger, graine=args.graine)
    print(f"Préparation : {time.time() - debut:.0f} s ; A = {len(machine.lignes_a)}, B = {len(machine.lignes_b)} parties.")
    if args.une_iteration:
        t = time.time()
        ev, cat = machine.evaluer(DEPART, avec_biais=True)
        print(f"Itération 0 (catalogue actuel) : score {ev.score:.3f} sur B, {ev.score_a:.3f} sur A, "
              f"{ev.nb_variables} variables, {time.time() - t:.2f} s.")
        for b in ev.biais[:15]:
            print(" -", bloc3.phrase(b))
        return 0
    palmares, historique, n = recuit(machine, args.minutes, args.graine)
    chemin = rapport(machine, palmares, historique, n, args.minutes, args.graine, melange=args.melanger)
    print(f"Recuit terminé : {n} essais, résultats dans {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
