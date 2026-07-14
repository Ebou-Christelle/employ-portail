#!/usr/bin/env python3
"""Couche 1 — normalisation + classification + scoring DC.
- niveau normalisé (Stage / Junior / Confirmé / Senior / Manager-Direction)
- secteur normalisé (heuristique mots-clés, sourcée par titre/secteur d'origine)
- score ⭐ pertinence Diaspora Connect (1-5) PAR NIVEAU DE QUALIFICATION
  → on NE filtre PAS les junior/mid (beaucoup de young graduates postulent à DC),
    on les note différemment. Le score combine niveau + adéquation secteur aux profils diaspora.
Toute classification reste traçable (on garde le niveau/secteur d'origine dans la base)."""
import re, unicodedata


def _norm(s):
    # remplacer apostrophes/tirets/slashes par une espace AVANT le strip ascii,
    # sinon « d'affaires » → « daffaires » (l'apostrophe courbe est juste supprimée)
    s = re.sub(r"[’'`\-/().,]", " ", s or "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


# ---- niveau --------------------------------------------------------------
def niveau(raw_level, titre):
    src = _norm(raw_level + " " + titre)
    if any(k in src for k in ["stage", "stagiaire", "alternance", "apprenti", "internship", "intern"]):
        return "Stage"
    if any(k in src for k in ["junior", "debutant", "premiere experience", "0 a 1", "0 a 2",
                              "jeune diplome", "entry level", "entry-level"]):
        return "Junior"
    if any(k in src for k in ["directeur", "director", "head of", "chief", "dga", "vp ", "executif", "executive"]):
        return "Manager/Direction"
    if any(k in src for k in ["senior", "mid-senior", "lead ", "manager", "responsable", "chef de", "chef d",
                              "coordinateur", "coordonnateur", "superviseur", "principal"]):
        return "Senior"
    if any(k in src for k in ["confirme", "experimente", "associate", "3 a", "4 a", "5 a", "6 a", "10 ans"]):
        return "Confirmé"
    return "Confirmé"  # défaut prudent (mid)


# ---- secteur -------------------------------------------------------------
SECTOR_RULES = [
    ("Tech & Digital", ["developpeur", "developer", "data", "software", "informatique", "it", "digital",
                          "reseau", "systeme", "systemes", "cyber", "cybersecurity", "ia", "ai", "web",
                          "devops", "sre", "cloud", "ntic", "ingenieur logiciel", "fullstack", "backend",
                          "frontend", "data center", "telecom", "administrateur systemes", "produit digital",
                          "product owner", "product manager", "machine learning", "data scientist",
                          "data analyst", "data engineer", "qa engineer", "tech lead",
                          "ux", "ui", "designer", "infographiste", "graphiste", "informaticien"]),
    ("Finance & Banque", ["comptable", "comptabilite", "finance", "financial", "financier", "audit", "auditor",
                           "banque", "bank", "banking", "assurance", "credit", "tresorerie", "treasury",
                           "controle de gestion", "controleur", "fiscal", "guichetier", "caisse", "recouvrement",
                           "accountant", "accounting", "payment", "investor", "investment"]),
    ("Marketing & Communication", ["marketing", "communication", "communications", "brand", "community",
                                     "content", "growth", "publicite", "social media", "media", "commercial digital"]),
    ("Ressources Humaines", ["ressources humaines", "rh", "recrutement", "recruteur", "recruiter", "recruiting",
                              "talent acquisition", "human resources", "people operations", "paie", "payroll",
                              "formation rh", "learning and development"]),
    ("Relation Client & BPO", ["customer support", "customer service", "customer experience", "customer care",
                                "customer success", "support client", "service client", "service a la clientele",
                                "relation client", "call center", "contact center", "bpo", "teleconseiller",
                                "support bilingue", "service a la clientele bilingue"]),
    ("Ingénierie & Industrie", ["production", "maintenance", "industrie", "usine", "qualite", "quality", "hse",
                                 "safety", "technicien", "ingenieur", "engineer", "engineering", "atelier",
                                 "mecanique", "mecanicien", "mechanical", "electrical", "electromecanique",
                                 "automatisme", "energie", "operateur machine", "reservoir", "packaging", "welding"]),
    ("Commerce & Vente", ["commercial", "vente", "sales", "business development", "business developer",
                           "account executive", "account manager", "account", "clientele", "distribution",
                           "technico-commercial", "chargee de clientele", "vendeur", "vendeuse", "caissier",
                           "caissiere", "charge d affaires", "chargee d affaires", "charge de comptes",
                           "affilie", "dermo-conseill", "conseiller"]),
    ("Logistique & Achats", ["logistique", "logistics", "supply", "supply chain", "achat", "procurement",
                              "transport", "magasinier", "warehouse", "approvisionnement", "import", "export",
                              "douane", "quai", "pointeur", "cariste", "chauffeur", "driver", "livreur",
                              "conducteur", "vtc", "manutention", "chef de quai"]),
    ("Hôtellerie & Tourisme", ["hotel", "restaurant", "cuisinier", "serveur", "tourisme", "reception", "chef de rang"]),
    ("Santé & Pharma", ["medecin", "infirmier", "nurse", "pharma", "pharmacien", "sante", "medical", "soignant", "biomedical"]),
    ("Éducation & Formation", ["enseignant", "professeur", "teacher", "formateur", "trainer", "education",
                                "instituteur", "maternelle", "primaire"]),
    ("Juridique", ["juriste", "avocat", "lawyer", "legal", "conformite", "compliance", "contentieux"]),
    ("BTP & Construction", ["genie civil", "btp", "construction", "architecte", "chantier", "topographe",
                             "batiment", "beton", "prefabrique", "macon", "coffreur"]),
    ("ONG & Projets", ["ong", "ngo", "humanitaire", "humanitarian", "coordinateur projet", "chef de projet",
                        "programme", "value chain", "biodiversity", "monitoring and evaluation", "mrv", "bailleur"]),
    ("Administration", ["assistant", "secretaire", "administratif", "administrative", "accueil",
                         "office manager", "standardiste", "saisie", "data entry", "correspondant fichier"]),
]


def _match(kws, src):
    """Tokens longs (≥4) = match préfixe en début de mot (gère pluriels/féminins :
    assistant→assistante, livreur→livreurs, beton→betons, conseiller→conseillère).
    Tokens courts (≤3 : it, ia, ai, ui, ux, rh) = limite de mot stricte (évite ai∈aide)."""
    for k in kws:
        pat = r"\b" + re.escape(k) + (r"\b" if len(k) <= 3 else "")
        if re.search(pat, src):
            return k
    return None


def secteur(raw_sector, titre, entreprise=""):
    # le TITRE seul est le signal le plus fiable. On n'utilise PAS le nom d'entreprise
    # (ex. "Talent2Africa" matcherait RH, "IT Services" matcherait Tech à tort).
    src = _norm(titre)
    for label, kws in SECTOR_RULES:
        if _match(kws, src):
            return label
    # repli : catégorie d'origine (ex. catégorie RMO)
    if raw_sector:
        rs = _norm(raw_sector)
        for label, kws in SECTOR_RULES:
            if _norm(label).split()[0] in rs or _match(kws, rs):
                return label
    return "Autres / Généraliste"


# ---- métier (fonction du poste) ------------------------------------------
# Plus FIN que le secteur : la fonction réelle. Ordre SPÉCIFIQUE→GÉNÉRAL —
# « Directeur Commercial » tombe sur Commercial (la fonction), « Directeur Général »
# sur Direction (aucune fonction nommée). Le niveau gère déjà la séniorité.
METIER_RULES = [
    ("Data & IA", ["data analyst", "data scientist", "data engineer", "machine learning",
                    "intelligence artificielle", "artificial intelligence", "business intelligence",
                    "data analytics", "statisticien", "analyste de donnees", "big data", "ai", "annotation"]),
    ("Développement & Logiciel", ["developpeur", "developer", "software engineer", "software",
                                   "fullstack", "full stack", "backend", "back end", "frontend",
                                   "front end", "ingenieur logiciel", "programmeur", "tech lead",
                                   "qa engineer", "testeur", "tester", "mobile developer", "web developer"]),
    ("DevOps, Infra & Réseau", ["devops", "sre", "cloud", "infrastructure", "administrateur systeme",
                                 "administrateur systemes", "sysadmin", "ingenieur reseau", "reseaux", "reseau",
                                 "base de donnees", "database", "information technology", "it support",
                                 "systems administrator", "it specialist"]),
    ("Cybersécurité", ["cybersecurite", "cybersecurity", "cyber", "securite informatique",
                        "soc analyst", "pentester", "rssi", "security analyst"]),
    ("Product & Design", ["product manager", "product owner", "chef de produit", "cheffe de produit",
                           "produit digital", "ux", "ui", "designer", "graphiste", "infographiste",
                           "direction artistique", "motion designer", "product designer"]),
    ("Marketing & Growth", ["marketing", "growth", "seo", "sem", "acquisition", "brand",
                             "digital marketing", "trafic manager", "publicite", "category manager"]),
    ("Communication & Contenu", ["communication", "community manager", "content", "redacteur", "redaction",
                                  "copywriter", "writer", "social media", "relations publiques", "contenu",
                                  "illustrator", "storyteller", "story teller", "creative", "audiovisuel"]),
    ("Commercial & Vente", ["commercial", "vente", "sales", "vendeur", "vendeuse", "vendedor",
                             "technico commercial", "account executive", "account manager", "key account",
                             "charge de clientele", "chargee de clientele", "charge de comptes",
                             "comptes entreprises", "caissier", "caissiere", "conseiller de vente",
                             "business developer", "business development", "charge d affaires",
                             "chargee d affaires", "responsable de magasin", "responsable d agence",
                             "affilie", "dermo conseill"]),
    ("Relation Client & Support", ["customer support", "customer service", "customer experience",
                                    "customer success", "customer care", "service client", "relation client",
                                    "support client", "call center", "contact center", "teleconseiller",
                                    "bpo", "assistance client", "service a la clientele", "support specialist",
                                    "support officer"]),
    ("Comptabilité", ["comptable", "comptabilite", "accountant", "accounting", "aide comptable", "book keeper"]),
    ("Finance & Contrôle de gestion", ["finance", "financier", "financial", "controle de gestion",
                                        "controleur", "tresorerie", "treasury", "analyste financier", "fiscal",
                                        "recouvrement", "analyste credit", "credit", "cash management", "payments",
                                        "payment", "budgetaire", "investisseurs"]),
    ("Audit", ["audit", "auditor", "auditeur", "commissaire aux comptes"]),
    ("Banque & Assurance", ["banque", "banking", "guichetier", "assurance", "actuaire", "souscription", "bancaire"]),
    ("Ressources Humaines", ["ressources humaines", "rh", "hr", "recrutement", "recruteur", "recruiter",
                              "talent acquisition", "talent manager", "people talent", "human resources",
                              "people operations", "learning and development", "paie", "payroll", "gestionnaire rh"]),
    ("Juridique & Conformité", ["juriste", "avocat", "lawyer", "legal", "conformite", "compliance",
                                 "contentieux", "secretaire juridique"]),
    ("Gestion de projet", ["chef de projet", "cheffe de projet", "project manager", "pmo",
                            "coordinateur projet", "coordonnateur projet", "scrum master",
                            "program manager", "chef de programme", "coordinateur de programme",
                            "chef projet"]),
    ("Conseil, Expertise & Stratégie", ["consultant", "conseil ", "conseiller regional", "strategie",
                                         "strategy", "business analyst", "analyste business", "advisor",
                                         "expert", "capacity development", "knowledge management",
                                         "government affairs", "screening"]),
    ("Direction & Management", ["directeur", "directrice", "director", "head of", "chief", "dga",
                                 "country manager", "general manager", "gerente", "country lead",
                                 "responsable pays", "responsable de departement"]),
    ("Logistique & Supply Chain", ["logistique", "logistics", "supply chain", "supply", "magasinier",
                                    "storekeeper", "store keeper", "entrepot", "warehouse", "distribution center",
                                    "transport", "douane", "import", "export", "cariste", "chef de quai",
                                    "pointeur", "manutention", "approvisionnement", "navire"]),
    ("Achats & Procurement", ["achat", "achats", "procurement", "acheteur", "approvisionneur"]),
    ("Ingénierie & Technique", ["ingenieur", "engineer", "engineering", "technicien", "tecnico", "mecanique",
                                 "mecanicien", "electrical", "electromecanique", "automatisme", "genie",
                                 "instrumentation", "electrique", "geologue", "geologist", "agronome"]),
    ("Production & Industrie", ["production", "usine", "operateur machine", "operateur de production",
                                "atelier", "fabrication", "conducteur de ligne", "packaging", "operator"]),
    ("Qualité, Hygiène & Sécurité", ["qhse", "hse", "qualite", "quality", "safety", "controle qualite",
                                      "environnement", "e s safeguards"]),
    ("Maintenance", ["maintenance"]),
    ("Opérations & Supervision", ["operations", "operationnel", "operationnelle", "operationnels", "supervis",
                                   "team leader", "superviseur", "moyens generaux", "performance observatory"]),
    ("Administration & Assistanat", ["assistant", "assistante", "secretaire", "administratif",
                                      "administrative", "office manager", "standardiste", "saisie",
                                      "data entry", "excel specialist", "accueil", "correspondant fichier"]),
    ("Santé & Médical", ["medecin", "infirmier", "infirmiere", "pharmacien", "pharmacie", "soignant",
                          "medical", "health", "sante", "biomedical", "sage femme", "kinesitherapeute", "opticien"]),
    ("Enseignement & Formation", ["enseignant", "professeur", "teacher", "formateur", "trainer", "training",
                                   "instituteur", "educateur", "maternelle", "primaire", "universitaire"]),
    ("BTP & Construction", ["genie civil", "btp", "construction", "architecte", "chantier", "topographe",
                            "macon", "coffreur", "conducteur de travaux", "metreur", "beton", "cartographique"]),
    ("Hôtellerie & Restauration", ["hotel", "restaurant", "cuisinier", "serveur", "serveuse",
                                    "chef de rang", "barman", "gouvernante", "housekeeper", "buandier",
                                    "food service"]),
    ("Métiers de terrain", ["chauffeur", "livreur", "coursier", "gardien", "agent de securite", "vigile",
                            "maitre chien", "manoeuvre", "menage", "nettoyage", "jardinier", "planton",
                            "agent d entretien", "femme de chambre", "ouvrier", "conducteur vehicule",
                            "conducteur"]),
]


def metier(titre, raw_level=""):
    src = _norm(titre)
    for label, kws in METIER_RULES:
        if _match(kws, src):
            return label
    return "Autres métiers"


# ---- score DC ------------------------------------------------------------
NONQUAL = ["chauffeur", "manoeuvre", "gardien", "agent de securite", "menage", "caissier", "livreur",
           "ouvrier", "manutention", "coursier", "soudeur", "macon", "tricot", "couturier", "planton",
           "nettoyage", "femme de chambre", "serveur", "serveuse", "cuisinier", "plongeur", "vigile",
           "poids lourd", "menagere", "jardinier", "agent d entretien"]
PRIORITY = {"Tech & Digital", "Finance & Banque", "Marketing & Communication", "Ressources Humaines",
            "Juridique", "Ingénierie & Industrie", "ONG & Projets"}
SECONDARY = {"Commerce & Vente", "Logistique & Achats", "Santé & Pharma", "Éducation & Formation",
             "BTP & Construction", "Administration", "Hôtellerie & Tourisme", "Relation Client & BPO"}


def score_dc(niv, sect, titre):
    """1-5 ⭐. Garde junior/mid (young graduates DC) mais valorise cadre + secteurs cibles diaspora."""
    t = _norm(titre)
    if any(k in t for k in NONQUAL):
        return 1
    base = {"Stage": 3, "Junior": 3, "Confirmé": 4, "Senior": 5, "Manager/Direction": 5}.get(niv, 3)
    if sect in PRIORITY:
        s = base
    elif sect in SECONDARY:
        s = base - 1
    else:
        s = base - 1
    return max(1, min(5, s))


def stars(n):
    return "★" * n + "☆" * (5 - n)


def classify(rec):
    niv = niveau(rec.get("niveau", ""), rec.get("titre", ""))
    sect = secteur(rec.get("secteur", ""), rec.get("titre", ""), rec.get("entreprise", ""))
    sc = score_dc(niv, sect, rec.get("titre", ""))
    rec["niveau_norm"] = niv
    rec["secteur_norm"] = sect
    rec["metier_norm"] = metier(rec.get("titre", ""), rec.get("niveau", ""))
    rec["score_dc"] = sc
    rec["score_etoiles"] = stars(sc)
    return rec
