"""Tests de la pente early / late (analyse/lanes/duree_degats.py)."""

import sys
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "lanes"))

try:
    import duree_degats as dd
except ImportError:          # numpy ou pandas absents : les analyses ne tournent pas, le test non plus
    dd = None


@unittest.skipIf(dd is None, "dépendances des analyses absentes")
class PenteTest(unittest.TestCase):
    T = [100, 500, 1500, 3000, 3000, 1500, 600]

    def test_plat(self):
        self.assertAlmostEqual(dd.pente(self.T, [t * 0.5 for t in self.T]), 0.0, places=6)

    def test_late_et_early(self):
        taux = [0.44, 0.46, 0.48, 0.50, 0.52, 0.54, 0.56]
        late = dd.pente(self.T, [t * w for t, w in zip(self.T, taux)])
        early = dd.pente(self.T, [t * (1 - w) for t, w in zip(self.T, taux)])
        self.assertGreater(late, 0.01)
        self.assertAlmostEqual(late, -early, places=6)

    def test_vide(self):
        self.assertIsNone(dd.pente([0] * 7, [0] * 7))

    def test_kayn(self):
        self.assertEqual(dd.nom_lola("Kayn rouge"), "Kayn")
        self.assertEqual(dd.nom_lola("Ivern"), "Ivern")


if __name__ == "__main__":
    unittest.main()
