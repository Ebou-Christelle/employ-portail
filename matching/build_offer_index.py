#!/usr/bin/env python3
"""Construit l'index d'embeddings des offres actives (couche 2 — matching).
Lit ../data/offers_active.csv -> embeddings OpenAI -> data/offer_index.json.
À relancer quand la base d'offres change (le cron hebdo peut l'appeler)."""
import csv, json, os
from lib import embed

HERE = os.path.dirname(__file__)
# offers_active.csv : dans le workspace portail (../data) ou à côté (data/) pour un repo autonome
SRC = next((p for p in (os.path.join(HERE, "..", "data", "offers_active.csv"),
                        os.path.join(HERE, "data", "offers_active.csv")) if os.path.exists(p)),
           os.path.join(HERE, "..", "data", "offers_active.csv"))
OUT = os.path.join(HERE, "data", "offer_index.json")
os.makedirs(os.path.join(HERE, "data"), exist_ok=True)

rows = list(csv.DictReader(open(SRC, encoding="utf-8")))


def offer_text(r):
    # représentation riche d'une offre pour l'embedding (fonction + domaine + séniorité + lieu)
    parts = [r["titre"]]
    if r.get("metier_norm"):  parts.append(f"Métier : {r['metier_norm']}")
    if r.get("secteur_norm"): parts.append(f"Secteur : {r['secteur_norm']}")
    if r.get("niveau_norm"):  parts.append(f"Niveau : {r['niveau_norm']}")
    if r.get("entreprise"):   parts.append(f"Entreprise : {r['entreprise']}")
    if r.get("lieu"):         parts.append(f"Lieu : {r['lieu']}")
    if r.get("contrat"):      parts.append(f"Contrat : {r['contrat']}")
    return ". ".join(parts)


texts = [offer_text(r) for r in rows]
print(f"embedding {len(texts)} offres…")
vecs = embed(texts)

index = []
for r, v in zip(rows, vecs):
    index.append({
        "titre": r["titre"], "entreprise": r["entreprise"], "metier": r.get("metier_norm", ""),
        "secteur": r["secteur_norm"], "niveau": r["niveau_norm"], "lieu": r["lieu"],
        "contrat": r["contrat"], "date_pub": r.get("date_pub", ""), "date_limite": r.get("date_limite", ""),
        "salaire": r.get("salaire", ""), "source": r["source"], "url": r["url"],
        "score_dc": int(r["score_dc"]), "emb": v,
    })
json.dump(index, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(f"index écrit : {OUT} ({len(index)} offres, dim {len(vecs[0])})")
