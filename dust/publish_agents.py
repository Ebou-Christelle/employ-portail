#!/usr/bin/env python3
"""Crée les 3 agents Dust GÉNÉRIQUES du moteur Intelligence Emploi (réutilisables Yelema) :
  1. Veille_Emploi       — intelligence du marché de l'emploi (collecte / classement / synthèse)
  2. Matching_Candidat   — matching profil (CV/LinkedIn) -> offres (fit, forces/écarts, lettres)
  3. Backoffice_Emploi   — pilotage insertion/rétention (KPIs, funnel, reporting)

Pattern éprouvé = POST /agent_configurations/import (cf projects/new-agents-2026-05-22/publish.py).
⚠️ /import crée des agents "nus" : les outils MCP (web, fichiers, viz) se branchent en UI ensuite.
Idempotent : skip si le nom existe déjà.
"""
import json, urllib.request, urllib.error, os
from pathlib import Path

# --- secrets ---
S = {}
for line in (Path.home() / ".config/agents/secrets.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        S[k.strip()] = v.strip().strip('"').strip("'")
KEY = S.get("DUST_API_KEY") or (Path.home() / ".config/dust/api_key").read_text().strip()
WID = S.get("DUST_WORKSPACE_ID") or (Path.home() / ".config/dust/workspace_id").read_text().strip()
EDITOR = "leslie@mstudio.vc"
TAG = "Recrutement"  # tag choisi par Leslie 20/6 (moteur générique réutilisable, ex-Yelema)
PROMPTS = Path(__file__).parent / "prompts"

AGENTS = [
    {
        "name": "Veille_Emploi",
        "handle": "Veille_Emploi",
        "file": "Veille_Emploi.md",
        "desc": "Intelligence du marché de l'emploi : collecte, normalise, classe (niveau/secteur/métier) et score des offres, puis produit une synthèse marché (compétences demandées, salaires sourcés, tendances). Générique, réutilisable par marché. Zéro donnée non sourcée.",
        "emoji_path": "bg-blue-300/mag/1f50d",
        "temperature": 0.3,
        "reasoning": "high",
    },
    {
        "name": "Matching_Candidat",
        "handle": "Matching_Candidat",
        "file": "Matching_Candidat.md",
        "desc": "Matching d'un profil (CV et/ou LinkedIn) vers des offres réelles : top offres notées (fit + sous-scores compétences/secteur/séniorité/localisation), points forts, écarts honnêtes, positionnement, et lettres de motivation prêtes à envoyer. Générique. Aucune invention, données perso protégées.",
        "emoji_path": "bg-emerald-400/handshake/1f91d",
        "temperature": 0.4,
        "reasoning": "high",
    },
    {
        "name": "Backoffice_Emploi",
        "handle": "Backoffice_Emploi",
        "file": "Backoffice_Emploi.md",
        "desc": "Pilotage d'un programme d'insertion : KPIs, funnel dépôts→placements→rétention avec taux de conversion, diagnostic des goulots, reporting équipe/financeur. Générique. Agrégats anonymisés only, jamais de donnée perso ni financière interne dans les docs tiers.",
        "emoji_path": "bg-amber-400/bar_chart/1f4ca",
        "temperature": 0.3,
        "reasoning": "high",
    },
]


def http(url, method="POST", body=None):
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        return json.loads(urllib.request.urlopen(req).read()), 200
    except urllib.error.HTTPError as e:
        return e.read().decode(), e.code


def list_agents():
    d, _ = http(f"https://dust.tt/api/v1/w/{WID}/assistant/agent_configurations", method="GET")
    if isinstance(d, dict):
        return {a["name"]: a["sId"] for a in d.get("agentConfigurations", [])}
    return {}


def create_agent(meta):
    inst = (PROMPTS / meta["file"]).read_text()
    avatar = f"https://dust.tt/static/emojis/{meta['emoji_path']}"
    body = {
        "agent": {
            "name": meta["name"],
            "handle": meta["handle"],
            "description": meta["desc"],
            "scope": "visible",
            "status": "active",
            "max_steps_per_run": 64,
            "visualization_enabled": False,
            "pictureUrl": avatar,
            "avatar_url": avatar,
        },
        "instructions": inst,
        "generation_settings": {
            "model_id": "claude-sonnet-4-6",
            "provider_id": "anthropic",
            "temperature": meta["temperature"],
            "reasoning_effort": meta["reasoning"],
        },
        "tags": [{"name": TAG, "kind": "standard"}],
        "editors": [EDITOR],
        "toolset": [],
    }
    return http(f"https://dust.tt/api/v1/w/{WID}/assistant/agent_configurations/import", body=body)


if __name__ == "__main__":
    existing = list_agents()
    results = []
    for meta in AGENTS:
        if meta["name"] in existing:
            print(f"⏭️  {meta['name']} existe déjà (sId {existing[meta['name']]})")
            results.append({"name": meta["name"], "sId": existing[meta["name"]], "status": "exists"})
            continue
        inst_len = len((PROMPTS / meta["file"]).read_text())
        print(f"🆕 Création {meta['name']} (tag: {TAG}, instr {inst_len} chars)...")
        resp, code = create_agent(meta)
        if code == 200 and isinstance(resp, dict):
            ac = resp.get("agentConfiguration", resp)
            sid = ac.get("sId")
            print(f"   ✅ sId={sid}")
            results.append({"name": meta["name"], "sId": sid, "tag": TAG})
        else:
            print(f"   ❌ {code} {str(resp)[:400]}")
            results.append({"name": meta["name"], "status": "error", "error": str(resp)[:300]})

    print("\n=== SUMMARY ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    Path(__file__).parent.joinpath("agents_sids.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False))
