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
        self.assertEqual(r, [("Dragon", 700.0, True), ("Héraut", None, False)])

    def test_ame_puis_ancien(self):
        ev = [{"EventName": "DragonKill", "EventTime": 300.0 * (i + 1), "KillerName": "Moi#EUW", "DragonType": "Earth"} for i in range(4)]
        self.assertEqual(S.objectifs(1300, ev, self.noms, V)[0], ("Ancien", 1560.0, False))

    def test_heraut_disparu(self):
        self.assertEqual(S.objectifs(1200, [], self.noms, V)[1], ("Héraut", None, False))

    def test_equipes(self):
        mon, adv, _ = S.equipes({"allPlayers": self.joueurs, "activePlayer": {"riotId": "Moi#EUW"}})
        self.assertEqual(mon, "ORDER")
        self.assertEqual([S.id_champion(j) for j in adv], ["Ahri"])


if __name__ == "__main__":
    unittest.main()
