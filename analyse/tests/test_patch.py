"""Tests de « Identifier les champions forts du patch » (analyse/patch/)."""

import sys
import tempfile
import time
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "patch"))

import collecte as c  # noqa: E402
import collecte_patch as cp  # noqa: E402

POSTES = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")


def faux_match(numero, version):
    joueurs = []
    for equipe in (100, 200):
        for i, poste in enumerate(POSTES):
            joueurs.append({"teamId": equipe, "teamPosition": poste, "championId": 1 + i + (equipe // 100) * 10,
                            "gameEndedInEarlySurrender": False})
    return {"metadata": {"matchId": f"EUW1_{numero}"},
            "info": {"queueId": 420, "participants": joueurs, "gameDuration": 1500, "gameVersion": version,
                     "teams": [{"teamId": 100, "win": True}, {"teamId": 200, "win": False}]}}


class FauxRiot:
    """Une page de 2 joueurs, chacun avec 2 parties : une du patch 16.21, une du 16.20."""

    appels = 0

    def get(self, base, chemin, params=None):
        self.appels += 1
        if "/entries/" in chemin:
            return [{"puuid": "a"}, {"puuid": "b"}]
        if "/by-puuid/a/" in chemin:
            return ["EUW1_1", "EUW1_2"]
        if "/by-puuid/b/" in chemin:
            return ["EUW1_3", "EUW1_2"]
        numero = int(chemin.rsplit("_", 1)[1])
        return faux_match(numero, "16.20.1.1" if numero == 2 else "16.21.5.1")


class CollectePatchTest(unittest.TestCase):
    def test_seul_le_patch_vise_est_garde(self):
        noms = {i: f"Champion{i}" for i in range(1, 30)}
        reglages = {"jours": 7, "paliers": ["DIAMOND"], "divisions": ["I"], "joueurs_par_page": 2,
                    "parties_par_joueur": 20, "pages_max": 1, "sauvegarde_minutes": 0}
        with tempfile.TemporaryDirectory() as dossier:
            dossier = Path(dossier)
            parties = c.Journal(dossier / "parties.csv", c.COLONNES)
            ecartees = c.Journal(dossier / "ecartees.csv", ["match", "raison"])
            compte = cp.collecter(FauxRiot(), reglages, "16.21", noms, parties, ecartees, set(), time.monotonic() + 0.3)
            gardees = [l.split(";")[0] for l in (dossier / "parties.csv").read_text().splitlines()[1:]]
            self.assertEqual(sorted(gardees), ["1", "3"])
            self.assertIn("2;patch_16.20", (dossier / "ecartees.csv").read_text())
            self.assertEqual(compte["autre_patch"], 1)
            self.assertEqual(cp.deja_vus(dossier), {"1", "2", "3"})


if __name__ == "__main__":
    unittest.main()
