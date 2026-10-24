"""Tests de la base commune (analyse/base/) et du recuit n° 2 (analyse/recuit/)."""

import sys
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "base"))
sys.path.insert(0, str(ICI.parent / "recuit"))

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

    def test_logistique_retrouve_un_effet(self):
        import bloc3_biais as bloc3

        rng = np.random.default_rng(0)
        x = rng.choice([-1.0, 0.0, 1.0], size=(20000, 1))
        y = (rng.random(20000) < bloc3.sigmoide(0.4 * x[:, 0])).astype(float)
        beta, _ = bloc3.logistique(x, y, lam=1.0)
        self.assertAlmostEqual(beta[0], 0.4, delta=0.06)



@unittest.skipUnless(AVEC_NUMPY, "numpy et pandas absents")
class RecuitPistesTest(unittest.TestCase):
    def _catalogue(self):
        lignes = {}
        styles = ["Engage", "Pick", "Poke", "Counter-engage", "Disengage"]
        groupes = ["Engage (tanks)", "Engage (bruisers)", "Supports tanks", "Pick (assassins)", "Poke (artilleurs)",
                   "Carrys", "Disengage (enchanteurs)"]
        for i in range(10):
            lignes[f"C{i}"] = {"champion": f"C{i}", "style_principal": styles[i % 5], "style_secondaire": styles[(i + 1) % 5],
                               "tanky": ["non", "HP", "HP+"][i % 3], "carry": "oui" if i % 4 == 0 else "non",
                               "degats": ["AD", "AP", "Hybride"][i % 3], "groupe_teamfight": groupes[i % 7],
                               "groupe_teamfight_mesure": groupes[i % 7], "groupe_voisin_mesure": groupes[(i + 1) % 7]}
        return lignes

    def test_variables_antisymetriques(self):
        """Échanger les deux équipes change le signe de toutes les variables, dans les deux pistes."""
        import bloc2_compos as bloc2
        import recuit_pistes as rp

        rng = np.random.default_rng(0)
        parties = []
        for _ in range(40):
            c = rng.permutation(10)
            parties.append(([f"C{i}" for i in c[:5]], [f"C{i}" for i in c[5:]], 1, "A"))
        t = table(parties)
        inverse = table([(r, b, 0, tas) for b, r, _, tas in parties])
        cat = self._catalogue()
        for piste, fonction in (("scenarios", rp.variables_scenarios), ("teamfight", rp.variables_teamfight)):
            params = rp.DEPART[piste]
            idx, idx_inv = bloc2.Index(t), bloc2.Index(inverse)
            X, _ = fonction(rp.tableaux(cat, idx.champions), idx, np.arange(40), params)
            Xi, _ = fonction(rp.tableaux(cat, idx_inv.champions), idx_inv, np.arange(40), params)
            np.testing.assert_allclose(X, -Xi)

    def test_scores_en_equivalents_champions(self):
        import recuit_pistes as rp

        code = np.array([0, 0, 1, 1, 2])
        equipe = np.array([[0, 1, 2, 3, 4]])
        s = rp.scores(code, None, np.ones(5), 0, equipe, 3)
        np.testing.assert_allclose(s, [[2, 2, 1]])


if __name__ == "__main__":
    unittest.main()
