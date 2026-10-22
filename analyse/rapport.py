"""Taux de victoire de chaque jungle, scénario adverse par scénario adverse."""

import configparser
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from regle import charger_catalogue, correspond, etiqueter

ICI = Path(__file__).resolve().parent
CONFIG = ICI / "collecte.ini"
PARTIES = ICI / "donnees" / "parties.csv"
ECARTEES = ICI / "donnees" / "ecartees.csv"
SCENARIOS = ICI / "scenarios_a_tester.json"
RESULTATS = ICI / "resultats"

POOL = ("Fiddlesticks", "Ivern", "Dr. Mundo", "Kayn bleu", "Kayn rouge")
POSTES = ("top", "jgl", "mid", "adc", "sup")


def wilson(victoires, parties, z=1.96):
    if parties == 0:
        return 0.0, 0.0
    p = victoires / parties
    centre = p + z * z / (2 * parties)
    marge = z * math.sqrt(p * (1 - p) / parties + z * z / (4 * parties * parties))
    diviseur = 1 + z * z / parties
    return (centre - marge) / diviseur, (centre + marge) / diviseur


def pourcent(valeur):
    return f"{100 * valeur:.1f}"


def lire_parties(patch):
    with open(PARTIES, encoding="utf-8", newline="") as fichier:
        lignes = list(csv.DictReader(fichier, delimiter=";"))
    if patch != "tous":
        lignes = [ligne for ligne in lignes if ligne["patch"] == patch]
    return lignes


def observations(lignes, catalogue):
    """Chaque partie donne deux observations : chaque équipe face à l'autre."""
    resultat = []
    hors_catalogue = 0
    for ligne in lignes:
        equipes = {cote: [ligne[f"{cote}_{poste}"] for poste in POSTES] for cote in ("b", "r")}
        if any(nom not in catalogue for equipe in equipes.values() for nom in equipe):
            hors_catalogue += 1
            continue
        etiquettes = {cote: etiqueter(equipe, catalogue) for cote, equipe in equipes.items()}
        for cote, autre in (("b", "r"), ("r", "b")):
            resultat.append({
                "jungle": ligne[f"{cote}_jgl"],
                "victoire": ligne["gagnant"] == cote,
                "allie": etiquettes[cote],
                "adverse": etiquettes[autre],
            })
    return resultat, hors_catalogue


def ecrire_csv(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(entete)
        ecrivain.writerows(lignes)


def volume_details(donnees=None):
    """Parties de parties.csv avec détails et avec timeline. Ne fait jamais échouer le rapport."""
    try:
        import lecture

        donnees = donnees or lecture.DONNEES
        avec_details = lecture.matchs_avec_details(donnees)
        avec_timeline = avec_details & lecture.matchs_presents("timeline_joueurs", donnees)
        return [["avec_details", len(avec_details)], ["avec_timeline", len(avec_timeline)]]
    except Exception as erreur:  # noqa: BLE001
        print(f"Volume des détails : sauté ({type(erreur).__name__} : {erreur}).")
        return []


def main():
    if not PARTIES.exists():
        print("Aucune partie collectée pour l'instant.")
        return 0

    config = configparser.ConfigParser()
    config.read(CONFIG, encoding="utf-8")
    patch = config.get("rapport", "patch", fallback="tous")
    parties_min = config.getint("rapport", "parties_min", fallback=30)

    catalogue = charger_catalogue()
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    lignes = lire_parties(patch)
    obs, hors_catalogue = observations(lignes, catalogue)

    global_jungle = defaultdict(lambda: [0, 0])
    for o in obs:
        global_jungle[o["jungle"]][0] += 1
        global_jungle[o["jungle"]][1] += o["victoire"]

    sortie = []
    for scenario in scenarios:
        retenues = [
            o for o in obs
            if correspond(o["adverse"], scenario.get("adverse", {}))
            and correspond(o["allie"], scenario.get("allie", {}))
        ]
        frequence = len(retenues) / len(obs) if obs else 0.0
        par_jungle = defaultdict(lambda: [0, 0])
        for o in retenues:
            par_jungle[o["jungle"]][0] += 1
            par_jungle[o["jungle"]][1] += o["victoire"]

        lignes_scenario = []
        for jungle in set(par_jungle) | set(POOL):
            parties, victoires = par_jungle.get(jungle, (0, 0))
            dans_pool = jungle in POOL
            if not dans_pool and parties < parties_min:
                continue
            total, gagnees = global_jungle.get(jungle, (0, 0))
            taux = victoires / parties if parties else 0.0
            taux_jungle = gagnees / total if total else 0.0
            bas, haut = wilson(victoires, parties)
            lignes_scenario.append((
                not dans_pool,
                -(taux - taux_jungle) if parties else 1.0,
                [
                    scenario["id"], jungle, "oui" if dans_pool else "non", parties, victoires,
                    pourcent(taux) if parties else "", pourcent(taux_jungle) if total else "",
                    f"{100 * (taux - taux_jungle):+.1f}" if parties and total else "",
                    pourcent(bas) if parties else "", pourcent(haut) if parties else "",
                    pourcent(frequence),
                ],
            ))
        lignes_scenario.sort(key=lambda element: (element[0], element[1]))
        sortie.extend(ligne for *_, ligne in lignes_scenario)

    RESULTATS.mkdir(exist_ok=True)
    ecrire_csv(
        RESULTATS / "scenarios.csv",
        ["scenario", "jungle", "pool", "parties", "victoires", "taux", "taux_jungle", "ecart", "bas_95", "haut_95", "frequence_scenario"],
        sortie,
    )

    volume = [["parties", len(lignes)], ["hors_catalogue", hors_catalogue], ["observations", len(obs)]]
    with open(PARTIES, encoding="utf-8", newline="") as fichier:
        toutes = list(csv.DictReader(fichier, delimiter=";"))
    volume += [[f"patch {p}", n] for p, n in sorted(Counter(l["patch"] for l in toutes).items())]
    volume += [[f"palier {p}", n] for p, n in sorted(Counter(l["palier"] for l in toutes).items())]
    volume += [[f"jungle {j}", n] for j, n in sorted(Counter(o["jungle"] for o in obs if o["jungle"] in POOL).items())]
    if ECARTEES.exists():
        with open(ECARTEES, encoding="utf-8", newline="") as fichier:
            raisons = Counter(l["raison"] for l in csv.DictReader(fichier, delimiter=";"))
        volume += [[f"ecartee {r}", n] for r, n in sorted(raisons.items())]
    volume += volume_details()
    ecrire_csv(RESULTATS / "volume.csv", ["mesure", "nombre"], volume)
    print(f"Rapport : {len(lignes)} parties, {len(obs)} observations, {len(scenarios)} scénarios.")

    # Les analyses par profil ne doivent jamais faire échouer le rapport.
    for nom in ("profils", "compos"):
        try:
            __import__(nom).main()
        except Exception as erreur:  # noqa: BLE001
            print(f"{nom} : analyse sautée ({type(erreur).__name__} : {erreur}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
