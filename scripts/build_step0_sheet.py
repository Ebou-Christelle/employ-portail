#!/usr/bin/env python3
"""Étape 0 — construit le GSheet 'Portail Emploi Diaspora Connect' (Source Map + Base sourcée v1).
Token zuri@ (scope drive suffit pour l'API Sheets). Partage domaine mstudio.vc + leslie@."""
import json, urllib.request, urllib.parse, sys

TOK = json.load(open("/tmp/dc/zuri.json"))
CRED = json.load(open("/home/openclaw/.config/gogcli/credentials.json"))

def access_token():
    data = urllib.parse.urlencode({
        "client_id": CRED["client_id"],
        "client_secret": CRED["client_secret"],
        "refresh_token": TOK["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    return json.load(urllib.request.urlopen(req))["access_token"]

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

# ---------- DATA ----------
SOURCE_MAP_HEADER = ["Source","Type","URL","Géo","Cible / spécialité","Méthode d'accès",
                     "Scrapable (testé 19/06)","Volume estimé","Pertinence DC","Notes"]
SOURCE_MAP = [
 ["Novojob","Job board","novojob.com/cote-d-ivoire","CI","Généraliste","Scrape HTML","✅ OK","121 offres live","Haute","Server-rendered, pagination ?page=N"],
 ["Educarriere","Job board","emploi.educarriere.ci","CI","Généraliste + concours/bourses","Scrape HTML","✅ OK","980 offres live","Haute","Gros volume, recruteurs nommés (Dangote, Roxgold…)"],
 ["RMO Jobcenter","Board + cabinet","rmo-jobcenter.com","CI + UEMOA (SN/ML/BF/TG)","Généraliste + intérim","Scrape HTML","✅ OK","n/a","Haute","Multi-pays = utile pour extension UEMOA"],
 ["Emploi.ci (groupe AfricaWork)","Job board","emploi.ci","CI","Généraliste","Apify / headers","⚠️ 403 anti-bot","Élevé","Haute","Bloque WebFetch → passer par Apify"],
 ["AfricaWork CI","Job board","africawork.ci","CI","Généraliste","Apify","⚠️ à retry (DNS)","Élevé","Moyenne","Réseau panafricain"],
 ["Talent2Africa","Cabinet + board","talent2africa.com","Afrique + diaspora","CADRES + DIASPORA","Scrape (URL offres à trouver)","⚠️ URL listing à mapper","n/a","TRÈS HAUTE","Executive search + EOR, cible diaspora = pile la cible DC"],
 ["LinkedIn Jobs","Plateforme","linkedin.com/jobs","Mondial + CI","Tous niveaux, riche en cadres/tech","Apify (actors) ou Unipile","⚠️ CGU + anti-bot","Très élevé","TRÈS HAUTE","Source #1 en volume cadre mais sensible légalement → arbitrer interne/public"],
 ["Indeed CI","Agrégateur","ci.indeed.com","CI","Généraliste","Apify","❓ non testé","Moyen","Moyenne",""],
 ["Michael Page Africa","Cabinet exec","michaelpageafrica.com","Afrique","Cadres / executive","Scrape","❓ non testé","Faible volume / haute qualité","Haute",""],
 ["AfricSearch","Cabinet","africsearch.com","Afrique + diaspora","Cadres / diaspora","Scrape","❓ non testé","Faible/qualité","Haute","Historiquement orienté diaspora"],
 ["Robert Walters / Fed Africa","Cabinets","—","Afrique","Cadres","Scrape","❓ non testé","Faible/qualité","Moyenne",""],
 ["Agence Emploi Jeunes (ex-AGEPE)","Public","agenceemploijeunes.ci","CI","Emploi jeunes / public","Scrape","❓ non testé","Moyen","Moyenne","Institutionnel, utile crédibilité bailleur"],
 ["Career pages grands groupes","Career page","Orange CI, SGCI, Ecobank, NSIA, AGL, Nestlé CI…","CI","Cadres","Scrape par page","❓ par page","Faible/qualité","Haute","Qualité élevée, faible volume — à cibler"],
 ["Startups Mstudio + écosystème","ATS / career","Recruitee (déjà connecté)","CI","Tech / startup","API Recruitee","✅ (Mstudio)","n/a","Haute","Connecté ; portfolio + clients"],
 ["VC/accélérateurs job boards","Agrégateur","Partech, Janngo, Saviu, Breega Africa…","Afrique","Startup / tech","Scrape","❓ non testé","Moyen","Moyenne",""],
 ["Groupes WhatsApp / Telegram emploi CI","Social","—","CI","Généraliste (flux informel énorme)","Bot / capture","⚠️ informel","Très élevé","Moyenne","Volume massif mais non structuré ; bruit à filtrer"],
 ["Socium Job","ATS (profils)","socium / DC","CI","Candidatures DC","API / export","✅ utilisé par DC","n/a","INPUT matching","Pas une source d'offres — source de PROFILS candidats DC"],
]

OFFERS_HEADER = ["ID","Date collecte","Source","Intitulé","Entreprise","Lieu","Type contrat",
                 "Secteur","Fonction","Niveau","Qualifié/Cadre (cible DC)","Salaire","Langue",
                 "Date publication","Lien source"]
# Qualifié/Cadre = O => remonté par la couche matching DC ; N => gardé dans la base générique, filtré pour DC
OFFERS = [
 ["1","2026-06-19","Novojob","Juriste Senior Contrats","BOA CI","Abidjan","CDI","Banque/Finance","Juridique","Confirmé (3-5a)","O","n.c.","FR","2026-06-12","novojob.com/.../136727"],
 ["2","2026-06-19","Novojob","Directeur d'Agence","BOA CI","Abidjan","CDI","Banque","Management réseau","Confirmé (3-5a)","O","n.c.","FR","2026-06-12","novojob.com/.../136726"],
 ["3","2026-06-19","Novojob","Business Development Manager","BOA CI","Abidjan","CDI","Banque","Commercial / BizDev","Senior (6-10a)","O","n.c.","FR","2026-06-12","novojob.com/.../136725"],
 ["4","2026-06-19","Novojob","Chargé Production Informatique","BOA CI","Abidjan","CDI","Banque / IT","IT / Infra","Junior (1-2a)","O","n.c.","FR","2026-06-12","novojob.com/.../136724"],
 ["5","2026-06-19","Novojob","Chargé d'Affaires Mid-Market","BOA CI","Abidjan","CDI","Banque","Commercial","Confirmé (3-5a)","O","n.c.","FR","2026-06-12","novojob.com/.../136723"],
 ["6","2026-06-19","Novojob","Chargé Relations Clients PME","BOA CI","Abidjan","CDI","Banque","Commercial","Confirmé (3-5a)","O","n.c.","FR","2026-06-12","novojob.com/.../136725"],
 ["7","2026-06-19","Novojob","Analyste Crédit","BOA CI","Abidjan","CDI","Banque","Risque / Crédit","Confirmé (3-5a)","O","n.c.","FR","2026-06-12","novojob.com/.../136719"],
 ["8","2026-06-19","Novojob","Responsable de Magasin / Operations","ACF Computer Store","Côte d'Ivoire","CDI","Retail / IT","Operations","Confirmé (3-5a)","O","n.c.","FR","2026-06-15","novojob.com/.../136732"],
 ["9","2026-06-19","Novojob","Opérateur Machine","SOLIBRA","Abidjan","CDI","Industrie","Production","Confirmé (3-5a)","N","n.c.","FR","2026-06-01","novojob.com/.../136713"],
 ["10","2026-06-19","Novojob","Magasinier Emballages","SOLIBRA","Bouaké","CDD","Industrie","Logistique","Junior (1-2a)","N","n.c.","FR","2026-05-26","novojob.com/.../136701"],
 ["11","2026-06-19","Novojob","Correspondant Fichier","Entreprise anonyme","Côte d'Ivoire","n.c.","Administration","Admin / Data","Confirmé","N","n.c.","FR","2026-06-16","novojob.com/.../136734"],
 ["12","2026-06-19","Educarriere","Technical Sales Representative","n.c.","Côte d'Ivoire","CDI","Commercial","Vente technique","n.c.","O","n.c.","FR","clôt. 2026-07-13","emploi.educarriere.ci"],
 ["13","2026-06-19","Educarriere","Commercial / Client Manager","n.c.","Côte d'Ivoire","CDI","Commercial","Management commercial","n.c.","O","n.c.","FR","clôt. 2026-07-02","emploi.educarriere.ci"],
 ["14","2026-06-19","Educarriere","Digital Content Creator (Stage)","n.c.","Côte d'Ivoire","Stage","Marketing / Digital","Création contenu","Junior / Stage","O","n.c.","FR","clôt. 2026-06-30","emploi.educarriere.ci"],
 ["15","2026-06-19","Educarriere","UI/UX Designer & Graphic Designer","n.c.","Côte d'Ivoire","CDI","Tech / Design","Design produit","n.c.","O","n.c.","FR","clôt. 2026-07-24","emploi.educarriere.ci"],
 ["16","2026-06-19","Educarriere","Commercial BTP","n.c.","Côte d'Ivoire","CDI","BTP","Commercial","n.c.","O","n.c.","FR","clôt. 2026-07-27","emploi.educarriere.ci"],
 ["17","2026-06-19","Educarriere","Visiteur Médical (Stage)","n.c.","Côte d'Ivoire","Stage","Santé / Pharma","Visite médicale","Junior / Stage","O","n.c.","FR","clôt. 2026-06-29","emploi.educarriere.ci"],
 ["18","2026-06-19","Educarriere","Assistant(e) Administratif(ve)","n.c.","Côte d'Ivoire","CDD","Administration","Admin","n.c.","N","n.c.","FR","clôt. 2026-06-29","emploi.educarriere.ci"],
 ["19","2026-06-19","Educarriere","Enseignants Primaire / Maternelle","Raynal & Fadika RH","Côte d'Ivoire","CDI","Éducation","Enseignement","n.c.","N","n.c.","FR","clôt. 2026-06-25","emploi.educarriere.ci"],
 ["20","2026-06-19","Educarriere","Chauffeur Poids Lourd","n.c.","Côte d'Ivoire","CDI","Transport","Conduite","n.c.","N","n.c.","FR","clôt. 2026-07-27","emploi.educarriere.ci"],
 ["21","2026-06-19","RMO Jobcenter","Country People & Talent Manager","Client RMO","Côte d'Ivoire","CDI","RH","RH / Talent Management","Senior","O","n.c.","FR","2026-06-18","rmo-jobcenter.com/.../4041"],
 ["22","2026-06-19","RMO Jobcenter","Administrateur Systèmes Unix/Linux","Client RMO","Côte d'Ivoire","CDI","IT / NTIC","SysAdmin / Infra","Confirmé","O","n.c.","FR","2026-06-18","rmo-jobcenter.com/.../4040"],
]

# ---------- CREATE ----------
ss = api("POST", "https://sheets.googleapis.com/v4/spreadsheets", {
    "properties": {"title": "Portail Emploi Diaspora Connect — Étape 0 (19-06-2026)"},
    "sheets": [
        {"properties": {"title": "Source Map", "gridProperties": {"frozenRowCount": 1}}},
        {"properties": {"title": "Base sourcée v1", "gridProperties": {"frozenRowCount": 1}}},
        {"properties": {"title": "Lisez-moi", "gridProperties": {"frozenRowCount": 0}}},
    ],
})
SID = ss["spreadsheetId"]
sheet_ids = {s["properties"]["title"]: s["properties"]["sheetId"] for s in ss["sheets"]}
print("SHEET_ID", SID)

readme = [
 ["Portail Emploi Diaspora Connect — Étape 0"],
 ["Construit le 2026-06-19 par Zuri."],
 [""],
 ["But : agréger les offres d'emploi qualifiées en CI (puis UEMOA), les classer et les sourcer,"],
 ["pour aider les cohortes Diaspora Connect à trouver un emploi et rester — et alimenter Yelema."],
 [""],
 ["Architecture (2 couches) :"],
 ["  Couche 1 — moteur GÉNÉRIQUE d'intelligence emploi (collecte → normalisation → classification IA → base sourcée). Réutilisable Yelema."],
 ["  Couche 2 — agent de matching spécifique : profils Diaspora Connect (Tally / Socium / vivier / CVs) ↔ offres."],
 [""],
 ["Onglet 'Source Map' : cartographie des sources (testées le 19/06)."],
 ["Onglet 'Base sourcée v1' : premier échantillon RÉEL d'offres collectées + classées. Chaque ligne garde sa source + date de collecte (règle : zéro donnée non sourcée)."],
 [""],
 ["Colonne 'Qualifié/Cadre (cible DC)' : O = remonté par la couche matching DC ; N = gardé dans la base générique mais filtré pour DC."],
 ["Échantillon = preuve de concept. Le lot complet (multi-sources, volume) suit sur 2-3 jours."],
]

def put(tab, values):
    rng = urllib.parse.quote(f"{tab}!A1")
    api("PUT", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{rng}?valueInputOption=RAW",
        {"values": values})

put("Source Map", [SOURCE_MAP_HEADER] + SOURCE_MAP)
put("Base sourcée v1", [OFFERS_HEADER] + OFFERS)
put("Lisez-moi", readme)

# ---------- FORMAT ----------
reqs = []
for tab in ("Source Map", "Base sourcée v1"):
    sid = sheet_ids[tab]
    reqs.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                 "backgroundColor": {"red":0.12,"green":0.16,"blue":0.40},
                 "horizontalAlignment":"LEFT"}},
        "fields": "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)"}})
    reqs.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": {"red":1,"green":1,"blue":1},"bold":True}}},
        "fields": "userEnteredFormat.textFormat(foregroundColor,bold)"}})
    reqs.append({"autoResizeDimensions": {"dimensions": {"sheetId": sid, "dimension":"COLUMNS",
                 "startIndex":0,"endIndex":len(OFFERS_HEADER)}}})
api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", {"requests": reqs})

# ---------- SHARE ----------
def share(body):
    try:
        api("POST", f"https://www.googleapis.com/drive/v3/files/{SID}/permissions?sendNotificationEmail=false&supportsAllDrives=true", body)
        print("shared", body.get("emailAddress") or body.get("domain"))
    except Exception as e:
        print("share fail", body, e)
share({"type":"domain","role":"writer","domain":"mstudio.vc"})
share({"type":"user","role":"writer","emailAddress":"leslie@mstudio.vc"})

print("URL", f"https://docs.google.com/spreadsheets/d/{SID}/edit")
