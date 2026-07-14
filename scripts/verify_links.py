#!/usr/bin/env python3
"""Vérifie que les liens des offres actives pointent vers une annonce ENCORE OUVERTE.
Une offre pourvue renvoie souvent un HTTP 200 + une page « no longer available » →
le code seul ne suffit pas, on inspecte le contenu. Politique SAFE :
  - confirmé mort (marqueur explicite dans la page)         -> archive (raison: lien expiré)
  - 404 / 410 / page introuvable                            -> archive (raison: lien introuvable)
  - bloqué / timeout / 999 / erreur réseau (non concluant)  -> ON GARDE (bénéfice du doute)
Idempotent : déplace les morts de offers_active.csv vers offers_archive.csv.
Usage: python3 verify_links.py            (applique, LinkedIn inclus ~5 min)
       python3 verify_links.py --dry-run  (rapport seulement)
       python3 verify_links.py --fast     (hors-LinkedIn seulement, threadé ~15s — pour le cron)"""
import csv, os, json, ssl, sys, time, datetime, urllib.request, urllib.error
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
ACTIVE = os.path.join(DATA, "offers_active.csv")
ARCHIVE = os.path.join(DATA, "offers_archive.csv")
DRY = "--dry-run" in sys.argv
FAST = "--fast" in sys.argv      # cron : hors-LinkedIn uniquement (rapide), LinkedIn géré par le cycle de vie Apify

CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

# Marqueurs « offre fermée » par famille de site (en minuscules).
DEAD_MARKERS = [
    "no longer accepting applications", "no longer available",
    "this job is no longer", "cette offre n'est plus", "offre expir",
    "offre clôtur", "offre pourvue", "annonce expir", "n'existe plus",
    "page introuvable", "page not found", "offre introuvable",
    "aucune offre", "cette annonce a expir",
]


def check(row):
    url = (row.get("url") or "").strip()
    if not url:
        return "dead", "lien vide"
    req = urllib.request.Request(url, headers=UA)
    try:
        resp = urllib.request.urlopen(req, timeout=12, context=CTX)
        html = resp.read(400000).decode("utf-8", "ignore").lower()
        code = resp.getcode()
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return "dead", f"http {e.code}"
        return "keep", f"http {e.code}"          # 403/429/999... non concluant
    except Exception as e:
        return "keep", type(e).__name__          # timeout/reset/dns -> on garde
    if any(m in html for m in DEAD_MARKERS):
        return "dead", "offre fermée"
    return "ok", str(code)


def main():
    rows = list(csv.DictReader(open(ACTIVE, encoding="utf-8")))
    fields = rows[0].keys() if rows else []
    # LinkedIn bloque le parallélisme (429) -> séquentiel avec pacing ; le reste -> threadé.
    li = [i for i, r in enumerate(rows) if "linkedin.com" in (r.get("url") or "")]
    other = [i for i, r in enumerate(rows) if i not in set(li)]
    results = {i: ("keep", "skip") for i in range(len(rows))}  # défaut = on garde
    mode = "FAST (hors-LinkedIn seulement)" if FAST else "complète"
    print(f"Vérification {mode} : {len(other)} hors-LinkedIn (threadé)"
          + ("" if FAST else f" + {len(li)} LinkedIn (séquentiel)") + "…")
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i, res in zip(other, ex.map(lambda i: check(rows[i]), other)):
            results[i] = res
    if not FAST:
        for n, i in enumerate(li):
            results[i] = check(rows[i])
            time.sleep(0.7)
            if (n + 1) % 40 == 0:
                print(f"  …LinkedIn {n + 1}/{len(li)}")

    dead_idx = [i for i, (v, _) in results.items() if v == "dead"]
    kept_unsure = sum(1 for v, _ in results.values() if v == "keep")
    ok = sum(1 for v, _ in results.values() if v == "ok")
    print(f"  ✅ ouvertes : {ok}")
    print(f"  ⚠️  non concluant (gardées) : {kept_unsure}")
    print(f"  💀 fermées/introuvables (à archiver) : {len(dead_idx)}")
    for i in dead_idx:
        print(f"     - {results[i][1]:18} | {rows[i]['titre'][:48]} — {rows[i]['entreprise'][:24]}")

    if DRY or not dead_idx:
        print("(dry-run / rien à faire)" if DRY else "Aucun lien mort confirmé.")
        return

    today = datetime.date.today().isoformat()
    dead_rows, live_rows = [], []
    for i, r in enumerate(rows):
        if i in dead_idx:
            r["statut"] = "expiré"
            r["raison_archive"] = f"lien {results[i][1]} ({today})"
            r["last_seen"] = today
            dead_rows.append(r)
        else:
            live_rows.append(r)

    # append aux archives (créer le header si besoin)
    arch_exists = os.path.exists(ARCHIVE)
    with open(ARCHIVE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not arch_exists:
            w.writeheader()
        for r in dead_rows:
            w.writerow(r)
    # réécrit l'actif sans les morts
    with open(ACTIVE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in live_rows:
            w.writerow(r)

    # marque aussi le store.json (source de vérité du cycle de vie) sinon le prochain
    # run_portal réécrit les morts en actives. Clé store = URL sans query/fragment (cf run_portal._key).
    store_path = os.path.join(DATA, "store.json")
    if os.path.exists(store_path):
        store = json.load(open(store_path, encoding="utf-8"))
        marked = 0
        for r in dead_rows:
            k = (r.get("url") or "").strip().split("#", 1)[0].split("?", 1)[0].rstrip("/")
            if k in store:
                store[k]["statut"] = "archive"
                store[k]["raison_archive"] = r["raison_archive"]
                store[k]["last_seen"] = today
                marked += 1
        json.dump(store, open(store_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  store.json : {marked}/{len(dead_rows)} clés marquées archive")
    print(f"\n→ {len(dead_rows)} offres archivées · {len(live_rows)} actives restantes.")


if __name__ == "__main__":
    main()
