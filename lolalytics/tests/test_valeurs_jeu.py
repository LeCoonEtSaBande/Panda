"""Tests de lolalytics/valeurs_jeu.py : lecture de Data Dragon et du wiki, choix de la valeur retenue."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import valeurs_jeu as v  # noqa: E402


class DataDragonTest(unittest.TestCase):
    def test_objets(self):
        items = {"data": {
            "3158": {"name": "Ionian Boots of Lucidity", "gold": {"total": 900}, "maps": {"11": True},
                     "description": "<mainText><stats><attention>10</attention> Ability Haste</stats><br><passive>Ionian Insight</passive><br>Gain <attention>10</attention> Summoner Spell Haste.</mainText>"},
            "3171": {"name": "Crimson Lucidity", "gold": {"total": 900}, "maps": {"11": True},
                     "description": "Gain <attention>20</attention> Summoner Spell Haste."},
            "3157": {"name": "Zhonya's Hourglass", "gold": {"total": 3250}, "maps": {"11": True}, "description": "Stasis"},
            "9999": {"name": "Objet d'Arena", "gold": {"total": 1}, "maps": {"11": False, "30": True},
                     "description": "Gain 99 Summoner Spell Haste."}}}
        prix, hate, zhonya = v.lire_objets(items)
        self.assertEqual(prix, {"3158": 900, "3171": 900, "3157": 3250})
        self.assertEqual(hate, {"3158": 10, "3171": 20})
        self.assertEqual(zhonya, ["3157"])

    def test_cosmic(self):
        runes = [{"id": 8300, "slots": [{"runes": [{"id": 8347, "key": "CosmicInsight",
                                                    "longDesc": "+18 Summoner Spell Haste<br>+10 Item Haste"}]}]}]
        self.assertEqual(v.lire_cosmic(runes), {"cosmic_id": 8347, "inspiration_id": 8300,
                                                "cosmic_hate_invocateur": 18, "cosmic_hate_objets": 10})

    def test_flash(self):
        self.assertEqual(v.lire_flash({"data": {"SummonerFlash": {"cooldown": [300]}}}), 300)
        self.assertIsNone(v.lire_flash({"data": {}}))


class ImagesTest(unittest.TestCase):
    def test_images_et_repli(self):
        import base64
        vues = []

        def faux(url):
            vues.append(url)
            return None if "Ahri" in url else b"png"
        images, echecs = v.images_surcouche("16.21.1", ["Aatrox", "Ahri"], ["3157"], {"champion_Ahri": "ancienne"}, faux)
        self.assertEqual(echecs, 1)
        self.assertEqual(images["champion_Ahri"], "ancienne")          # introuvable : la version précédente
        self.assertIn("item_3157", images)
        self.assertIn("spell_SummonerFlash", images)
        self.assertIn("https://ddragon.leagueoflegends.com/cdn/16.21.1/img/champion/Aatrox.png", vues)
        self.assertTrue(base64.b64decode(images["champion_Aatrox"]))


class WikiTest(unittest.TestCase):
    def test_heraut(self):
        t = "The Rift Herald spawns at 15:00 in the Baron pit. She despawns at 19:45 if not killed."
        self.assertEqual(v.lire_heraut_wiki(t), {"heraut_apparition_s": 900, "heraut_disparition_s": 1185})

    def test_dragons(self):
        t = ("The first dragon spawns at 5:00. Elemental drakes respawn 5 minutes after being slain. "
             "The Elder Dragon spawns after a soul is claimed and respawns 6 minutes after being slain.")
        self.assertEqual(v.lire_dragons_wiki(t), {"dragon_premier_s": 300, "dragon_reapparition_s": 300,
                                                  "ancien_reapparition_s": 360})

    def test_baron(self):
        t = "Baron Nashor spawns at 20:00 in the Baron pit and respawns 6 minutes after being slain."
        self.assertEqual(v.lire_baron_wiki(t), {"baron_apparition_s": 1200, "baron_reapparition_s": 360})

    def test_zhonya(self):
        self.assertEqual(v.lire_zhonya_wiki("Active - Stasis: put yourself in stasis (120 seconds cooldown)."), 120)
        self.assertIsNone(v.lire_zhonya_wiki("Rien d'utile ici, 5 seconds cooldown"))


class AssemblerTest(unittest.TestCase):
    def test_priorites(self):
        precedent = {"zhonya_s": 110, "flash_s": 300}
        lus = {"flash_s": (280, "Data Dragon"),           # lu et plausible : retenu
               "zhonya_s": (None, "wiki"),                # pas lu : le fichier précédent
               "heraut_apparition_s": (30, "wiki")}       # lu mais absurde : défaut
        valeurs, sources, changements = v.assembler(precedent, lus)
        self.assertEqual(valeurs["flash_s"], 280)
        self.assertEqual(sources["flash_s"], "Data Dragon")
        self.assertEqual(valeurs["zhonya_s"], 110)
        self.assertEqual(sources["zhonya_s"], "fichier précédent")
        self.assertEqual(valeurs["heraut_apparition_s"], 900)
        self.assertEqual(changements, ["flash_s : 300 → 280"])


if __name__ == "__main__":
    unittest.main()
