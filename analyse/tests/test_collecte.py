import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collecte import COLONNES, Limiteur, convertir  # noqa: E402

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


class LimiteurTest(unittest.TestCase):
    def test_entete_riot(self):
        limiteur = Limiteur()
        limiteur.regler("20:1,100:120")
        self.assertEqual(limiteur.fenetres, [(20, 1), (100, 120)])


if __name__ == "__main__":
    unittest.main()
