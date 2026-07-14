# Cadrage données personnelles — Portail / Moteur de matching Diaspora Connect

> Note interne Mstudio · Diaspora Connect — v1, 19/06/2026
> Objet : poser le cadre de protection des données **avant** de collecter le moindre CV réel.
> Statut : à valider (Leslie + Program Manager DC + relecture juridique légère).
> ⚠️ Tant que ce cadre n'est pas validé, le moteur tourne **uniquement sur des CV fictifs de test**.

---

## 1. Pourquoi cette note

L'outil demande au candidat de déposer son **CV et/ou profil LinkedIn**. Ce sont des
**données à caractère personnel** (identité, parcours, coordonnées, parfois données
« sensibles » glissées dans un CV : photo, nationalité, situation familiale, santé).

Deux raisons de cadrer dès maintenant :

1. **Bailleur FEF (Fonds Équipe France+ / MEAE)** : financement public français → attentes
   de conformité **RGPD** sur tout traitement de données lié au projet.
2. **Côte d'Ivoire** : la collecte se fait en CI → **Loi n°2013-450 du 19/06/2013** relative
   à la protection des données à caractère personnel s'applique (autorité : **ARTCI**).
   *(Références à faire confirmer par un conseil ; à minima déclaration/notification du
   traitement à l'ARTCI à vérifier.)*

Principe directeur : **collecter le strict minimum, pour une finalité claire, le garder peu
de temps, le protéger, et permettre au candidat de partir.**

---

## 2. Finalité (à afficher au candidat)

Le CV est utilisé **uniquement pour** :
- proposer au candidat les offres d'emploi les plus adaptées en Côte d'Ivoire ;
- générer des recommandations de positionnement + une lettre de motivation ;
- permettre à l'équipe Diaspora Connect de l'accompagner dans son insertion.

**Interdits explicites** (pas de réutilisation hors finalité) :
- pas de revente / partage à des tiers hors écosystème DC ;
- pas d'envoi du CV à une entreprise sans accord du candidat ;
- pas d'usage pour autre chose que l'accompagnement emploi DC.

---

## 3. Base légale

**Consentement explicite** du candidat, recueilli **au moment du dépôt** (case à cocher
non pré-cochée + lien vers la présente notice). Le consentement doit être :
- libre (le refus n'empêche pas de consulter les offres publiques du portail) ;
- spécifique (matching emploi DC) ;
- révocable à tout moment (cf. §6).

---

## 4. Minimisation

- On demande **le CV + un email de contact**, rien de plus en obligatoire.
- On **n'exige pas** : photo, date de naissance, nationalité, situation familiale, n° pièce
  d'identité. Si présents dans le CV, ils ne sont **ni extraits ni indexés** comme critères.
- Le matching s'appuie sur : intitulés de postes, compétences, secteurs, niveau, localisation
  visée — **pas** sur des attributs personnels sensibles.

---

## 5. Stockage & sécurité

| Règle | Mise en œuvre |
|---|---|
| **Jamais** dans le brain partagé de la flotte | les CV ne sont jamais écrits dans `~/brain/` ni gbrain |
| **Jamais** dans un doc partagé au domaine `mstudio.vc` ni un espace Dust ouvert | rapport candidat = privé, non publié sur GitHub Pages |
| Accès limité | seuls Leslie + l'équipe DC habilitée accèdent aux CV / rapports |
| Données au repos | dossier dédié à accès restreint sur le serveur, séparé du code public |
| Pas de log de contenu | les CV ne transitent pas dans des logs en clair |
| Sous-traitant IA (OpenAI) | le contenu du CV est envoyé à l'API OpenAI pour l'analyse → **à mentionner au candidat** ; option à étudier : modèle auto-hébergé si exigence bailleur |

> Point d'attention sous-traitance : l'analyse passe par l'API OpenAI (hors UE). À documenter
> dans la notice + vérifier l'acceptabilité côté FEF. Alternative possible si bloquant :
> embeddings/LLM auto-hébergés.

---

## 6. Rétention & droits du candidat

- **Rétention** : CV + rapport conservés **12 mois** après le dernier contact, ou jusqu'à la
  fin de l'accompagnement DC, puis **suppression automatique**. *(durée à arbitrer avec DC)*
- **Droits** (à rappeler dans la notice + un email de contact dédié) :
  - accès à ses données,
  - rectification,
  - **suppression** sur simple demande,
  - retrait du consentement (= suppression + arrêt du traitement).
- **Point de contact** : une adresse unique (ex. `diaspora@mstudio.vc` — à confirmer) qui
  traite les demandes sous un délai raisonnable (≤ 30 jours).

---

## 7. Notice de confidentialité (à afficher au dépôt)

Texte court à présenter avant l'upload, avec case de consentement :

> « En déposant votre CV, vous permettez à Diaspora Connect d'analyser votre profil pour vous
> proposer des offres d'emploi en Côte d'Ivoire adaptées, des recommandations et une lettre de
> motivation. Vos données sont réservées à cet usage, accessibles uniquement à l'équipe
> Diaspora Connect, conservées 12 mois maximum, et supprimées sur simple demande à
> [contact]. L'analyse utilise un service d'IA (OpenAI). Vous pouvez retirer votre
> consentement à tout moment. ☐ J'ai lu et j'accepte. »

---

## 8. Ce qui est déjà respecté côté technique (état actuel)

- Le moteur tourne **sur CV fictif** (`matching/cv_test.txt`) — aucun vrai CV collecté.
- Le code du moteur porte la règle en commentaire : « ne jamais écrire un CV réel dans le
  brain partagé / un doc domaine ».
- Le **portail public** (offres) ne contient **aucune** donnée candidat — uniquement des
  offres d'emploi publiques.
- Le rapport candidat est généré **en local**, **non publié**.

## 9. À trancher avant la mise en service réelle

1. Durée de rétention exacte (12 mois proposé).
2. Adresse de contact « données » (proposé `diaspora@mstudio.vc`).
3. Acceptabilité du sous-traitant OpenAI côté FEF, ou bascule modèle auto-hébergé.
4. Déclaration/notification ARTCI à vérifier (CI).
5. Qui, côté DC, est habilité à voir les CV/rapports.
