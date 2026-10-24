"""Tests de la détection des contrôles dans les sorts (assistant_panda/sorts.py)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assistant_panda"))

import sorts  # noqa: E402


class ControlesTest(unittest.TestCase):
    def test_types(self):
        self.assertEqual(sorts.cc_du_texte("Enemies in the center of the area are stunned."), ["étourdit"])
        self.assertEqual(sorts.cc_du_texte("knocking an opponent into the air"), ["projette en l'air"])
        self.assertIn("attire", sorts.cc_du_texte("Pulling them towards Thresh for {{ tauntlength }} seconds"))

    def test_faux_positifs(self):
        self.assertEqual(sorts.cc_du_texte("Briar enters a Blood Frenzy, self-taunting to the nearest enemy."), [])
        self.assertEqual(sorts.cc_du_texte("triggers Fleet of Foot"), [])
        self.assertEqual(sorts.cc_du_texte("The shield prevents Disabling and Immobilizing effects until it breaks."), [])
        self.assertEqual(sorts.cc_du_texte("Gain <status>Slow</status> immunity. Immune to stuns."), [])

    def test_ralentissement_ignore(self):
        self.assertEqual(sorts.cc_du_texte("Gangplank signals his ship to bombard an area, slowing and damaging enemies."), [])


if __name__ == "__main__":
    unittest.main()
