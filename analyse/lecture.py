"""Raccourci vers le lecteur des données de la collecte : collecte/lecture.py (branche main).

Les analyses ne gardent aucune copie des données ni du lecteur : `analyse/preparer.sh` récupère
collecte/, donnees/ et archives/ depuis main, à la racine du dépôt (dossiers ignorés par git sur cette
branche). Ce fichier charge ce lecteur pour que les analyses puissent écrire simplement `import lecture`.
"""

import importlib.util
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[1] / "collecte" / "lecture.py"
if not _SOURCE.exists():
    raise ImportError(f"{_SOURCE} absent : lancer d'abord « bash analyse/preparer.sh » (récupère la collecte de main).")
_spec = importlib.util.spec_from_file_location("_lecture_de_main", _SOURCE)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
globals().update({k: v for k, v in vars(_module).items() if not k.startswith("__")})
