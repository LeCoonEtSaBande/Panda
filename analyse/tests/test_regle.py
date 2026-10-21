import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regle import charger_catalogue, correspond, etiqueter  # noqa: E402

CATALOGUE = charger_catalogue()


class RegleTest(unittest.TestCase):
    def test_compo_engage_avec_front(self):
        etiquettes = etiqueter(["Malphite", "Sejuani", "Leona", "Nami", "Samira"], CATALOGUE)
        self.assertEqual(etiquettes["scores"]["Engage"], 6)
        self.assertEqual(etiquettes["scores"]["Counter-engage"], 4)
        self.assertEqual(etiquettes["principal"], "Engage")
        self.assertEqual(etiquettes["secondaire"], "Counter-engage")
        self.assertFalse(etiquettes["assassin"])
        self.assertEqual(etiquettes["front"], "HP+")
        self.assertTrue(etiquettes["protect"])
        self.assertFalse(etiquettes["side"])
        self.assertEqual(etiquettes["degats"], "AP")

    def test_un_pick_secondaire_ne_fait_pas_un_assassin(self):
        self.assertFalse(etiqueter(["Diana"], CATALOGUE)["assassin"])
        self.assertTrue(etiqueter(["Ahri"], CATALOGUE)["assassin"])

    def test_un_seul_champion_ne_nomme_pas_la_compo(self):
        etiquettes = etiqueter(["Ahri", "Jinx", "Garen", "Darius", "Sivir"], CATALOGUE)
        self.assertEqual(etiquettes["principal"], "")
        self.assertEqual(etiquettes["secondaire"], "")
        self.assertTrue(etiquettes["assassin"])

    def test_egalite_departagee_par_les_principaux(self):
        # Engage 4, Counter-engage 2 (deux secondaires), Disengage 2 (Janna en principal).
        etiquettes = etiqueter(["Malphite", "Sejuani", "Janna"], CATALOGUE)
        self.assertEqual(etiquettes["principal"], "Engage")
        self.assertEqual(etiquettes["secondaire"], "Disengage")

    def test_egalite_departagee_par_l_ordre(self):
        # Disengage 3, puis Poke 2 et Pick 2, chacun principal d'un champion.
        etiquettes = etiqueter(["Caitlyn", "Janna", "Ahri"], CATALOGUE)
        self.assertEqual(etiquettes["principal"], "Disengage")
        self.assertEqual(etiquettes["secondaire"], "Pick")

    def test_kayn_par_forme(self):
        self.assertTrue(etiqueter(["Kayn bleu"], CATALOGUE)["assassin"])
        self.assertFalse(etiqueter(["Kayn rouge"], CATALOGUE)["assassin"])

    def test_condition(self):
        etiquettes = {"principal": "Engage", "front": "HP"}
        self.assertTrue(correspond(etiquettes, {"principal": "Engage", "front": ["HP", ""]}))
        self.assertFalse(correspond(etiquettes, {"front": "HP+"}))


if __name__ == "__main__":
    unittest.main()
