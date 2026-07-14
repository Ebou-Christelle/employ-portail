#!/usr/bin/env python3
"""Couche 1 — collecteurs multi-sources d'offres d'emploi (générique, réutilisable Yelema).
Chaque collecteur renvoie une liste de dicts normalisés. RÈGLE DURE : aucune donnée inventée.
Tout champ inconnu = "" (jamais comblé par déduction non sourcée). La source (nom+URL+date
de collecte) accompagne CHAQUE offre."""
import re, time, datetime, urllib.parse
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
TODAY = datetime.date.today().isoformat()
HEADERS = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}


_SESS = requests.Session()
_SESS.headers.update({
    "User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive"})


def _get(url, timeout=25, retries=3):
    last = None
    for i in range(retries):
        try:
            r = _SESS.get(url, timeout=timeout, allow_redirects=True)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _txt(el):
    return el.get_text(" ", strip=True) if el else ""


def _rec(**kw):
    base = dict(titre="", entreprise="", lieu="", contrat="", secteur="", niveau="",
               date_pub="", date_limite="", salaire="", url="", source="", date_collecte=TODAY)
    base.update(kw)
    return base


# ---------------------------------------------------------------- NOVOJOB (CI)
def novojob(max_pages=6, pause=1.0):
    out, seen = [], set()
    for p in range(1, max_pages + 1):
        url = f"https://www.novojob.com/cote-d-ivoire/offres-d-emploi?page={p}"
        try:
            soup = BeautifulSoup(_get(url), "html.parser")
        except Exception as e:
            print(f"  [novojob] page {p} fail: {e}"); break
        cards = soup.find_all(class_="job-details")
        if not cards:
            # page 200 mais vide = soft-block transitoire → un retry après pause
            time.sleep(4)
            try:
                cards = BeautifulSoup(_get(url), "html.parser").find_all(class_="job-details")
            except Exception:
                cards = []
            if not cards:
                print(f"  [novojob] page {p}: vide (stop)")
                break
        new = 0
        for c in cards:
            a = c.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            if href in seen:
                continue
            seen.add(href)
            title = _txt(c.find("h2"))
            company = _txt(c.find(class_="contact"))
            loc = lvl = pub = ""
            mk = c.find("i", class_="fa-map-marker")
            if mk and mk.parent:
                loc = _txt(mk.parent)
            ck = c.find("i", class_="fa-clock-o")
            if ck and ck.parent:
                pub = _txt(ck.parent)
            bk = c.find("i", class_="fa-bookmark")
            if bk and bk.parent:
                lvl = _txt(bk.parent)
            if title:
                out.append(_rec(titre=title, entreprise=company, lieu=loc, niveau=lvl,
                                date_pub=pub, url=href, source="Novojob"))
                new += 1
        print(f"  [novojob] page {p}: +{new} (total {len(out)})")
        if new == 0:
            break
        time.sleep(pause)
    return out


# ------------------------------------------------------------ EDUCARRIERE (CI)
def educarriere(pause=1.0):
    out, seen = [], set()
    for url in ["https://emploi.educarriere.ci/", "https://emploi.educarriere.ci/emploi/page/all"]:
        try:
            soup = BeautifulSoup(_get(url), "html.parser")
        except Exception as e:
            print(f"  [educarriere] {url} fail: {e}"); continue
        for post in soup.find_all(class_="rt-post"):
            a = post.select_one("h4.post-title a[href]") or post.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            if not re.search(r"/offre-\d+-", href) or href in seen:
                continue
            seen.add(href)
            title = _txt(post.select_one("h4.post-title"))
            company = ""
            img = post.find("img")
            if img and img.get("title"):
                t = img["title"]
                if " recrute " in t:
                    company = t.split(" recrute ")[0].strip()
            pub = lim = ""
            meta = _txt(post.find(class_="rt-meta"))
            dates = re.findall(r"(\d{2}/\d{2}/\d{4})", meta)
            if dates:
                pub = dates[0]
                if len(dates) > 1:
                    lim = dates[1]
            if title:
                out.append(_rec(titre=title, entreprise=company, lieu="Côte d'Ivoire",
                                date_pub=pub, date_limite=lim, url=href, source="Educarriere"))
        time.sleep(pause)
    print(f"  [educarriere] total {len(out)}")
    return out


# ---------------------------------------------------------------- RMO (CI)
RMO_BASE = "https://www.rmo-jobcenter.com/"


def _abs(href):
    return urllib.parse.urljoin(RMO_BASE, href.lstrip("/"))


def rmo(pause=1.0):
    out, seen = [], set()
    try:
        idx = BeautifulSoup(_get(_abs("fr/cote-d-ivoire/offres-emploi.html")), "html.parser")
    except Exception as e:
        print(f"  [rmo] index fail: {e}"); return out
    cats = {}
    for a in idx.find_all("a", href=True):
        h = a["href"]
        if re.search(r"/cote-d-ivoire/offres-emploi/[a-z0-9-]+\.html$", h):
            label = _txt(a)
            sect = re.sub(r"\s*\(\d+\)\s*$", "", label).strip()
            cats[_abs(h)] = sect
    for caturl, sect in cats.items():
        try:
            soup = BeautifulSoup(_get(caturl), "html.parser")
        except Exception:
            continue
        for a in soup.find_all("a", href=True):
            if not re.search(r"/offres-emploi/[^/]+/\d+-", a["href"]):
                continue
            href = _abs(a["href"])
            if href in seen:
                continue
            seen.add(href)
            # title from slug (anchor text is "+détails")
            slug = href.rstrip(".html").split("/")[-1]
            slug = re.sub(r"^\d+-", "", slug)
            title = slug.replace("-", " ").title()
            ref = ""
            m = re.search(r"/(\d+)-", a["href"])
            if m:
                ref = m.group(1)
            out.append(_rec(titre=title, lieu="Côte d'Ivoire", secteur=sect,
                            url=href, source="RMO Jobcenter"))
        time.sleep(pause)
    print(f"  [rmo] total {len(out)} sur {len(cats)} catégories")
    return out


# ------------------------------------------------ LinkedIn (via Apify, fichier)
def linkedin():
    """Lit data/linkedin_offers.json (produit par fetch_apify_linkedin.py). Pas de coût ici."""
    import json, os
    path = os.path.join(os.path.dirname(__file__), "..", "data", "linkedin_offers.json")
    if not os.path.exists(path):
        print("  [linkedin] pas de fichier (lancer fetch_apify_linkedin.py)"); return []
    recs = json.load(open(path, encoding="utf-8"))
    for r in recs:
        r.setdefault("date_collecte", TODAY)
    print(f"  [linkedin] {len(recs)} (depuis fichier Apify)")
    return recs


COLLECTORS = {"Novojob": novojob, "Educarriere": educarriere, "RMO Jobcenter": rmo, "LinkedIn": linkedin}

if __name__ == "__main__":
    import json, sys
    name = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = {}
    for k, fn in COLLECTORS.items():
        if name in ("all", k):
            print(f"== {k} ==")
            res[k] = fn()
    total = sum(len(v) for v in res.values())
    print(f"\nTOTAL {total}")
    print(json.dumps((res.get("Novojob") or res.get(name) or [])[:2], ensure_ascii=False, indent=2))
