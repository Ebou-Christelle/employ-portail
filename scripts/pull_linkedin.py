#!/usr/bin/env python3
"""Lance un run Apify LinkedIn (CI, 30j), attend la fin, écrit data/linkedin_offers.json.
Pour le cron hebdo (autonome). Budget : ~$0.25/run. Garde-fou wall-clock ~5 min."""
import json, os, time, datetime, urllib.request

TODAY = datetime.date.today().isoformat()
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "data", "linkedin_offers.json")
TOK = os.environ.get("APIFY_TOKEN", "").strip()
if not TOK:  # secours : ancien emplacement fichier (machine Mstudio)
    TOK = open(os.path.expanduser("~/.config/agents/secrets/apify.txt")).read().strip()
ACTOR = "curious_coder~linkedin-jobs-scraper"
COUNT = int(os.environ.get("LI_COUNT", "250"))
URL = "https://www.linkedin.com/jobs/search/?location=C%C3%B4te%20d%27Ivoire&f_TPR=r2592000&sortBy=DD"


def post(url, body):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=40))


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=60))


def norm(j):
    apply_link = (j.get("applyUrl") or "").strip() or (j.get("link") or "").strip()
    inds = j.get("industries")
    inds = ", ".join(inds) if isinstance(inds, list) else (inds or j.get("jobFunction") or "")
    return {"titre": (j.get("title") or "").strip(), "entreprise": (j.get("companyName") or "").strip(),
            "lieu": (j.get("location") or "").strip(), "contrat": (j.get("employmentType") or "").strip(),
            "secteur": inds if isinstance(inds, str) else "", "niveau": (j.get("seniorityLevel") or "").strip(),
            "date_pub": (j.get("postedAt") or "").strip(), "date_limite": "",
            "salaire": (j.get("salary") or "").strip() if isinstance(j.get("salary"), str) else "",
            "url": apply_link, "source": "LinkedIn", "date_collecte": TODAY}


def main():
    run = post(f"https://api.apify.com/v2/acts/{ACTOR}/runs?token={TOK}",
               {"urls": [URL], "count": COUNT, "scrapeCompany": False})["data"]
    rid, dsid = run["id"], run["defaultDatasetId"]
    print(f"run {rid} dataset {dsid}")
    # LI_WAIT : temps d'attente max du run Apify (défaut 150s, héritage du cron Mstudio ;
    # en GitHub Actions on met plus long, aucun timeout global ne nous presse)
    deadline = time.time() + int(os.environ.get("LI_WAIT", "150"))
    while time.time() < deadline:
        time.sleep(15)
        st = get(f"https://api.apify.com/v2/actor-runs/{rid}?token={TOK}")["data"]["status"]
        print("  status", st)
        if st in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    items, off = [], 0
    while True:
        batch = get(f"https://api.apify.com/v2/datasets/{dsid}/items?token={TOK}&offset={off}&limit=1000&clean=true")
        if not batch:
            break
        items.extend(batch); off += len(batch)
        if len(batch) < 1000:
            break
    recs = [norm(j) for j in items if j.get("title") and j.get("link")]
    if not recs and os.path.exists(OUT):
        print("0 résultat — on garde le fichier précédent"); return
    json.dump(recs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"LinkedIn: {len(recs)} offres -> {OUT}")


if __name__ == "__main__":
    main()
