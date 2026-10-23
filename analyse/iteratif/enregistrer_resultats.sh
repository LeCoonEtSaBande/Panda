#!/usr/bin/env bash
# Committe et pousse analyse/iteratif/resultats/ sur la branche du code (jamais les données).
set -u
cd "$(git rev-parse --show-toplevel)"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
branche="$(git rev-parse --abbrev-ref HEAD)"
git add analyse/iteratif/resultats
if git diff --cached --quiet; then
  echo "Aucun résultat à enregistrer."
  exit 0
fi
# (Le message par défaut est dans une variable : une apostrophe dans ${1:-...} casse bash.)
message_defaut="Résultats de l'analyse itérative"
git commit -q -m "${1:-$message_defaut}"
for essai in 1 2 3; do
  if git pull -q --rebase origin "$branche" && git push -q origin "HEAD:$branche"; then
    echo "Résultats enregistrés sur $branche."
    exit 0
  fi
  git rebase --abort 2>/dev/null
  sleep 5
done
echo "::error::Impossible de pousser les résultats."
exit 1
