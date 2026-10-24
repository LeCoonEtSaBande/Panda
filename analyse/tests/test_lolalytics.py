"""Tests du lecteur Lolalytics (analyse/lolalytics/recuperer.py), sur une page miniature au même format."""

import json
import sys
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "lolalytics"))

import recuperer as r  # noqa: E402


def page(objs):
    return '<html><script type="qwik/json">' + json.dumps({"objs": objs}) + "</script></html>"


class LolalyticsTest(unittest.TestCase):
    def test_tierlist(self):
        # Objets : 0-2 valeurs, 3 une ligne, 4 la table (identifiant -> ligne), 5 le patch, 6 le parent.
        objs = [50.5, 1200, 2.1, {"wr": "0", "games": "1", "pr": "2"}, None, "16.21", {"patch": "5", "champPath": "0"}]
        objs[4] = {str(i): "3" for i in range(1, 60)}
        lignes, patch = r.lire_tierlist(page(objs))
        self.assertEqual(patch, "16.21")
        self.assertEqual(lignes[7]["wr"], 50.5)
        self.assertEqual(lignes[7]["games"], 1200)

    def test_build(self):
        # Un matchup [id, wr, d1, d2, pr, n] contre le jungler 234.
        objs = [234, 48.8, -0.3, -3.5, 4.5, 254, ["0", "1", "2", "3", "4", "5"], ["6"], {"jungle": "7"}, 5668, 51.0,
                {"enemy": "8", "n": "9", "avgWr": "a"}]
        n, moyenne, ennemis = r.lire_build(page(objs))
        self.assertEqual((n, moyenne), (5668, 51.0))
        self.assertEqual(ennemis["jungle"][0], [234, 48.8, -0.3, -3.5, 4.5, 254])

    def test_page_changee(self):
        with self.assertRaises(ValueError):
            r.lire_build("<html>rien</html>")


if __name__ == "__main__":
    unittest.main()
