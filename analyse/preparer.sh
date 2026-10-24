#!/usr/bin/env bash
# Récupère, à la racine du dépôt, ce dont les analyses ont besoin sans le garder sur cette branche :
#   collecte/, donnees/, archives/ (branche main) et lolalytics/ (branche scraping).
# Ces dossiers sont ignorés par git ici (.gitignore). À relancer pour avoir les données à jour.
set -eu
cd "$(git rev-parse --show-toplevel)"
git fetch -q origin main scraping
rm -rf collecte donnees archives lolalytics
git archive origin/main collecte donnees archives | tar -x
git archive origin/scraping lolalytics | tar -x
echo "Prêt : $(($(wc -l < donnees/parties.csv) - 1)) parties ; Lolalytics : $(ls -d lolalytics/[0-9]*/ | sort -V | tail -1)"
