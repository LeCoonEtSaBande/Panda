#!/usr/bin/env bash
# Committe et pousse les données collectées. Appelé pendant la collecte et à la fin.
set -u
cd "$(git rev-parse --show-toplevel)"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
for dossier in analyse/donnees analyse/resultats; do
  if [ -e "$dossier" ]; then git add "$dossier"; fi
done
if git diff --cached --quiet; then
  echo "Rien de nouveau à enregistrer."
  exit 0
fi
total=$(($(wc -l < analyse/donnees/parties.csv) - 1))
git commit -q -m "Collecte : ${total} parties au total."
branche="${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD)}"
for essai in 1 2 3; do
  git pull -q --rebase origin "$branche" && git push -q origin "HEAD:$branche" && echo "Enregistré : ${total} parties." && exit 0
  sleep 5
done
exit 1
