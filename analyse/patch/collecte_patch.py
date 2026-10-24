"""Collecte légère pour « Identifier les champions forts du patch ».

Seulement le détail des parties (pas de timeline) : un appel par partie, environ deux fois plus de
parties par heure que la collecte principale. Seules les parties du patch visé sont gardées.
Écrit dans analyse/donnees_patch/<patch>/parties.csv et ecartees.csv (mêmes colonnes que la collecte
principale), en ajout seulement. Ne touche jamais à analyse/donnees/.

Bibliothèque standard seulement. Réutilise le client Riot et la conversion de analyse/collecte.py.

    RIOT_API_KEY=... python3 analyse/patch/collecte_patch.py
"""

import configparser
import csv
import json
import os
import random
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import collecte as c  # noqa: E402

CONFIG = ICI / "patch.ini"
DONNEES_PATCH = ICI.parent / "donnees_patch"


def lire_config(chemin=CONFIG):
    config = configparser.ConfigParser()
    config.read(chemin, encoding="utf-8")
    s = config["collecte"]
    return {
        "minutes": s.getint("minutes"),
        "sauvegarde_minutes": s.getint("sauvegarde_minutes", 0),
        "jours": s.getint("jours"),
        "patch": s.get("patch", "actuel").strip(),
        "paliers": [p.strip() for p in s["paliers"].split(",")],
        "divisions": [d.strip() for d in s["divisions"].split(",")],
        "joueurs_par_page": s.getint("joueurs_par_page"),
        "parties_par_joueur": s.getint("parties_par_joueur"),
        "pages_max": s.getint("pages_max"),
    }


def patch_actuel():
    with urllib.request.urlopen("https://ddragon.leagueoflegends.com/api/versions.json", timeout=30) as reponse:
        version = json.load(reponse)[0]
    return ".".join(version.split(".")[:2])


def deja_vus(dossier):
    vus = set()
    for nom in ("parties.csv", "ecartees.csv"):
        chemin = dossier / nom
        if chemin.exists():
            with open(chemin, encoding="utf-8", newline="") as fichier:
                lecteur = csv.reader(fichier, delimiter=";")
                next(lecteur, None)
                vus.update(ligne[0] for ligne in lecteur if ligne)
    return vus


def collecter(riot, reglages, patch, noms, parties, ecartees, vus, fin, sauvegarder=None):
    debut = int(time.time()) - reglages["jours"] * 86400
    pages_max = {(p, d): reglages["pages_max"] for p in reglages["paliers"] for d in reglages["divisions"]}
    compte = {"parties": 0, "autre_patch": 0, "ecartees": 0}
    temps_restant = c.chronometre(reglages, fin, sauvegarder)
    while temps_restant():
        cases = list(pages_max)
        random.shuffle(cases)
        for palier, division in cases:
            if not temps_restant():
                break
            page = random.randint(1, pages_max[(palier, division)])
            entrees = c.essayer(riot, c.PLATEFORME, f"/lol/league/v4/entries/RANKED_SOLO_5x5/{palier}/{division}", {"page": page})
            if entrees is c.RATE:
                continue
            if not entrees:
                pages_max[(palier, division)] = max(1, page // 2)
                continue
            code = c.INITIALE.get(palier, palier[:1]) + c.CHIFFRE.get(division, division)
            for entree in random.sample(entrees, min(reglages["joueurs_par_page"], len(entrees))):
                if not temps_restant():
                    break
                puuid = entree.get("puuid")
                if not puuid:
                    continue
                ids = c.essayer(riot, c.REGION, f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
                                {"queue": c.FILE_SOLO, "start": 0, "count": reglages["parties_par_joueur"], "startTime": debut})
                if ids is c.RATE:
                    continue
                for identifiant in ids or []:
                    court = identifiant.removeprefix(c.PREFIXE)
                    if court in vus or not temps_restant():
                        continue
                    match = c.essayer(riot, c.REGION, f"/lol/match/v5/matches/{identifiant}")
                    if match is c.RATE:
                        continue
                    vus.add(court)
                    if match is None:
                        ecartees.ecrire([court, "introuvable"])
                        compte["ecartees"] += 1
                        continue
                    ligne, raison = c.convertir(match, code, noms)
                    if ligne and ligne[1] != patch:
                        # Partie d'un autre patch : notée pour ne pas la retélécharger, jamais analysée.
                        ecartees.ecrire([court, f"patch_{ligne[1]}"])
                        compte["autre_patch"] += 1
                        continue
                    if ligne:
                        parties.ecrire(ligne)
                        compte["parties"] += 1
                        if compte["parties"] % 200 == 0:
                            print(f"{compte['parties']} parties du patch {patch}, {compte['autre_patch']} d'un autre patch, "
                                  f"{riot.appels} appels", flush=True)
                    else:
                        ecartees.ecrire([court, raison])
                        compte["ecartees"] += 1
    return compte


def main():
    reglages = lire_config()
    cle = os.environ.get("RIOT_API_KEY", "").strip()
    if not cle:
        print(f"::error::Clé Riot absente. {c.OU_METTRE_LA_CLE}")
        return 1
    patch = patch_actuel() if reglages["patch"] in ("", "actuel") else reglages["patch"]
    dossier = DONNEES_PATCH / patch
    dossier.mkdir(parents=True, exist_ok=True)
    (DONNEES_PATCH / "dernier_patch.txt").write_text(patch + "\n", encoding="utf-8")
    commande = os.environ.get("COMMANDE_SAUVEGARDE", "").strip()

    def sauvegarder():
        if subprocess.run(commande, shell=True).returncode != 0:
            print("::warning::Sauvegarde intermédiaire en échec, nouvel essai au prochain intervalle.", flush=True)

    noms = c.noms_des_champions()
    vus = deja_vus(dossier)
    parties = c.Journal(dossier / "parties.csv", c.COLONNES)
    ecartees = c.Journal(dossier / "ecartees.csv", ["match", "raison"])
    riot = c.Riot(cle)
    print(f"Patch {patch} : collecte pendant {reglages['minutes']} min ({', '.join(reglages['paliers'])}). "
          f"Déjà vues : {len(vus)} parties.", flush=True)
    try:
        compte = collecter(riot, reglages, patch, noms, parties, ecartees, vus,
                           time.monotonic() + reglages["minutes"] * 60, sauvegarder if commande else None)
    except c.CleRefusee as erreur:
        print(f"::error::{erreur} {c.OU_METTRE_LA_CLE}")
        return 1
    print(f"Terminé : {compte['parties']} parties du patch {patch} ajoutées, {compte['autre_patch']} d'un autre patch, "
          f"{compte['ecartees']} écartées, {riot.appels} appels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
