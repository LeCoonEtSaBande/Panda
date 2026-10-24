"""Tests des contres par lane (analyse/contres/contres.py)."""

import sys
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "contres"))

try:
    import numpy as np
    import contres
    AVEC_NUMPY = True
except ImportError:
    AVEC_NUMPY = False


@unittest.skipUnless(AVEC_NUMPY, "numpy absent")
class ContresTest(unittest.TestCase):
    def test_contre_retrouve_et_antisymetrique(self):
        """Une paire avec un vrai effet propre de 600 or est retrouvée, dans les deux sens."""
        rng = np.random.default_rng(1)
        champions = [f"C{i}" for i in range(12)]
        force = {c: rng.normal(0, 300) for c in champions}
        lignes = []
        for i in range(6000):
            a, b = rng.choice(champions, 2, replace=False)
            effet = 600 if (a, b) == ("C0", "C1") else (-600 if (a, b) == ("C1", "C0") else 0)
            if i % 20 == 0:
                a, b, effet = "C0", "C1", 600
            lignes.append({"match": str(i), "b_top": a, "r_top": b, "bleu_gagne": 1.0,
                           "or": force[a] - force[b] + effet + rng.normal(0, 800),
                           "xp": 0.0, "kda": 0.0, "plaques": 0.0, "tour": 0.0})
        forces, _, residu, _, _ = contres.forces_de_lane(lignes, ("top",))
        paires, _, _, _ = contres.effets_de_paires(lignes, residu, "top")
        e, inverse = paires[("C0", "C1")], paires[("C1", "C0")]
        self.assertGreater(e["specifique"], 300)
        self.assertAlmostEqual(e["specifique"], -inverse["specifique"], places=6)
        self.assertEqual(contres.statut(e), "contre identifié")
        sans = [p for k, p in paires.items() if "C0" not in k and "C1" not in k and p["parties"] >= 20]
        self.assertLess(sum(contres.statut(p) == "contre identifié" for p in sans), 3)


if __name__ == "__main__":
    unittest.main()
