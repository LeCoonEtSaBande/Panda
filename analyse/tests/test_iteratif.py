"""Tests de l'analyse itérative (analyse/iteratif/)."""

import sys
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "iteratif"))

try:
    import numpy as np
    import pandas as pd
    AVEC_NUMPY = True
except ImportError:
    AVEC_NUMPY = False

POSTES = ("top", "jgl", "mid", "adc", "sup")


def table(lignes):
    """Petite table de drafts : lignes = (bleus, rouges, bleu_gagne, tas)."""
    donnees = []
    for bleus, rouges, gagne, tas in lignes:
        ligne = {f"b_{p}": c for p, c in zip(POSTES, bleus)}
        ligne.update({f"r_{p}": c for p, c in zip(POSTES, rouges)})
        ligne.update({"bleu_gagne": gagne, "tas": tas})
        donnees.append(ligne)
    return pd.DataFrame(donnees)


@unittest.skipUnless(AVEC_NUMPY, "numpy et pandas absents")
class IteratifTest(unittest.TestCase):
    def test_decoupage_stable(self):
        import commun

        regle = {"graine": "essai", "part_B": 1 / 3}
        tas = [commun.tas_ab(str(m), regle) for m in range(3000)]
        self.assertEqual(tas, [commun.tas_ab(str(m), regle) for m in range(3000)])
        self.assertAlmostEqual(tas.count("B") / 3000, 1 / 3, delta=0.03)

    def test_type_de_compo_comme_la_regle(self):
        import bloc1_champions as bloc1
        import bloc2_compos as bloc2
        import bloc4_recuit as bloc4
        from regle import charger_catalogue, etiqueter

        catalogue = charger_catalogue()
        noms, groupe, secondaire = bloc1.depuis_catalogue({"separer_tanks": False}, catalogue)
        cat = bloc1.Catalogue(noms=noms, groupe=groupe, secondaire=secondaire)
        equipes = [
            (("Malphite", "Sejuani", "Ahri", "Jinx", "Leona"), ("Garen", "Viego", "Zed", "Caitlyn", "Lux")),
            (("Shen", "Ivern", "Orianna", "Ezreal", "Janna"), ("Teemo", "Karthus", "Xerath", "Varus", "Lux")),
        ]
        t = table([(b, r, 1, "A") for b, r in equipes])
        compos = bloc2.construire(cat, bloc2.Index(t), bloc4.DEPART)
        for i, (bleus, rouges) in enumerate(equipes):
            for typ, equipe in ((compos.type_b[i], bleus), (compos.type_r[i], rouges)):
                attendu = etiqueter(list(equipe), catalogue)["principal"] or "Mixte"
                self.assertEqual(compos.noms[typ], attendu, equipe)

    def test_variables_antisymetriques(self):
        import bloc1_champions as bloc1
        import bloc2_compos as bloc2
        import bloc3_biais as bloc3
        import bloc4_recuit as bloc4

        noms, groupe, secondaire = bloc1.depuis_catalogue({"separer_tanks": False})
        cat = bloc1.Catalogue(noms=noms, groupe=groupe, secondaire=secondaire,
                              capacites={c: (0.5, -0.2, 0.3) for c in groupe})
        b = ("Malphite", "Sejuani", "Ahri", "Jinx", "Leona")
        r = ("Teemo", "Ivern", "Xerath", "Varus", "Lux")
        t = table([(b, r, 1, "A"), (r, b, 0, "A")])
        compos = bloc2.construire(cat, bloc2.Index(t), bloc4.DEPART)
        X, _ = bloc3.caracteristiques(compos, np.array([0, 1]))
        self.assertTrue(np.allclose(X[0], -X[1]))
        self.assertTrue((X[0] != 0).any())

    def test_logistique_retrouve_un_effet(self):
        import bloc3_biais as bloc3

        rng = np.random.default_rng(0)
        x = rng.choice([-1.0, 0.0, 1.0], size=(20000, 1))
        y = (rng.random(20000) < bloc3.sigmoide(0.4 * x[:, 0])).astype(float)
        beta, _ = bloc3.logistique(x, y, lam=1.0)
        self.assertAlmostEqual(beta[0], 0.4, delta=0.06)

    def test_garde_fou_taille_des_groupes(self):
        import bloc4_recuit as bloc4

        self.assertGreaterEqual(bloc4.TAILLE_MIN_GROUPE, 5)
        self.assertLessEqual(bloc4.BORNES["k"][1], 12)
        self.assertGreaterEqual(bloc4.BORNES["role_jgl"][0], 0.5)


if __name__ == "__main__":
    unittest.main()
