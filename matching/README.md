# Diaspora Connect — Moteur de matching emploi (self-service)

Outil candidat : on dépose un **CV** (PDF / Word / texte), on reçoit en quelques secondes
les **offres les mieux adaptées** en Côte d'Ivoire, des **recommandations de positionnement**
et une **lettre de motivation prête à copier-coller**.

Brique complémentaire du **portail offres** Diaspora Connect (board public des offres).

## Comment ça marche
1. Extraction du texte du CV (PDF via PyMuPDF + fallback `pdftotext`, DOCX, TXT).
2. Embeddings du CV vs index des offres réelles (OpenAI `text-embedding-3-small`, cosine).
3. Un appel LLM (`gpt-4o`) re-classe le top et rédige profil + offres notées + recos + lettre.

## Fichiers
| Fichier | Rôle |
|---|---|
| `lib.py` | helpers OpenAI (embeddings + génération), 0 dépendance (urllib) |
| `build_offer_index.py` | construit `data/offer_index.json` depuis `../data/offers_active.csv` |
| `engine.py` | extraction CV + `run_match(cv_text)` (cœur commun) |
| `report.py` | rendu du rapport candidat HTML brandé |
| `app.py` | service web self-service (FastAPI) avec consentement + RGPD |
| `match.py` / `build_report.py` | démo en ligne de commande |

## Lancer en local
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # jamais commité
python3 build_offer_index.py        # une fois, ou quand la base d'offres change
uvicorn app:app --port 8061         # puis http://127.0.0.1:8061
```

## ⚠️ Hébergement
GitHub **Pages** est statique : il ne peut **pas** exécuter ce service (Python + appel IA),
et la clé OpenAI **ne doit jamais** être mise dans une page statique (fuite). Pour un lien
public fonctionnel, déployer ce dépôt sur un petit hôte applicatif (le `Procfile` est prêt :
Render / Railway / Fly / un VPS), avec `OPENAI_API_KEY` en variable d'environnement.

## 🔒 Données personnelles (RGPD / bailleur FEF)
Voir `RGPD-cadrage-donnees-perso.md`. Règles déjà appliquées dans le code :
- **consentement explicite obligatoire** avant toute analyse ;
- le CV est traité **en mémoire** et **n'est pas conservé** ;
- seul un **événement anonyme** (date + métier dominant) est journalisé pour le backoffice —
  aucun nom, email ni contenu de CV ;
- **CV fictifs uniquement** tant que la note de cadrage n'est pas validée.
