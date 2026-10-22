import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from profils import benjamini_hochberg, charger_profils, observations, profil_de, resume_compo  # noqa: E402
from regle import charger_catalogue  # noqa: E402

CATALOGUE = charger_catalogue()
PROFILS = charger_profils()


class ProfilsTest(unittest.TestCase):
    def test_profils_du_pool(self):
        attendus = {
            "Fiddlesticks": "reaction", "Ivern": "reaction", "Maokai": "reaction", "Skarner": "reaction",
            "Kayn rouge": "bruiser-engage", "Kayn bleu": "assassin", "Viego": "assassin",
            "Dr. Mundo": "sans-style", "Sejuani": "tank-engage", "Lillia": "engage-fragile", "Karthus": "poke",
        }
        for jungle, profil in attendus.items():
            self.assertEqual(profil_de(CATALOGUE[jungle], PROFILS), profil, jungle)

    def test_tout_le_catalogue_a_un_profil(self):
        sans = [nom for nom, fiche in CATALOGUE.items() if profil_de(fiche, PROFILS) == "autre"]
        self.assertEqual(sans, [])

    def test_resume_compo(self):
        resume = resume_compo(["Malphite", "Sejuani", "Leona", "Nami", "Samira"], CATALOGUE)
        self.assertEqual(resume["style"], "Engage")
        self.assertEqual(resume["valeurs"]["nb_Engage"], 3)
        self.assertEqual(resume["valeurs"]["front_HP+"], 1.0)

    def test_la_compo_alliee_exclut_le_jungler(self):
        ligne = {"match": "1", "patch": "16.20", "palier": "E2", "gagnant": "b",
                 "b_top": "Garen", "b_jgl": "Sejuani", "b_mid": "Ahri", "b_adc": "Jinx", "b_sup": "Sona",
                 "r_top": "Darius", "r_jgl": "Viego", "r_mid": "Zed", "r_adc": "Caitlyn", "r_sup": "Lux"}
        bleu, rouge = observations([ligne], CATALOGUE, PROFILS)
        self.assertEqual(bleu["allie"]["valeurs"]["nb_Engage"], 0)
        self.assertGreater(rouge["adverse"]["valeurs"]["nb_Engage"], 0)
        self.assertTrue(bleu["victoire"])
        self.assertFalse(rouge["victoire"])

    def test_benjamini_hochberg(self):
        q = benjamini_hochberg([0.01, 0.04, 0.03, 0.5])
        self.assertAlmostEqual(q[0], 0.04)
        self.assertAlmostEqual(q[1], 0.04 * 4 / 3)
        self.assertAlmostEqual(q[3], 0.5)


if __name__ == "__main__":
    unittest.main()
