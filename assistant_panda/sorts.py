"""Contrôles (CC) de chaque champion, d'après Data Dragon (descriptions officielles des sorts, patch en cours).

Pour chaque champion : les sorts (passif P, Q, W, E, R) qui posent un contrôle « dur » (étourdissement,
projection, immobilisation, attraction, charme, peur, provocation, neutralisation, sommeil, silence,
transformation, recul). Les ralentissements sont laissés de côté, pour ne garder que l'essentiel.
Détection par mots-clés dans la description et l'infobulle anglaises ; nom du sort en français.
Écrit assistant_panda/sorts.json, lu par construire.py.

    python3 assistant_panda/sorts.py                 (Data Dragon officiel, dernière version)
    python3 assistant_panda/sorts.py --dossier <d>   (fichiers championFull_en_US.json et championFull_fr_FR.json déjà là)
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "sorts.json"
DDRAGON = "https://ddragon.leagueoflegends.com"

# Du plus fort au plus léger : l'ordre sert à trier les sorts à surveiller.
CC = [
    ("neutralise", r"\bsuppress"),
    ("projette en l'air", r"knock(?:s|ing|ed)? (?:\w+ ){0,2}(?:up|into the air)|\bairborne|\blaunch(?:es|ing)? (?:\w+ )?(?:enem|champion|target)"),
    ("étourdit", r"\bstun"),
    ("charme", r"\bcharm"),
    ("terrifie", r"\bfear|\bterrif|\bflee(?:s|ing)?\b"),
    ("provoque", r"\btaunt"),
    ("endort", r"\bsleep|\bdrows"),
    ("attire", r"\bpull(?:s|ing|ed)?\b|\bdrag(?:s|ging|ged)?\b|\byank"),
    ("immobilise", r"\broot|\bimmobiliz|\bsnare|\bbind(?:s|ing)?\b|\btether(?:s|ed)? .{0,40}unable to move"),
    ("repousse", r"knock(?:s|ing|ed)? (?:\w+ )?(?:back|away|aside)|\bpush(?:es|ing)? .{0,30}(?:away|back)"),
    ("réduit au silence", r"\bsilenc"),
    ("transforme", r"\bpolymorph"),
]
MOTIFS = [(nom, re.compile(m, re.IGNORECASE)) for nom, m in CC]
# Phrases où le mot ne veut pas dire que le sort contrôle (immunités, renvois).
NEGATIONS = re.compile(r"immun\w* to [^.]*|cannot be [^.]*|unstoppable[^.]*|cleans\w*[^.]*|remov\w* [^.]*crowd control[^.]*"
                       r"|prevents? [^.]*|\w+ effects on [^.]*|self-taunt\w*|taste their fear", re.IGNORECASE)


# Passifs : leur texte parle souvent des contrôles des autres (« résiste au premier contrôle », « les contrôles des alliés »).
# On ne garde que les passifs qui contrôlent vraiment (vérifiés à la main sur le patch 16.21).
PASSIFS_QUI_CONTROLENT = {"Annie", "Braum", "Kennen", "Nautilus", "Sejuani", "Vex"}


def cc_du_texte(texte):
    """Types de contrôle (en français, du plus fort au plus léger) décrits dans un texte anglais."""
    texte = re.sub(r"\{\{[^}]*\}\}", " ", re.sub(r"<[^>]+>", " ", texte or ""))   # balises et variables ({{ tauntlength }}…)
    texte = NEGATIONS.sub(" ", texte)
    return [nom for nom, motif in MOTIFS if motif.search(texte)]


def nom_assistant(nom):
    return nom


def extraire(en, fr):
    """{champion: [[touche, nom du sort en français, [types]], ...]}, sorts triés du contrôle le plus fort au plus léger."""
    ordre = {nom: i for i, (nom, _) in enumerate(CC)}
    sortie = {}
    for cle, c in en["data"].items():
        cf = fr["data"].get(cle, c)
        sorts = [("P", c["passive"], cf.get("passive", c["passive"]))] if c["name"] in PASSIFS_QUI_CONTROLENT else []
        sorts += [(t, s, sf) for t, s, sf in zip("QWER", c["spells"], cf.get("spells", c["spells"]))]
        liste = []
        for touche, s, sf in sorts:
            types = cc_du_texte(s.get("description", "") + " . " + s.get("tooltip", ""))
            if types:
                liste.append([touche, sf.get("name", s.get("name", "")), types])
        liste.sort(key=lambda x: (ordre[x[2][0]], "RQWEP".index(x[0])))
        sortie[c["name"]] = liste
    return sortie


def telecharger(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dossier", help="dossier avec championFull_en_US.json et championFull_fr_FR.json")
    args = parser.parse_args()
    if args.dossier:
        en = json.loads((Path(args.dossier) / "championFull_en_US.json").read_text(encoding="utf-8"))
        fr = json.loads((Path(args.dossier) / "championFull_fr_FR.json").read_text(encoding="utf-8"))
    else:
        version = telecharger(f"{DDRAGON}/api/versions.json")[0]
        en = telecharger(f"{DDRAGON}/cdn/{version}/data/en_US/championFull.json")
        fr = telecharger(f"{DDRAGON}/cdn/{version}/data/fr_FR/championFull.json")
    sorts = extraire(en, fr)
    SORTIE.write_text(json.dumps({"version": en.get("version"), "champions": sorts}, ensure_ascii=False, indent=0) + "\n",
                      encoding="utf-8")
    avec = sum(bool(v) for v in sorts.values())
    print(f"Sorts : {SORTIE} (Data Dragon {en.get('version')}), {len(sorts)} champions, {avec} avec au moins un contrôle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
