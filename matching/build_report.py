#!/usr/bin/env python3
"""Rend data/match_result.json en rapport candidat HTML (rendu dans report.py).
Usage : python3 build_report.py [--demo]   -> data/rapport_candidat.html"""
import json, os, sys
from report import render_report

HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, "data", "match_result.json")
OUT = os.path.join(HERE, "data", "rapport_candidat.html")

r = json.load(open(RES, encoding="utf-8"))
html = render_report(r, demo="--demo" in sys.argv)
open(OUT, "w", encoding="utf-8").write(html)
print("OK ->", OUT, f"({len(html)} chars)")
