#!/usr/bin/env python3
"""Cœur du moteur de matching candidat -> offres (couche 2).
Réutilisé par match.py (CLI/démo) et app.py (service web self-service).
- extract_cv_text(filename, data) : PDF / DOCX / TXT -> texte (OCR vision si PDF scanné)
- scrape_linkedin(url) : profil LinkedIn public -> texte (Apify harvestapi)
- run_match(candidate_text) : embeddings + LLM -> dict riche (sous-scores, forces/écarts, 3 lettres)
RÈGLE données perso : ne jamais persister un CV réel ici (le CV reste en mémoire)."""
import json, os, io, re, base64, urllib.request, urllib.error
import numpy as np
from lib import embed, chat_json, vision_text

HERE = os.path.dirname(__file__)
INDEX = os.path.join(HERE, "data", "offer_index.json")
PRESELECT = 14

_IDX = None
_M = None


def _load_index():
    global _IDX, _M
    if _IDX is None:
        _IDX = json.load(open(INDEX, encoding="utf-8"))
        M = np.array([o["emb"] for o in _IDX], dtype=np.float32)
        _M = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return _IDX, _M


# ---------- extraction CV (avec OCR pour les CV scannés) ----------
def _ocr_pdf(data, max_pages=4):
    """Rasterise les pages d'un PDF image et les transcrit via le modèle vision."""
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        uris = []
        for p in list(doc)[:max_pages]:
            pix = p.get_pixmap(dpi=150)
            png = pix.tobytes("png")
            uris.append("data:image/png;base64," + base64.b64encode(png).decode())
        doc.close()
        if uris:
            out = vision_text(uris)
            if _is_refusal(out):
                out = vision_text(uris, instruction="OCR only. Output the raw text content of these pages verbatim, nothing else.")
            return "" if _is_refusal(out) else out
    except Exception:
        pass
    return ""


def _is_refusal(t):
    t = (t or "").strip().lower()
    if len(t) < 40:
        return True
    pats = ["je ne peux pas", "je suis désolé", "i can't", "i cannot", "i'm sorry",
            "unable to", "i am unable", "désolé, mais"]
    return any(p in t[:120] for p in pats)


def extract_cv_text(filename, data):
    """filename: nom (pour l'extension), data: bytes. -> texte nettoyé (OCR si scanné)."""
    ext = os.path.splitext(filename or "")[1].lower()
    txt = ""
    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            txt = "\n".join(p.get_text() for p in doc)
            doc.close()
        except Exception:
            txt = ""
        if len(txt.strip()) < 120:  # PDF scanné/illisible -> OCR vision
            ocr = _ocr_pdf(data)
            if len(ocr.strip()) > len(txt.strip()):
                txt = ocr
    elif ext == ".docx":
        import docx
        d = docx.Document(io.BytesIO(data))
        txt = "\n".join(p.text for p in d.paragraphs)
    else:
        txt = data.decode("utf-8", "ignore")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    return txt


# ---------- scrape LinkedIn (profil public fourni par le candidat) ----------
def _apify_token():
    t = os.environ.get("APIFY_TOKEN")
    if not t:
        try:
            t = open(os.path.expanduser("~/.config/agents/secrets/apify.txt")).read().strip()
        except FileNotFoundError:
            t = ""
    return t


def scrape_linkedin(url, timeout=70):  # borné pour rester sous le timeout HTTP de l'hébergeur
    """URL profil LinkedIn -> texte profil (headline, about, expériences, formations, skills).
    Retourne '' si indisponible (échec gracieux)."""
    url = (url or "").strip()
    if "linkedin.com/in/" not in url:
        return ""
    token = _apify_token()
    if not token:
        return ""
    body = json.dumps({"queries": [url],
                       "profileScraperMode": "Profile details no email ($4 per 1k)"}).encode()
    api = ("https://api.apify.com/v2/acts/harvestapi~linkedin-profile-scraper/"
           "run-sync-get-dataset-items?token=" + token)
    try:
        req = urllib.request.Request(api, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        items = json.load(urllib.request.urlopen(req, timeout=timeout))
    except Exception:
        return ""
    if not items or not isinstance(items, list) or "error" in items[0]:
        return ""
    p = items[0]
    parts = []
    nom = " ".join(x for x in [p.get("firstName"), p.get("lastName")] if x)
    if nom: parts.append(f"Nom : {nom}")
    if p.get("headline"): parts.append(f"Titre LinkedIn : {p['headline']}")
    loc = (p.get("location") or {}).get("linkedinText") or (p.get("location") or {}).get("parsed", {})
    if isinstance(loc, str) and loc: parts.append(f"Localisation : {loc}")
    if p.get("about"): parts.append(f"À propos : {p['about']}")
    exp = p.get("experience") or []
    if exp:
        parts.append("Expériences :")
        for e in exp[:8]:
            line = " - " + " | ".join(str(x) for x in [
                e.get("position") or e.get("title"), e.get("companyName") or e.get("company"),
                e.get("duration") or e.get("dateRange") or ""] if x)
            desc = e.get("description") or ""
            if desc: line += f" — {desc[:300]}"
            parts.append(line)
    edu = p.get("education") or []
    if edu:
        parts.append("Formations :")
        for e in edu[:6]:
            deg = " ".join(x for x in [e.get("degree") or e.get("subtitle") or "", e.get("fieldOfStudy") or ""] if x)
            parts.append(" - " + " | ".join(str(x) for x in [
                e.get("schoolName") or e.get("title"), deg,
                e.get("period") or e.get("dateRange") or ""] if x))
    sk = p.get("skills") or []
    if sk:
        names = [s.get("name") if isinstance(s, dict) else str(s) for s in sk][:25]
        parts.append("Compétences : " + ", ".join(n for n in names if n))
    certs = p.get("certifications") or []
    if certs:
        cn = [c.get("title") if isinstance(c, dict) else str(c) for c in certs][:10]
        parts.append("Certifications : " + ", ".join(n for n in cn if n))
    langs = p.get("languages") or []
    if langs:
        ln = [l.get("name") if isinstance(l, dict) else str(l) for l in langs][:8]
        parts.append("Langues : " + ", ".join(n for n in ln if n))
    return "\n".join(parts).strip()


def build_candidate_text(cv_text="", linkedin_text=""):
    blocks = []
    if cv_text.strip():
        blocks.append("=== CV ===\n" + cv_text.strip())
    if linkedin_text.strip():
        blocks.append("=== PROFIL LINKEDIN ===\n" + linkedin_text.strip())
    return "\n\n".join(blocks).strip()


# ---------- matching ----------
def _enrich(i):
    o = _IDX[i]
    return {"titre": o["titre"], "entreprise": o["entreprise"], "metier": o.get("metier", ""),
            "secteur": o["secteur"], "niveau": o["niveau"], "lieu": o["lieu"],
            "contrat": o["contrat"], "url": o["url"], "score_dc": o["score_dc"], "source": o["source"]}


SYSTEM = (
    "Tu es un conseiller carrière senior pour Diaspora Connect, un programme qui aide les talents de la "
    "diaspora ivoirienne formés à l'étranger à trouver un emploi en Côte d'Ivoire et à s'y installer "
    "durablement. Tu raisonnes comme un recruteur exigeant : tu compares concrètement le profil aux "
    "exigences de chaque offre. Tu écris en français, précis et chaleureux. "
    "Tu ne formules JAMAIS d'affirmation non fondée sur le profil ou l'offre (aucune invention de chiffre, "
    "diplôme ou expérience). Les sous-scores doivent refléter des éléments RÉELS du profil ; un écart non "
    "couvert par le profil doit être signalé honnêtement.\n\n"
    "RÈGLES POUR LES LETTRES DE MOTIVATION — elles doivent sonner comme écrites par la personne, "
    "PAS par une IA. Une lettre réussie est COURTE (140–200 mots), CONCRÈTE et SPÉCIFIQUE à cette "
    "offre précise. Applique :\n"
    "• Accroche qui parle de l'ENTREPRISE et du POSTE précis (ce qu'elle fait, l'enjeu du rôle), pas du candidat.\n"
    "• 2 éléments RÉELS et chiffrés/nommés du profil (une réalisation, un employeur, un outil, un résultat "
    "  concret) reliés explicitement à un besoin de CETTE offre. Pas de qualités vagues.\n"
    "• L'angle diaspora rendu CONCRET (ce que l'expérience à l'étranger apporte ici : bilinguisme opérationnel, "
    "  méthode, réseau, standards), jamais comme un slogan.\n"
    "• Ton direct, humain, première personne, phrases courtes. Pas de remplissage.\n\n"
    "INTERDITS ABSOLUS (ce sont des marqueurs d'IA) : « C'est avec un grand intérêt / un vif intérêt », "
    "« Je me permets de vous écrire », « Fort de mon expérience », « dynamique et motivé(e) », "
    "« je suis convaincu(e) que mon profil correspond parfaitement », « rejoindre vos équipes », "
    "« relever de nouveaux défis », « mes compétences et mon savoir-être », « En outre / Par ailleurs / "
    "De plus » en enfilade, superlatifs creux, tirets cadratins (—), points-virgules décoratifs, "
    "crochets à remplir, et toute phrase qui pourrait servir pour n'importe quel poste. "
    "Si une info manque, écris une phrase honnête plutôt qu'une formule creuse. "
    "Termine par une formule de politesse simple et une signature au prénom/nom réel s'il figure au profil, "
    "sinon sans signature inventée."
)


def run_match(candidate_text):
    idx, M = _load_index()
    candidate_text = (candidate_text or "").strip()
    if len(candidate_text) < 40:
        raise ValueError("Profil trop court ou illisible (texte non extrait).")
    q = np.array(embed(candidate_text)[0], dtype=np.float32)
    q /= (np.linalg.norm(q) + 1e-9)
    sims = M @ q
    order = np.argsort(-sims)[:PRESELECT]
    shortlist = [{"i": int(i), "sim": round(float(sims[i]), 3), "titre": idx[int(i)]["titre"],
                  "entreprise": idx[int(i)]["entreprise"], "metier": idx[int(i)].get("metier", ""),
                  "secteur": idx[int(i)]["secteur"], "niveau": idx[int(i)]["niveau"],
                  "lieu": idx[int(i)]["lieu"], "contrat": idx[int(i)]["contrat"],
                  "score_dc": idx[int(i)]["score_dc"]} for i in order]

    user = f"""Voici le profil d'un candidat (CV et/ou LinkedIn) :
\"\"\"{candidate_text[:8000]}\"\"\"

Voici une présélection d'offres réelles (déjà triées par proximité sémantique), au format JSON.
Le champ "i" est l'identifiant de l'offre à réutiliser dans ta réponse :
{json.dumps(shortlist, ensure_ascii=False, indent=1)}

Réponds en JSON STRICT avec ce schéma :
{{
  "profil": "2-3 phrases : profil + projet du candidat",
  "atout_diaspora": "1-2 phrases : en quoi son parcours international/bilingue est un atout en Côte d'Ivoire",
  "offres": [
    {{"i": <id>, "fit": <0-100>,
      "sous_scores": {{"competences": <0-100>, "secteur": <0-100>, "seniorite": <0-100>, "localisation": <0-100>}},
      "points_forts": ["2 à 3 éléments PRÉCIS du profil qui collent à CETTE offre"],
      "ecarts": ["1 à 2 manques/risques honnêtes pour CETTE offre (ou [] si aucun)"],
      "positionnement": "comment se présenter spécifiquement pour CETTE offre (1-2 phrases)"}}
  ],   // les 6 meilleures, triées par fit décroissant ; fit cohérent avec les sous-scores
  "recos": ["3 à 5 recos transverses : forces à mettre en avant, gaps à combler, comment se positionner sur le marché ivoirien"],
  "lettres": [
    {{"i": <id de l'offre>, "texte": "lettre FR 140-200 mots, spécifique à CETTE offre, suivant les RÈGLES POUR LES LETTRES (accroche sur l'entreprise/poste, 2 faits réels du profil reliés au besoin, angle diaspora concret, ton humain, aucun marqueur d'IA, prête à copier-coller)"}}
  ]   // UNE lettre pour CHACUNE des 3 meilleures offres (les 3 premiers "i" de "offres") ; deux lettres ne doivent pas se ressembler
}}"""

    res = chat_json(SYSTEM, user)
    for off in res.get("offres", []):
        if "i" in off:
            off["offre"] = _enrich(off["i"])
    for lt in res.get("lettres", []):
        if "i" in lt:
            lt["offre"] = _enrich(lt["i"])
    return res
