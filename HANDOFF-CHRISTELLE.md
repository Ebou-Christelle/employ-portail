# Portail Emploi Diaspora Connect — Passation technique

**Pour :** Christelle (tech lead) — déploiement en production
**Objet :** tout le nécessaire pour reprendre, héberger et faire vivre le portail emploi.

---

## 1. Ce que c'est (3 briques)

| Brique | Rôle | Techno | État actuel |
|---|---|---|---|
| **A. Board d'offres** (front public) | Page unique qui liste les offres d'emploi CI, filtrable (métier / secteur / niveau / lieu), bouton « Postuler » par offre | HTML/CSS/JS **statique**, single-file, **zéro backend** | 🟢 en ligne (aperçu GitHub Pages) |
| **B. Moteur de matching** | Le candidat dépose son CV → top offres adaptées + reco de positionnement + lettre de motivation | **FastAPI** (Python) + OpenAI (embeddings + `gpt-4o`) | 🟠 tourne en local / tunnel temporaire — **à héberger** |
| **C. Pipeline de rafraîchissement** | Récupère les offres (LinkedIn via Apify + Novojob + Educarriere + RMO), gère le cycle de vie (nouvelles / archivées), pousse la base, rebuild le front | Scripts Python + bash, orchestré 1×/semaine | 🟢 automatisé (cron hebdo, côté Mstudio) |

+ **3 agents Dust** optionnels (`Veille_Emploi`, `Matching_Candidat`, `Backoffice_Emploi`) — prompts fournis dans `dust/prompts/`.

---

## 2. Liens

- **Aperçu live (front) :** https://leslita06.github.io/diaspora-emploi-portal/  *(noindex — lien de partage, pas référencé)*
- **Repo GitHub du front publié :** `github.com/leslita06/diaspora-emploi-portal` *(contient uniquement le site statique buildé)*
- **Base de données des offres (source de vérité partagée) :** Google Sheet `1gVK-uouTs-KhJ4l1iiShUrcuGaugWqP7S7r24BQILPU`
- **TDR / cahier des charges :** Google Doc `1V_Cs1mrUFcLZ33m0ZRQ5UIS-M-rVlQMD8vWndSYl0TE`
- **Code source complet :** le zip qui accompagne ce document (`diaspora-emploi-portal-source_v1.zip`).

---

## 3. Arborescence du code

```
diaspora-emploi-portal/
├── site/                     # BRIQUE A — front statique buildé (ce qui est publié)
│   ├── index.html            #   page unique (offres embarquées en JSON dans la page)
│   ├── assets/dc-logo.png
│   └── .nojekyll             #   requis pour GitHub Pages
├── scripts/                  # BRIQUE C — pipeline data + build
│   ├── build_site.py         #   data → site/index.html  (le générateur du front)
│   ├── collectors.py         #   scrapers Novojob / Educarriere / RMO Jobcenter
│   ├── pull_linkedin.py      #   scraper LinkedIn via Apify
│   ├── run_portal.py         #   moteur cycle de vie (nouvelles / archivées / dédup)
│   ├── classify.py           #   normalisation métier/secteur/niveau + score
│   ├── verify_links.py       #   retire les annonces fermées (liens morts)
│   ├── push_portal_sheet.py  #   pousse la base vers le Google Sheet
│   ├── publish_site.sh       #   rebuild + push du front sur GitHub Pages
│   └── refresh_portal.sh     #   orchestrateur hebdo (enchaîne tout ci-dessus)
├── data/                     # base vivante
│   ├── offers_active.csv     #   offres actives = SOURCE de build du front
│   └── offers_archive.csv    #   historique des offres archivées
├── matching/                 # BRIQUE B — moteur de matching (app web à déployer)
│   ├── app.py                #   service FastAPI (consentement + RGPD intégrés)
│   ├── engine.py             #   extraction CV + run_match()
│   ├── build_offer_index.py  #   construit l'index d'offres (embeddings)
│   ├── lib.py, report.py     #   helpers OpenAI + rendu du rapport candidat
│   ├── requirements.txt
│   ├── Procfile              #   prêt pour Render / Railway / Fly / VPS
│   └── render.yaml           #   blueprint Render (déploiement 1-clic)
├── dust/prompts/             # 3 agents Dust (optionnel)
├── RGPD-cadrage-donnees-perso.md
└── HANDOFF-CHRISTELLE.md     # ce document
```

**Schéma d'une offre** (`data/offers_active.csv`) :
`score_etoiles, score_dc, titre, entreprise, metier_norm, secteur_norm, niveau_norm, lieu, contrat, date_pub, date_limite, salaire, source, url, niveau_source, secteur_source, first_seen, last_seen, statut, raison_archive`

> **Règle d'or du projet :** zéro donnée inventée. Un champ vide = l'info n'existait pas à la source (ne jamais le combler par déduction).

---

## 4. Lancer en local (validation rapide)

**Front (brique A) :**
```bash
python3 scripts/build_site.py       # régénère site/index.html depuis data/offers_active.csv
# ouvrir site/index.html dans un navigateur (statique, aucun serveur requis)
```

**Moteur de matching (brique B) :**
```bash
cd matching
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...         # fourni séparément (jamais commité)
python3 build_offer_index.py         # 1× (ou à chaque MAJ de la base d'offres)
uvicorn app:app --port 8061          # → http://127.0.0.1:8061
```

---

## 5. Déployer en production — recette

### Brique A — le board (statique)
Le front est un **fichier statique** : il tourne sur n'importe quel hébergement statique (GitHub Pages, Netlify, Vercel, Cloudflare Pages, un bucket S3, ou le serveur web de Mstudio).
- **Le plus simple pour passer sur un vrai domaine** (ex. `emploi.diaspora-connect.africa`) : garder GitHub Pages et brancher un domaine custom (fichier `CNAME`), **ou** copier `site/` sur votre hébergeur et pointer le DNS.
- **Pour rendre le portail indexable** (SEO) une fois validé : retirer la balise `noindex` dans `build_site.py` et rebuild.

### Brique B — le moteur de matching (applicatif)
GitHub Pages est statique → **il ne peut pas** exécuter ce service (Python + appel IA), et la clé OpenAI **ne doit jamais** être dans une page statique.
- **Render (recommandé, blueprint fourni)** : New → Blueprint → repo dédié → `render.yaml` fait le reste ; renseigner `OPENAI_API_KEY` dans l'onglet Environment (secret).
- Alternatives : Railway / Fly.io / un petit VPS (le `Procfile` marche partout).
- ⚠️ **Une fois l'URL Render obtenue**, remplacer dans `scripts/build_site.py` la variable `MATCH_URL` (aujourd'hui un tunnel Cloudflare **temporaire**) par l'URL permanente, puis rebuild le front. Sinon le bouton « déposer mon CV » cassera.

### Brique C — le rafraîchissement hebdo
`scripts/refresh_portal.sh` enchaîne : LinkedIn (Apify) → collectors web → cycle de vie → vérif liens → push GSheet → rebuild + republie le front. Aujourd'hui déclenché par un cron côté Mstudio (lundi 06h30 UTC). À reprendre en cron sur votre infra (crontab / GitHub Action planifiée / worker Render).

---

## 6. Secrets / accès nécessaires (transmis séparément, jamais dans le code)

| Clé | Sert à | Où la mettre |
|---|---|---|
| **Apify token** | scraper LinkedIn (actor `curious_coder~linkedin-jobs-scraper`) | variable d'env (le code lit `~/.config/agents/secrets/apify.txt` — à adapter à votre env) |
| **OPENAI_API_KEY** | moteur de matching (embeddings + `gpt-4o`) | variable d'env de l'hôte applicatif (Render : Environment) |
| **Accès Google Sheet** | écrire la base d'offres dans le GSheet | actuellement OAuth `zuri@mstudio.vc` (`gog`) — pour la prod, prévoir un **compte de service Google** avec accès en écriture au Sheet |
| **GitHub token** | pousser le front sur GitHub Pages | variable d'env `GITHUB_TOKEN` (ou vos propres identifiants d'hébergeur) |

> Aucune de ces clés n'est dans le code source (vérifié). Les scripts les lisent depuis l'environnement / le secrets store. Leslie te transmettra les valeurs par un canal sécurisé.

---

## 7. Données personnelles (RGPD — important, bailleur FEF)

Le moteur de matching traite des **CV** (donnée personnelle). Cadrage complet dans `RGPD-cadrage-donnees-perso.md`. Déjà implémenté côté code :
- **consentement explicite obligatoire** avant toute analyse ;
- le CV est traité **en mémoire** et **n'est pas conservé** ;
- seul un **événement anonyme** (date + métier dominant) est journalisé pour le backoffice — aucun nom, email, ni contenu de CV.

À valider/adapter avec vous avant l'ouverture au public réel (aujourd'hui : CV fictifs uniquement).

---

## 8. Ordre de priorité suggéré pour la reprise

1. Cloner le code (zip) dans un repo que vous maîtrisez.
2. Déployer la **brique B** (matching) sur Render → obtenir l'URL permanente.
3. Mettre `MATCH_URL` à jour + rebuild le front → déployer la **brique A** sur le domaine cible.
4. Reprendre le **cron hebdo** (brique C) sur votre infra avec vos secrets.
5. Valider le cadrage RGPD avant ouverture publique.

Des questions sur un bout précis du pipeline : je peux détailler n'importe quel script.
