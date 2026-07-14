#!/usr/bin/env bash
# Rafraîchissement hebdo du Portail Emploi Diaspora Connect (lancé en precheck par le cron).
# Pipeline déterministe : token zuri@ -> LinkedIn (Apify) -> moteur cycle de vie -> push GSheet.
# Exit 0 (toujours, sauf token manquant) pour que le cron envoie le résumé.
set -uo pipefail
DIR="/home/openclaw/agents/main/projects/diaspora-emploi-portal"
export GOG_KEYRING_PASSWORD=""
mkdir -p /tmp/dc

echo "== [1/4] token zuri@ =="
rm -f /tmp/dc/zuri.json
gog auth tokens export zuri@mstudio.vc --out /tmp/dc/zuri.json || { echo "TOKEN FAIL"; exit 1; }

# ⚠️ Le cron wrappe ce script dans `timeout 300` (run-job.sh). Somme des timeouts < 300s,
# sinon le precheck est tué -> claude non lancé -> pas de résumé Telegram.
echo "== [2/6] LinkedIn (Apify) =="
timeout 145 python3 "$DIR/scripts/pull_linkedin.py" || echo "  (LinkedIn KO/lent — on continue avec le fichier précédent)"

echo "== [3/6] moteur cycle de vie =="
timeout 55 python3 "$DIR/scripts/run_portal.py" || echo "  (run_portal a renvoyé une erreur)"

# Vérif liens : sort les annonces fermées des sites tolérants (Novojob/Educarriere/RMO).
# Les LinkedIn pourvues sont déjà droppées par le cycle de vie Apify (étape précédente).
echo "== [4/6] vérif liens (hors-LinkedIn, rapide) =="
timeout 18 python3 "$DIR/scripts/verify_links.py" --fast || echo "  (verify KO — on continue)"

echo "== [5/6] push GSheet =="
timeout 45 python3 "$DIR/scripts/push_portal_sheet.py" || echo "  (push KO)"

echo "== [6/6] rebuild + republie le front (GitHub Pages) =="
timeout 30 bash "$DIR/scripts/publish_site.sh" || echo "  (publish KO)"

echo "== terminé =="
exit 0
