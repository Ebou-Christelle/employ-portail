#!/usr/bin/env python3
"""Pousse le portail (modèle cycle de vie) dans le GSheet :
  - 'Offres actives ⭐'  : la base vivante (avec LIEN POUR POSTULER sur chaque offre)
  - 'Archive'           : offres sorties du portail + raison + date
  - 'Synthèse'          : intelligence marché (par score/secteur/niveau/source)
Renomme les anciens onglets Phase 1. Token zuri@. Champs vides = non publiés (jamais inventés)."""
import json, csv, os, urllib.request, urllib.parse
from collections import Counter

SID = "1gVK-uouTs-KhJ4l1iiShUrcuGaugWqP7S7r24BQILPU"
HERE = os.path.dirname(__file__)
TOK = json.load(open("/tmp/dc/zuri.json"))
CRED = json.load(open("/home/openclaw/.config/gogcli/credentials.json"))


def access_token():
    data = urllib.parse.urlencode({"client_id": CRED["client_id"], "client_secret": CRED["client_secret"],
                                   "refresh_token": TOK["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data)))["access_token"]


AT = access_token()


def api(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + AT); req.add_header("Content-Type", "application/json")
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:400]); raise


def rd(name):
    return list(csv.DictReader(open(os.path.join(HERE, "..", "data", name), encoding="utf-8")))


actives, archives = rd("offers_active.csv"), rd("offers_archive.csv")

ACT_H = ["⭐", "Score", "Intitulé", "Entreprise", "Métier", "Secteur", "Niveau", "Lieu", "Contrat",
         "Date publication", "Date limite", "Salaire", "Source", "Lien pour postuler",
         "Niveau (source)", "1ère vue", "Dernière vue"]
ACT = [[r["score_etoiles"], r["score_dc"], r["titre"], r["entreprise"], r.get("metier_norm", ""),
        r["secteur_norm"], r["niveau_norm"], r["lieu"], r["contrat"], r["date_pub"], r["date_limite"],
        r["salaire"], r["source"], r["url"], r["niveau_source"], r.get("first_seen", ""),
        r.get("last_seen", "")] for r in actives]

ARC_H = ["⭐", "Score", "Intitulé", "Entreprise", "Métier", "Secteur", "Niveau", "Source", "Lien",
         "Date limite", "Raison archive", "Archivée le (dernière vue)"]
ARC = [[r["score_etoiles"], r["score_dc"], r["titre"], r["entreprise"], r.get("metier_norm", ""),
        r["secteur_norm"], r["niveau_norm"], r["source"], r["url"], r["date_limite"],
        r.get("raison_archive", ""), r.get("last_seen", "")] for r in archives]

n = len(actives)
def blk(title, c, order=None):
    items = c.most_common() if order is None else [(k, c.get(k, 0)) for k in order]
    return [[title, "Nb"]] + [[str(k), str(v)] for k, v in items if v] + [[""]]

SYN = [["Synthèse — intelligence marché emploi CI (MAJ 2026-06-19)"], [""],
       [f"Offres ACTIVES : {n}   |   en Archive : {len(archives)}"],
       ["Sources : LinkedIn (via Apify) + Novojob + Educarriere + RMO Jobcenter."],
       ["Cycle de vie : une offre dont la date limite passe, ou qui disparaît de sa source, bascule en Archive."],
       ["Champs Salaire/Contrat vides = non publiés à la source (jamais inventés)."], [""]]
SYN += blk("Par score ⭐ (pertinence DC)", Counter(int(r["score_dc"]) for r in actives), [5, 4, 3, 2, 1])
SYN += blk("Par métier", Counter(r.get("metier_norm", "") for r in actives))
SYN += blk("Par secteur", Counter(r["secteur_norm"] for r in actives))
SYN += blk("Par niveau", Counter(r["niveau_norm"] for r in actives),
           ["Manager/Direction", "Senior", "Confirmé", "Junior", "Stage"])
SYN += blk("Par source", Counter(r["source"] for r in actives))
SYN += [["KPI futur portail : vues, clics, candidatures, taux conversion par offre ;"],
        ["+ KPI insertion DC : mises en relation, placements, temps-vers-placement, rétention."]]

# ---- onglets : créer/renommer ----
meta = api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}?fields=sheets.properties")
ex = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
reqs = []
renames = {"Base Phase 1 ⭐": "Offres actives ⭐", "Synthèse Phase 1": "Synthèse"}
for old, new in renames.items():
    if old in ex and new not in ex:
        reqs.append({"updateSheetProperties": {"properties": {"sheetId": ex[old], "title": new}, "fields": "title"}})
for title in ("Offres actives ⭐", "Archive", "Synthèse"):
    if title not in ex and title not in renames.values():
        reqs.append({"addSheet": {"properties": {"title": title, "gridProperties": {"frozenRowCount": 1}}}})
if reqs:
    api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", {"requests": reqs})
meta = api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}?fields=sheets.properties")
ids = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def clear(tab):
    api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{urllib.parse.quote(tab)}:clear", {})


def put(tab, values):
    api("PUT", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{urllib.parse.quote(tab+'!A1')}?valueInputOption=RAW", {"values": values})


for tab, data in (("Offres actives ⭐", [ACT_H] + ACT), ("Archive", [ARC_H] + ARC), ("Synthèse", SYN)):
    clear(tab); put(tab, data)

# ---- mise en forme ----
fmt = []
for tab in ("Offres actives ⭐", "Archive", "Synthèse"):
    sid = ids[tab]
    fmt.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                 "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.40}}},
        "fields": "userEnteredFormat(textFormat,backgroundColor)"}})
    fmt.append({"autoResizeDimensions": {"dimensions": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 17}}})
sidb = ids["Offres actives ⭐"]
fmt.append({"setBasicFilter": {"filter": {"range": {"sheetId": sidb, "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": 17}}}})
for col, w in [(2, 300), (13, 300), (3, 170)]:
    fmt.append({"updateDimensionProperties": {"range": {"sheetId": sidb, "dimension": "COLUMNS",
                "startIndex": col, "endIndex": col + 1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})
api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", {"requests": fmt})

# ---- Lisez-moi (réécrit) ----
readme = [
 ["Portail Intelligence Emploi — Diaspora Connect (& réutilisable Yelema)"],
 ["MAJ 2026-06-19."], [""],
 ["Onglets :"],
 ["  • Offres actives ⭐  : la base VIVANTE. Triée par score ⭐ (pertinence DC). Lien pour postuler sur chaque offre."],
 ["  • Archive           : offres sorties du portail (date limite passée OU retirées de la source) + raison + date."],
 ["  • Synthèse          : intelligence marché (répartition par score/secteur/niveau/source)."],
 ["  • Source Map        : cartographie des sources."],
 [""],
 ["Scoring ⭐ (1 à 5) par niveau de qualification : valorise les cadres MAIS garde les junior/stage"],
 ["intéressants (beaucoup de young graduates postulent à DC). Le score priorise, il n'exclut rien."],
 [""],
 [f"Sources actives : LinkedIn (via Apify, {sum(1 for r in actives if r['source']=='LinkedIn')} offres) + Novojob + Educarriere + RMO Jobcenter."],
 ["Cycle de vie automatique : à chaque rafraîchissement, les offres expirées/disparues passent en Archive."],
 ["Règle d'or : zéro donnée inventée. Salaire/contrat vides = non publiés à la source."],
]
clear("Lisez-moi"); put("Lisez-moi", readme)

print(f"OK — actives {n} | archive {len(archives)}")
print("URL", f"https://docs.google.com/spreadsheets/d/{SID}/edit")
