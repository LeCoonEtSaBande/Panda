"""Confirmation, sur l'archive du 22/10/2026, des hypothèses qui ne portent que sur les champions.

À lancer en local seulement (jamais depuis rapport.py) :

    python3 analyse/explorations/confirmer_archives.py

- Profils de champion mesurés sur l'échantillon figé (categories.py), timing complet (pas de validation
  croisée : les parties de l'archive n'ont pas servi à le mesurer).
- Parties de l'archive SANS celles qui sont aussi dans l'échantillon figé (liste notée dans
  echantillon_fige.json), pour que les deux échantillons soient indépendants.
- Hypothèses testées : A1, D1, E1, F2, G2 (trouvées ou définies sur l'échantillon figé).
  F1 et G1 ont été trouvées sur l'archive : leur confirmation est l'échantillon figé lui-même.
- L'archive est lue, jamais modifiée.

Écrit analyse/explorations/confirmation_archives.csv.
"""

import csv
import sys
import warnings
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import biais  # noqa: E402
import categories  # noqa: E402
import echantillon  # noqa: E402
from regle import charger_catalogue  # noqa: E402

ARCHIVE = ICI.parent.parent / "archives" / "2026-10-22_avant_details" / "parties.csv"
A_CONFIRMER = {"A1", "D1", "E1", "F2", "G2"}


def main():
    import pandas as pd

    warnings.filterwarnings("ignore")
    fige = echantillon.lire_fige()
    if not fige:
        raise SystemExit("Pas d'échantillon figé.")
    matchs, _ = echantillon.decouper()
    _, _, profils = categories.calculer(matchs)
    fiches = biais.table_profils(profils)

    with open(ARCHIVE, encoding="utf-8", newline="") as fichier:
        archive = pd.DataFrame(list(csv.DictReader(fichier, delimiter=";")))
    communs = set(fige.get("communs_archive", [])) | set(matchs)
    avant = len(archive)
    archive = archive[~archive["match"].isin(communs)].reset_index(drop=True)
    print(f"Archive : {avant} parties, {avant - len(archive)} écartées car aussi dans l'échantillon figé, {len(archive)} gardées.")

    v = biais.variables_parties(archive, fiches, charger_catalogue())
    resultats = biais.tests(v, fiches, avec_details=False, seulement=A_CONFIRMER)
    for r in resultats:
        # Sur l'échantillon de confirmation, chaque hypothèse est testée seule : p < 0,05 dans le sens attendu.
        r["verdict"] = "retrouvé" if r["p"] < 0.05 and r["sens"] else ("sens contraire" if r["p"] < 0.05 else "pas retrouvé")
    lignes = biais.lignes_csv("archive", resultats)
    with open(ICI / "confirmation_archives.csv", "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";", lineterminator="\n")
        ecrivain.writerow(biais.ENTETE)
        ecrivain.writerows(lignes)
    for r in resultats:
        print(f"{r['id']} : p = {r['p']:.4f}, sens attendu : {r['sens']}, {r['verdict']} — {r['texte']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
