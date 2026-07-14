#!/usr/bin/env python3
"""Phase 1 — orchestre la collecte multi-sources, classe, déduplique, écrit le CSV sourcé.
Sortie : data/offers_phase1.csv (1 ligne/offre, source obligatoire)."""
import csv, os, re, unicodedata
from collectors import COLLECTORS
from classify import classify

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "offers_phase1.csv")
COLS = ["score_etoiles", "score_dc", "titre", "entreprise", "secteur_norm", "niveau_norm",
        "lieu", "contrat", "date_pub", "date_limite", "salaire",
        "niveau_source", "secteur_source", "source", "url", "date_collecte"]


def _key(rec):
    def n(s):
        s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()
    t, c = n(rec.get("titre")), n(rec.get("entreprise"))
    return (t, c) if c and "anonyme" not in c else (t, n(rec.get("source")))


def main():
    raw = []
    for name, fn in COLLECTORS.items():
        print(f"== {name} ==")
        try:
            raw.extend(fn())
        except Exception as e:
            print(f"  !! {name} échec: {e}")
    print(f"\nCollectées (brut) : {len(raw)}")

    seen, deduped = set(), []
    for r in raw:
        k = _key(r)
        if k in seen:
            continue
        seen.add(k)
        r["niveau_source"] = r.get("niveau", "")
        r["secteur_source"] = r.get("secteur", "")
        deduped.append(classify(r))
    print(f"Après dédup : {len(deduped)}")

    deduped.sort(key=lambda r: (-r["score_dc"], r["secteur_norm"], r["source"]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in deduped:
            w.writerow(r)
    print(f"Écrit : {os.path.abspath(OUT)}")

    # résumés
    from collections import Counter
    print("\nPar source :", dict(Counter(r["source"] for r in deduped)))
    print("Par score  :", dict(sorted(Counter(r["score_dc"] for r in deduped).items(), reverse=True)))
    print("Par secteur:", dict(Counter(r["secteur_norm"] for r in deduped).most_common()))
    print("Par niveau :", dict(Counter(r["niveau_norm"] for r in deduped).most_common()))


if __name__ == "__main__":
    main()
