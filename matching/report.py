#!/usr/bin/env python3
"""Rendu du rapport candidat (HTML brandé Diaspora Connect) à partir d'un dict résultat.
Partagé par build_report.py (CLI) et app.py (service web). Aucune donnée inventée :
tout vient du profil fourni + des offres réelles."""
import html, os

e = html.escape
HERE = os.path.dirname(__file__)


def _logo():
    try:
        return open(os.path.join(HERE, "assets", "logo_b64.txt")).read().strip()
    except Exception:
        return ""


LOGO = _logo()
SUBLABELS = [("competences", "Compétences"), ("secteur", "Secteur"),
             ("seniorite", "Séniorité"), ("localisation", "Localisation")]


def _fit_color(f):
    f = int(f or 0)
    if f >= 85: return "#1F9D55"
    if f >= 70: return "#E89B00"
    return "#9A6B00"


def _bars(ss):
    if not isinstance(ss, dict):
        return ""
    rows = []
    for k, lbl in SUBLABELS:
        v = int(ss.get(k, 0) or 0)
        rows.append(f"""<div class="bar"><span class="bl">{lbl}</span>
          <span class="bt"><span class="bf" style="width:{v}%;background:{_fit_color(v)}"></span></span>
          <span class="bv">{v}</span></div>""")
    return '<div class="bars">' + "".join(rows) + "</div>"


def _offer_card(o):
    of = o.get("offre", {})
    fit = int(o.get("fit", 0) or 0)
    col = _fit_color(fit)
    meta = " · ".join(x for x in [e(of.get("lieu", "")), e(of.get("contrat", "")), e(of.get("source", ""))] if x)
    forts = "".join(f"<li class='ok'>{e(x)}</li>" for x in (o.get("points_forts") or []))
    ecarts = "".join(f"<li class='gap'>{e(x)}</li>" for x in (o.get("ecarts") or []))
    forts_html = f"<ul class='pl'>{forts}</ul>" if forts else ""
    ecarts_html = f"<ul class='pl'>{ecarts}</ul>" if ecarts else ""
    return f"""
    <div class="card">
      <div class="card-top">
        <div class="card-titre">{e(of.get('titre',''))}<span class="ent"> — {e(of.get('entreprise',''))}</span></div>
        <div class="fit" style="background:{col}">{fit}%</div>
      </div>
      <div class="tags"><span class="tag met">{e(of.get('metier',''))}</span>
        <span class="tag">{e(of.get('secteur',''))}</span>
        <span class="tag">{e(of.get('niveau',''))}</span></div>
      <div class="meta">{meta}</div>
      {_bars(o.get('sous_scores'))}
      {forts_html}
      {ecarts_html}
      <p class="pos"><b>Se positionner&nbsp;:</b> {e(o.get('positionnement',''))}</p>
      <a class="postuler" href="{e(of.get('url',''))}" target="_blank" rel="noopener">Voir l'offre &amp; postuler →</a>
    </div>"""


def _letter_block(lt, idx):
    of = lt.get("offre", {})
    titre = e(of.get("titre", "")) + (f" — {e(of.get('entreprise',''))}" if of.get("entreprise") else "")
    txt = e(lt.get("texte", "")).replace("\n", "<br>")
    return f"""<div class="letter">
      <div class="letter-h"><span class="ln">{idx}</span> Lettre pour <b>{titre}</b></div>
      <div class="lettre">{txt}</div></div>"""


def render_report(r, demo=False):
    cards = "\n".join(_offer_card(o) for o in r.get("offres", []))
    recos = "\n".join(f"<li>{e(x)}</li>" for x in r.get("recos", []))
    lettres = r.get("lettres") or ([r["lettre"]] if r.get("lettre") else [])
    letters_html = "\n".join(_letter_block(lt, i + 1) for i, lt in enumerate(lettres))
    demo_banner = ('<div class="demo">DÉMO — profil de test fictif</div>' if demo else "")
    logo_html = f'<img class="logo" src="{LOGO}" alt="Diaspora Connect">' if LOGO else \
        '<div class="brandtext">Diaspora Connect</div>'
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Rapport candidat — Diaspora Connect</title>
<style>
:root{{--coral:#E83030;--purple:#682890;--amber:#F8C000;--cream:#F7F3EE;--ink:#241A2E;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,system-ui,sans-serif;color:var(--ink);background:var(--cream);line-height:1.5}}
.wrap{{max-width:880px;margin:0 auto;padding:0 0 60px}}
.topbar{{background:#fff;padding:16px 40px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #EEE7E0}}
.logo{{height:42px;width:auto;max-width:62%}}
.brandtext{{font-family:Poppins,sans-serif;font-weight:700;color:var(--purple);font-size:20px}}
.topbar .lbl{{font:700 11px/1 Inter;letter-spacing:.16em;text-transform:uppercase;color:var(--coral)}}
.hero{{background:linear-gradient(120deg,var(--purple),var(--coral));color:#fff;padding:30px 40px}}
.hero h1{{font-family:Poppins,sans-serif;font-size:28px;margin:0 0 4px;font-weight:700}}
.hero .sub{{font-size:14.5px;opacity:.93}}
.section{{padding:0 40px}}
.block{{background:#fff;border-radius:16px;padding:24px 26px;margin-top:22px;box-shadow:0 2px 14px rgba(40,20,60,.06)}}
h2{{font-family:Poppins,sans-serif;font-size:18px;color:var(--purple);margin-bottom:14px;display:flex;align-items:center;gap:9px}}
h2 .n{{background:var(--amber);color:var(--ink);width:26px;height:26px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;font-weight:700}}
.profil p{{font-size:15px}} .profil .atout{{margin-top:10px;padding:12px 14px;background:#FBF4FD;border-left:4px solid var(--purple);border-radius:8px;font-size:14.5px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.card{{background:#fff;border:1px solid #EEE7E0;border-radius:14px;padding:16px 17px;display:flex;flex-direction:column}}
.card-top{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}}
.card-titre{{font-family:Poppins,sans-serif;font-weight:600;font-size:15px;line-height:1.25}}
.card-titre .ent{{font-weight:400;color:#7A7080}}
.fit{{color:#fff;font-weight:700;font-size:14px;border-radius:9px;padding:5px 9px;white-space:nowrap}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}}
.tag{{font-size:11px;background:#F1ECF5;color:#5A4A6A;border-radius:20px;padding:3px 9px;font-weight:500}}
.tag.met{{background:var(--amber);color:var(--ink);font-weight:600}}
.meta{{font-size:12px;color:#8A8090;margin:0 0 10px}}
.bars{{margin:4px 0 10px;display:flex;flex-direction:column;gap:4px}}
.bar{{display:flex;align-items:center;gap:8px;font-size:11.5px}}
.bar .bl{{width:84px;color:#6A6072}} .bar .bv{{width:24px;text-align:right;color:#6A6072;font-weight:600}}
.bar .bt{{flex:1;height:7px;background:#F0EBE4;border-radius:6px;overflow:hidden}}
.bar .bf{{display:block;height:100%;border-radius:6px}}
.pl{{list-style:none;margin:2px 0 6px;padding:0}}
.pl li{{font-size:12.5px;padding-left:20px;position:relative;margin:3px 0;line-height:1.4}}
.pl li.ok:before{{content:"✓";position:absolute;left:0;color:#1F9D55;font-weight:700}}
.pl li.gap:before{{content:"⚠";position:absolute;left:0;color:#E89B00}}
.pos{{font-size:12.5px;margin:4px 0 7px}} .pos b{{color:var(--purple)}}
.postuler{{margin-top:auto;font-size:13px;font-weight:600;color:var(--coral);text-decoration:none;padding-top:6px}}
.recos li{{margin:7px 0 7px 4px;font-size:14.5px;list-style:none;padding-left:24px;position:relative}}
.recos li:before{{content:"➜";position:absolute;left:0;color:var(--coral);font-weight:700}}
.letter{{margin-top:16px}} .letter:first-child{{margin-top:0}}
.letter-h{{font-size:13.5px;color:#5A4A6A;margin-bottom:8px;display:flex;align-items:center;gap:8px}}
.letter-h .ln{{background:var(--coral);color:#fff;width:22px;height:22px;border-radius:6px;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700}}
.lettre{{background:#FCFAF7;border:1px dashed #D8CFC4;border-radius:12px;padding:18px 20px;font-size:13.5px;line-height:1.6}}
.foot{{text-align:center;font-size:12px;color:#9A92A2;padding:26px 40px 0}}
.demo{{background:var(--amber);color:var(--ink);text-align:center;font-size:12.5px;font-weight:600;padding:8px}}
.actions{{text-align:center;padding:22px 40px 0}}
.actions a{{display:inline-block;background:var(--purple);color:#fff;text-decoration:none;font-weight:600;font-size:14px;border-radius:30px;padding:11px 22px}}
@media(max-width:660px){{.grid{{grid-template-columns:1fr}}.section,.hero,.topbar{{padding-left:18px;padding-right:18px}}.logo{{height:34px;max-width:70%}}}}
</style></head><body><div class="wrap">
{demo_banner}
<div class="topbar">{logo_html}<span class="lbl">Intelligence Emploi</span></div>
<div class="hero">
  <h1>Votre rapport de matching</h1>
  <div class="sub">Profil analysé → offres les mieux adaptées, ce qui matche & ce qui manque, et 3 lettres prêtes à envoyer</div>
</div>
<div class="section">
  <div class="block profil">
    <h2><span class="n">1</span> Votre profil</h2>
    <p>{e(r.get('profil',''))}</p>
    <div class="atout"><b>Atout diaspora :</b> {e(r.get('atout_diaspora',''))}</div>
  </div>
  <div class="block">
    <h2><span class="n">2</span> Vos {len(r.get('offres',[]))} meilleures offres</h2>
    <div class="grid">{cards}</div>
  </div>
  <div class="block">
    <h2><span class="n">3</span> Comment vous positionner</h2>
    <ul class="recos">{recos}</ul>
  </div>
  <div class="block">
    <h2><span class="n">4</span> Vos lettres de motivation ({len(lettres)})</h2>
    {letters_html}
  </div>
  <div class="actions"><a href="/">↺ Analyser un autre profil</a></div>
</div>
<div class="foot">Généré par le moteur de matching Diaspora Connect — données issues de votre profil et des offres réelles de la base. Aucune donnée inventée. Votre CV n'est pas conservé sans votre accord.</div>
</div></body></html>"""
