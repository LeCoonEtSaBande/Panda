#!/usr/bin/env bash
# Committe et pousse les données collectées. Appelé pendant la collecte et à la fin.
# Avec --rapport : régénère le rapport après avoir récupéré la branche, pour ne jamais
# entrer en conflit avec des résultats poussés entre-temps.
set -u
cd "$(git rev-parse --show-toplevel)"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
branche="${BRANCHE:-$(git rev-parse --abbrev-ref HEAD)}"
rapport=false
if [ "${1:-}" = "--rapport" ]; then rapport=true; fi

total() { echo $(($(wc -l < analyse/donnees/parties.csv) - 1)); }

if [ -e analyse/donnees ]; then git add analyse/donnees; fi
if ! git diff --cached --quiet; then
  git commit -q -m "Collecte : $(total) parties au total."
elif ! $rapport && [ -z "$(git log "origin/$branche..HEAD" --oneline 2>/dev/null)" ]; then
  echo "Rien de nouveau à enregistrer."
  exit 0
fi

for essai in 1 2 3; do
  if ! git pull -q --rebase origin "$branche"; then
    git rebase --abort 2>/dev/null
    echo "::warning::Récupération de la branche impossible (essai $essai)."
    sleep 5
    continue
  fi
  rapport_commite=false
  if $rapport; then
    python3 analyse/rapport.py || echo "::warning::Rapport en échec, données enregistrées quand même."
    if [ -e analyse/resultats ]; then git add analyse/resultats; fi
    if ! git diff --cached --quiet; then
      git commit -q -m "Rapport : $(total) parties."
      rapport_commite=true
    fi
  fi
  if git push -q origin "HEAD:$branche"; then
    echo "Enregistré : $(total) parties."
    exit 0
  fi
  if $rapport_commite; then git reset -q --hard HEAD~1; fi
  sleep 5
done
exit 1
