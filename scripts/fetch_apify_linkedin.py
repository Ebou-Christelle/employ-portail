#!/usr/bin/env python3
"""Récupère un dataset Apify (acteur curious_coder/linkedin-jobs-scraper) et le normalise
au schéma du portail → data/linkedin_offers.json. NE relance PAS de run payant : lit un
dataset existant (id passé en arg, sinon /tmp/dc/li_run.txt). source = LinkedIn.
Lien pour postuler = applyUrl si présent, sinon link (page LinkedIn avec bouton Postuler)."""
import json, os, sys, datetime, urllib.request

TODAY = datetime.date.today().isoformat()
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "linkedin_offers.json")
TOK = open(os.path.expanduser("~/.config/agents/secrets/apify.txt")).read().strip()


def dataset_id():
    if len(sys.argv) > 1:
        return sys.argv[1]
    line = open("/tmp/dc/li_run.txt").read().split()
    return line[1]  # "RID DSID"


def fetch(dsid):
    items, off = [], 0
    while True:
        url = f"https://api.apify.com/v2/datasets/{dsid}/items?token={TOK}&offset={off}&limit=1000&clean=true"
        batch = json.load(urllib.request.urlopen(url, timeout=60))
        if not batch:
            break
        items.extend(batch)
        off += len(batch)
        if len(batch) < 1000:
            break
    return items


def norm(j):
    apply_link = (j.get("applyUrl") or "").strip() or (j.get("link") or "").strip()
    inds = j.get("industries")
    if isinstance(inds, list):
        inds = ", ".join(inds)
    return {
        "titre": (j.get("title") or "").strip(),
        "entreprise": (j.get("companyName") or "").strip(),
        "lieu": (j.get("location") or "").strip(),
        "contrat": (j.get("employmentType") or "").strip(),
        "secteur": (inds or j.get("jobFunction") or "").strip() if isinstance(inds or j.get("jobFunction"), str) else "",
        "niveau": (j.get("seniorityLevel") or "").strip(),
        "date_pub": (j.get("postedAt") or "").strip(),
        "date_limite": "",
        "salaire": (j.get("salary") or "").strip() if isinstance(j.get("salary"), str) else "",
        "url": apply_link,
        "source": "LinkedIn",
        "date_collecte": TODAY,
    }


def main():
    dsid = dataset_id()
    items = fetch(dsid)
    recs = [norm(j) for j in items if (j.get("title") and j.get("link"))]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(recs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"LinkedIn: {len(recs)} offres normalisées -> {os.path.abspath(OUT)}")
    # contrôle géo : ne garder que la Côte d'Ivoire (le filtre LinkedIn peut déborder)
    ci = [r for r in recs if "ivoire" in r["lieu"].lower() or "abidjan" in r["lieu"].lower() or not r["lieu"]]
    print(f"  dont CI/Abidjan (ou lieu vide) : {len(ci)}")


if __name__ == "__main__":
    main()
