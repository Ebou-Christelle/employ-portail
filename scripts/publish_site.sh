#!/usr/bin/env bash
# Rebuild + republie le front statique sur GitHub Pages (compte leslita06).
# Publie depuis un dossier ISOLÉ /tmp (jamais depuis le workspace = repo git avec secrets).
# Pas de `git push -f`. Le token est lu localement (secrets.env), jamais hardcodé.
set -uo pipefail
DIR="/home/openclaw/agents/main/projects/diaspora-emploi-portal"
PUB="/tmp/dc-pub-v1"
REPO="diaspora-emploi-portal"

set -a; source ~/.config/agents/secrets.env 2>/dev/null; set +a
GH="${GITHUB_TOKEN:-}"
[ -z "$GH" ] && { echo "PUBLISH: pas de GITHUB_TOKEN, skip"; exit 0; }

python3 "$DIR/scripts/build_site.py" || { echo "PUBLISH: build_site KO"; exit 0; }

mkdir -p "$PUB"
cp -r "$DIR/site/." "$PUB"/
cd "$PUB" || exit 0
if [ ! -d "$PUB/.git" ]; then
  git init -q
  git config user.email "leslie@mstudio.vc"; git config user.name "Diaspora Connect"
  git branch -M main
  git remote add origin "https://leslita06:${GH}@github.com/leslita06/${REPO}.git" 2>/dev/null || \
    git remote set-url origin "https://leslita06:${GH}@github.com/leslita06/${REPO}.git"
  git fetch -q origin main 2>/dev/null && git reset -q --soft origin/main 2>/dev/null || true
else
  git remote set-url origin "https://leslita06:${GH}@github.com/leslita06/${REPO}.git"
fi
git add -A
if git diff --cached --quiet; then
  echo "PUBLISH: aucun changement"; exit 0
fi
git -c commit.gpgsign=false commit -q -m "refresh hebdo portail emploi"
git push -q origin main && echo "PUBLISH: front republié -> https://leslita06.github.io/${REPO}/"
exit 0
