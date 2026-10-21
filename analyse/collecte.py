"""Collecte des parties classées solo EUW, une ligne par partie, écrite dès réception."""

import configparser
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

ICI = Path(__file__).resolve().parent
CONFIG = ICI / "collecte.ini"
DONNEES = ICI / "donnees"
PARTIES = DONNEES / "parties.csv"
ECARTEES = DONNEES / "ecartees.csv"

PLATEFORME = "https://euw1.api.riotgames.com"
REGION = "https://europe.api.riotgames.com"
PREFIXE = "EUW1_"
FILE_SOLO = 420
DUREE_REMAKE = 300
POSTES = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")
COLONNES = ["match", "patch", "palier", "gagnant"] + [
    f"{cote}_{poste}" for cote in ("b", "r") for poste in ("top", "jgl", "mid", "adc", "sup")
]
KAYN_ID = 141
KAYN = {1: "Kayn rouge", 2: "Kayn bleu"}
INITIALE = {"IRON": "F", "BRONZE": "B", "SILVER": "S", "GOLD": "G", "PLATINUM": "P", "EMERALD": "E", "DIAMOND": "D"}
CHIFFRE = {"I": "1", "II": "2", "III": "3", "IV": "4"}


class CleRefusee(Exception):
    pass


class Limiteur:
    """Fenêtres glissantes « n appels par s secondes », réglées par les en-têtes Riot."""

    def __init__(self, fenetres=((20, 1), (100, 120))):
        self.fenetres = list(fenetres)
        self.appels = deque()

    def regler(self, entete):
        fenetres = []
        for morceau in entete.split(","):
            nombre, secondes = morceau.split(":")
            fenetres.append((int(nombre), int(secondes)))
        if fenetres:
            self.fenetres = fenetres

    def attendre(self):
        while True:
            maintenant = time.monotonic()
            horizon = max(secondes for _, secondes in self.fenetres)
            while self.appels and maintenant - self.appels[0] >= horizon:
                self.appels.popleft()
            attente = 0.0
            for nombre, secondes in self.fenetres:
                recents = [t for t in self.appels if maintenant - t < secondes]
                if len(recents) >= nombre:
                    attente = max(attente, secondes - (maintenant - recents[-nombre]) + 0.05)
            if attente <= 0:
                self.appels.append(maintenant)
                return
            time.sleep(attente)


class Riot:
    def __init__(self, cle):
        self.cle = cle
        self.limiteurs = {}
        self.appels = 0

    def get(self, base, chemin, params=None):
        limiteur = self.limiteurs.setdefault(base, Limiteur())
        url = base + chemin + ("?" + urllib.parse.urlencode(params) if params else "")
        for essai in range(6):
            limiteur.attendre()
            requete = urllib.request.Request(url, headers={"X-Riot-Token": self.cle, "User-Agent": "panda-collecte"})
            try:
                with urllib.request.urlopen(requete, timeout=30) as reponse:
                    self.appels += 1
                    entete = reponse.headers.get("X-App-Rate-Limit")
                    if entete:
                        limiteur.regler(entete)
                    return json.load(reponse)
            except urllib.error.HTTPError as erreur:
                self.appels += 1
                if erreur.code in (401, 403):
                    raise CleRefusee(f"Riot refuse la clé ({erreur.code}).") from erreur
                if erreur.code == 404:
                    return None
                if erreur.code == 429:
                    time.sleep(int(erreur.headers.get("Retry-After") or 10))
                    continue
                if erreur.code >= 500:
                    time.sleep(2**essai)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError):
                time.sleep(2**essai)
        raise RuntimeError(f"Riot ne répond plus sur {chemin}")


def noms_des_champions():
    with urllib.request.urlopen("https://ddragon.leagueoflegends.com/api/versions.json", timeout=30) as reponse:
        version = json.load(reponse)[0]
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
    with urllib.request.urlopen(url, timeout=30) as reponse:
        donnees = json.load(reponse)["data"]
    return {int(fiche["key"]): fiche["name"] for fiche in donnees.values()}


def convertir(match, palier, noms):
    """Une partie devient une ligne, ou une raison d'être écartée."""
    info = match["info"]
    if info.get("queueId") != FILE_SOLO:
        return None, "file"
    joueurs = info.get("participants", [])
    if len(joueurs) != 10:
        return None, "joueurs"
    if info.get("gameDuration", 0) < DUREE_REMAKE or any(j.get("gameEndedInEarlySurrender") for j in joueurs):
        return None, "remake"

    equipes = {100: {}, 200: {}}
    for joueur in joueurs:
        equipe = equipes.get(joueur.get("teamId"))
        poste = joueur.get("teamPosition")
        if equipe is None or poste not in POSTES or poste in equipe:
            return None, "postes"
        if joueur["championId"] == KAYN_ID:
            nom = KAYN.get(joueur.get("championTransform"))
            if nom is None:
                return None, "kayn_sans_forme"
        else:
            nom = noms.get(joueur["championId"], f"?{joueur['championId']}")
        equipe[poste] = nom

    gagnant = next((equipe["teamId"] for equipe in info.get("teams", []) if equipe.get("win")), None)
    if gagnant not in equipes:
        return None, "sans_vainqueur"

    patch = ".".join(info.get("gameVersion", "").split(".")[:2])
    identifiant = match["metadata"]["matchId"].removeprefix(PREFIXE)
    ligne = [identifiant, patch, palier, "b" if gagnant == 100 else "r"]
    ligne += [equipes[100][poste] for poste in POSTES]
    ligne += [equipes[200][poste] for poste in POSTES]
    return ligne, None


class Journal:
    """Ajout ligne à ligne, écrit sur disque avant l'appel suivant."""

    def __init__(self, chemin, entete):
        neuf = not chemin.exists() or chemin.stat().st_size == 0
        self.fichier = open(chemin, "a", encoding="utf-8", newline="")
        self.ecrivain = csv.writer(self.fichier, delimiter=";", lineterminator="\n")
        if neuf:
            self.ecrire(entete)

    def ecrire(self, ligne):
        self.ecrivain.writerow(ligne)
        self.fichier.flush()
        os.fsync(self.fichier.fileno())

    def fermer(self):
        self.fichier.close()


def deja_vus():
    vus = set()
    for chemin in (PARTIES, ECARTEES):
        if chemin.exists():
            with open(chemin, encoding="utf-8", newline="") as fichier:
                lecteur = csv.reader(fichier, delimiter=";")
                next(lecteur, None)
                vus.update(ligne[0] for ligne in lecteur if ligne)
    return vus


def lire_config():
    config = configparser.ConfigParser()
    config.read(CONFIG, encoding="utf-8")
    section = config["collecte"]
    return {
        "minutes": section.getint("minutes"),
        "jours": section.getint("jours"),
        "paliers": [p.strip() for p in section["paliers"].split(",")],
        "divisions": [d.strip() for d in section["divisions"].split(",")],
        "joueurs_par_page": section.getint("joueurs_par_page"),
        "parties_par_joueur": section.getint("parties_par_joueur"),
        "pages_max": section.getint("pages_max"),
    }


def collecter(riot, reglages, noms, parties, ecartees, vus, fin):
    debut = int(time.time()) - reglages["jours"] * 86400
    divisions = [(palier, division) for palier in reglages["paliers"] for division in reglages["divisions"]]
    pages_max = dict.fromkeys(divisions, reglages["pages_max"])
    compte = {"parties": 0, "ecartees": 0}

    def temps_restant():
        return time.monotonic() < fin

    while temps_restant():
        random.shuffle(divisions)
        for palier, division in divisions:
            if not temps_restant():
                break
            page = random.randint(1, pages_max[(palier, division)])
            entrees = riot.get(PLATEFORME, f"/lol/league/v4/entries/RANKED_SOLO_5x5/{palier}/{division}", {"page": page})
            if not entrees:
                pages_max[(palier, division)] = max(1, page // 2)
                continue
            code = INITIALE.get(palier, palier[:1]) + CHIFFRE.get(division, division)
            for entree in random.sample(entrees, min(reglages["joueurs_par_page"], len(entrees))):
                if not temps_restant():
                    break
                puuid = entree.get("puuid")
                if not puuid:
                    continue
                identifiants = riot.get(
                    REGION,
                    f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
                    {"queue": FILE_SOLO, "start": 0, "count": reglages["parties_par_joueur"], "startTime": debut},
                ) or []
                for identifiant in identifiants:
                    court = identifiant.removeprefix(PREFIXE)
                    if court in vus:
                        continue
                    if not temps_restant():
                        break
                    match = riot.get(REGION, f"/lol/match/v5/matches/{identifiant}")
                    vus.add(court)
                    if match is None:
                        ecartees.ecrire([court, "introuvable"])
                        compte["ecartees"] += 1
                        continue
                    ligne, raison = convertir(match, code, noms)
                    if ligne:
                        parties.ecrire(ligne)
                        compte["parties"] += 1
                        if compte["parties"] % 100 == 0:
                            print(f"{compte['parties']} parties, {compte['ecartees']} écartées, {riot.appels} appels", flush=True)
                    else:
                        ecartees.ecrire([court, raison])
                        compte["ecartees"] += 1
    return compte


def main():
    cle = os.environ.get("RIOT_API_KEY", "").strip()
    if not cle:
        print("::error::RIOT_API_KEY absente. Ajouter la clé dans Settings > Secrets and variables > Actions.")
        return 1

    reglages = lire_config()
    noms = noms_des_champions()
    DONNEES.mkdir(exist_ok=True)
    vus = deja_vus()
    parties = Journal(PARTIES, COLONNES)
    ecartees = Journal(ECARTEES, ["match", "raison"])
    riot = Riot(cle)
    fin = time.monotonic() + reglages["minutes"] * 60
    print(f"Collecte pendant {reglages['minutes']} min. Déjà vues : {len(vus)} parties.", flush=True)
    try:
        compte = collecter(riot, reglages, noms, parties, ecartees, vus, fin)
    except CleRefusee as erreur:
        print(f"::error::{erreur} Une clé de développement expire au bout de 24 heures : la régénérer, puis mettre à jour le secret RIOT_API_KEY.")
        return 1
    finally:
        parties.fermer()
        ecartees.fermer()
    print(f"Terminé : {compte['parties']} parties ajoutées, {compte['ecartees']} écartées, {riot.appels} appels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
