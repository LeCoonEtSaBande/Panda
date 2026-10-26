"""Base commune des analyses : table des drafts et découpage en tas A, B, C (voir decoupage.json).

Une partie = une draft (10 champions à leur poste), son rang, son patch et le gagnant.
Sources (Émeraude et Diamant seulement, pour apprendre et valider sur les mêmes rangs) :
- « neuf » : donnees/parties.csv (branche main) ;
- « archive » : archives/2026-10-22_avant_details/parties.csv (branche main).

Tas : tout ce qui est connu au « gel » sert à apprendre, partagé par empreinte du numéro de partie en A
(apprentissage, 3/4) et B (vérification, 1/4) ; C (confirmation) = les parties collectées après le gel,
jamais lues avant une confirmation. Bibliothèque standard + pandas.
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

import lecture  # noqa: E402

ARCHIVE = RACINE / "archives" / "2026-10-22_avant_details" / "parties.csv"
DECOUPAGE = ICI / "decoupage.json"
POSTES = ("top", "jgl", "mid", "adc", "sup")


def dossier_donnees():
    """Les données : donnees/ à la racine (récupéré de main par analyse/preparer.sh), ou le dossier
    donné par PANDA_DONNEES."""
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


def ordre_parties(donnees):
    """Identifiants de parties.csv dans l'ordre du fichier (chronologique), sans doublon."""
    chemin = Path(donnees) / "parties.csv"
    vus, ordre = set(), []
    if not chemin.exists():
        return ordre
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lecteur = csv.reader(fichier, delimiter=";")
        next(lecteur, None)
        for ligne in lecteur:
            if ligne and ligne[0] not in vus:
                vus.add(ligne[0])
                ordre.append(ligne[0])
    return ordre


def drafts(regle=None, donnees=None):
    """Table des drafts avec la colonne `tas` (A, B, C). Une ligne par partie."""
    regle = regle or lire_decoupage()
    donnees = Path(donnees or dossier_donnees())
    if regle.get("version", 1) < 2:
        raise SystemExit("Découpage n° 1 (échantillon figé) abandonné : utiliser un découpage par gel (version 2 ou plus).")
    return _drafts_v2(regle, donnees)


def drafts_ab(regle=None, donnees=None):
    """Table des drafts de TOUTES les parties (archive comprise), partagées en A (3/4) et B (1/4) par empreinte.

    Pour les analyses de nos parties (or à 15 min, ganks, envahir, duels, dégâts, types) : apprises sur A, vérifiées
    sur B, sans C (26/10/2026). Le gel ne concerne que le recuit (`drafts`, tas A, B, C). Même graine que le gel :
    une partie a le même tas A ou B dans les deux découpages."""
    import pandas as pd

    regle = regle or lire_decoupage()
    donnees = Path(donnees or dossier_donnees())
    rangs = set(regle["rangs"])
    lignes, vus = [], set()
    for l in _lire(donnees / "parties.csv"):
        m = l["match"]
        if m in vus or l["palier"][:1] not in rangs:
            continue
        vus.add(m)
        lignes.append({**l, "source": "neuf", "tas": tas_ab(m, regle)})
    if ARCHIVE.exists() and regle.get("archive", True):
        for l in _lire(ARCHIVE):
            if l["palier"][:1] in rangs and l["match"] not in vus:
                vus.add(l["match"])
                lignes.append({**l, "source": "archive", "tas": tas_ab(l["match"], regle)})
    table = pd.DataFrame(lignes)
    table["rang"] = table["palier"].str[:1]
    table["bleu_gagne"] = (table["gagnant"] == "b").astype(int)
    return table.reset_index(drop=True)


def _drafts_v2(regle, donnees):
    """Découpage n° 2 (gel du 23/10 au soir) : tout ce qui était connu au gel sert à l'apprentissage.

    - Apprentissage = l'archive + les parties de parties.csv jusqu'au gel inclus (position dans le
      fichier). Partagé par empreinte en A (choix des réglages, 3/4) et B (jugement, 1/4, lu une seule
      fois à la fin d'un recuit).
    - C (confirmation) = les parties de parties.csv écrites après le gel, sauf les parties de
      l'archive recollectées (elles restent dans l'apprentissage, par l'archive).
    """
    import pandas as pd

    rangs = set(regle["rangs"])
    gel = regle["gel"]
    ordre = ordre_parties(donnees)
    position = {m: i for i, m in enumerate(ordre)}
    n_gel = int(gel["position"])
    if n_gel > len(ordre) or ordre[n_gel - 1] != gel["dernier_match"]:
        raise SystemExit("decoupage.json : la partie du gel n'est pas à sa place dans parties.csv.")
    archive = _lire(ARCHIVE) if ARCHIVE.exists() and regle.get("archive", True) else []
    dans_archive = {l["match"] for l in archive}
    lignes, vus = [], set()
    for l in _lire(donnees / "parties.csv"):
        m = l["match"]
        if m in vus or l["palier"][:1] not in rangs:
            continue
        vus.add(m)
        if position[m] < n_gel:
            lignes.append({**l, "source": "neuf", "tas": tas_ab(m, regle)})
        elif m not in dans_archive:
            lignes.append({**l, "source": "neuf", "tas": "C"})
    apprentissage_neuf = {l["match"] for l in lignes if l["tas"] != "C"}
    for l in archive:
        if l["palier"][:1] not in rangs or l["match"] in apprentissage_neuf:
            continue
        lignes.append({**l, "source": "archive", "tas": tas_ab(l["match"], regle)})
    table = pd.DataFrame(lignes)
    table["rang"] = table["palier"].str[:1]
    table["bleu_gagne"] = (table["gagnant"] == "b").astype(int)
    return table.reset_index(drop=True)


def proposer_gel(donnees, chemin=DECOUPAGE, part_b=0.25, graine="panda-2026-10-23-gel2", version=3, precedent=""):
    """Écrit un découpage (non validé) : gel à la dernière partie actuelle de parties.csv."""
    from datetime import datetime, timezone

    ordre = ordre_parties(donnees)
    regle = {
        "version": version,
        "valide": False,
        "commentaire": "Proposition. Passer « valide » à true une fois relue avec le propriétaire.",
        "rangs": ["D", "E"],
        "archive": True,
        "part_B": part_b,
        "graine": graine,
        "gel": {"position": len(ordre), "dernier_match": ordre[-1],
                "date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")},
        "regle_AB": "Apprentissage = archive + parties de parties.csv jusqu'au gel (Émeraude-Diamant). "
                    "B (jugement) si sha256(graine:match) % 1000 < 1000 × part_B, sinon A (choix).",
        "regle_C": "Parties de parties.csv écrites après le gel (Émeraude-Diamant), sauf les parties de l'archive recollectées.",
        "precedent": precedent,
    }
    table = _drafts_v2(regle, Path(donnees))
    regle["comptes_au_moment_de_la_proposition"] = resume_tas(table)
    Path(chemin).write_text(json.dumps(regle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return regle, table


def resume_tas(table):
    """Comptes par tas, source et rang (pour le contrôle avant usage)."""
    lignes = []
    for (tas, source, rang), n in table.groupby(["tas", "source", "rang"]).size().items():
        lignes.append({"tas": tas, "source": source, "rang": rang, "parties": int(n)})
    return lignes


def exiger_validation(regle):
    if not regle.get("valide"):
        raise SystemExit("decoupage.json n'est pas validé : à mettre en place avec le propriétaire avant usage.")


if __name__ == "__main__":
    r = lire_decoupage()
    r["comptes_actuels"] = resume_tas(drafts(r))
    print(json.dumps({k: v for k, v in r.items()}, ensure_ascii=False, indent=2))
