#!/usr/bin/env python3
"""Génère le front statique brandé Diaspora Connect (single-file index.html).
Lit data/offers_active.csv (la base vivante) + data/last_refresh.json (date/compteurs),
embarque les offres en JSON dans la page (aucun backend), écrit site/index.html.
Charte DC : coral #E83030 / purple #682890 / amber #F8C000 / cream #F7F3EE.
Règle d'or : zéro donnée inventée (champ vide = non publié à la source)."""
import csv, json, os, datetime

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
SITE = os.path.join(HERE, "..", "site")
os.makedirs(SITE, exist_ok=True)

# Lien vers le mini-outil de matching (CV/LinkedIn -> offres + lettres).
# Service Render (blueprint render.yaml). Surchargable via la variable d'env MATCH_URL
# si l'URL réelle diffère (Render suffixe le nom si déjà pris) — puis rebuild.
MATCH_URL = os.environ.get("MATCH_URL") or "https://diaspora-emploi-matching.onrender.com"

rows = list(csv.DictReader(open(os.path.join(DATA, "offers_active.csv"), encoding="utf-8")))
try:
    meta = json.load(open(os.path.join(DATA, "last_refresh.json"), encoding="utf-8"))
except FileNotFoundError:
    meta = {}


def clean_url(u):
    """LinkedIn ajoute des params de contexte de recherche (?position=&pageNum=&refId=)
    volatils ; on garde le lien canonique vers l'annonce."""
    u = (u or "").strip()
    if "linkedin.com" in u and "?" in u:
        return u.split("?")[0]
    return u


def ville(loc):
    """Normalise le lieu en bucket lisible pour le filtre localisation.
    Regroupe les communes d'Abidjan, nomme les grandes villes, isole 'Non précisé'."""
    s = (loc or "").strip().lower()
    if not s or s.rstrip(", ") in ("côte d'ivoire", "cote d'ivoire", "côte d’ivoire", "ci"):
        return "Non précisé"
    if any(k in s for k in ("remote", "télétravail", "teletravail", "à distance", "a distance")):
        return "Remote / Télétravail"
    ABJ = ("abidjan", "plateau", "cocody", "yopougon", "marcory", "treichville", "koumassi",
           "adjamé", "adjame", "abobo", "port-bou", "bingerville", "anyama", "attécoub",
           "attecoub", "songon", "riviera")
    if any(k in s for k in ABJ):
        return "Abidjan"
    NAMED = [("yamoussoukro", "Yamoussoukro"), ("bouak", "Bouaké"), ("san-pédro", "San-Pédro"),
             ("san pedro", "San-Pédro"), ("san-pedro", "San-Pédro"), ("korhogo", "Korhogo"),
             ("bondoukou", "Bondoukou"), ("zouan", "Zouan-Hounien"), ("bouafl", "Bouaflé"),
             ("daloa", "Daloa"), ("gagnoa", "Gagnoa"), ("divo", "Divo"), ("abengourou", "Abengourou"),
             ("vitib", "Grand-Bassam (VITIB)"), ("grand-bassam", "Grand-Bassam"), ("bassam", "Grand-Bassam"),
             ("séguéla", "Séguéla"), ("seguela", "Séguéla")]
    for k, v in NAMED:
        if k in s:
            return v
    return "Autres villes / régions"


# garder uniquement les champs utiles au front (allège la page)
offers = [{
    "t": r["titre"], "e": r["entreprise"], "m": r.get("metier_norm", ""), "s": r["secteur_norm"],
    "n": r["niveau_norm"], "loc": r["lieu"], "v": ville(r["lieu"]), "c": r["contrat"],
    "dp": r["date_pub"], "dl": r["date_limite"],
    "sal": r["salaire"], "src": r["source"], "u": clean_url(r["url"]), "sc": int(r["score_dc"]),
} for r in rows]
offers.sort(key=lambda o: (-o["sc"], o["s"], o["t"]))

# métiers triés par fréquence (les plus courants en haut du menu)
from collections import Counter
metiers = [m for m, _ in Counter(o["m"] for o in offers if o["m"]).most_common()]
secteurs = sorted({o["s"] for o in offers})
# villes triées par fréquence ; "Non précisé" relégué en fin de liste
_vc = Counter(o["v"] for o in offers)
villes = [v for v, _ in _vc.most_common() if v != "Non précisé"]
if "Non précisé" in _vc:
    villes.append("Non précisé")
niveaux_order = ["Stage", "Junior", "Confirmé", "Senior", "Manager/Direction"]
niveaux = [n for n in niveaux_order if any(o["n"] == n for o in offers)]
iso = meta.get("date") or datetime.date.today().isoformat()
MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
_d = datetime.date.fromisoformat(iso)
date_maj = f"{_d.day} {MOIS[_d.month]} {_d.year}"
n_actives = len(offers)
n_secteurs = len(secteurs)
n_new = meta.get("nouvelles_ce_run", 0)
n_sources = len({o["src"] for o in offers})
# 1er chargement (tout est "nouveau") -> on affiche le nombre de sources, plus parlant
if 0 < n_new < n_actives:
    stat3 = f'<div class="stat"><b>{n_new}</b><span>nouvelles cette semaine</span></div>'
else:
    stat3 = f'<div class="stat"><b>{n_sources}</b><span>sources agrégées</span></div>'

DATA_JSON = json.dumps(offers, ensure_ascii=False)

HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Portail Emploi — Diaspora Connect</title>
<meta name="description" content="Les opportunités d'emploi en Côte d'Ivoire pour les talents de la diaspora. Mis à jour chaque semaine.">
<meta name="robots" content="noindex,nofollow">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --coral:#E83030; --coral-d:#C81F1F; --purple:#682890; --purple-l:#8E4FB8;
  --amber:#F8C000; --orange:#F26522; --cream:#F7F3EE; --ink:#23202B; --muted:#6B6770;
  --card:#FFFFFF; --line:#ECE6DD;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;color:var(--ink);background:var(--cream);
  line-height:1.5;-webkit-font-smoothing:antialiased}
h1,h2,h3,.brandfont{font-family:'Poppins',sans-serif}
a{color:inherit}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}

/* Header */
header{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:30}
.hd{display:flex;align-items:center;gap:16px;height:74px}
.hd img{height:40px;width:auto}
.hd .sep{width:1px;height:34px;background:var(--line)}
.hd .ttl{font-family:'Poppins';font-weight:700;font-size:18px;letter-spacing:-.3px}
.hd .ttl small{display:block;font-family:'Inter';font-weight:500;font-size:12px;color:var(--muted);letter-spacing:0}

/* Hero */
.hero{padding:38px 0 26px}
.hero h1{font-size:clamp(28px,4.2vw,42px);font-weight:800;letter-spacing:-1px;margin:0 0 10px;
  background:linear-gradient(95deg,var(--coral),var(--orange) 45%,var(--purple));
  -webkit-background-clip:text;background-clip:text;color:transparent;display:inline-block}
.hero p{font-size:17px;color:var(--muted);max-width:680px;margin:0}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
.stat{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 18px;min-width:120px}
.stat b{font-family:'Poppins';font-weight:700;font-size:24px;display:block;line-height:1}
.stat span{font-size:12.5px;color:var(--muted)}
.stat.accent b{color:var(--coral)}

/* CTA matching */
.cta{margin-top:24px;background:linear-gradient(100deg,var(--purple),var(--coral));border-radius:18px;
  padding:20px 24px;display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;
  color:#fff;box-shadow:0 10px 26px rgba(104,40,144,.20)}
.cta-txt b{font-family:'Poppins';font-weight:700;font-size:17.5px;display:block;margin-bottom:4px}
.cta-txt span{font-size:13.5px;opacity:.93;max-width:580px;display:block;line-height:1.45}
.cta-btn{font-family:'Poppins';font-weight:700;font-size:15px;text-decoration:none;background:#fff;
  color:var(--purple);border-radius:30px;padding:13px 26px;white-space:nowrap;transition:.14s;flex-shrink:0}
.cta-btn:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(0,0,0,.18)}

/* Filters */
.filters{position:sticky;top:74px;z-index:20;background:var(--cream);padding:16px 0 12px;border-bottom:1px solid var(--line)}
.frow{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.frow input[type=search],.frow select{font-family:'Inter';font-size:14px;border:1px solid var(--line);
  background:#fff;border-radius:11px;padding:11px 14px;color:var(--ink);outline:none}
.frow input[type=search]{flex:1;min-width:220px}
.frow input:focus,.frow select:focus{border-color:var(--purple-l);box-shadow:0 0 0 3px rgba(142,79,184,.12)}
.frow select{cursor:pointer}
.count{font-size:13px;color:var(--muted);margin-left:auto;white-space:nowrap}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}
.chip{font-size:12.5px;border:1px solid var(--line);background:#fff;border-radius:999px;padding:5px 13px;cursor:pointer;color:var(--muted);transition:.12s}
.chip:hover{border-color:var(--purple-l)}
.chip.on{background:var(--purple);border-color:var(--purple);color:#fff}
.help{flex-basis:100%;margin-top:4px;font-size:12.5px}
.help summary{cursor:pointer;color:var(--purple);font-weight:600;list-style:none;width:fit-content}
.help summary::-webkit-details-marker{display:none}
.help summary:hover{text-decoration:underline}
.help p{color:var(--muted);margin:8px 0 0;line-height:1.5;max-width:760px}
.help b{color:var(--ink)}

/* Grid */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;padding:22px 0 10px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--line);
  border-radius:16px;padding:17px 18px;display:flex;flex-direction:column;gap:9px;transition:.14s}
.card:hover{box-shadow:0 8px 24px rgba(35,32,43,.08);transform:translateY(-2px)}
.card.s5{border-left-color:var(--coral)} .card.s4{border-left-color:var(--orange)}
.card.s3{border-left-color:var(--amber)} .card.s2{border-left-color:var(--purple-l)}
.card.s1{border-left-color:#C9C3BA}
.c-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.c-title{font-family:'Poppins';font-weight:600;font-size:16px;line-height:1.3;letter-spacing:-.2px}
.c-comp{font-size:13.5px;color:var(--muted);font-weight:500}
.stars{font-size:13px;letter-spacing:1px;color:var(--amber);white-space:nowrap;flex-shrink:0}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:1px}
.tag{font-size:11.5px;border-radius:7px;padding:3px 9px;background:#F3EEE7;color:#5A5560;font-weight:500}
.tag.met{background:rgba(248,192,0,.18);color:#8a6500;font-weight:600}
.tag.sect{background:rgba(104,40,144,.09);color:var(--purple)}
.tag.niv{background:rgba(232,48,48,.08);color:var(--coral-d)}
.c-foot{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:6px;padding-top:11px;border-top:1px solid var(--line)}
.c-src{font-size:11.5px;color:var(--muted)}
.btn{font-family:'Poppins';font-weight:600;font-size:13px;text-decoration:none;border-radius:10px;
  padding:9px 16px;background:var(--coral);color:#fff;white-space:nowrap;transition:.12s}
.btn:hover{background:var(--coral-d)}
.btn.off{background:#E7E1D8;color:#9A948B;pointer-events:none}
.empty{text-align:center;color:var(--muted);padding:60px 0;font-size:15px}

footer{margin-top:30px;border-top:1px solid var(--line);background:#fff}
footer .wrap{padding:26px 20px;font-size:13px;color:var(--muted)}
footer b{color:var(--ink)}
.note{font-size:12px;margin-top:8px}
</style>
</head>
<body>
<header><div class="wrap hd">
  <img src="assets/dc-logo.png" alt="Diaspora Connect">
  <div class="sep"></div>
  <div class="ttl">Portail Emploi<small>Opportunités en Côte d'Ivoire</small></div>
</div></header>

<div class="wrap hero">
  <h1>Trouvez votre poste en Côte d'Ivoire</h1>
  <p>Les opportunités d'emploi du marché ivoirien, rassemblées et classées par pertinence pour les talents de la diaspora. Chaque offre renvoie au lien officiel pour postuler.</p>
  <div class="stats">
    <div class="stat accent"><b id="st-shown">__N__</b><span>offres disponibles</span></div>
    <div class="stat"><b>__SEC__</b><span>secteurs</span></div>
    __STAT3__
    <div class="stat"><b>__DATE__</b><span>dernière mise à jour</span></div>
  </div>
  <div class="cta">
    <div class="cta-txt">
      <b>✨ Vous avez un CV ou un profil LinkedIn ?</b>
      <span>Recevez en quelques secondes vos offres les mieux adaptées, comment vous positionner, et vos lettres de motivation prêtes à envoyer.</span>
    </div>
    <a class="cta-btn" href="__MATCH_URL__" target="_blank" rel="noopener">Analyser mon profil →</a>
  </div>
</div>

<div class="filters"><div class="wrap">
  <div class="frow">
    <input id="q" type="search" placeholder="Rechercher un intitulé, une entreprise…">
    <select id="loc"><option value="">📍 Toute la Côte d'Ivoire</option>__LOCOPTS__</select>
    <select id="met"><option value="">Tous les métiers</option>__METOPTS__</select>
    <select id="sect"><option value="">Tous les secteurs</option>__SECTOPTS__</select>
    <select id="niv"><option value="">Tous les niveaux</option>__NIVOPTS__</select>
    <span class="count" id="count"></span>
  </div>
  <div class="chips">
    <span class="chip" data-min="0">Toutes les notes</span>
    <span class="chip" data-min="5" title="Pertinence maximale pour la diaspora">★★★★★ uniquement</span>
    <span class="chip" data-min="4" title="4 étoiles et plus">★★★★ et +</span>
    <span class="chip" data-min="3" title="3 étoiles et plus">★★★ et +</span>
    <details class="help"><summary>ⓘ Comment lire les étoiles & les niveaux ?</summary>
      <p><b>Les étoiles (★)</b> notent la <b>pertinence d'une offre pour un talent de la diaspora</b>, pas la qualité de l'employeur. La note combine&nbsp;:
      le <b>niveau de séniorité</b> (les postes qualifiés et cadres montent) et le <b>secteur</b> (Tech, Finance, RH, Juridique, Ingénierie, ONG sont priorisés ; les postes peu qualifiés sont à 1★).</p>
      <p><b>Les niveaux</b> correspondent à l'expérience attendue&nbsp;:
      <b>Stage</b> (stage / alternance) · <b>Junior</b> (0–2 ans) · <b>Confirmé</b> (3–5 ans) · <b>Senior</b> (6–10 ans) · <b>Manager / Direction</b> (encadrement, 10+ ans).</p>
    </details>
  </div>
</div></div>

<div class="wrap"><div class="grid" id="grid"></div><div class="empty" id="empty" style="display:none">Aucune offre ne correspond à ces critères.<br><span style="font-size:13.5px">Essayez d'élargir : moins d'étoiles, une autre localisation, ou « Tous les niveaux ».</span></div></div>

<footer><div class="wrap">
  <b>Diaspora Connect</b> — Accélérer l'innovation ivoirienne. Portail mis à jour chaque semaine.<br>
  Sources : LinkedIn, Novojob, Educarriere, RMO Jobcenter. Les offres expirées basculent automatiquement en archive.
  <div class="note">Règle : zéro donnée inventée. Un champ vide (salaire, contrat) signifie qu'il n'était pas publié à la source. Cliquez « Postuler » pour accéder à l'annonce officielle.</div>
</div></footer>

<script>
const OFFERS = __DATA__;
const grid=document.getElementById('grid'), empty=document.getElementById('empty');
const q=document.getElementById('q'), loc=document.getElementById('loc'), met=document.getElementById('met'), sect=document.getElementById('sect'), niv=document.getElementById('niv');
const count=document.getElementById('count'), stShown=document.getElementById('st-shown');
let minStars=0;
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const stars=n=>'★'.repeat(n)+'☆'.repeat(5-n);
function card(o){
  const tags=[];
  if(o.m) tags.push(`<span class="tag met">${esc(o.m)}</span>`);
  if(o.s) tags.push(`<span class="tag sect">${esc(o.s)}</span>`);
  if(o.n) tags.push(`<span class="tag niv">${esc(o.n)}</span>`);
  if(o.loc) tags.push(`<span class="tag">${esc(o.loc)}</span>`);
  if(o.c) tags.push(`<span class="tag">${esc(o.c)}</span>`);
  if(o.sal) tags.push(`<span class="tag">${esc(o.sal)}</span>`);
  const btn=o.u?`<a class="btn" href="${esc(o.u)}" target="_blank" rel="noopener">Postuler →</a>`:`<span class="btn off">Lien indisponible</span>`;
  const when=o.dp?`Publié ${esc(o.dp)}`:'';
  return `<article class="card s${o.sc}">
    <div class="c-top"><div><div class="c-title">${esc(o.t)}</div>${o.e?`<div class="c-comp">${esc(o.e)}</div>`:''}</div>
      <div class="stars" title="Pertinence ${o.sc}/5">${stars(o.sc)}</div></div>
    <div class="meta">${tags.join('')}</div>
    <div class="c-foot"><span class="c-src">${esc(o.src)}${when?' · '+when:''}</span>${btn}</div>
  </article>`;
}
function render(){
  const term=q.value.trim().toLowerCase(), fl=loc.value, fm=met.value, fs=sect.value, fn=niv.value;
  const list=OFFERS.filter(o=>o.sc>=minStars
    && (!fl||o.v===fl) && (!fm||o.m===fm) && (!fs||o.s===fs) && (!fn||o.n===fn)
    && (!term || (o.t+' '+o.e).toLowerCase().includes(term)));
  grid.innerHTML=list.map(card).join('');
  empty.style.display=list.length?'none':'block';
  count.textContent=list.length+' offre'+(list.length>1?'s':'');
  stShown.textContent=list.length;
}
[q,loc,met,sect,niv].forEach(el=>el.addEventListener('input',render));
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
  document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));
  c.classList.add('on'); minStars=+c.dataset.min; render();
}));
document.querySelector('.chip[data-min="0"]').classList.add('on');
render();
</script>
</body>
</html>
"""

locopts = "".join(f'<option value="{v}">{v} ({_vc[v]})</option>' for v in villes)
metopts = "".join(f'<option value="{m}">{m}</option>' for m in metiers)
sectopts = "".join(f'<option value="{s}">{s}</option>' for s in secteurs)
nivopts = "".join(f'<option value="{n}">{n}</option>' for n in niveaux)
html = (HTML.replace("__DATA__", DATA_JSON).replace("__N__", str(n_actives))
        .replace("__SEC__", str(n_secteurs)).replace("__STAT3__", stat3)
        .replace("__DATE__", date_maj).replace("__LOCOPTS__", locopts).replace("__METOPTS__", metopts)
        .replace("__SECTOPTS__", sectopts).replace("__NIVOPTS__", nivopts)
        .replace("__MATCH_URL__", MATCH_URL))

open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(html)
open(os.path.join(SITE, ".nojekyll"), "w").write("")
print(f"site/index.html écrit — {n_actives} offres, {n_secteurs} secteurs, MAJ {date_maj}")
print(f"  poids: {len(html)//1024} Ko")
