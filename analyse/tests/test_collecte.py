import copy
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collecte import COLONNES, Limiteur, collecter, convertir  # noqa: E402

NOMS = {1: "Annie", 2: "Olaf", 3: "Galio", 22: "Ashe", 12: "Alistar", 266: "Aatrox", 64: "Lee Sin", 103: "Ahri", 51: "Caitlyn", 412: "Thresh"}
POSTES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]


def partie():
    bleus = [266, 2, 1, 22, 12]
    rouges = [3, 141, 103, 51, 412]
    joueurs = []
    for equipe, champions in ((100, bleus), (200, rouges)):
        for poste, champion in zip(POSTES, champions):
            joueurs.append({"teamId": equipe, "teamPosition": poste, "championId": champion, "championTransform": 0})
    joueurs[6]["championTransform"] = 2
    return {
        "metadata": {"matchId": "EUW1_7000000001"},
        "info": {
            "queueId": 420,
            "gameDuration": 1800,
            "gameVersion": "16.21.712.4510",
            "participants": joueurs,
            "teams": [{"teamId": 100, "win": False}, {"teamId": 200, "win": True}],
        },
    }


class ConvertirTest(unittest.TestCase):
    def test_ligne_par_poste(self):
        ligne, raison = convertir(partie(), "E2", NOMS)
        self.assertIsNone(raison)
        self.assertEqual(len(ligne), len(COLONNES))
        self.assertEqual(ligne[:4], ["7000000001", "16.21", "E2", "r"])
        self.assertEqual(ligne[4:9], ["Aatrox", "Olaf", "Annie", "Ashe", "Alistar"])
        self.assertEqual(ligne[9:], ["Galio", "Kayn bleu", "Ahri", "Caitlyn", "Thresh"])

    def test_kayn_rouge(self):
        match = partie()
        match["info"]["participants"][6]["championTransform"] = 1
        ligne, _ = convertir(match, "P1", NOMS)
        self.assertEqual(ligne[10], "Kayn rouge")

    def test_kayn_sans_forme_ecarte(self):
        match = partie()
        match["info"]["participants"][6]["championTransform"] = 0
        self.assertEqual(convertir(match, "P1", NOMS), (None, "kayn_sans_forme"))

    def test_remake_ecarte(self):
        match = partie()
        match["info"]["gameDuration"] = 200
        self.assertEqual(convertir(match, "P1", NOMS), (None, "remake"))

    def test_poste_manquant_ecarte(self):
        match = partie()
        match["info"]["participants"][0]["teamPosition"] = ""
        self.assertEqual(convertir(match, "P1", NOMS), (None, "postes"))

    def test_champion_inconnu_garde(self):
        match = copy.deepcopy(partie())
        match["info"]["participants"][0]["championId"] = 999
        ligne, raison = convertir(match, "P1", NOMS)
        self.assertIsNone(raison)
        self.assertEqual(ligne[4], "?999")


class FauxRiot:
    """Diamant : que des parties déjà vues. Émeraude : une partie neuve à chaque joueur."""

    def __init__(self):
        self.appels = 0
        self.ligues = []
        self.compteur = 0

    def get(self, base, chemin, params=None):
        time.sleep(0.002)
        if "/entries/" in chemin:
            self.ligues.append(chemin.split("/")[-2])
            return [{"puuid": f"j{i}"} for i in range(8)]
        if chemin.endswith("/ids"):
            if self.ligues[-1] == "DIAMOND":
                return ["EUW1_1", "EUW1_2"]
            self.compteur += 1
            return [f"EUW1_9{self.compteur:06d}"]
        match = partie()
        match["metadata"]["matchId"] = chemin.rsplit("/", 1)[-1]
        return match


class Journal:
    def __init__(self):
        self.lignes = []

    def ecrire(self, ligne):
        self.lignes.append(ligne)


class PassageDePalierTest(unittest.TestCase):
    def reglages(self, tour_min):
        return {"jours": 14, "paliers": ["DIAMOND", "EMERALD"], "divisions": ["I"], "pages_max": 1,
                "joueurs_par_page": 5, "parties_par_joueur": 20, "sauvegarde_minutes": 0, "tour_min": tour_min}

    def lancer(self, tour_min):
        riot, parties = FauxRiot(), Journal()
        collecter(riot, self.reglages(tour_min), NOMS, parties, Journal(), {"1", "2"}, time.monotonic() + 0.6)
        return riot, parties

    def test_diamant_epuise_on_passe_a_emeraude(self):
        riot, parties = self.lancer(tour_min=3)
        self.assertEqual(riot.ligues[0], "DIAMOND")
        self.assertEqual(riot.ligues[1], "EMERALD")
        self.assertNotIn("DIAMOND", riot.ligues[1:])
        self.assertGreater(len(parties.lignes), 0)
        self.assertTrue(all(ligne[2] == "E1" for ligne in parties.lignes))

    def test_sans_seuil_on_reste_en_diamant(self):
        riot, parties = self.lancer(tour_min=0)
        self.assertEqual(set(riot.ligues), {"DIAMOND"})
        self.assertEqual(parties.lignes, [])


class AucuneCleDansLeDepotTest(unittest.TestCase):
    """Le dépôt est public : la clé Riot ne vit que dans le secret RIOT_API_KEY."""

    def test_pas_de_cle_riot_ecrite(self):
        racine = Path(__file__).resolve().parents[2]
        motifs = ("*.ini", "*.py", "*.sh", "*.md", "*.yml", "*.json", "*.js", "*.html")
        fichiers = [
            chemin for motif in motifs for chemin in racine.rglob(motif)
            if ".git" not in chemin.parts and "donnees" not in chemin.parts
        ]
        cle = re.compile(r"RGAPI-[0-9a-f]{8}-")
        avec_cle = []
        for chemin in fichiers:
            try:
                texte = chemin.read_text(encoding="utf-8", errors="ignore")
            except OSError:  # fichier temporaire d'un autre test, déjà supprimé
                continue
            if cle.search(texte):
                avec_cle.append(str(chemin.relative_to(racine)))
        self.assertEqual(avec_cle, [])


class LimiteurTest(unittest.TestCase):
    def test_entete_riot(self):
        limiteur = Limiteur()
        limiteur.regler("20:1,100:120")
        self.assertEqual(limiteur.fenetres, [(20, 1), (100, 120)])


if __name__ == "__main__":
    unittest.main()
