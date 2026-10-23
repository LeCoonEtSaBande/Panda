"""Tests de l'échantillon figé, du contrôle des données, des catégories mesurées et des biais."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI))

import collecte  # noqa: E402
import controle  # noqa: E402
import echantillon  # noqa: E402
from test_details import NOMS, FauxRiot, match  # noqa: E402

try:
    import pandas  # noqa: F401
    import statsmodels  # noqa: F401
    AVEC_PANDAS = True
except ImportError:
    AVEC_PANDAS = False


def donnees_synthetiques(identifiants, timeline=True):
    """Dossier de données complet (parties.csv + détails) à partir du match synthétique."""
    dossier = Path(tempfile.mkdtemp())
    details = collecte.ouvrir_details(dossier)
    with open(dossier / "parties.csv", "w", encoding="utf-8") as fichier:
        fichier.write(";".join(collecte.COLONNES) + "\n")
    for identifiant in identifiants:
        riot = FauxRiot() if timeline else FauxRiot(timeline=None)
        collecte.ecrire_details(riot, match(identifiant), NOMS, details)
        ligne, _ = collecte.convertir(match(identifiant), "E2", NOMS)
        with open(dossier / "parties.csv", "a", encoding="utf-8") as fichier:
            fichier.write(";".join(str(v) for v in ligne) + "\n")
    return dossier


class EchantillonTest(unittest.TestCase):
    def setUp(self):
        self.archive = echantillon.ARCHIVE
        echantillon.ARCHIVE = Path(tempfile.mkdtemp()) / "absente" / "parties.csv"

    def tearDown(self):
        echantillon.ARCHIVE = self.archive

    def test_figer_puis_decouper(self):
        donnees = donnees_synthetiques(["101", "102", "103"])
        fige = donnees / "echantillon_fige.json"
        contenu = echantillon.figer(donnees, fige)
        self.assertEqual((contenu["N"], contenu["dernier_match"]), (3, "103"))
        with self.assertRaises(SystemExit):
            echantillon.figer(donnees, fige)
        # Deux parties arrivent ensuite : elles vont dans la confirmation, pas dans l'échantillon.
        details = collecte.ouvrir_details(donnees)
        for identifiant in ("104", "105"):
            collecte.ecrire_details(FauxRiot(), match(identifiant), NOMS, details)
            ligne, _ = collecte.convertir(match(identifiant), "E2", NOMS)
            with open(donnees / "parties.csv", "a", encoding="utf-8") as fichier:
                fichier.write(";".join(str(v) for v in ligne) + "\n")
        fige_avant, suite = echantillon.decouper(donnees, fige)
        self.assertEqual(fige_avant, ["101", "102", "103"])
        self.assertEqual(suite, ["104", "105"])

    def test_sans_fichier_fige(self):
        donnees = donnees_synthetiques(["101", "102"])
        tout, suite = echantillon.decouper(donnees, donnees / "absent.json")
        self.assertEqual((tout, suite), (["101", "102"], []))


class ControleTest(unittest.TestCase):
    def test_donnees_coherentes(self):
        donnees = donnees_synthetiques(["201", "202"])
        sortie = {mesure: (valeur, statut) for mesure, valeur, statut in controle.controler(donnees)}
        self.assertEqual(sortie["parties completes (parties.csv et details_parties)"][0], 2)
        self.assertEqual(sortie["parties dont les champions different de parties.csv"], (0, "ok"))
        self.assertEqual(sortie["parties sans 10 joueurs distincts"], (0, "ok"))
        self.assertEqual(sortie["parties completes sans timeline"][0], 0)
        self.assertNotIn("parties presentes aussi dans l'archive du 22/10", sortie)


@unittest.skipUnless(AVEC_PANDAS, "pandas et statsmodels absents")
class CategoriesTest(unittest.TestCase):
    def test_combats(self):
        import pandas as pd

        import categories

        # Combat 1 : le bleu 1 meurt d'abord (rouges 6 et 7), puis le bleu 2 tue le rouge 6 (réponse) :
        # 3 rouges présents contre 2 bleus, donc le takedown du bleu 2 est aussi en infériorité.
        # Combat 2, loin dans le temps : un kill isolé.
        ev = pd.DataFrame([
            {"match": "1", "t_ms": 1000, "x": 100, "y": 100, "type": "CHAMPION_KILL", "participant": 6, "victime": 1, "assistants": "7", "equipe": "r"},
            {"match": "1", "t_ms": 5000, "x": 200, "y": 200, "type": "CHAMPION_KILL", "participant": 2, "victime": 6, "assistants": "", "equipe": "b"},
            {"match": "1", "t_ms": 6000, "x": 250, "y": 200, "type": "CHAMPION_KILL", "participant": 8, "victime": 2, "assistants": "", "equipe": "r"},
            {"match": "1", "t_ms": 90000, "x": 9000, "y": 9000, "type": "CHAMPION_KILL", "participant": 3, "victime": 9, "assistants": "", "equipe": "b"},
        ])
        equipe_de = {("1", p): ("b" if p <= 5 else "r") for p in range(1, 11)}
        inferiorite, reponse = categories.combats(ev, equipe_de)
        self.assertEqual(inferiorite.get(("1", 2)), 1)
        self.assertEqual(reponse.get(("1", 2)), 1)
        self.assertIsNone(reponse.get(("1", 6)))
        self.assertIsNone(inferiorite.get(("1", 3)))

    def test_bout_en_bout(self):
        import categories
        import lecture
        from tables import charger

        donnees = donnees_synthetiques([str(300 + i) for i in range(4)])
        t = charger(sorted(lecture.matchs_avec_details(donnees)), donnees)
        self.assertEqual(len(t.joueurs), 40)
        # Le match synthétique dure moins de 15 min : on abaisse le seuil pour le test.
        ancien = categories.DUREE_MIN
        categories.DUREE_MIN = 1
        try:
            j = categories.indicateurs_joueurs(t)
            profils = categories.profils(j, minimum=1)
        finally:
            categories.DUREE_MIN = ancien
        self.assertEqual(len(profils), 10)
        for colonne in ("score_engage", "score_peel", "part_physique", "degats_mesures", "style_mesure"):
            self.assertIn(colonne, profils.columns)


@unittest.skipUnless(AVEC_PANDAS, "pandas et statsmodels absents")
class BiaisTest(unittest.TestCase):
    def test_hypotheses_fixees(self):
        hypotheses = json.loads((ICI.parent / "hypotheses.json").read_text(encoding="utf-8"))["hypotheses"]
        self.assertEqual([h["id"] for h in hypotheses],
                         ["A1", "B1", "B2", "C1", "C2", "D1", "D2", "E1", "E2", "F1", "F2", "G1", "G2"])
        self.assertTrue(all(h["sens_attendu"] for h in hypotheses))

    def test_effets_fixes_opposes(self):
        import pandas as pd

        import biais

        v = pd.DataFrame([
            {"b_top": "A", "b_jgl": "B", "b_mid": "C", "b_adc": "D", "b_sup": "E",
             "r_top": "A2", "r_jgl": "B2", "r_mid": "C2", "r_adc": "D2", "r_sup": "E2"},
            {"b_top": "A2", "b_jgl": "B2", "b_mid": "C2", "b_adc": "D2", "b_sup": "E2",
             "r_top": "A", "r_jgl": "B", "r_mid": "C", "r_adc": "D", "r_sup": "E"},
        ])
        fiches = {(n, p): {} for p, noms in zip(biais.POSTES, (("A", "A2"), ("B", "B2"), ("C", "C2"), ("D", "D2"), ("E", "E2"))) for n in noms}
        fe = biais.effets_fixes_compos(v, fiches)
        # Les deux parties sont le miroir l'une de l'autre.
        self.assertTrue(((fe.iloc[0] + fe.iloc[1]) == 0).all())
        self.assertEqual(fe.shape[1], 5)

    def test_benjamini_hochberg(self):
        import biais

        q = biais.benjamini_hochberg([0.01, 0.04, 0.03, 0.5])
        self.assertAlmostEqual(q[0], 0.04)
        self.assertAlmostEqual(q[3], 0.5)


if __name__ == "__main__":
    unittest.main()
