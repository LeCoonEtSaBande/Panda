"""Tests du classement des sorts (analyse/catalogues/datadragon.py) : une seule catégorie par sort."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "catalogues"))

import datadragon as DD  # noqa: E402


class ClasserSortTest(unittest.TestCase):
    def test_controle_avant_deplacement(self):
        self.assertEqual(DD.classer_sort("Vi charges forward and knocks up the first enemy champion hit.")[0], "controle")

    def test_cage_de_veigar_est_un_controle_seulement(self):
        self.assertEqual(DD.classer_sort("Veigar twists the edges of space, creating a cage that stuns enemies who pass through.")[0], "controle")

    def test_deplacement(self):
        self.assertEqual(DD.classer_sort("Ezreal teleports to a target nearby location and fires a homing bolt.")[0], "deplacement")
        self.assertEqual(DD.classer_sort("Kha'Zix leaps to an area, dealing damage.")[0], "deplacement")

    def test_health_n_est_pas_un_soin(self):
        self.assertEqual(DD.classer_sort("Deals damage based on the target's missing health.")[0], None)

    def test_protection_et_allies(self):
        self.assertEqual(DD.classer_sort("Lulu grants a shield to an allied champion."), ("protection", "bouclier (alliés)"))

    def test_immunite_n_est_pas_un_controle(self):
        self.assertNotEqual(DD.classer_sort("Olaf becomes immune to crowd control and gains attack damage.")[0], "controle")

    def test_kayn_deux_lignes(self):
        self.assertEqual(DD.noms_catalogue("Kayn"), ["Kayn rouge", "Kayn bleu"])

    def test_catalogue_garde_les_types(self):
        en = {"data": {"A": {"name": "Ahri", "key": "103"}, "N": {"name": "Nouveau", "key": "999"}}}
        lignes = [{"champion": "Ahri", "id_riot": "", "carry": "oui", "source": "calcul"}]
        sortie, nouveaux = DD.mettre_a_jour_catalogue(en, lignes)
        self.assertEqual(nouveaux, ["Nouveau"])
        ahri = next(l for l in sortie if l["champion"] == "Ahri")
        self.assertEqual((ahri["carry"], ahri["id_riot"]), ("oui", "103"))


if __name__ == "__main__":
    unittest.main()
