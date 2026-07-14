#!/usr/bin/env python3
"""Pousse la Base Phase 1 (données RÉELLES scrapées + classées + scorées) dans le GSheet Étape 0.
- ajoute l'onglet 'Base Phase 1 ⭐' (86 offres, vraies URLs)
- ajoute l'onglet 'Synthèse Phase 1' (intelligence marché : par score/secteur/niveau/source)
- rétrograde l'ancien échantillon manuel + met à jour Lisez-moi
Token zuri@ (scope drive). Règle : champs vides = non publiés à la source (jamais inventés)."""
import json, csv, os, urllib.request, urllib.parse
from collections import Counter

SID = "1gVK-uouTs-KhJ4l1iiShUrcuGaugWqP7S7r24BQILPU"
CSV = os.path.join(os.path.dirname(__file__), "..", "data", "offers_phase1.csv")
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
    req.add_header("Authorization", "Bearer " + AT)
    req.add_header("Content-Type", "application/json")
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:500]); raise


rows = list(csv.DictReader(open(CSV, encoding="utf-8")))

HEADER = ["⭐", "Score", "Intitulé", "Entreprise", "Secteur", "Niveau", "Lieu", "Contrat",
          "Date publication", "Date limite", "Salaire", "Source", "Lien", "Niveau (libellé source)", "Date collecte"]
DATA = [[r["score_etoiles"], r["score_dc"], r["titre"], r["entreprise"], r["secteur_norm"], r["niveau_norm"],
         r["lieu"], r.get("contrat", ""), r["date_pub"], r["date_limite"], r.get("salaire", ""),
         r["source"], r["url"], r["niveau_source"], r["date_collecte"]] for r in rows]

# ---- Synthèse (intelligence marché) ----
def block(title, counter, order=None):
    items = counter.most_common() if order is None else [(k, counter.get(k, 0)) for k in order]
    return [[title, "Nb"]] + [[str(k), str(v)] for k, v in items if v] + [[""]]

n = len(rows)
synth = [["Synthèse Phase 1 — intelligence marché (échantillon réel du 2026-06-19)"], [""],
         [f"Total offres sourcées : {n}"],
         ["Sources : Novojob + Educarriere + RMO Jobcenter (scrape HTML live, CI)."],
         ["Champs Salaire/Contrat souvent vides = non publiés à la source (jamais inventés)."], [""]]
synth += block("Par score ⭐ (pertinence DC)", Counter(int(r["score_dc"]) for r in rows), order=[5, 4, 3, 2, 1])
synth += block("Par secteur", Counter(r["secteur_norm"] for r in rows))
synth += block("Par niveau", Counter(r["niveau_norm"] for r in rows),
               order=["Manager/Direction", "Senior", "Confirmé", "Junior", "Stage"])
synth += block("Par source", Counter(r["source"] for r in rows))
synth += [["Note KPI (futur portail) : tracker aussi vues, clics, candidatures, taux de conversion par offre,"],
          ["+ KPIs insertion DC : mises en relation, placements attribués, temps-vers-placement, rétention."]]

# ---- créer les onglets ----
meta = api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}?fields=sheets.properties")
existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
reqs = []
for title in ("Base Phase 1 ⭐", "Synthèse Phase 1"):
    if title not in existing:
        reqs.append({"addSheet": {"properties": {"title": title, "gridProperties": {"frozenRowCount": 1}}}})
# rétrograder l'ancien échantillon manuel
if "Base sourcée v1" in existing:
    reqs.append({"updateSheetProperties": {"properties": {"sheetId": existing["Base sourcée v1"],
                 "title": "Échantillon v1 (illustratif — déprécié)"}, "fields": "title"}})
res = api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", {"requests": reqs})
# re-read ids
meta = api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}?fields=sheets.properties")
ids = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def put(tab, values):
    rng = urllib.parse.quote(f"{tab}!A1")
    api("PUT", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{rng}?valueInputOption=RAW", {"values": values})


put("Base Phase 1 ⭐", [HEADER] + DATA)
put("Synthèse Phase 1", synth)

# ---- mise en forme ----
fmt = []
for tab in ("Base Phase 1 ⭐", "Synthèse Phase 1"):
    sid = ids[tab]
    fmt.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                 "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.40}}},
        "fields": "userEnteredFormat(textFormat,backgroundColor)"}})
    fmt.append({"autoResizeDimensions": {"dimensions": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 15}}})
# filtre sur la base + cap largeur intitulé/lien
sidb = ids["Base Phase 1 ⭐"]
fmt.append({"setBasicFilter": {"filter": {"range": {"sheetId": sidb, "startRowIndex": 0,
            "startColumnIndex": 0, "endColumnIndex": 15}}}})
for col, w in [(2, 320), (12, 280), (3, 200)]:
    fmt.append({"updateDimensionProperties": {"range": {"sheetId": sidb, "dimension": "COLUMNS",
                "startIndex": col, "endIndex": col + 1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})
api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", {"requests": fmt})

# ---- maj Lisez-moi (append note Phase 1) ----
note = [[""], ["— MAJ 2026-06-19 (Phase 1) —"],
        [f"Onglet 'Base Phase 1 ⭐' = base RÉELLE de {n} offres scrapées en direct (Novojob + Educarriere + RMO), vraies URLs."],
        ["Scoring ⭐ par niveau de qualification (1 à 5) : valorise les postes cadres MAIS garde les postes junior/stage"],
        ["intéressants (beaucoup de young graduates postulent à Diaspora Connect). Le score n'EXCLUT rien, il priorise."],
        ["L'ancien onglet a été renommé 'Échantillon v1 (illustratif)' : c'était un échantillon manuel, remplacé par la base réelle."],
        ["Onglet 'Synthèse Phase 1' = première intelligence marché (répartition par score/secteur/niveau/source)."]]
api("PUT", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{urllib.parse.quote('Lisez-moi!A20')}?valueInputOption=RAW", {"values": note})

print(f"OK — {n} offres poussées.")
print("URL", f"https://docs.google.com/spreadsheets/d/{SID}/edit")
