"""Données communes de l'analyse itérative : table des drafts et découpage en tas A, B, C.

Une partie = une draft (10 champions à leur poste), son rang, son patch et le gagnant.
Sources (Émeraude et Diamant seulement, pour apprendre et valider sur les mêmes rangs) :
- « neuf » : analyse/donnees/parties.csv ;
- « archive » : archives/2026-10-22_avant_details/parties.csv, sans les parties déjà recollectées.

Tas (voir decoupage.json et README.md) :
- A (apprentissage) et B (validation) : l'échantillon figé (echantillon_fige.json) + l'archive,
  partagés au hasard par une empreinte du numéro de partie (toujours le même tas pour une partie) ;
- C (confirmation) : les parties neuves arrivées APRÈS l'échantillon figé. Jamais lues par le recuit.

Bibliothèque standard + numpy/pandas.
"""

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
ANALYSE = ICI.parent
RACINE = ANALYSE.parent
if str(ANALYSE) not in sys.path:
    sys.path.insert(0, str(ANALYSE))

import echantillon  # noqa: E402
import lecture  # noqa: E402

ARCHIVE = RACINE / "archives" / "2026-10-22_avant_details" / "parties.csv"
DECOUPAGE = ICI / "decoupage.json"
RESULTATS = ICI / "resultats"
POSTES = ("top", "jgl", "mid", "adc", "sup")


def dossier_donnees():
    """Les données neuves : analyse/donnees, ou le dossier donné par PANDA_DONNEES (les workflows y
    extraient les données à jour de main, sans les committer sur la branche de travail)."""
    return Path(os.environ.get("PANDA_DONNEES") or lecture.DONNEES)


def lire_decoupage(chemin=DECOUPAGE):
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def tas_ab(match, regle):
    """« A » ou « B » pour une partie de l'échantillon figé ou de l'archive (empreinte stable)."""
    empreinte = hashlib.sha256(f"{regle['graine']}:{match}".encode()).hexdigest()
    return "B" if int(empreinte[:8], 16) % 1000 < round(1000 * regle["part_B"]) else "A"


def _lire(chemin):
    with open(chemin, encoding="utf-8", newline="") as fichier:
        return list(csv.DictReader(fichier, delimiter=";"))


def drafts(regle=None, donnees=None):
    """Table des drafts avec la colonne `tas` (A, B, C). Une ligne par partie."""
    import pandas as pd

    regle = regle or lire_decoupage()
    donnees = Path(donnees or dossier_donnees())
    rangs = set(regle["rangs"])

    fige, suite = echantillon.decouper(donnees)
    tas_neuf = {m: "fige" for m in fige}
    tas_neuf.update({m: "C" for m in suite})
    neuves = [l for l in _lire(donnees / "parties.csv") if l["match"] in tas_neuf]
    tous_neufs = {l["match"] for l in _lire(donnees / "parties.csv")}
    lignes = []
    for l in neuves:
        if l["palier"][:1] not in rangs:
            continue
        tas = tas_neuf[l["match"]]
        lignes.append({**l, "source": "neuf", "tas": "C" if tas == "C" else tas_ab(l["match"], regle)})
    if ARCHIVE.exists() and regle.get("archive", True):
        for l in _lire(ARCHIVE):
            # Une partie de l'archive recollectée depuis est gardée une seule fois, dans sa version neuve.
            if l["palier"][:1] not in rangs or l["match"] in tous_neufs:
                continue
            lignes.append({**l, "source": "archive", "tas": tas_ab(l["match"], regle)})
    table = pd.DataFrame(lignes)
    table["rang"] = table["palier"].str[:1]
    table["bleu_gagne"] = (table["gagnant"] == "b").astype(int)
    return table.reset_index(drop=True)


def resume_tas(table):
    """Comptes par tas, source et rang (pour le contrôle avant usage)."""
    lignes = []
    for (tas, source, rang), n in table.groupby(["tas", "source", "rang"]).size().items():
        lignes.append({"tas": tas, "source": source, "rang": rang, "parties": int(n)})
    return lignes


def proposer_decoupage(chemin=DECOUPAGE, part_b=1 / 3, graine="panda-2026-10-23"):
    """Écrit une proposition de découpage (non validée) avec ses comptes."""
    regle = {
        "valide": False,
        "commentaire": "Proposition. Passer « valide » à true une fois relue avec le propriétaire.",
        "rangs": ["D", "E"],
        "archive": True,
        "part_B": part_b,
        "graine": graine,
        "regle_AB": "Échantillon figé et archive (Émeraude-Diamant) : B si sha256(graine:match) % 1000 < 1000 × part_B, sinon A.",
        "regle_C": "Parties neuves arrivées après l'échantillon figé (echantillon_fige.json), Émeraude-Diamant.",
    }
    table = drafts(regle)
    regle["comptes_au_moment_de_la_proposition"] = resume_tas(table)
    Path(chemin).write_text(json.dumps(regle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return regle


def exiger_validation(regle):
    if not regle.get("valide"):
        raise SystemExit("decoupage.json n'est pas validé : à mettre en place avec le propriétaire avant usage.")


if __name__ == "__main__":
    if "--proposer" in sys.argv:
        r = proposer_decoupage()
    else:
        r = lire_decoupage()
        r["comptes_actuels"] = resume_tas(drafts(r))
    print(json.dumps({k: v for k, v in r.items()}, ensure_ascii=False, indent=2))
