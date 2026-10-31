"""Tests de la surcouche en jeu (assistant/surcouche.py) : recharges, objectifs, or des objets. Sans fenêtre."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import surcouche as S  # noqa: E402

V = dict(S.VALEURS_DEFAUT, prix_objets={"3158": 900, "3157": 3250, "2003": 50})


def joueur(champion, equipe, objets=(), flash=True, inspiration=False, nom=None):
    return {"championName": champion, "rawChampionName": f"game_character_displayname_{champion}", "team": equipe,
            "riotId": nom or f"{champion}#EUW",
            "items": [{"itemID": i, "count": 1, "price": 1, "consumable": i == 2003} for i in objets],
            "summonerSpells": {"summonerSpellOne": {"rawDisplayName": "GeneratedTip_SummonerSpell_SummonerFlash_DisplayName" if flash else "x"},
                               "summonerSpellTwo": {"rawDisplayName": "GeneratedTip_SummonerSpell_SummonerSmite_DisplayName"}},
            "runes": {"primaryRuneTree": {"id": 8100}, "secondaryRuneTree": {"id": 8300 if inspiration else 8400}}}


class RechargesTest(unittest.TestCase):
    def test_flash_sans_rien(self):
        self.assertAlmostEqual(S.recharge(300, S.hate_invocateur(joueur("Ahri", "CHAOS"), V)), 290)

    def test_flash_bottes_et_cosmic(self):
        j = joueur("Ahri", "CHAOS", objets=[3158], inspiration=True)
        self.assertEqual(S.hate_invocateur(j, V), 28)
        self.assertAlmostEqual(S.recharge(300, 28), 300 * 100 / 128 - 10)     # 234,4 s - 10 s

    def test_zhonya(self):
        j = joueur("Ahri", "CHAOS", objets=[3157], inspiration=True)
        self.assertTrue(S.a_zhonya(j, V))
        self.assertAlmostEqual(S.recharge(120, S.hate_objets(j, V)), 120 * 100 / 110 - 10)

    def test_or_des_objets(self):
        j = joueur("Ahri", "CHAOS", objets=[3158, 3157, 2003, 1055])         # potion exclue ; 1055 : prix du jeu
        self.assertEqual(S.or_objets(j, V), 900 + 3250 + 1)
        self.assertEqual(S.format_or(4151), "4.2k")


class SuiviTest(unittest.TestCase):
    def test_clic_puis_reclic(self):
        s = S.Suivi()
        s.basculer("Ahri", "F", 100.0, None)
        self.assertAlmostEqual(s.restant("Ahri", "F", 150.0, 290), 240)
        s.basculer("Ahri", "F", 150.0, 240)                                  # reclic : remis à zéro
        self.assertIsNone(s.restant("Ahri", "F", 151.0, 290))

    def test_fin_du_compte(self):
        s = S.Suivi()
        s.basculer("Ahri", "F", 100.0, None)
        self.assertIsNone(s.restant("Ahri", "F", 391.0, 290))


class ObjectifsTest(unittest.TestCase):
    def setUp(self):
        self.joueurs = [joueur("Ahri", "CHAOS"), joueur("Lee", "ORDER", nom="Moi#EUW")]
        _, _, self.noms = S.equipes({"allPlayers": self.joueurs, "activePlayer": {"riotId": "Moi#EUW"}})

    def test_debut_de_partie(self):
        r = S.objectifs(100, [], self.noms, V)
        self.assertEqual(r, [("Dragon", 300, False), ("Héraut", 900, False)])

    def test_dragon_tue(self):
        r = S.objectifs(700, [{"EventName": "DragonKill", "EventTime": 400.0, "KillerName": "Ahri#EUW", "DragonType": "Fire"},
                              {"EventName": "HeraldKill", "EventTime": 650.0}], self.noms, V)
        self.assertEqual(r, [("Dragon", 700.0, True), ("Nashor", 1200, False)])

    def test_ame_puis_ancien(self):
        ev = [{"EventName": "DragonKill", "EventTime": 300.0 * (i + 1), "KillerName": "Moi#EUW", "DragonType": "Earth"} for i in range(4)]
        self.assertEqual(S.objectifs(1300, ev, self.noms, V)[0], ("Ancien", 1560.0, False))

    def test_nashor_apres_le_heraut(self):
        self.assertEqual(S.objectifs(1190, [], self.noms, V)[1], ("Nashor", 1200, False))      # Héraut disparu à 19:45
        ev = [{"EventName": "HeraldKill", "EventTime": 950.0}, {"EventName": "BaronKill", "EventTime": 1300.0}]
        self.assertEqual(S.objectifs(1400, ev, self.noms, V)[1], ("Nashor", 1660.0, False))

    def test_equipes(self):
        mon, adv, _ = S.equipes({"allPlayers": self.joueurs, "activePlayer": {"riotId": "Moi#EUW"}})
        self.assertEqual(mon, "ORDER")
        self.assertEqual([S.id_champion(j) for j in adv], ["Ahri"])


class VisAVisTest(unittest.TestCase):
    def test_postes_du_jeu_puis_chatiment(self):
        eux = [dict(joueur(c, "CHAOS"), position=p) for c, p in (("Jinx", "BOTTOM"), ("Ahri", "MIDDLE"), ("Aatrox", "TOP"),
                                                                  ("Thresh", "UTILITY"), ("Kayn", "JUNGLE"))]
        nous = [joueur("Lux", "ORDER", nom="Moi#EUW"), joueur("Darius", "ORDER")]
        nous[1]["summonerSpells"]["summonerSpellTwo"]["rawDisplayName"] = "x"
        nous[0]["summonerSpells"]["summonerSpellTwo"]["rawDisplayName"] = "GeneratedTip_SummonerSpell_SummonerSmite_DisplayName"
        nous[1]["summonerSpells"]["summonerSpellOne"]["rawDisplayName"] = "x"
        paires = S.vis_a_vis({"allPlayers": eux + nous, "activePlayer": {"riotId": "Moi#EUW"}})
        self.assertEqual([S.id_champion(e) for e, _ in paires], ["Aatrox", "Kayn", "Ahri", "Jinx", "Thresh"])
        self.assertEqual([S.id_champion(n) if n else None for _, n in paires], ["Darius", "Lux", None, None, None])

    def test_couleurs(self):
        self.assertEqual(S.couleurs_or(5000, 4600), ("orange", "orange"))
        self.assertEqual(S.couleurs_or(5000, 4500), ("vert", "rouge"))
        self.assertEqual(S.couleurs_or(3000, 4000), ("rouge", "vert"))
        self.assertEqual(S.couleurs_or(3000, None), ("gris", "gris"))


class PlacementTest(unittest.TestCase):
    def test_jamais_sur_le_chrono_ni_la_minimap(self):
        # Écran 1920 × 1080 : rien au-dessus de 76 px (chrono, scores), rien sous 756 px (minimap).
        self.assertEqual(S.borner(1700, 0, 250, 300, 1920, 1080), (1670, 76))
        self.assertEqual(S.borner(1700, 900, 250, 300, 1920, 1080), (1670, 456))
        self.assertEqual(S.borner(1600, 320, 250, 300, 1920, 1080), (1600, 320))

    def test_taille_des_images(self):
        dispo = {"16": {}, "24": {}, "28": {}, "32": {}, "48": {}}
        self.assertEqual(S.cote_proche(24, dispo), "24")      # 1080p : comme le tableau des scores
        self.assertEqual(S.cote_proche(37, dispo), "32")      # 1440p (portrait 37 px)
        self.assertEqual(S.cote_proche(24, {"0": {}}), "0")
        self.assertIsNone(S.cote_proche(24, {}))


if __name__ == "__main__":
    unittest.main()
