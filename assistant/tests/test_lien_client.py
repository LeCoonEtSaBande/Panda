"""Tests du lien client (assistant/lien_client.py) : ce qui est transmis à la page."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lien_client as L  # noqa: E402


class ResumerTest(unittest.TestCase):
    def session(self):
        return {"gameId": 7, "localPlayerCellId": 1, "timer": {"phase": "BAN_PICK"},
                "myTeam": [{"cellId": 0, "assignedPosition": "top", "championId": 54, "summonerId": 123, "gameName": "secret"},
                           {"cellId": 1, "assignedPosition": "jungle", "championId": 9}],
                "theirTeam": [{"cellId": 5, "assignedPosition": "", "championId": 234}, {"cellId": 6, "championId": 103}],
                "actions": [[{"actorCellId": 0, "championId": 238, "type": "ban", "completed": True}],
                            [{"actorCellId": 0, "championId": 54, "type": "pick", "completed": True}],
                            [{"actorCellId": 1, "championId": 9, "type": "pick", "completed": False}],
                            [{"actorCellId": 5, "championId": 234, "type": "pick", "completed": True}]],
                "bans": {"myTeamBans": [], "theirTeamBans": []}}

    def test_seulement_les_choix_verrouilles(self):
        r = L.resumer(self.session())
        self.assertEqual([j["champion"] for j in r["nous"]], [54, 0])        # le survol de Fiddlesticks ne compte pas
        self.assertEqual([j["champion"] for j in r["eux"]], [234, 0])
        self.assertEqual(r["bans"], [238])
        self.assertEqual([j["poste"] for j in r["nous"]], ["top", "jgl"])
        self.assertTrue(r["nous"][1]["moi"])

    def test_rien_sur_les_joueurs(self):
        texte = str(L.resumer(self.session()))
        self.assertNotIn("secret", texte)
        self.assertNotIn("123", texte)

    def test_hors_selection(self):
        self.assertEqual(L.resumer(None), {"etat": "hors_selection"})


if __name__ == "__main__":
    unittest.main()
