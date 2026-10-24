#!/usr/bin/env bash
# Committe et pousse les parties et les résultats de « Identifier les champions forts du patch »
# (analyse/donnees_patch et analyse/resultats_patch), sur la branche du code. Jamais analyse/donnees.
set -u
cd "$(git rev-parse --show-toplevel)"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
branche="$(git rev-parse --abbrev-ref HEAD)"
patch="$(cat analyse/donnees_patch/dernier_patch.txt 2>/dev/null || echo '?')"
total() { if [ -e "analyse/donnees_patch/$patch/parties.csv" ]; then echo $(($(wc -l < "analyse/donnees_patch/$patch/parties.csv") - 1)); else echo 0; fi; }
for dossier in analyse/donnees_patch analyse/resultats_patch; do
  if [ -e "$dossier" ]; then git add "$dossier"; fi
done
if git diff --cached --quiet; then
  echo "Rien de nouveau à enregistrer."
  exit 0
fi
git commit -q -m "Champions du patch $patch : $(total) parties"
for essai in 1 2 3 4 5; do
  if git pull -q --rebase origin "$branche" && git push -q origin "HEAD:$branche"; then
    echo "Enregistré : patch $patch, $(total) parties."
    exit 0
  fi
  git rebase --abort 2>/dev/null
  sleep $((5 + RANDOM % 10))
done
echo "::warning::Enregistrement impossible pour l'instant, nouvel essai au prochain intervalle."
exit 1
