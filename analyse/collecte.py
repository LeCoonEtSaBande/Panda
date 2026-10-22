"""Collecte des parties classées solo EUW, une ligne par partie, écrite dès réception.

Pour chaque partie retenue, les fichiers de détails (joueurs, timeline, événements, détails de
partie) sont écrits d'abord, la ligne de parties.csv en dernier. En mode « rattrapage », on ne
cherche pas de nouvelles parties : on complète les détails des parties déjà dans parties.csv.
"""

import configparser
import csv
import json
import os
import random
import subprocess
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
COTES = {100: "b", 200: "r"}
NOMS_POSTES = dict(zip(POSTES, ("top", "jgl", "mid", "adc", "sup")))

# Détails : un dossier par type de fichier, découpé en tranches de TRANCHE parties.
TRANCHE = 2000
RATTRAPAGE_ECHECS = DONNEES / "rattrapage_echecs.csv"

# Clés de info.teams[].objectives vérifiées sur de vrais matchs (octobre 2026) : pas d'« atakhan »,
# mais un « voidGator ».
OBJECTIFS = ("baron", "champion", "dragon", "horde", "inhibitor", "riftHerald", "tower", "voidGator")
COLONNES_DETAILS = ["match", "duree_s", "fin_surrender", "fin_surrender_precoce"]
COLONNES_DETAILS += [f"{cote}_ban{n}" for cote in ("b", "r") for n in range(1, 6)]
COLONNES_DETAILS += [
    f"{cote}_{objectif}_{mesure}" for cote in ("b", "r") for objectif in OBJECTIFS for mesure in ("premier", "nb")
]

# Colonne du fichier joueurs -> champ de info.participants[].
CHAMPS_JOUEUR = {
    "kills": "kills",
    "deaths": "deaths",
    "assists": "assists",
    "niveau": "champLevel",
    "or_gagne": "goldEarned",
    "degats_physiques_champions": "physicalDamageDealtToChampions",
    "degats_magiques_champions": "magicDamageDealtToChampions",
    "degats_vrais_champions": "trueDamageDealtToChampions",
    "degats_subis": "totalDamageTaken",
    "degats_attenues": "damageSelfMitigated",
    "soins_total": "totalHeal",
    "soins_allies": "totalHealsOnTeammates",
    "boucliers_allies": "totalDamageShieldedOnTeammates",
    "temps_cc_inflige": "timeCCingOthers",
    "cc_total": "totalTimeCCDealt",
    "degats_batiments": "damageDealtToBuildings",
    "degats_objectifs": "damageDealtToObjectives",
    "score_vision": "visionScore",
    "sort1": "summoner1Id",
    "sort2": "summoner2Id",
}
CHALLENGES = (
    "killParticipation", "teamDamagePercentage", "damageTakenOnTeamPercentage", "enemyChampionImmobilizations",
    "immobilizeAndKillWithAlly", "knockEnemyIntoTeamAndKill", "pickKillWithAlly", "soloKills", "outnumberedKills",
    "saveAllyFromDeath", "effectiveHealAndShielding", "skillshotsHit", "skillshotsDodged", "killsNearEnemyTurret",
    "takedownsFirstXMinutes", "laningPhaseGoldExpAdvantage", "earlyLaningPhaseGoldExpAdvantage",
    "maxCsAdvantageOnLaneOpponent", "turretPlatesTaken", "jungleCsBefore10Minutes", "enemyJungleMonsterKills",
    "killsOnLanersEarlyJungleAsJungler", "damagePerMinute", "goldPerMinute",
)
ITEMS = [f"item{n}" for n in range(7)]
COLONNES_JOUEURS = (
    ["match", "equipe", "poste", "champion", "participant", "kills", "deaths", "assists", "niveau", "or_gagne", "cs"]
    + [colonne for colonne in CHAMPS_JOUEUR if colonne not in ("kills", "deaths", "assists", "niveau", "or_gagne")]
    + ["rune_principale"] + ITEMS + list(CHALLENGES)
)

MINUTES_TIMELINE = (5, 10, 15, 20, 25, 30)
MESURES_TIMELINE = ("or", "xp", "cs", "niveau", "degats_champions", "x", "y")
COLONNES_TIMELINE = ["match", "participant"] + [f"{mesure}_{m}" for m in MINUTES_TIMELINE for mesure in MESURES_TIMELINE]

TYPES_EVENEMENTS = ("CHAMPION_KILL", "ELITE_MONSTER_KILL", "BUILDING_KILL", "TURRET_PLATE_DESTROYED")
COLONNES_EVENEMENTS = [
    "match", "t_ms", "type", "participant", "victime", "assistants", "equipe", "x", "y", "detail",
    "degats_recus_victime", "nb_sources",
]

DETAILS = {
    "details_parties": COLONNES_DETAILS,
    "joueurs": COLONNES_JOUEURS,
    "timeline_joueurs": COLONNES_TIMELINE,
    "evenements": COLONNES_EVENEMENTS,
}


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
        nom = nom_du_champion(joueur, noms)
        if nom is None:
            return None, "kayn_sans_forme"
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


def nom_du_champion(joueur, noms):
    """Nom du catalogue ; Kayn selon sa forme, None si elle est inconnue."""
    if joueur["championId"] == KAYN_ID:
        return KAYN.get(joueur.get("championTransform"))
    return noms.get(joueur["championId"], f"?{joueur['championId']}")


def valeur(brute):
    """Une case de CSV : vide si absente, 0/1 pour un booléen, flottants arrondis."""
    if brute is None:
        return ""
    if isinstance(brute, bool):
        return int(brute)
    if isinstance(brute, float):
        arrondi = round(brute, 4)
        return int(arrondi) if arrondi.is_integer() else arrondi
    return brute


def court(match):
    return match["metadata"]["matchId"].removeprefix(PREFIXE)


def details_partie(match, noms):
    """Ligne de details_parties : durée, fin, bans et objectifs de chaque équipe."""
    info = match["info"]
    joueurs = info.get("participants", [])
    ligne = [
        court(match),
        valeur(info.get("gameDuration")),
        int(any(j.get("gameEndedInSurrender") for j in joueurs)),
        int(any(j.get("gameEndedInEarlySurrender") for j in joueurs)),
    ]
    equipes = {equipe.get("teamId"): equipe for equipe in info.get("teams", [])}
    for identifiant in (100, 200):
        bans = sorted(equipes.get(identifiant, {}).get("bans", []), key=lambda ban: ban.get("pickTurn", 0))
        noms_bans = []
        for ban in bans[:5]:
            champion = ban.get("championId")
            if champion is None or champion < 0:
                noms_bans.append("")
            elif champion == KAYN_ID:
                noms_bans.append("Kayn")
            else:
                noms_bans.append(noms.get(champion, f"?{champion}"))
        ligne += noms_bans + [""] * (5 - len(noms_bans))
    for identifiant in (100, 200):
        objectifs = equipes.get(identifiant, {}).get("objectives", {})
        for objectif in OBJECTIFS:
            fiche = objectifs.get(objectif)
            if fiche is None:
                ligne += ["", ""]
            else:
                ligne += [valeur(bool(fiche.get("first"))), valeur(fiche.get("kills"))]
    return ligne


def joueurs_partie(match, noms):
    """Dix lignes de joueurs, dans l'ordre de parties.csv : bleus puis rouges, top à sup."""
    identifiant = court(match)
    joueurs = sorted(
        match["info"].get("participants", []),
        key=lambda j: (j.get("teamId"), POSTES.index(j["teamPosition"]) if j.get("teamPosition") in POSTES else 9),
    )
    lignes = []
    for joueur in joueurs:
        cs = None
        if joueur.get("totalMinionsKilled") is not None or joueur.get("neutralMinionsKilled") is not None:
            cs = (joueur.get("totalMinionsKilled") or 0) + (joueur.get("neutralMinionsKilled") or 0)
        challenges = joueur.get("challenges") or {}
        styles = (joueur.get("perks") or {}).get("styles") or []
        principal = next((style for style in styles if style.get("description") == "primaryStyle"), None)
        selections = (principal or {}).get("selections") or [{}]
        ligne = [
            identifiant,
            COTES.get(joueur.get("teamId"), ""),
            NOMS_POSTES.get(joueur.get("teamPosition"), ""),
            nom_du_champion(joueur, noms) or "",
            valeur(joueur.get("participantId")),
        ]
        ligne += [valeur(joueur.get(CHAMPS_JOUEUR[c])) for c in ("kills", "deaths", "assists", "niveau", "or_gagne")]
        ligne.append(valeur(cs))
        ligne += [
            valeur(joueur.get(champ)) for colonne, champ in CHAMPS_JOUEUR.items()
            if colonne not in ("kills", "deaths", "assists", "niveau", "or_gagne")
        ]
        ligne.append(valeur(selections[0].get("perk")))
        ligne += [valeur(joueur.get(item)) for item in ITEMS]
        ligne += [valeur(challenges.get(champ)) for champ in CHALLENGES]
        lignes.append(ligne)
    return lignes


def cotes_des_participants(match):
    return {j.get("participantId"): COTES.get(j.get("teamId")) for j in match["info"].get("participants", [])}


def timeline_partie(timeline, identifiant):
    """Une ligne par participant : son état aux minutes 5, 10… 30 (vide si la partie était finie)."""
    images = (timeline or {}).get("info", {}).get("frames") or []
    if not images:
        return []
    par_minute = {}
    for minute in MINUTES_TIMELINE:
        image = next((i for i in images if i.get("timestamp", 0) >= minute * 60000), None)
        if image is not None and image.get("timestamp", 0) < (minute + 1) * 60000:
            par_minute[minute] = image.get("participantFrames") or {}
    participants = sorted({int(p) for image in images for p in (image.get("participantFrames") or {})})
    lignes = []
    for participant in participants:
        ligne = [identifiant, participant]
        for minute in MINUTES_TIMELINE:
            etat = par_minute.get(minute, {}).get(str(participant))
            if etat is None:
                ligne += [""] * len(MESURES_TIMELINE)
                continue
            cs = None
            if etat.get("minionsKilled") is not None or etat.get("jungleMinionsKilled") is not None:
                cs = (etat.get("minionsKilled") or 0) + (etat.get("jungleMinionsKilled") or 0)
            position = etat.get("position") or {}
            ligne += [
                valeur(etat.get("totalGold")),
                valeur(etat.get("xp")),
                valeur(cs),
                valeur(etat.get("level")),
                valeur((etat.get("damageStats") or {}).get("totalDamageDoneToChampions")),
                valeur(position.get("x")),
                valeur(position.get("y")),
            ]
        lignes.append(ligne)
    return lignes


def adverse(cote):
    return {"b": "r", "r": "b"}.get(cote, "")


def evenements_partie(timeline, identifiant, cotes):
    """Kills, monstres épiques, bâtiments et plaques. « equipe » est l'équipe de l'auteur."""
    lignes = []
    for image in (timeline or {}).get("info", {}).get("frames") or []:
        for evenement in image.get("events") or []:
            genre = evenement.get("type")
            if genre not in TYPES_EVENEMENTS:
                continue
            auteur = evenement.get("killerId") or 0
            victime = ""
            equipe = cotes.get(auteur) or ""
            degats = sources = ""
            if genre == "CHAMPION_KILL":
                victime = evenement.get("victimId", "")
                if not equipe:
                    equipe = adverse(cotes.get(victime))
                recus = evenement.get("victimDamageReceived") or []
                degats = sum(
                    (d.get("physicalDamage") or 0) + (d.get("magicDamage") or 0) + (d.get("trueDamage") or 0)
                    for d in recus
                )
                cote_victime = cotes.get(victime)
                sources = len({
                    d.get("participantId") for d in recus
                    if cotes.get(d.get("participantId")) and cotes.get(d.get("participantId")) != cote_victime
                })
                detail = ""
            elif genre == "ELITE_MONSTER_KILL":
                equipe = equipe or COTES.get(evenement.get("killerTeamId"), "")
                detail = "/".join(filter(None, (evenement.get("monsterType"), evenement.get("monsterSubType"))))
            else:
                # teamId est l'équipe propriétaire du bâtiment ou de la plaque détruite.
                equipe = equipe or adverse(COTES.get(evenement.get("teamId")))
                detail = "/".join(filter(None, (
                    evenement.get("buildingType"), evenement.get("towerType"), evenement.get("laneType"),
                )))
            position = evenement.get("position") or {}
            lignes.append([
                identifiant, valeur(evenement.get("timestamp")), genre, auteur, victime,
                "|".join(str(p) for p in evenement.get("assistingParticipantIds") or []),
                equipe, valeur(position.get("x")), valeur(position.get("y")), detail, degats, sources,
            ])
    return lignes


def ecrire_details(riot, match, noms, details):
    """Écrit joueurs, timeline et événements, puis details_parties en dernier (marque de complétude).

    Renvoie True si la timeline a pu être téléchargée.
    """
    identifiant = court(match)
    try:
        timeline = riot.get(REGION, f"/lol/match/v5/matches/{PREFIXE}{identifiant}/timeline")
    except (RuntimeError, urllib.error.HTTPError) as erreur:
        print(f"::warning::Timeline de {identifiant} indisponible ({erreur}), partie gardée sans timeline.", flush=True)
        timeline = None
    details["joueurs"].ecrire(joueurs_partie(match, noms))
    lignes_timeline = timeline_partie(timeline, identifiant) if timeline else []
    if lignes_timeline:
        details["timeline_joueurs"].ecrire(lignes_timeline)
        details["evenements"].ecrire(evenements_partie(timeline, identifiant, cotes_des_participants(match)))
    details["details_parties"].ecrire([details_partie(match, noms)])
    return bool(lignes_timeline)


class Journal:
    """Ajout ligne à ligne, écrit sur disque avant l'appel suivant.

    Le fichier est rouvert à chaque ligne : une sauvegarde intermédiaire (pull --rebase)
    peut remplacer le fichier sur disque, et un descripteur gardé ouvert écrirait dans le vide.
    """

    def __init__(self, chemin, entete):
        self.chemin = chemin
        if not chemin.exists() or chemin.stat().st_size == 0:
            self.ecrire(entete)

    def ecrire(self, ligne):
        with open(self.chemin, "a", encoding="utf-8", newline="") as fichier:
            csv.writer(fichier, delimiter=";", lineterminator="\n").writerow(ligne)
            fichier.flush()
            os.fsync(fichier.fileno())


def finir_la_ligne(chemin):
    """Si un arrêt brutal a laissé une ligne incomplète, la suivante commencera sur une nouvelle ligne."""
    if not chemin.exists() or chemin.stat().st_size == 0:
        return
    with open(chemin, "rb") as fichier:
        fichier.seek(-1, os.SEEK_END)
        fin = fichier.read(1)
    if fin != b"\n":
        with open(chemin, "a", encoding="utf-8") as fichier:
            fichier.write("\n")


class Tranches:
    """Fichiers de détails découpés en tranches de `taille` parties : dossier/<nom>_0001.csv, _0002.csv…

    Les lignes d'une partie sont écrites d'un bloc, dans une seule tranche. Comme Journal, le
    fichier est rouvert à chaque écriture.
    """

    def __init__(self, dossier, entete, taille=TRANCHE):
        self.dossier = Path(dossier)
        self.entete = entete
        self.taille = taille
        self.dossier.mkdir(parents=True, exist_ok=True)
        numeros = [numero_de_tranche(chemin) for chemin in self.dossier.glob(f"{self.dossier.name}_*.csv")]
        numeros = [numero for numero in numeros if numero]
        self.numero = max(numeros) if numeros else 1
        self.matchs = set()
        if self.chemin().exists():
            with open(self.chemin(), encoding="utf-8", newline="") as fichier:
                lecteur = csv.reader(fichier, delimiter=";")
                next(lecteur, None)
                self.matchs = {ligne[0] for ligne in lecteur if ligne}

    def chemin(self):
        return self.dossier / f"{self.dossier.name}_{self.numero:04d}.csv"

    def ecrire(self, lignes):
        if not lignes:
            return
        match = str(lignes[0][0])
        if match not in self.matchs and len(self.matchs) >= self.taille:
            self.numero += 1
            self.matchs = set()
        chemin = self.chemin()
        neuf = not chemin.exists() or chemin.stat().st_size == 0
        finir_la_ligne(chemin)
        with open(chemin, "a", encoding="utf-8", newline="") as fichier:
            ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
            if neuf:
                ecrivain.writerow(self.entete)
            ecrivain.writerows(lignes)
            fichier.flush()
            os.fsync(fichier.fileno())
        self.matchs.add(match)


def numero_de_tranche(chemin):
    fin = Path(chemin).stem.rsplit("_", 1)[-1]
    return int(fin) if fin.isdigit() else 0


def ouvrir_details(dossier=DONNEES, taille=TRANCHE):
    return {nom: Tranches(Path(dossier) / nom, entete, taille) for nom, entete in DETAILS.items()}


def matchs_avec_details(dossier=DONNEES):
    """Matchs déjà présents dans details_parties (écrit en dernier, donc détails complets)."""
    matchs = set()
    for chemin in sorted((Path(dossier) / "details_parties").glob("details_parties_*.csv")):
        with open(chemin, encoding="utf-8", newline="") as fichier:
            lecteur = csv.reader(fichier, delimiter=";")
            next(lecteur, None)
            matchs.update(ligne[0] for ligne in lecteur if len(ligne) == len(COLONNES_DETAILS))
    return matchs


def premiere_colonne(chemin):
    if not Path(chemin).exists():
        return []
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lecteur = csv.reader(fichier, delimiter=";")
        next(lecteur, None)
        return [ligne[0] for ligne in lecteur if ligne]


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
        "cle_api": section.get("cle_api", "").strip(),
        "sauvegarde_minutes": section.getint("sauvegarde_minutes", 0),
        "tour_min": section.getint("tour_min", 0),
        "mode": section.get("mode", "nouvelles").strip() or "nouvelles",
    }


def chronometre(reglages, fin, sauvegarder):
    """Renvoie une fonction « reste-t-il du temps ? » qui lance aussi les sauvegardes intermédiaires."""
    intervalle = reglages.get("sauvegarde_minutes", 0) * 60
    prochaine = time.monotonic() + intervalle

    def temps_restant():
        nonlocal prochaine
        if sauvegarder and intervalle and time.monotonic() >= prochaine:
            sauvegarder()
            prochaine = time.monotonic() + intervalle
        return time.monotonic() < fin

    return temps_restant


def collecter(riot, reglages, noms, parties, ecartees, vus, fin, sauvegarder=None, details=None):
    debut = int(time.time()) - reglages["jours"] * 86400
    paliers = reglages["paliers"]
    pages_max = {(palier, division): reglages["pages_max"] for palier in paliers for division in reglages["divisions"]}
    niveau = 0
    compte = {"parties": 0, "ecartees": 0, "timelines": 0}
    temps_restant = chronometre(reglages, fin, sauvegarder)

    while temps_restant():
        divisions = [(paliers[niveau], division) for division in reglages["divisions"]]
        random.shuffle(divisions)
        avant = compte["parties"]
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
                        if details is not None:
                            compte["timelines"] += ecrire_details(riot, match, noms, details)
                        parties.ecrire(ligne)
                        compte["parties"] += 1
                        if compte["parties"] % 100 == 0:
                            print(
                                f"{compte['parties']} parties ({compte['timelines']} avec timeline), "
                                f"{compte['ecartees']} écartées, {riot.appels} appels",
                                flush=True,
                            )
                    else:
                        ecartees.ecrire([court, raison])
                        compte["ecartees"] += 1
        nouvelles = compte["parties"] - avant
        if temps_restant() and niveau + 1 < len(paliers) and nouvelles < reglages.get("tour_min", 0):
            print(f"{paliers[niveau]} : {nouvelles} nouvelles parties sur un tour complet, passage à {paliers[niveau + 1]}.", flush=True)
            niveau += 1
    return compte


def rattraper(riot, reglages, noms, details, echecs, fin, sauvegarder=None, parties=PARTIES, dossier=DONNEES):
    """Complète les détails des parties de parties.csv qui n'en ont pas. N'écrit jamais parties.csv."""
    deja = matchs_avec_details(dossier) | set(premiere_colonne(echecs.chemin))
    a_faire = [match for match in dict.fromkeys(premiere_colonne(parties)) if match not in deja]
    print(f"Rattrapage : {len(a_faire)} parties sans détails.", flush=True)
    compte = {"parties": 0, "echecs": 0, "timelines": 0, "restantes": len(a_faire)}
    temps_restant = chronometre(reglages, fin, sauvegarder)
    for identifiant in a_faire:
        if not temps_restant():
            break
        match = riot.get(REGION, f"/lol/match/v5/matches/{PREFIXE}{identifiant}")
        compte["restantes"] -= 1
        if match is None:
            echecs.ecrire([identifiant, "introuvable"])
            compte["echecs"] += 1
            continue
        _, raison = convertir(match, "", noms)
        if raison:
            echecs.ecrire([identifiant, raison])
            compte["echecs"] += 1
            continue
        compte["timelines"] += ecrire_details(riot, match, noms, details)
        compte["parties"] += 1
        if compte["parties"] % 100 == 0:
            print(
                f"Rattrapage : {compte['parties']} parties ({compte['timelines']} avec timeline), "
                f"{compte['echecs']} échecs, {compte['restantes']} restantes, {riot.appels} appels",
                flush=True,
            )
    return compte


def main():
    reglages = lire_config()
    cle = os.environ.get("RIOT_API_KEY", "").strip() or reglages["cle_api"]
    if not cle:
        print("::error::Clé Riot absente. La mettre dans « cle_api » de analyse/collecte.ini.")
        return 1

    commande = os.environ.get("COMMANDE_SAUVEGARDE", "").strip()

    def sauvegarder():
        if subprocess.run(commande, shell=True).returncode != 0:
            print("::warning::Sauvegarde intermédiaire en échec, nouvel essai au prochain intervalle.", flush=True)

    if reglages["mode"] not in ("nouvelles", "rattrapage"):
        print(f"::error::Mode « {reglages['mode']} » inconnu dans analyse/collecte.ini : « nouvelles » ou « rattrapage ».")
        return 1

    noms = noms_des_champions()
    DONNEES.mkdir(exist_ok=True)
    details = ouvrir_details()
    riot = Riot(cle)
    fin = time.monotonic() + reglages["minutes"] * 60
    sauvegarde = sauvegarder if commande else None
    try:
        if reglages["mode"] == "rattrapage":
            print(f"Rattrapage des détails pendant {reglages['minutes']} min.", flush=True)
            echecs = Journal(RATTRAPAGE_ECHECS, ["match", "raison"])
            compte = rattraper(riot, reglages, noms, details, echecs, fin, sauvegarde)
            print(
                f"Terminé : {compte['parties']} parties complétées ({compte['timelines']} avec timeline), "
                f"{compte['echecs']} échecs, {compte['restantes']} restantes, {riot.appels} appels."
            )
            return 0
        vus = deja_vus()
        parties = Journal(PARTIES, COLONNES)
        ecartees = Journal(ECARTEES, ["match", "raison"])
        print(f"Collecte pendant {reglages['minutes']} min. Déjà vues : {len(vus)} parties.", flush=True)
        compte = collecter(riot, reglages, noms, parties, ecartees, vus, fin, sauvegarde, details)
    except CleRefusee as erreur:
        print(f"::error::{erreur} Une clé de développement expire au bout de 24 heures : coller la nouvelle dans « cle_api » de analyse/collecte.ini.")
        return 1
    print(
        f"Terminé : {compte['parties']} parties ajoutées ({compte['timelines']} avec timeline), "
        f"{compte['ecartees']} écartées, {riot.appels} appels."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
