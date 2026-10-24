import copy
import csv
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import collecte  # noqa: E402
import lecture  # noqa: E402
import bilan  # noqa: E402
from collecte import (  # noqa: E402
    COLONNES_DETAILS, COLONNES_EVENEMENTS, COLONNES_JOUEURS, COLONNES_TIMELINE, Journal, Tranches,
    collecter, convertir, details_partie, ecrire_details, evenements_partie, joueurs_partie, ouvrir_details,
    rattraper, timeline_partie,
)

NOMS = {1: "Annie", 2: "Olaf", 3: "Galio", 22: "Ashe", 12: "Alistar", 266: "Aatrox", 64: "Lee Sin", 103: "Ahri",
        51: "Caitlyn", 412: "Thresh"}
MATCH = json.loads((ICI / "match_synthetique.json").read_text(encoding="utf-8"))
TIMELINE = json.loads((ICI / "timeline_synthetique.json").read_text(encoding="utf-8"))


def match(identifiant="7000000042"):
    copie = copy.deepcopy(MATCH)
    copie["metadata"]["matchId"] = f"EUW1_{identifiant}"
    return copie


def en_dict(colonnes, ligne):
    return dict(zip(colonnes, ligne))


def lire_csv(chemin):
    with open(chemin, encoding="utf-8", newline="") as fichier:
        return list(csv.reader(fichier, delimiter=";"))


class FauxRiot:
    """Renvoie le match synthétique ; la timeline selon `timeline` (dict, None pour 404, ou exception)."""

    def __init__(self, timeline=TIMELINE, introuvables=()):
        self.timeline = timeline
        self.introuvables = set(introuvables)
        self.chemins = []
        self.appels = 0

    def get(self, base, chemin, params=None):
        self.chemins.append(chemin)
        self.appels += 1
        identifiant = chemin.split("/")[5].removeprefix("EUW1_")
        if chemin.endswith("/timeline"):
            if isinstance(self.timeline, Exception):
                raise self.timeline
            return copy.deepcopy(self.timeline)
        if identifiant in self.introuvables:
            return None
        return match(identifiant)


class ConversionTest(unittest.TestCase):
    def test_details_partie(self):
        ligne = details_partie(match(), NOMS)
        self.assertEqual(len(ligne), len(COLONNES_DETAILS))
        d = en_dict(COLONNES_DETAILS, ligne)
        self.assertEqual((d["match"], d["duree_s"], d["fin_surrender"], d["fin_surrender_precoce"]), ("7000000042", 1000, 1, 0))
        self.assertEqual([d[f"b_ban{n}"] for n in range(1, 6)], ["Kayn", "", "Annie", "Olaf", "Galio"])
        self.assertEqual([d[f"r_ban{n}"] for n in range(1, 6)], ["Ashe", "Alistar", "Caitlyn", "Ahri", "Lee Sin"])
        self.assertEqual((d["b_horde_premier"], d["b_horde_nb"], d["r_tower_premier"], d["r_tower_nb"]), (1, 3, 1, 6))
        self.assertEqual((d["b_voidGator_premier"], d["b_voidGator_nb"]), ("", ""))
        self.assertEqual((d["r_voidGator_premier"], d["r_voidGator_nb"]), (1, 1))

    def test_joueurs_comme_parties_csv(self):
        partie, _ = convertir(match(), "E2", NOMS)
        lignes = joueurs_partie(match(), NOMS)
        self.assertEqual(len(lignes), 10)
        self.assertTrue(all(len(ligne) == len(COLONNES_JOUEURS) for ligne in lignes))
        self.assertEqual([ligne[3] for ligne in lignes], partie[4:])
        self.assertEqual(
            [(ligne[1], ligne[2]) for ligne in lignes],
            [(cote, poste) for cote in "br" for poste in ("top", "jgl", "mid", "adc", "sup")],
        )
        rouge_jungle = en_dict(COLONNES_JOUEURS, lignes[6])
        self.assertEqual(rouge_jungle["champion"], "Kayn rouge")
        self.assertEqual(rouge_jungle["cs"], 111)
        self.assertEqual(rouge_jungle["rune_principale"], 8010)
        self.assertEqual(rouge_jungle["killsOnLanersEarlyJungleAsJungler"], 2)
        premier = en_dict(COLONNES_JOUEURS, lignes[0])
        self.assertEqual(premier["soloKills"], "")
        self.assertEqual(premier["killParticipation"], 0.3333)
        self.assertEqual(premier["jungleCsBefore10Minutes"], 66)
        self.assertEqual((premier["item0"], premier["item6"]), (3071, 3340))

    def test_kayn_bleu(self):
        bleu = match()
        bleu["info"]["participants"][6]["championTransform"] = 2
        self.assertEqual(joueurs_partie(bleu, NOMS)[6][3], "Kayn bleu")
        self.assertEqual(convertir(bleu, "E2", NOMS)[0][10], "Kayn bleu")

    def test_timeline(self):
        lignes = timeline_partie(TIMELINE, "7000000042")
        self.assertEqual(len(lignes), 10)
        self.assertTrue(all(len(ligne) == len(COLONNES_TIMELINE) for ligne in lignes))
        jungle = en_dict(COLONNES_TIMELINE, lignes[1])
        self.assertEqual(jungle["participant"], 2)
        self.assertEqual((jungle["or_5"], jungle["xp_5"], jungle["cs_5"], jungle["niveau_5"]), (2002, 2002, 39, 3))
        self.assertEqual((jungle["degats_champions_15"], jungle["x_15"], jungle["y_15"]), (1502, 1002, 2015))
        for minute in (20, 25, 30):
            self.assertEqual(jungle[f"or_{minute}"], "")

    def test_evenements(self):
        cotes = collecte.cotes_des_participants(match())
        lignes = [en_dict(COLONNES_EVENEMENTS, ligne) for ligne in evenements_partie(TIMELINE, "7000000042", cotes)]
        self.assertEqual(
            [ligne["type"] for ligne in lignes],
            ["CHAMPION_KILL", "TURRET_PLATE_DESTROYED", "ELITE_MONSTER_KILL", "CHAMPION_KILL", "BUILDING_KILL"],
        )
        kill, plaque, dragon, tour, batiment = lignes
        self.assertEqual((kill["participant"], kill["victime"], kill["assistants"], kill["equipe"]), (7, 3, "8|9", "r"))
        self.assertEqual((kill["degats_recus_victime"], kill["nb_sources"]), (550, 2))
        self.assertEqual((plaque["participant"], plaque["equipe"], plaque["detail"]), (0, "r", "BOT_LANE"))
        self.assertEqual((plaque["degats_recus_victime"], plaque["nb_sources"]), ("", ""))
        self.assertEqual((dragon["equipe"], dragon["detail"], dragon["assistants"]), ("r", "DRAGON/EARTH_DRAGON", "10"))
        self.assertEqual((tour["participant"], tour["victime"], tour["equipe"], tour["nb_sources"]), (0, 9, "b", 0))
        self.assertEqual((batiment["equipe"], batiment["detail"]), ("r", "TOWER_BUILDING/OUTER_TURRET/BOT_LANE"))


class Ordre:
    """Note l'ordre des écritures de tous les fichiers."""

    def __init__(self, nom, journal):
        self.nom, self.journal = nom, journal

    def ecrire(self, lignes):
        self.journal.append(self.nom)


class EcritureTest(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp())

    def test_parties_csv_ecrit_en_dernier(self):
        ordre = []
        details = {nom: Ordre(nom, ordre) for nom in collecte.DETAILS}

        class Parties:
            def ecrire(self, ligne):
                ordre.append("parties")

        reglages = {"jours": 14, "paliers": ["DIAMOND"], "divisions": ["I"], "pages_max": 1, "joueurs_par_page": 1,
                    "parties_par_joueur": 1, "sauvegarde_minutes": 0, "tour_min": 0}

        class Riot(FauxRiot):
            def get(self, base, chemin, params=None):
                if "/entries/" in chemin:
                    return [{"puuid": "j"}]
                if chemin.endswith("/ids"):
                    return [f"EUW1_{len(self.chemins) + 8000000000}"]
                return super().get(base, chemin, params)

        collecter(Riot(), reglages, NOMS, Parties(), Ordre("ecartees", ordre), set(), time.monotonic() + 0.3,
                  details=details)
        self.assertGreater(ordre.count("parties"), 0)
        attendu = ["joueurs", "timeline_joueurs", "evenements", "details_parties", "parties"]
        self.assertEqual(ordre[:5], attendu)
        self.assertEqual(ordre, attendu * ordre.count("parties"))

    def test_timeline_absente(self):
        for timeline in (None, RuntimeError("Riot ne répond plus")):
            dossier = Path(tempfile.mkdtemp())
            details = ouvrir_details(dossier)
            self.assertFalse(ecrire_details(FauxRiot(timeline=timeline), match(), NOMS, details))
            self.assertEqual(len(lire_csv(dossier / "joueurs" / "joueurs_0001.csv")), 11)
            self.assertEqual(len(lire_csv(dossier / "details_parties" / "details_parties_0001.csv")), 2)
            self.assertFalse((dossier / "timeline_joueurs" / "timeline_joueurs_0001.csv").exists())
            self.assertFalse((dossier / "evenements" / "evenements_0001.csv").exists())

    def test_timeline_presente(self):
        details = ouvrir_details(self.dossier)
        self.assertTrue(ecrire_details(FauxRiot(), match(), NOMS, details))
        self.assertEqual(len(lire_csv(self.dossier / "timeline_joueurs" / "timeline_joueurs_0001.csv")), 11)
        self.assertEqual(len(lire_csv(self.dossier / "evenements" / "evenements_0001.csv")), 6)


class TranchesTest(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp()) / "joueurs"

    def test_decoupage_et_reprise(self):
        tranches = Tranches(self.dossier, ["match", "n"], taille=2)
        for match_id in ("1", "2", "3"):
            tranches.ecrire([[match_id, 1], [match_id, 2]])
        reprise = Tranches(self.dossier, ["match", "n"], taille=2)
        self.assertEqual(reprise.numero, 2)
        for match_id in ("4", "5"):
            reprise.ecrire([[match_id, 1]])
        fichiers = sorted(p.name for p in self.dossier.iterdir())
        self.assertEqual(fichiers, ["joueurs_0001.csv", "joueurs_0002.csv", "joueurs_0003.csv"])
        self.assertEqual(lire_csv(self.dossier / "joueurs_0001.csv"), [["match", "n"], ["1", "1"], ["1", "2"], ["2", "1"], ["2", "2"]])
        self.assertEqual(lire_csv(self.dossier / "joueurs_0002.csv"), [["match", "n"], ["3", "1"], ["3", "2"], ["4", "1"]])
        self.assertEqual(lire_csv(self.dossier / "joueurs_0003.csv"), [["match", "n"], ["5", "1"]])

    def test_ligne_interrompue(self):
        tranches = Tranches(self.dossier, ["match", "n"], taille=10)
        tranches.ecrire([["1", 1]])
        with open(tranches.chemin(), "a", encoding="utf-8") as fichier:
            fichier.write("2;")
        tranches.ecrire([["3", 1]])
        self.assertEqual(lire_csv(tranches.chemin())[-1], ["3", "1"])


class LectureTest(unittest.TestCase):
    def setUp(self):
        self.donnees = Path(tempfile.mkdtemp())
        with open(self.donnees / "parties.csv", "w", encoding="utf-8") as fichier:
            fichier.write(";".join(collecte.COLONNES) + "\n")
            for identifiant in ("10", "11", "12"):
                fichier.write(identifiant + ";16.21;E2;b" + ";X" * 10 + "\n")

    def test_concatene_filtre_et_dedoublonne(self):
        details = ouvrir_details(self.donnees, taille=2)

        def joueurs(*lignes):
            details["joueurs"].ecrire([ligne + [""] * (len(COLONNES_JOUEURS) - 3) for ligne in lignes])

        def fin(identifiant):
            details["details_parties"].ecrire([[identifiant] + [""] * (len(COLONNES_DETAILS) - 1)])

        joueurs(["10", "b", "top"], ["10", "b", "jgl"])
        fin("10")
        joueurs(["99", "b", "top"])
        fin("99")
        # Écriture de 11 interrompue, puis reprise complète juste derrière.
        joueurs(["11", "b", "top"])
        joueurs(["11", "b", "top"], ["11", "b", "jgl"])
        fin("11")
        # 12 : détails incomplets (details_parties jamais écrit).
        joueurs(["12", "b", "top"])

        self.assertGreater(len(lecture.tranches("joueurs", self.donnees)), 1)
        self.assertEqual(lecture.matchs_avec_details(self.donnees), {"10", "11"})
        lignes = list(lecture.lire_details("joueurs", self.donnees))
        self.assertEqual([(l["match"], l["poste"]) for l in lignes], [("10", "top"), ("10", "jgl"), ("11", "top"), ("11", "jgl")])

    def test_volume_du_rapport(self):
        details = ouvrir_details(self.donnees)
        ecrire_details(FauxRiot(), match("10"), NOMS, details)
        ecrire_details(FauxRiot(timeline=None), match("11"), NOMS, details)
        ecrire_details(FauxRiot(), match("77"), NOMS, details)
        self.assertEqual(bilan.volume_details(self.donnees), [["avec_details", 2], ["avec_timeline", 1]])
        self.assertEqual(len(list(lecture.lire_details("evenements", self.donnees))), 5)

    def test_volume_sans_details(self):
        self.assertEqual(bilan.volume_details(self.donnees), [["avec_details", 0], ["avec_timeline", 0]])


class RattrapageTest(unittest.TestCase):
    def setUp(self):
        self.donnees = Path(tempfile.mkdtemp())
        self.parties = self.donnees / "parties.csv"
        with open(self.parties, "w", encoding="utf-8") as fichier:
            fichier.write(";".join(collecte.COLONNES) + "\n")
            for identifiant in ("20", "21", "22", "23"):
                fichier.write(identifiant + ";16.21;E2;r;Aatrox;Lee Sin;Ahri;Ashe;Alistar;Galio;Kayn rouge;Annie;Caitlyn;Thresh\n")
        self.contenu = self.parties.read_bytes()
        self.reglages = {"sauvegarde_minutes": 0}

    def lancer(self, riot):
        details = ouvrir_details(self.donnees)
        echecs = Journal(self.donnees / "rattrapage_echecs.csv", ["match", "raison"])
        return rattraper(riot, self.reglages, NOMS, details, echecs, time.monotonic() + 5,
                         parties=self.parties, dossier=self.donnees)

    def test_rattrapage(self):
        ecrire_details(FauxRiot(), match("20"), NOMS, ouvrir_details(self.donnees))
        riot = FauxRiot(introuvables={"22"})
        compte = self.lancer(riot)
        self.assertEqual((compte["parties"], compte["echecs"], compte["timelines"]), (2, 1, 2))
        self.assertEqual(self.parties.read_bytes(), self.contenu)
        self.assertNotIn("/lol/match/v5/matches/EUW1_20", riot.chemins)
        self.assertEqual(lire_csv(self.donnees / "rattrapage_echecs.csv"), [["match", "raison"], ["22", "introuvable"]])
        self.assertEqual(lecture.matchs_avec_details(self.donnees), {"20", "21", "23"})

        relance = FauxRiot(introuvables={"22"})
        compte = self.lancer(relance)
        self.assertEqual(relance.chemins, [])
        self.assertEqual(compte["parties"], 0)
        self.assertEqual(self.parties.read_bytes(), self.contenu)

    def test_mode_par_defaut(self):
        self.assertEqual(collecte.lire_config()["mode"], "nouvelles")


if __name__ == "__main__":
    unittest.main()
