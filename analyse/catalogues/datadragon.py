"""Met le catalogue à jour avec Data Dragon (données officielles de Riot, dernière version du jeu).

Deux choses :
1. **Les champions** : chaque champion de Data Dragon a sa ligne dans analyse/catalogues/catalogue_unifie.csv, avec son
   identifiant Riot (`id_riot`, utilisé par le lien client). Un champion qui sort est ajouté, ses types vides : ils
   viennent de la classification (analyse/types/classer.py) une fois qu'il a assez de parties. Rien n'est jamais retiré.
   Kayn a deux lignes (Kayn rouge, Kayn bleu), comme dans les données.
2. **Les sorts par catégorie** (analyse/catalogues/sorts.csv) : chaque sort (Q, W, E, R, et quelques passifs) est rangé
   dans UNE seule catégorie, la première qui s'applique :
     - controle    : il contrôle un ennemi (étourdit, projette, immobilise, attire, repousse, charme…) ;
     - deplacement : il déplace le champion (dash, saut, téléportation, invisibilité, vitesse) — affiché « fuite »
                     pour une cible, « mobilité » pour un assassin ou un plongeur ;
     - protection  : il protège (bouclier, invulnérabilité, soin, mur contre les projectiles, renvoi des contrôles).
   Les sorts sans rien de tout cela ne sont pas écrits. Détection par mots-clés dans les textes anglais, nom du sort
   en français. Les erreurs se corrigent à la main dans analyse/catalogues/sorts_corrections.csv, appliqué en dernier.

    python3 analyse/catalogues/datadragon.py                   (télécharge la dernière version)
    python3 analyse/catalogues/datadragon.py --dossier <d>     (championFull_en_US.json et championFull_fr_FR.json déjà là)

Bibliothèque standard seulement. Écrit aussi analyse/catalogues/datadragon.md (le bilan du passage).
"""

import argparse
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
CATALOGUE = ICI / "catalogue_unifie.csv"
SORTS = ICI / "sorts.csv"
CORRECTIONS = ICI / "sorts_corrections.csv"
BILAN = ICI / "datadragon.md"
DDRAGON = "https://ddragon.leagueoflegends.com"
TYPES = ("carry", "enchanteur", "assassin", "plongeur", "attrapeur", "tank", "bloqueur", "dueliste", "splitpusher", "teamfighter")
COLONNES = ("champion", "id_riot") + TYPES + ("source",)
CATEGORIES = ("controle", "deplacement", "protection")

# --- Contrôles (du plus fort au plus léger) -------------------------------------------------------------
CC = [
    ("neutralise", r"\bsuppress"),
    ("projette en l'air", r"knock(?:s|ing|ed)? (?:\w+ ){0,2}(?:up|into the air)|\bairborne|\blaunch(?:es|ing)? (?:\w+ )?(?:enem|champion|target)"),
    ("étourdit", r"\bstun"),
    ("charme", r"\bcharm"),
    ("terrifie", r"\bfear|\bterrif|\bflee(?:s|ing)?\b"),
    ("provoque", r"\btaunt"),
    ("endort", r"\bsleep|\bdrows"),
    ("attire", r"\bpull(?:s|ing|ed)? (?:the |an |all |nearby )?(?:enem|target|champion|them|it\b)|\bdrag(?:s|ging|ged)? (?:the |an )?(?:enem|target|champion|them)|\byank|\bhook(?:s|ing|ed)? (?:the |an )?(?:enem|target|champion)"),
    ("immobilise", r"\broot|\bimmobiliz|\bsnare|\btether(?:s|ed)? .{0,40}unable to move"),
    ("repousse", r"knock(?:s|ing|ed)? (?:\w+ )?(?:back|away|aside)|\bpush(?:es|ing)? (?:\w+ ){0,3}(?:enem|champion|them).{0,30}(?:away|back)"),
    ("réduit au silence", r"\bsilenc"),
    ("transforme", r"\bpolymorph"),
]
NEGATIONS = re.compile(r"immun\w* to [^.]*|cannot be [^.]*|unstoppable[^.]*|cleans\w*[^.]*|remov\w* [^.]*crowd control[^.]*"
                       r"|prevents? [^.]*|\w+ effects on [^.]*|self-taunt\w*|taste their fear", re.IGNORECASE)

# --- Déplacements -------------------------------------------------------------------------------------------
DEPLACEMENT = [
    ("téléportation", r"\bteleport|\bblink"),
    ("dash", r"\bdash|\bleap|\blunge|\bvault|\bjump|\bpounce|\btumble|\bhops?\b|\bflips?\b|\bdives?\b|\bsurges? (?:forward|toward)"
             r"|\bcharges? (?:forward|toward|in a direction|to )|\brolls? (?:forward|toward|in a direction)|\bflies|\bfly\b"
             r"|\bpulls? (?:himself|herself|themselves|itself)|\bpropels? (?:himself|herself|themselves|itself)"),
    ("invisible", r"\binvisib|\bcamouflag|\bstealth"),
    ("vitesse", r"(?:gain|grant|bonus|increas)\w* [^.]{0,40}\bmove(?:ment)? speed|\bmove(?:ment)? speed (?:boost|increase)"),
]
# --- Protections ----------------------------------------------------------------------------------------------
PROTECTION = [
    ("invulnérable", r"\binvulnerab|\buntargetable|\bstasis|\bcannot die|\bcan't die|\bcannot be killed|\brevive|\bresurrect"),
    ("bloque les projectiles", r"\bblock\w* (?:\w+ ){0,2}(?:projectile|missile|attack)|\bwind ?wall|\bspell shield|\bnegat\w* (?:the next|an incoming)"),
    ("bouclier", r"\bshield"),
    ("soin", r"\bheal|\brestor\w* (?:\w+ ){0,2}health"),
    ("contre les contrôles", r"\bunstoppable|\bcleans|\bremov\w* (?:all )?(?:crowd control|disables|debuffs)|\bimmun\w* to (?:crowd control|disables|slows)"),
    ("réduit les dégâts", r"\breduc\w* (?:\w+ ){0,3}damage (?:taken|received)|\bdamage reduction|\btakes? (?:\d+% )?(?:less|reduced) damage"),
]

# Passifs : leur texte parle souvent des contrôles des autres. On ne garde que ceux qui comptent vraiment.
PASSIFS = {"Annie": "controle", "Braum": "controle", "Kennen": "controle", "Nautilus": "controle", "Sejuani": "controle",
           "Vex": "controle", "Zac": "protection", "Anivia": "protection", "Kindred": "", "Zilean": "", "Olaf": ""}


def nettoyer(texte):
    texte = re.sub(r"<[^>]+>", " ", texte or "")
    texte = re.sub(r"\{\{[^}]*\}\}", " ", texte)               # variables ({{ tauntlength }}…)
    return re.sub(r"\s+", " ", texte)


def motifs(liste):
    return [(nom, re.compile(m, re.IGNORECASE)) for nom, m in liste]


M_CC, M_DEP, M_PROT = motifs(CC), motifs(DEPLACEMENT), motifs(PROTECTION)


def classer_sort(texte):
    """(catégorie, détail) d'un sort d'après son texte anglais, ou (None, "") s'il ne fait rien de tout cela.

    Une seule catégorie par sort, la première qui s'applique : contrôle, puis déplacement, puis protection."""
    brut = nettoyer(texte)
    sans_negation = NEGATIONS.sub(" ", brut)
    cc = [nom for nom, m in M_CC if m.search(sans_negation)]
    if cc:
        return "controle", ", ".join(cc)
    dep = [nom for nom, m in M_DEP if m.search(brut)]
    if dep:
        return "deplacement", dep[0]
    prot = [nom for nom, m in M_PROT if m.search(brut)]
    if prot:
        allie = re.search(r"\ball(?:y|ies|ied)\b", brut, re.IGNORECASE)
        return "protection", prot[0] + (" (alliés)" if allie else "")
    return None, ""


def noms_catalogue(nom_dd):
    """Kayn a deux lignes dans le catalogue, comme dans nos parties."""
    return ["Kayn rouge", "Kayn bleu"] if nom_dd == "Kayn" else [nom_dd]


def portee(sort):
    try:
        return max(int(float(x)) for x in sort.get("range", []) if float(x) < 25000)
    except (ValueError, TypeError):
        return ""


def lire_corrections(chemin=CORRECTIONS):
    """{(champion, touche): (catégorie ou "", détail)} ; catégorie « aucune » = le sort est retiré."""
    if not chemin.exists():
        return {}
    with open(chemin, encoding="utf-8", newline="") as f:
        return {(l["champion"], l["touche"]): ("" if l["categorie"] == "aucune" else l["categorie"], l.get("detail", ""))
                for l in csv.DictReader(f, delimiter=";") if l.get("champion")}


def extraire_sorts(en, fr, corrections=None):
    """Lignes de sorts.csv : [champion, touche, sort en français, catégorie, détail, portée]."""
    corrections = lire_corrections() if corrections is None else corrections
    lignes = []
    for cle, c in sorted(en["data"].items(), key=lambda kv: kv[1]["name"]):
        cf = fr["data"].get(cle, c)
        sorts = []
        if c["name"] in PASSIFS and PASSIFS[c["name"]]:
            p, pf = c["passive"], cf.get("passive", c["passive"])
            sorts.append(("P", pf.get("name", p.get("name", "")), p.get("description", ""), "", PASSIFS[c["name"]]))
        for touche, s, sf in zip("QWER", c["spells"], cf.get("spells", c["spells"])):
            sorts.append((touche, sf.get("name", s.get("name", "")), s.get("description", "") + " . " + s.get("tooltip", ""), portee(s), None))
        for touche, nom, texte, port, force in sorts:
            categorie, detail = classer_sort(texte)
            if force and categorie != force:
                categorie, detail = force, detail or ""
            for champion in noms_catalogue(c["name"]):
                cat, det = categorie, detail
                if (champion, touche) in corrections:
                    cat, det_c = corrections[(champion, touche)]
                    det = det_c or det
                elif (c["name"], touche) in corrections:
                    cat, det_c = corrections[(c["name"], touche)]
                    det = det_c or det
                if cat:
                    lignes.append([champion, touche, nom, cat, det, port])
    return lignes


def lire_catalogue(chemin=CATALOGUE):
    if not chemin.exists():
        return []
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def mettre_a_jour_catalogue(en, lignes):
    """Ajoute les champions absents, met à jour les identifiants ; ne retire et ne réécrit aucun type."""
    par_nom = {l["champion"]: l for l in lignes}
    nouveaux = []
    for c in en["data"].values():
        for champion in noms_catalogue(c["name"]):
            if champion not in par_nom:
                ligne = {k: "" for k in COLONNES}
                ligne.update(champion=champion, source="nouveau")
                par_nom[champion] = ligne
                nouveaux.append(champion)
            par_nom[champion]["id_riot"] = c["key"]
    sortie = sorted(par_nom.values(), key=lambda l: l["champion"].lower())
    for l in sortie:
        for k in COLONNES:
            l.setdefault(k, "")
    return sortie, nouveaux


def ecrire_csv(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(entete)
        w.writerows(lignes)


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
    version = en.get("version", "?")

    catalogue, nouveaux = mettre_a_jour_catalogue(en, lire_catalogue())
    ecrire_csv(CATALOGUE, COLONNES, [[l[k] for k in COLONNES] for l in catalogue])
    sorts = extraire_sorts(en, fr)
    ecrire_csv(SORTS, ("champion", "touche", "sort", "categorie", "detail", "portee"), sorts)

    par_cat = {k: sum(1 for s in sorts if s[3] == k) for k in CATEGORIES}
    bilan = [f"# Data Dragon {version}", "",
             f"- {len(en['data'])} champions dans Data Dragon, {len(catalogue)} lignes au catalogue (Kayn compte deux fois).",
             f"- Nouveaux champions : {', '.join(nouveaux) if nouveaux else 'aucun'}.",
             f"- Sorts retenus : {len(sorts)} (contrôle {par_cat['controle']}, déplacement {par_cat['deplacement']}, protection {par_cat['protection']}).",
             f"- Corrections à la main appliquées : {len(lire_corrections())} (analyse/catalogues/sorts_corrections.csv).", ""]
    BILAN.write_text("\n".join(bilan), encoding="utf-8")
    print("\n".join(bilan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
