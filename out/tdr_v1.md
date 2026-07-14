# Termes de Référence — Portail Intelligence Emploi Diaspora Connect (v1)

*Document de cadrage — 19 juin 2026 — Mstudio / Diaspora Connect*

## 1. Contexte & justification

Le KPI le plus fragile du programme Diaspora Connect est la **conversion des immersions en emploi durable** et la **rétention** des talents en Côte d'Ivoire (cf. webinaire « Diaspora Connect, et après ? »). Aujourd'hui, l'accès à l'information emploi est éclaté entre dizaines de job boards, cabinets, LinkedIn et réseaux informels — coûteux à suivre, jamais centralisé, jamais relié aux profils des cohortes.

Le portail vise à transformer cette information dispersée en **un actif structuré, sourcé et actionnable** : agréger les offres qualifiées du marché ivoirien, les classer, et les **matcher aux talents** des cohortes pour accélérer leur insertion et leur ancrage.

**Principe directeur** : on ne construit pas « un job board de plus ». La valeur n'est pas le scraping (commodité) mais la **curation** (postes qualifiés) + le **matching** (talent ↔ offre) + l'**intelligence marché** (pour piloter le programme).

## 2. Objectifs

**Objectif général** : doter Diaspora Connect d'un système d'intelligence emploi qui augmente le taux d'insertion et de rétention des cohortes.

**Objectifs spécifiques**
1. Agréger en continu les offres d'emploi qualifiées en Côte d'Ivoire (puis UEMOA) depuis LinkedIn, job boards, cabinets, career pages et réseaux.
2. Normaliser et classer chaque offre (secteur, niveau, fonction, contrat, lieu, compétences, langue…), chaque donnée restant sourcée.
3. Matcher les profils des cohortes (Tally, Socium, vivier, CVs) aux offres pertinentes + alertes personnalisées.
4. Fournir à l'équipe un **dashboard d'intelligence marché** (secteurs qui recrutent, tensions de compétences, fourchettes salaires là où postées).
5. Construire la couche socle de façon **générique et réutilisable** (Yelema, autres usages).

## 3. Périmètre

- **Géographie** : Côte d'Ivoire d'abord ; architecture prête pour extension UEMOA (Sénégal, Mali, Burkina, Togo, Bénin…).
- **Type de postes** : focus **qualifié / cadre** (tech, data/IA, finance, produit, marketing digital, management) — la cible des profils diaspora (86 % Bac+5). Inclut aussi **freelance / missions** et **opportunités entrepreneuriales** (pour nourrir le track EIR, point faible du programme).
- **Hors périmètre (phase 1)** : postes non qualifiés / non-cadres (conservés dans la base générique mais filtrés pour DC), géographies hors UEMOA.

## 4. Architecture — 2 couches

**Couche 1 — Moteur générique d'intelligence emploi** *(réutilisable Yelema)*
Collecte multi-sources → normalisation → classification IA → **base sourcée** + dashboard marché. Indépendant de Diaspora Connect : c'est un service de veille emploi/marché brandable et vendable (SKU Yelema).

**Couche 2 — Agents de matching spécifiques** *(branchés sur la couche 1)*
- Agent « Profils Diaspora Connect » : matche les talents des cohortes aux offres, génère un flux personnalisé + alertes.
- Demain : un agent Yelema pour un client X, sans retoucher la couche 1.

## 5. Sources de données

Cartographie complète et testée dans le GSheet associé, onglet **Source Map** : https://docs.google.com/spreadsheets/d/1gVK-uouTs-KhJ4l1iiShUrcuGaugWqP7S7r24BQILPU/edit

- **Offres** : Novojob ✅, Educarriere ✅, RMO Jobcenter ✅ (testés live le 19/06) ; Emploi.ci / AfricaWork (anti-bot → Apify) ; Talent2Africa (cabinet cadres/diaspora = cible ++) ; LinkedIn Jobs (via Apify/Unipile — sensible CGU) ; Indeed CI ; cabinets (Michael Page Africa, AfricSearch) ; career pages grands groupes ; job boards VC/accélérateurs ; Agence Emploi Jeunes (public) ; groupes WhatsApp/Telegram (informel) ; Recruitee Mstudio (connecté).
- **Profils candidats (input matching)** : Tally (réponses mensuelles), Socium Job (ATS), « Candidates export » (vivier ~12k), dossier « ALL CVS », Notion (SDR Pipeline / Personas), dossiers cohortes 1 & 2.

## 6. Modèle de données & taxonomie

Chaque offre = un enregistrement avec : intitulé · entreprise · lieu · type de contrat (CDI/CDD/stage/freelance/alternance) · secteur · fonction · niveau (stage/junior/confirmé/senior/manager/exec) · compétences · langue · salaire (si posté) · date de publication · **source (nom + URL) + date de collecte** · drapeau « qualifié/cadre ». Dédoublonnage inter-sources (même offre sur plusieurs boards).

## 7. Fonctionnalités

1. **Collecte** automatisée multi-sources (scrapers + Apify + APIs), rafraîchissement quotidien.
2. **Normalisation + classification IA** : un agent lit l'offre et la tague selon la taxonomie.
3. **Déduplication**.
4. **Matching** profil ↔ offre (embeddings, comme le sourcing vivier existant) + scoring.
5. **Alertes** personnalisées par talent (email / WhatsApp).
6. **Dashboard intelligence marché** (secteurs, salaires sourcés, tensions de compétences).
7. **Recherche / filtres** côté talents (portail web, phase 3).

## 8. Moteur de matching Diaspora Connect

Entrée : profils cohortes (compétences, séniorité, fonction visée, secteur, contraintes). Sortie : pour chaque talent, top offres scorées + alertes ; pour l'équipe, vue « talents non encore matchés » et « offres sans candidat ». Réutilise le pipeline de matching éprouvé (Fanga / Waribei Finance).

## 9. Livrables & phasage

- **Étape 0 (faite — 19/06)** : Source Map testée + **Base sourcée v1** (échantillon réel d'offres classées et sourcées). GSheet : https://docs.google.com/spreadsheets/d/1gVK-uouTs-KhJ4l1iiShUrcuGaugWqP7S7r24BQILPU/edit
- **Phase 1 (~2-3 jours)** : premier lot complet multi-sources (volume), classé et sourcé, dans une base unique.
- **Phase 2** : moteur de matching cohortes + alertes.
- **Phase 3** : portail web (interne d'abord, public ensuite) + dashboard marché.

## 10. Gouvernance & règles

- **Donnée toujours sourcée** : chaque offre garde nom de source + URL + date de collecte ; le dashboard n'agrège que du sourcé (fourchettes salaires uniquement là où réellement postées — **zéro chiffre inventé**).
- **Légal / CGU** : le scraping LinkedIn est sensible (CGU + anti-bot) → faible risque en outil interne, à arbitrer avant tout passage en produit public.
- **RGPD / données candidats** : profils traités en interne, accès restreint.
- **Fraîcheur** : rafraîchissement quotidien, offres expirées archivées.

## 11. Rôles & pilotage

- **Sponsor** : Leslie Ossété.
- **Pilote programme** : Andréa Mbuyamba (Diaspora Connect).
- **Build & ops** : Zuri (agent) + ressource tech à confirmer.

## 12. Indicateurs de succès du portail

Couverture (nb sources / nb offres agrégées) · taux de matching (offres pertinentes par talent) · nb de mises en relation générées · **placements attribués** · réduction du temps-vers-placement · taux de rétention des cohortes.

## 13. Réutilisation Yelema

La couche 1 est livrée comme un module autonome → devient un **SKU Yelema « veille emploi / intelligence marché »** vendable à des clients (RH, cabinets, institutions), sans dépendance à Diaspora Connect.

## 14. Risques & mitigations

| Risque | Mitigation |
|---|---|
| Blocage anti-bot (LinkedIn, Emploi.ci) | Apify / APIs officielles / rotation ; arbitrage interne vs public |
| Données non sourcées / inventées | Règle dure : source obligatoire par ligne |
| Bruit (offres non qualifiées) | Drapeau « qualifié/cadre » + filtre couche matching |
| Doublons inter-sources | Déduplication systématique |
| Dépendance à une source | Multi-sources dès la phase 1 |

## 15. Questions ouvertes / décisions

1. Portail **interne** (cohortes) d'abord, puis **public** : confirmer le moment du passage public (impacte le risque LinkedIn).
2. Ressource tech dédiée côté Mstudio / Diaspora Connect.
3. Canal d'alerte préféré des talents (email vs WhatsApp).
4. Monétisation Yelema de la couche 1 : à cadrer après la phase 1.

---
*Annexe vivante : GSheet « Portail Emploi Diaspora Connect — Étape 0 » (Source Map + Base sourcée v1).*
