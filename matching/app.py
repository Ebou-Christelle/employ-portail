#!/usr/bin/env python3
"""Mini-service self-service Diaspora Connect : le candidat dépose son CV (PDF/DOCX/TXT)
et/ou son lien LinkedIn, reçoit son rapport de matching (offres notées + forces/écarts +
recos + 3 lettres). Couche 2 = engine.py / report.py.

Données perso (cf RGPD-cadrage-donnees-perso.md) :
- consentement explicite OBLIGATOIRE avant analyse ;
- CV/LinkedIn traités EN MÉMOIRE, NON persistés ;
- seul un événement ANONYME (horodatage, métier dominant) est journalisé pour le backoffice.

Lancer : uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import os, json, datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from engine import extract_cv_text, scrape_linkedin, build_candidate_text, run_match
from report import render_report, LOGO

HERE = os.path.dirname(__file__)
EVENTS = os.path.join(HERE, "data", "events.jsonl")
MAX_BYTES = 15 * 1024 * 1024   # CV scannés multi-pages peuvent être lourds

app = FastAPI(title="Diaspora Connect — Intelligence Emploi")

BRAND_CSS = """
:root{--coral:#E83030;--purple:#682890;--amber:#F8C000;--cream:#F7F3EE;--ink:#241A2E;}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,system-ui,sans-serif;color:var(--ink);background:var(--cream);line-height:1.55}
.wrap{max-width:640px;margin:0 auto;padding:0 18px 70px}
.topbar{background:#fff;border-radius:0 0 16px 16px;padding:16px 22px;display:flex;align-items:center;justify-content:space-between}
.logo{height:40px;width:auto;max-width:64%}
.brandtext{font-family:Poppins,sans-serif;font-weight:700;color:var(--purple);font-size:19px}
.topbar .lbl{font:700 11px/1 Inter;letter-spacing:.16em;text-transform:uppercase;color:var(--coral)}
.hero{background:linear-gradient(120deg,var(--purple),var(--coral));color:#fff;padding:30px 30px;border-radius:18px;margin-top:14px}
.hero h1{font-family:Poppins,sans-serif;font-size:25px;margin:0 0 6px}
.hero .sub{font-size:14.5px;opacity:.93}
.card{background:#fff;border-radius:18px;padding:24px 24px;margin-top:18px;box-shadow:0 2px 16px rgba(40,20,60,.07)}
.steps{display:flex;gap:14px;margin:2px 0 18px;flex-wrap:wrap}
.step{flex:1;min-width:150px;font-size:13px;color:#5A4A6A}
.step b{display:block;color:var(--purple);font-family:Poppins,sans-serif;font-size:14px;margin-bottom:2px}
label.file{display:block;border:2px dashed #D8CFC4;border-radius:14px;padding:20px;text-align:center;cursor:pointer;background:#FCFAF7;font-size:14px;color:#6A6072}
label.file b{color:var(--coral)}
input[type=file]{display:none}
.fname{margin-top:8px;font-size:13px;color:var(--purple);font-weight:600}
.or{text-align:center;color:#9A92A2;font-size:12px;margin:14px 0 6px;font-weight:600;letter-spacing:.08em}
.li label{display:block;font-size:13px;color:#5A4A6A;margin-bottom:6px;font-weight:600}
.li input{width:100%;border:1px solid #D8CFC4;border-radius:12px;padding:12px 14px;font-size:14px;font-family:inherit}
.li .hint{font-size:11.5px;color:#9A92A2;margin-top:5px}
.notice{font-size:12.5px;color:#6A6072;background:#FBF4FD;border-left:4px solid var(--purple);border-radius:8px;padding:12px 14px;margin:18px 0}
.consent{display:flex;gap:10px;align-items:flex-start;font-size:13.5px;margin:14px 0}
.consent input{margin-top:3px;width:18px;height:18px;accent-color:var(--purple)}
button{width:100%;background:var(--coral);color:#fff;border:0;border-radius:30px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;font-family:Poppins,sans-serif}
button:disabled{opacity:.5;cursor:not-allowed}
.err{background:#FDECEC;color:#B12020;border-radius:10px;padding:12px 14px;font-size:14px;margin-top:14px}
.foot{text-align:center;font-size:12px;color:#9A92A2;padding:24px 18px 0}
#load{display:none;text-align:center;color:var(--purple);font-weight:600;margin-top:16px}
"""

NOTICE = (
    "En déposant votre CV et/ou votre lien LinkedIn, vous permettez à Diaspora Connect d'analyser votre "
    "profil pour vous proposer des offres d'emploi en Côte d'Ivoire adaptées, des recommandations et des "
    "lettres de motivation. Vos données sont réservées à cet usage, accessibles uniquement à l'équipe "
    "Diaspora Connect, conservées 12 mois maximum, et supprimées sur simple demande. "
    "L'analyse utilise un service d'IA (OpenAI) et, pour le profil LinkedIn, un service de récupération de "
    "données. Vous pouvez retirer votre consentement à tout moment."
)


def page(err=""):
    err_html = f'<div class="err">{err}</div>' if err else ""
    logo_html = f'<img class="logo" src="{LOGO}" alt="Diaspora Connect">' if LOGO else \
        '<div class="brandtext">Diaspora Connect</div>'
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Diaspora Connect — Trouvez votre poste en Côte d'Ivoire</title>
<style>{BRAND_CSS}</style></head><body><div class="wrap">
<div class="topbar">{logo_html}<span class="lbl">Intelligence Emploi</span></div>
<div class="hero">
  <h1>Votre profil → vos meilleures offres en Côte d'Ivoire</h1>
  <div class="sub">Déposez votre CV et/ou votre LinkedIn. En quelques secondes : les offres les plus adaptées, ce qui matche & ce qui manque, et des lettres de motivation prêtes à envoyer.</div>
</div>
<div class="card">
  <div class="steps">
    <div class="step"><b>1. Déposez</b>votre CV et/ou votre lien LinkedIn</div>
    <div class="step"><b>2. On analyse</b>votre profil vs nos offres réelles</div>
    <div class="step"><b>3. Vous recevez</b>offres notées + recos + lettres</div>
  </div>
  <form id="f" method="post" action="/match" enctype="multipart/form-data">
    <label class="file" for="cv">📄 <b>Choisir mon CV</b> — PDF, Word, texte (CV scannés acceptés)
      <div class="fname" id="fname"></div>
      <input id="cv" name="cv" type="file" accept=".pdf,.docx,.txt">
    </label>
    <div class="or">— ET / OU —</div>
    <div class="li">
      <label for="linkedin_url">🔗 Mon profil LinkedIn</label>
      <input id="linkedin_url" name="linkedin_url" type="url" placeholder="https://www.linkedin.com/in/votre-profil">
      <div class="hint">Optionnel — améliore le matching. Indiquez au moins un CV ou un lien LinkedIn.</div>
    </div>
    <div class="notice"><b>Vos données :</b> {NOTICE}</div>
    <label class="consent"><input type="checkbox" name="consent" value="yes" required>
      <span>J'ai lu et j'accepte que mon CV / profil LinkedIn soit analysé par Diaspora Connect dans les conditions ci-dessus.</span></label>
    <button id="btn" type="submit">Analyser mon profil →</button>
    <div id="load">⏳ Analyse en cours… (10–40 s, surtout si LinkedIn)</div>
  </form>
  {err_html}
</div>
<script>
var fi=document.getElementById('cv'),fn=document.getElementById('fname');
fi.addEventListener('change',function(){{fn.textContent=fi.files[0]?fi.files[0].name:''}});
document.getElementById('f').addEventListener('submit',function(){{
  document.getElementById('btn').disabled=true;document.getElementById('load').style.display='block';}});
</script>
</div></body></html>"""


def log_event(res, used):
    offres = res.get("offres", [])
    top = offres[0] if offres else {}
    ev = {"ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
          "source": "self-serve", "inputs": used,
          "n_offres": len(offres),
          "top_metier": top.get("offre", {}).get("metier", ""),
          "top_fit": top.get("fit", None)}
    line = json.dumps(ev, ensure_ascii=False)
    print("EVENT " + line, flush=True)  # visible dans les logs de l'hébergeur (Vercel)
    try:
        with open(EVENTS, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # disque en lecture seule en serverless : le log console fait foi


@app.get("/", response_class=HTMLResponse)
def home():
    return page()


@app.get("/analyse", response_class=HTMLResponse)
def home_analyse():
    """Chemin public sur Vercel (rewrite /analyse -> cette app) ; même page que /."""
    return page()


@app.post("/match", response_class=HTMLResponse)
async def match(cv: UploadFile = File(None), linkedin_url: str = Form(""), consent: str = Form(None)):
    if consent != "yes":
        return HTMLResponse(page("Merci de cocher la case de consentement pour lancer l'analyse."))
    cv_text, li_text, used = "", "", []
    # CV (optionnel)
    if cv is not None and cv.filename:
        data = await cv.read()
        if data and len(data) > MAX_BYTES:
            return HTMLResponse(page("Fichier trop volumineux (max 15 Mo)."))
        if data:
            try:
                cv_text = extract_cv_text(cv.filename, data)
                if cv_text.strip():
                    used.append("cv")
            except Exception:
                cv_text = ""
            del data
    # LinkedIn (optionnel)
    if linkedin_url and "linkedin.com/in/" in linkedin_url:
        try:
            li_text = scrape_linkedin(linkedin_url)
            if li_text.strip():
                used.append("linkedin")
        except Exception:
            li_text = ""
    candidate = build_candidate_text(cv_text, li_text)
    if len(candidate) < 60:
        if linkedin_url and "linkedin" not in used:
            return HTMLResponse(page("On n'a pas pu lire votre profil LinkedIn (lien privé ou indisponible). Ajoutez plutôt votre CV."))
        return HTMLResponse(page("Ajoutez un CV (PDF avec du texte, ou scanné) ou un lien LinkedIn public pour lancer l'analyse."))
    try:
        res = run_match(candidate)
    except Exception:
        return HTMLResponse(page("Une erreur est survenue pendant l'analyse. Réessayez dans un instant."))
    log_event(res, used)
    del cv_text, li_text, candidate
    return HTMLResponse(render_report(res))
