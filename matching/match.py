#!/usr/bin/env python3
"""Démo CLI du moteur de matching (couche 2). Logique dans engine.py.
Usage : python3 match.py [cv.txt]   (défaut: cv_test.txt — profil FICTIF)
Sortie : data/match_result.json
RÈGLE données perso : ne jamais écrire un CV réel dans le brain partagé / un doc domaine."""
import json, os, sys
from engine import run_match, build_candidate_text

HERE = os.path.dirname(__file__)
CV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "cv_test.txt")
OUT = os.path.join(HERE, "data", "match_result.json")

cv_text = open(CV, encoding="utf-8").read()
print(f"CV : {os.path.basename(CV)} -> matching…")
res = run_match(build_candidate_text(cv_text=cv_text))
res["_cv_file"] = os.path.basename(CV)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"OK -> {OUT}  ({len(res.get('lettres',[]))} lettres)")
print(f"  profil : {res.get('profil','')[:90]}")
for off in res.get("offres", [])[:6]:
    ss = off.get("sous_scores", {})
    sub = "/".join(str(ss.get(k, '-')) for k in ("competences", "secteur", "seniorite", "localisation"))
    print(f"  {off.get('fit','?'):>3}%  [{sub}]  {off['offre']['titre'][:42]:42}")
