#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dry-run des 3 agents Dust Recrutement sur des inputs réels (offres + CV fictif + suivi).
Agents 'nus' (outils non branchés) → on fournit l'input EN TEXTE dans le message (mode
'contenu collé' prévu par les prompts). Briefs MINIMAUX/neutres (cf feedback run générique).
Crée 3 convs unlisted staggered ~55s (anti rate-limit), poll jusqu'à succeeded, sauve outputs
+ URLs au bon format app.dust.tt/.../conversation/."""
import os, csv, json, time, urllib.request, urllib.error
from pathlib import Path

API = "https://dust.tt/api/v1"
WID = os.environ["DUST_WORKSPACE_ID"]
KEY = os.environ["DUST_API_KEY"]
ROOT = Path("/home/openclaw/agents/main/projects/diaspora-emploi-portal")
OUT = ROOT / "dust" / "dryrun"
OUT.mkdir(parents=True, exist_ok=True)
H = {"Authorization": f"Bearer {KEY}"}
HJ = {**H, "Content-Type": "application/json"}

AG = {"veille": "08APkang9w", "matching": "a25Wm97Q4X", "backoffice": "6dPGFGwAIs"}


# ---------- build inputs ----------
def load_offers():
    rows = list(csv.DictReader(open(ROOT / "data" / "offers_active.csv", encoding="utf-8")))
    return rows


def sample_spread(rows, n):
    """échantillon réparti sur tout le fichier (diversité secteurs/scores)."""
    if len(rows) <= n:
        return rows
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)]


def offers_block_raw(rows):
    """offres 'brutes' (labels source, sans notre classification) pour Veille."""
    lines = []
    for i, r in enumerate(rows):
        lines.append(" | ".join(x for x in [
            f"[{i}] {r['titre']} — {r['entreprise']}",
            r.get("lieu", ""), r.get("contrat", ""),
            (f"salaire: {r['salaire']}" if r.get("salaire") else ""),
            (f"niveau source: {r['niveau_source']}" if r.get("niveau_source") else ""),
            (f"secteur source: {r['secteur_source']}" if r.get("secteur_source") else ""),
            f"source: {r['source']}", r.get("url", "")] if x))
    return "\n".join(lines)


def offers_block_classified(rows):
    """offres avec champs structurés pour Matching."""
    lines = []
    for i, r in enumerate(rows):
        lines.append(" | ".join(x for x in [
            f"[{i}] {r['titre']} — {r['entreprise']}",
            f"secteur: {r['secteur_norm']}", f"niveau: {r['niveau_norm']}",
            f"métier: {r['metier_norm']}", r.get("lieu", ""), r.get("contrat", ""),
            f"URL: {r['url']}"] if x))
    return "\n".join(lines)


def build_briefs():
    rows = load_offers()
    veille_rows = sample_spread(rows, 45)
    match_rows = sample_spread(rows, 35)

    veille = (
        "Voici un lot d'offres d'emploi réelles collectées en Côte d'Ivoire (échantillon de "
        f"{len(veille_rows)} offres sur une base de {len(rows)} actives). "
        "Classe-les (niveau / secteur / métier) avec un score d'adéquation, puis donne la synthèse marché.\n\n"
        + offers_block_raw(veille_rows))

    cv = (ROOT / "matching" / "cv_test.txt").read_text()
    matching = (
        "Voici un profil candidat (CV) et une base d'offres réelles en Côte d'Ivoire. "
        "Sors le matching : meilleures offres notées, forces/écarts, positionnement, et lettres de motivation.\n\n"
        "=== PROFIL CANDIDAT (CV) ===\n" + cv +
        f"\n\n=== BASE D'OFFRES ({len(match_rows)}) ===\n" + offers_block_classified(match_rows))

    # backoffice : chiffres cohortes réels (mémoire DC) + funnel reconstitué pour la démo + activité outil réelle
    ev = [json.loads(l) for l in (ROOT / "matching" / "data" / "events.jsonl").read_text().splitlines() if l.strip()]
    backoffice = (
        "Voici les données de suivi du programme d'accompagnement vers l'emploi « Diaspora Connect » "
        "(échantillon illustratif : chiffres de cohortes réels là où connus + funnel intermédiaire reconstitué "
        "pour la démonstration). Fais le tableau de bord, le funnel avec taux de conversion, le diagnostic et les actions.\n\n"
        "PÉRIODE : programme à date, juin 2026.\n\n"
        "COHORTE 1 (clôturée) :\n"
        "- Talents accompagnés : 32 (70% femmes)\n"
        "- Profils déposés (outil matching) : 32\n"
        "- Matchings générés : 32\n"
        "- Candidatures envoyées : 121\n"
        "- Entretiens obtenus : 47\n"
        "- Placements (emploi/mission) : 22\n"
        "- Rétention à 6 mois : 22/22\n"
        "- Délai moyen dépôt→placement : 64 jours\n"
        "- Secteurs des placements : Banque/Finance 7, Tech 5, BPO/Relation client 4, Conseil 3, Autres 3\n\n"
        "COHORTE 2 (en cours) :\n"
        "- Talents : 25 (80% femmes)\n"
        "- Profils déposés : 19\n"
        "- Matchings générés : 19\n"
        "- Candidatures envoyées : 58\n"
        "- Entretiens obtenus : 21\n"
        "- Placements : 6\n"
        "- Rétention à 3 mois : 6/6\n"
        "- Délai moyen dépôt→placement (placés) : 41 jours\n\n"
        f"ACTIVITÉ OUTIL SELF-SERVICE (réel, 19–23 juin) : {len(ev)} dépôts ; "
        "métiers dominants Finance & Contrôle de gestion et Data & IA ; fit moyen du top ~88%.")

    (OUT / "brief_veille.txt").write_text(veille)
    (OUT / "brief_matching.txt").write_text(matching)
    (OUT / "brief_backoffice.txt").write_text(backoffice)
    return {"veille": veille, "matching": matching, "backoffice": backoffice}


# ---------- dust conv ----------
def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=HJ, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=90).read())


def get(path):
    req = urllib.request.Request(API + path, headers=H, method="GET")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def create(name, agent, content):
    body = {"title": f"Dry-run {name} — {time_label}", "visibility": "unlisted",
            "message": {"content": content, "mentions": [{"configurationId": agent}],
                        "context": {"username": "zuri", "timezone": "Africa/Abidjan",
                                    "fullName": "Zuri (Mstudio)", "email": "zuri@mstudio.vc",
                                    "profilePictureUrl": None, "origin": "api"}},
            "blocking": False}
    r = post(f"/w/{WID}/assistant/conversations", body)
    csid = r["conversation"]["sId"]
    url = f"https://app.dust.tt/w/{WID}/conversation/{csid}"
    return csid, url


def poll(csid):
    c = get(f"/w/{WID}/assistant/conversations/{csid}")
    content = c.get("conversation", {}).get("content", [])
    if not content:
        return None, None
    lv = content[-1]
    msg = lv[-1] if isinstance(lv, list) else lv
    if msg.get("type") == "agent_message":
        return msg.get("status"), (msg.get("content") or "")
    return None, None


time_label = "23 juin 2026"

if __name__ == "__main__":
    briefs = build_briefs()
    print("briefs:", {k: len(v) for k, v in briefs.items()})
    convs = {}
    for i, (name, agent) in enumerate(AG.items()):
        csid, url = create(name, agent, briefs[name])
        convs[name] = {"sId": csid, "url": url, "status": "created"}
        print(f"🆕 {name} -> {csid} | {url}")
        if i < len(AG) - 1:
            time.sleep(55)  # anti rate-limit

    deadline = time.time() + 600
    done = set()
    while time.time() < deadline and len(done) < len(convs):
        for name, c in convs.items():
            if name in done:
                continue
            try:
                st, txt = poll(c["sId"])
            except Exception as e:
                print(f"poll {name} err {repr(e)[:120]}"); continue
            if st and st != c["status"]:
                print(f"{name}: {st}"); c["status"] = st
            if st == "succeeded":
                (OUT / f"out_{name}.md").write_text(f"# Dry-run {name}\nConv: {c['url']}\n\n---\n\n{txt}")
                c["chars"] = len(txt); done.add(name)
                print(f"✅ {name} DONE {len(txt)} chars")
            elif st in ("errored", "cancelled"):
                c["error"] = txt[:200]; done.add(name)
                print(f"❌ {name} {st}: {txt[:160]}")
        if len(done) < len(convs):
            time.sleep(8)

    (OUT / "convs.json").write_text(json.dumps(convs, indent=2, ensure_ascii=False))
    print("\n=== SUMMARY ===")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'error'} for k, v in convs.items()}, indent=2, ensure_ascii=False))
