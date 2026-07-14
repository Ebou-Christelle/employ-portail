#!/usr/bin/env python3
"""Portail emploi — moteur avec CYCLE DE VIE (active vs archive).
À chaque run :
  1. collecte multi-sources (Novojob, Educarriere, RMO, LinkedIn via fichier Apify)
  2. upsert dans un store persistant (data/store.json), clé = URL
  3. règle d'archivage :
       - date limite dépassée (< aujourd'hui)  -> archive (raison: date limite dépassée)
       - offre disparue de la source           -> archive (raison: retirée de la source)
         (UNIQUEMENT si la source a bien répondu ce run, sinon on ne touche pas)
  4. classe (secteur/niveau/score ⭐) et écrit data/offers_active.csv + data/offers_archive.csv
Le portail n'affiche que les ACTIVES ; les passées vont dans l'Archive.
RÈGLE : zéro donnée inventée (champ inconnu = vide)."""
import csv, json, os, re, datetime, unicodedata
from collectors import COLLECTORS
from classify import classify

HERE = os.path.dirname(__file__)
STORE = os.path.join(HERE, "..", "data", "store.json")
ACTIVE = os.path.join(HERE, "..", "data", "offers_active.csv")
ARCH = os.path.join(HERE, "..", "data", "offers_archive.csv")
TODAY = datetime.date.today()
COLS = ["score_etoiles", "score_dc", "titre", "entreprise", "metier_norm", "secteur_norm", "niveau_norm",
        "lieu", "contrat", "date_pub", "date_limite", "salaire", "source", "url",
        "niveau_source", "secteur_source", "first_seen", "last_seen", "statut", "raison_archive"]


def _key(rec):
    # Clé = URL SANS query/fragment : l'identité d'une offre est dans le chemin
    # (LinkedIn ajoute ?position=&refId= volatiles à chaque scrape -> sinon faux archivage).
    u = (rec.get("url") or "").strip().split("#", 1)[0].split("?", 1)[0].rstrip("/")
    if u:
        return u
    def n(s):
        s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()
    return n(rec.get("titre")) + "|" + n(rec.get("source"))


def parse_deadline(s):
    s = (s or "").strip()
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s)        # dd/mm/yyyy (Educarriere)
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)         # yyyy-mm-dd
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


_FR_MOIS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
            "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10,
            "novembre": 11, "décembre": 12, "decembre": 12}


def parse_pub(s):
    """Date de publication : ISO, dd/mm/yyyy, ou 'JJ Mois' (français, sans année -> année
    la plus récente <= aujourd'hui). None si illisible."""
    s = (s or "").strip()
    if not s:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    m = re.match(r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)", s)       # "19 Juin"
    if m:
        mois = _FR_MOIS.get(m.group(2).lower())
        if mois:
            day = int(m.group(1))
            for yr in (TODAY.year, TODAY.year - 1):
                try:
                    d = datetime.date(yr, mois, day)
                except ValueError:
                    return None
                if d <= TODAY:
                    return d
    return None


def months_ago(d, n):
    """Date d - n mois (gère le débordement de mois + jours courts)."""
    import calendar
    y, m = d.year, d.month - n
    while m <= 0:
        m += 12; y -= 1
    return datetime.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def main():
    # 1. collecte + suivi des sources qui ont répondu
    fresh, ok_sources = {}, set()
    for name, fn in COLLECTORS.items():
        print(f"== {name} ==")
        try:
            recs = fn()
        except Exception as e:
            print(f"  !! {name} échec: {e}"); recs = []
        if recs:
            ok_sources.add(name)
        for r in recs:
            fresh[_key(r)] = r
    print(f"\nFraîches (dédup) : {len(fresh)} | sources OK : {sorted(ok_sources)}")

    # 2. store persistant
    store = json.load(open(STORE, encoding="utf-8")) if os.path.exists(STORE) else {}
    today = TODAY.isoformat()

    # upsert des fraîches
    for k, r in fresh.items():
        prev = store.get(k, {})
        r["first_seen"] = prev.get("first_seen", today)
        r["last_seen"] = today
        r["statut"] = "active"
        r["raison_archive"] = ""
        store[k] = r

    # 3. archivage
    n_deadline = n_gone = n_old = 0
    cutoff_10m = months_ago(TODAY, 10)   # offres publiées avant cette date = trop anciennes
    for k, r in store.items():
        dl = parse_deadline(r.get("date_limite"))
        if dl and dl < TODAY:
            if r.get("statut") != "archive":
                n_deadline += 1
            r["statut"] = "archive"; r["raison_archive"] = f"date limite dépassée ({r['date_limite']})"
            continue
        # ancienneté : date de publication (fallback first_seen) > 10 mois -> archive
        age_date = parse_pub(r.get("date_pub")) or parse_deadline(r.get("first_seen"))
        if age_date and age_date < cutoff_10m:
            if r.get("statut") != "archive":
                n_old += 1
            r["statut"] = "archive"
            r["raison_archive"] = f"offre de plus de 10 mois (publiée {age_date.isoformat()})"
            continue
        if k not in fresh:
            # disparue : archiver seulement si SA source a répondu ce run (sinon panne, on garde)
            if r.get("source") in ok_sources and r.get("statut") == "active":
                r["statut"] = "archive"; r["raison_archive"] = "retirée de la source"; n_gone += 1

    json.dump(store, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 4. classement + export
    actives, archives = [], []
    for r in store.values():
        r["niveau_source"] = r.get("niveau", "")
        r["secteur_source"] = r.get("secteur", "")
        c = classify(r)
        (archives if c["statut"] == "archive" else actives).append(c)
    actives.sort(key=lambda r: (-r["score_dc"], r["secteur_norm"], r["titre"]))
    archives.sort(key=lambda r: (r.get("last_seen", ""), r["titre"]), reverse=True)

    for path, rows in ((ACTIVE, actives), (ARCH, archives)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)

    from collections import Counter
    summary = {
        "date": today, "actives": len(actives), "archive": len(archives),
        "nouvelles_ce_run": sum(1 for r in actives if r.get("first_seen") == today),
        "archivees_ce_run": {"date_limite": n_deadline, "retirees_source": n_gone, "plus_10_mois": n_old},
        "sources_ok": sorted(ok_sources),
        "par_source": dict(Counter(r["source"] for r in actives)),
        "sheet": "https://docs.google.com/spreadsheets/d/1gVK-uouTs-KhJ4l1iiShUrcuGaugWqP7S7r24BQILPU/edit",
    }
    json.dump(summary, open(os.path.join(HERE, "..", "data", "last_refresh.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"\nACTIVES : {len(actives)}  |  ARCHIVE : {len(archives)}")
    print(f"  archivées ce run : {n_deadline} (date limite) + {n_gone} (retirées source) + {n_old} (>10 mois, avant {cutoff_10m})")
    print("  actives par source :", dict(Counter(r["source"] for r in actives)))
    print("  actives par score  :", dict(sorted(Counter(r["score_dc"] for r in actives).items(), reverse=True)))
    print("  actives par secteur:", dict(Counter(r["secteur_norm"] for r in actives).most_common()))


if __name__ == "__main__":
    main()
