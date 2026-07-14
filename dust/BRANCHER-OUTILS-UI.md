# Brancher les outils des 3 agents Dust (à faire en UI)

Les agents sont créés via l'API → ils arrivent SANS outils (limite Dust connue). Cette fiche
ajoute les outils en 5 min côté interface. Modèle (Sonnet 4.6, reasoning high) + instructions
+ garde-fous sont déjà en place — ne PAS y toucher.

## Chemin commun
dust.tt → espace de travail Mstudio → **Agents** (menu gauche) → chercher l'agent →
bouton **Éditer / Edit** → section **Outils / Tools** (ou « Capabilities ») → **Ajouter un outil**.
Activer aussi le toggle **Visualisation / Visualization** quand indiqué. → **Enregistrer / Save**.

---

## 1. Veille_Emploi  (sId 08APkang9w)
- ✅ **Recherche web / Web search** — pour aller chercher les offres sur les job boards.
- ✅ **Visualisation** — tableaux interactifs + graphes de marché.
> Test : « Donne-moi un panorama des offres data/finance en Côte d'Ivoire cette semaine. »

## 2. Matching_Candidat  (sId a25Wm97Q4X)
- ✅ **Visualisation** — rapport candidat visuel (cartes d'offres, barres de sous-scores).
- ℹ️ **Lecture des CV** : déjà native — on **attache** le CV (PDF/DOCX) directement dans la
  conversation, l'agent lit le contenu. (Optionnel : activer « Extraire des données » si tu veux
  forcer l'extraction sur des PDF complexes.)
> Test : attacher un CV (fictif pour l'instant) + coller quelques offres → il sort le matching + lettres.

## 3. Backoffice_Emploi  (sId 6dPGFGwAIs)
- ✅ **Visualisation** — dashboard (funnel, courbes, répartitions).
- ✅ **Source de données / connexion** : connecter le **Google Sheet de suivi** (Drive) OU
  utiliser **Query tables** en y déposant le tableur de suivi.
> Test : « Fais le point d'activité du mois + où ça bloque dans le funnel. »

---

## Notes
- Si un outil n'apparaît pas : vérifier que la connexion (Drive/Sheets, Web) est activée au niveau
  de l'espace de travail Dust avant de l'ajouter à l'agent.
- ⚠️ Données perso : pour Matching, **CV fictifs uniquement** tant que la note RGPD n'est pas validée.
- Après branchement, plus rien à refaire : les instructions pilotent déjà le comportement.
