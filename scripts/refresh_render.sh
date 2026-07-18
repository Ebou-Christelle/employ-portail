#!/usr/bin/env bash
# Rafraîchissement hebdo du portail — exécuté par le Cron Job Render (voir render.yaml).
# Chaîne : offres LinkedIn (Apify) + scrapers web -> cycle de vie -> rebuild front + index
# matching -> push vers le repo GitHub -> Render redéploie automatiquement board et matching.
#
# Variables d'env requises (à renseigner dans Render -> service cron -> Environment) :
#   APIFY_TOKEN     collecte des offres LinkedIn
#   OPENAI_API_KEY  reconstruction de l'index d'embeddings du matching
#   GITHUB_TOKEN    token GitHub (droits Contents read/write sur le repo) pour pousser le résultat
#
# Les étapes de collecte échouent "gracieusement" (on garde les données précédentes) ;
# les étapes de build, elles, doivent réussir (set -e).
set -euo pipefail

REPO="github.com/Ebou-Christelle/employ-portail.git"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== [0/6] clone frais du repo =="
git clone --depth 1 "https://x-access-token:${GITHUB_TOKEN}@${REPO}" "$WORK"
cd "$WORK"

echo "== [1/6] offres LinkedIn (Apify) =="
python3 scripts/pull_linkedin.py || echo "  (LinkedIn KO — on garde le fichier précédent)"

echo "== [2/6] collecte Novojob/Educarriere/RMO + cycle de vie =="
python3 scripts/run_portal.py || echo "  (run_portal a renvoyé une erreur — on continue)"

echo "== [3/6] vérification des liens morts =="
python3 scripts/verify_links.py --fast || echo "  (verify KO — on continue)"

echo "== [4/6] rebuild du front (site/index.html) =="
python3 scripts/build_site.py

echo "== [5/6] rebuild de l'index matching (embeddings des offres) =="
(cd matching && python3 build_offer_index.py)

echo "== [6/6] commit + push (déclenche le redéploiement Render) =="
git config user.name "refresh-bot"
git config user.email "refresh-bot@users.noreply.github.com"
git add data site matching/data/offer_index.json
if git diff --cached --quiet; then
  echo "Aucun changement cette semaine — rien à pousser."
  exit 0
fi
git commit -m "refresh hebdo des offres ($(date -u +%F))"
git push

echo "== refresh terminé =="
