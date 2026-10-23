"""Contrôle des données (bibliothèque standard uniquement).

Parties complètes, couverture de la timeline, cohérence des 10 joueurs avec parties.csv,
durées aberrantes, kills des événements contre le total Riot, recouvrement avec l'archive.
Écrit analyse/resultats/controle_donnees.csv : mesure, valeur, statut (ok / attention / probleme).
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import lecture

ICI = Path(__file__).resolve().parent
RESULTATS = ICI / "resultats"
ARCHIVE = ICI.parent / "archives" / "2026-10-22_avant_details" / "parties.csv"
POSTES = ("top", "jgl", "mid", "adc", "sup")
DUREE_COURTE_S = 15 * 60
DUREE_LONGUE_S = 60 * 60


def _entier(texte):
    try:
        return int(float(texte))
    except (TypeError, ValueError):
        return None


def lire_parties(donnees):
    chemin = Path(donnees) / "parties.csv"
    with open(chemin, encoding="utf-8", newline="") as fichier:
        return list(csv.DictReader(fichier, delimiter=";"))


def controler(donnees=lecture.DONNEES, archive=None):
    """Liste de [mesure, valeur, statut]."""
    sortie = []

    def noter(mesure, valeur, statut="ok"):
        sortie.append([mesure, valeur, statut])

    parties = lire_parties(donnees)
    identifiants = [p["match"] for p in parties]
    doublons = len(identifiants) - len(set(identifiants))
    noter("lignes parties.csv", len(parties))
    noter("doublons parties.csv", doublons, "probleme" if doublons else "ok")

    completes = lecture.matchs_avec_details(donnees)
    sans_details = set(identifiants) - completes
    noter("parties completes (parties.csv et details_parties)", len(completes))
    noter("parties.csv sans details", len(sans_details), "attention" if sans_details else "ok")
    avec_timeline = completes & lecture.matchs_presents("timeline_joueurs", donnees)
    avec_evenements = completes & lecture.matchs_presents("evenements", donnees)
    noter("parties completes sans timeline", len(completes - avec_timeline),
          "attention" if len(completes - avec_timeline) > 0.01 * max(1, len(completes)) else "ok")
    noter("parties avec timeline mais sans evenement", len(avec_timeline - avec_evenements),
          "attention" if avec_timeline - avec_evenements else "ok")

    # Joueurs : 10 par partie, mêmes champions aux mêmes postes que parties.csv.
    attendu = {p["match"]: {(c, poste): p[f"{c}_{poste}"] for c in "br" for poste in POSTES} for p in parties}
    joueurs = defaultdict(dict)
    participants = defaultdict(set)
    for j in lecture.lire_details("joueurs", donnees, matchs=completes):
        joueurs[j["match"]][(j["equipe"], j["poste"])] = j["champion"]
        participants[j["match"]].add(j["participant"])
    pas_dix = sum(1 for m in completes if len(joueurs.get(m, {})) != 10 or len(participants.get(m, ())) != 10)
    differences = sum(1 for m in completes if joueurs.get(m, {}) != attendu.get(m))
    noter("parties sans 10 joueurs distincts", pas_dix, "probleme" if pas_dix else "ok")
    noter("parties dont les champions different de parties.csv", differences, "probleme" if differences else "ok")

    # Timeline : 10 participants.
    timeline = Counter(t["match"] for t in lecture.lire_details("timeline_joueurs", donnees, matchs=avec_timeline))
    noter("timelines sans 10 participants", sum(1 for n in timeline.values() if n != 10),
          "probleme" if any(n != 10 for n in timeline.values()) else "ok")

    # Durées.
    durees = {}
    kills_riot = {}
    surrender = 0
    for d in lecture.lire_details("details_parties", donnees, matchs=completes):
        durees[d["match"]] = _entier(d["duree_s"])
        surrender += d["fin_surrender"] == "1"
        kills_riot[d["match"]] = (_entier(d["b_champion_nb"]), _entier(d["r_champion_nb"]))
    valeurs = sorted(v for v in durees.values() if v is not None)
    noter("durees absentes", sum(v is None for v in durees.values()), "probleme" if None in durees.values() else "ok")
    if valeurs:
        noter("duree mediane (min)", round(valeurs[len(valeurs) // 2] / 60, 1))
        noter("duree minimale (min)", round(valeurs[0] / 60, 1))
        noter("duree maximale (min)", round(valeurs[-1] / 60, 1))
    courtes = sum(1 for v in valeurs if v < DUREE_COURTE_S)
    noter("parties de moins de 15 min (ecartees des analyses de timing)", courtes)
    noter("parties de plus de 60 min", sum(1 for v in valeurs if v > DUREE_LONGUE_S),
          "attention" if any(v > DUREE_LONGUE_S for v in valeurs) else "ok")
    noter("parties finies par abandon", surrender)

    # Kills : événements CHAMPION_KILL contre le total Riot par équipe.
    kills_evenements = defaultdict(Counter)
    executions = Counter()
    for e in lecture.lire_details("evenements", donnees, matchs=avec_evenements):
        if e["type"] == "CHAMPION_KILL":
            kills_evenements[e["match"]][e["equipe"]] += 1
            executions[e["match"]] += e["participant"] == "0"
    ecarts = [
        m for m in avec_evenements
        if kills_riot.get(m) and None not in kills_riot[m]
        and (kills_evenements[m]["b"], kills_evenements[m]["r"]) != kills_riot[m]
    ]
    # Constaté le 23/10 : tous les écarts (1 ou 2 kills) viennent de parties avec une exécution
    # (participant 0), que Riot ne compte pas toujours. Seuls les autres écarts sont un problème.
    inexpliques = sum(1 for m in ecarts if not executions[m])
    noter("parties dont les kills des evenements different du total Riot (avec execution)", len(ecarts) - inexpliques)
    noter("parties dont les kills des evenements different du total Riot (sans execution)", inexpliques,
          "probleme" if inexpliques else "ok")

    noter("patchs", " ".join(f"{p}:{n}" for p, n in sorted(Counter(p["patch"] for p in parties).items())))
    noter("rangs", " ".join(f"{r}:{n}" for r, n in sorted(Counter(p["palier"][:1] for p in parties).items())))

    # L'archive n'est lue qu'en local (option --archive), jamais par le rapport.
    if archive and Path(archive).exists():
        with open(archive, encoding="utf-8", newline="") as fichier:
            anciens = {ligne["match"] for ligne in csv.DictReader(fichier, delimiter=";")}
        commun = len(anciens & set(identifiants))
        noter("parties presentes aussi dans l'archive du 22/10", commun, "attention" if commun else "ok")
    return sortie


def main(archive=False):
    if not (lecture.DONNEES / "parties.csv").exists():
        print("Contrôle : aucune partie.")
        return 0
    sortie = controler(archive=ARCHIVE if archive else None)
    RESULTATS.mkdir(exist_ok=True)
    with open(RESULTATS / "controle_donnees.csv", "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(["mesure", "valeur", "statut"])
        ecrivain.writerows(sortie)
    alertes = [ligne for ligne in sortie if ligne[2] != "ok"]
    print(f"Contrôle : {len(sortie)} mesures, {len(alertes)} alerte(s).")
    for ligne in alertes:
        print(f"  {ligne[2]} : {ligne[0]} = {ligne[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(archive="--archive" in sys.argv))
