# modules/ia.py - Générateur de contenu Ben Tech PRO
import requests
import pandas as pd
import random
import time
from datetime import datetime
from urllib.parse import quote
import os
import warnings
from typing import Tuple, Optional, Dict, Any, List

# Ignorer les avertissements NumPy
warnings.filterwarnings('ignore', category=RuntimeWarning)

# -----------------------------------------------------------------
# CONFIGURATION GOOGLE SHEETS
# -----------------------------------------------------------------
try:
    from modules.google_sheets_db import (
        lire_historique_gsheets, 
        sauvegarder_post_gsheets,
        mettre_a_jour_post_gsheets,
        compter_posts_gsheets
    )
    GOOGLE_SHEETS_AVAILABLE = True
    print("✅ Module Google Sheets disponible")
except ImportError as e:
    GOOGLE_SHEETS_AVAILABLE = False
    print(f"⚠️ Google Sheets non disponible: {e}")
except Exception as e:
    GOOGLE_SHEETS_AVAILABLE = False
    print(f"⚠️ Erreur chargement Google Sheets: {e}")

# -----------------------------------------------------------------
# CONFIGURATION GOOGLE DRIVE
# -----------------------------------------------------------------
try:
    from modules.google_drive import drive_manager, initialize_drive_manager
    GOOGLE_DRIVE_AVAILABLE = True
    print("✅ Module Google Drive disponible")
except ImportError as e:
    GOOGLE_DRIVE_AVAILABLE = False
    print(f"⚠️ Google Drive non disponible: {e}")
except Exception as e:
    GOOGLE_DRIVE_AVAILABLE = False
    print(f"⚠️ Erreur chargement Google Drive: {e}")

# -----------------------------------------------------------------
# CONFIGURATION DES APIS (utilise votre config.py existant)
# -----------------------------------------------------------------
try:
    from config import (
        OPENAI_API_KEY, 
        OPENAI_MODEL, 
        UNSPLASH_API_KEY,
        GOOGLE_DRIVE_CREDENTIALS,  # De votre config.py
        GOOGLE_DRIVE_FOLDER_ID     # De votre config.py
    )
    
    # Initialiser Google Drive manager si disponible
    if GOOGLE_DRIVE_AVAILABLE and GOOGLE_DRIVE_CREDENTIALS and os.path.exists(GOOGLE_DRIVE_CREDENTIALS):
        try:
            initialize_drive_manager(GOOGLE_DRIVE_CREDENTIALS, GOOGLE_DRIVE_FOLDER_ID)
            if drive_manager and drive_manager.service:
                print("✅ Gestionnaire Google Drive initialisé")
            else:
                print("⚠️ Google Drive non initialisé correctement")
                GOOGLE_DRIVE_AVAILABLE = False
        except Exception as e:
            print(f"⚠️ Erreur initialisation Google Drive: {e}")
            GOOGLE_DRIVE_AVAILABLE = False
    else:
        if GOOGLE_DRIVE_AVAILABLE:
            print("⚠️ Credentials Google Drive non trouvés, désactivation")
            GOOGLE_DRIVE_AVAILABLE = False
            
except ImportError:
    # Fallback pour les variables d'environnement directes
    import os
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY", "")
    GOOGLE_DRIVE_CREDENTIALS = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON", "")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    
    # Initialiser Google Drive manager
    if GOOGLE_DRIVE_AVAILABLE and GOOGLE_DRIVE_CREDENTIALS:
        initialize_drive_manager(GOOGLE_DRIVE_CREDENTIALS, GOOGLE_DRIVE_FOLDER_ID)

EXCEL_FILE = "historique_posts.xlsx"
IMAGE_FOLDER = "images_posts"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ---------------------------
# AGENTS BEN TECH AVEC DÉPARTEMENTS
# ---------------------------
AGENTS_BEN_TECH = [
    {
        "nom": "Badibanga",
        "prenom": "Beny",
        "poste": "CEO & Fondateur",
        "departement": "Direction Générale",
        "specialite": "Stratégie digitale & Transformation numérique",
        "signature": "Ensemble, créons l'avenir digital de votre entreprise. 💼"
    },
    {
        "nom": "NGOLA",
        "prenom": "David",
        "poste": "Directeur Technique",
        "departement": "Développement & Innovation",
        "specialite": "Architecture logicielle & Solutions IA",
        "signature": "L'excellence technique au service de votre vision. 🚀"
    },
    {
        "nom": "Paul",
        "prenom": "Paul",
        "poste": "Responsable Marketing Digital",
        "departement": "Marketing & Communication",
        "specialite": "Stratégie de contenu & Growth Hacking",
        "signature": "Votre succès digital est notre priorité. 📈"
    },
    {
        "nom": "Sarah",
        "prenom": "sandrina",
        "poste": "Cheffe de Projet",
        "departement": "Gestion de Projet",
        "specialite": "Suivi client & Optimisation processus",
        "signature": "Votre projet, notre engagement total. 🤝"
    },
    {
        "nom": "Daniel",
        "prenom": "Daniel",
        "poste": "Expert en Cybersécurité",
        "departement": "Sécurité & Infrastructure",
        "specialite": "Protection données & Conformité RGPD",
        "signature": "Votre sécurité digitale, notre expertise. 🔒"
    },
    {
        "nom": "Anderson",
        "prenom": "philippe",
        "poste": "Spécialiste Mobile",
        "departement": "Développement Mobile",
        "specialite": "Applications iOS/Android & UX Design",
        "signature": "Votre application, une expérience exceptionnelle. 📱"
    },
    {
        "nom": "Dercy",
        "prenom": "Dercy",
        "poste": "Responsable Formation",
        "departement": "Formation & Support",
        "specialite": "Formation technique & Support client",
        "signature": "Votre réussite, notre mission pédagogique. 🎓"
    }
]

def get_agent_aleatoire() -> Dict[str, str]:
    """Retourne un agent aléatoire avec ses informations complètes"""
    return random.choice(AGENTS_BEN_TECH)

# ---------------------------
# Utilitaires OpenAI (retry)
# ---------------------------
def openai_chat_request(messages: list, model: str = OPENAI_MODEL, max_retries: int = 3, timeout: int = 15) -> Dict[str, Any]:
    """Requête à l'API OpenAI avec retry"""
    if not OPENAI_API_KEY:
        raise ValueError("❌ OPENAI_API_KEY non configurée")
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 900}

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == max_retries:
                raise
            backoff = 1.5 ** attempt
            time.sleep(backoff)

# ---------------------------
# 1. Lecture/écriture des données (Google Sheets + fallback Excel)
# ---------------------------
def lire_historique() -> pd.DataFrame:
    """Lit l'historique depuis Google Sheets ou fallback local"""
    
    # Essayer Google Sheets d'abord
    if GOOGLE_SHEETS_AVAILABLE:
        try:
            df = lire_historique_gsheets()
            if df is not None and not df.empty:
                print(f"📊 {len(df)} posts chargés depuis Google Sheets")
                return df
            else:
                print("⚠️ Google Sheets vide ou erreur, fallback local")
        except Exception as e:
            print(f"⚠️ Erreur Google Sheets, fallback local: {e}")
    
    # Fallback : Excel local
    try:
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        
        # Vérifier que toutes les colonnes nécessaires existent
        colonnes_requises = [
            "titre", "theme", "service", "style",
            "texte_marketing", "script_video",
            "reaction_positive", "reaction_negative",
            "taux_conversion_estime", "publication_effective",
            "nom_plateforme", "suggestion", "date",
            "score_performance_final", "image_path", "image_auteur", "type_publication",
            "agent_responsable",
            "image_drive_id", "image_drive_filename", "image_drive_url",
            "image_public_link", "image_direct_link"
        ]
        
        for col in colonnes_requises:
            if col not in df.columns:
                df[col] = ""
        
        print(f"📊 {len(df)} posts chargés depuis Excel local")
        return df
        
    except FileNotFoundError:
        df = pd.DataFrame(columns=colonnes_requises)
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        print("📝 Fichier Excel créé avec colonnes")
        return df
    except Exception as e:
        print(f"❌ Erreur lecture Excel: {e}")
        return pd.DataFrame(columns=colonnes_requises)

def mettre_a_jour_historique(nouveau_post: dict):
    """Sauvegarde dans Google Sheets ou fallback local"""
    
    gsheets_success = False
    
    # Essayer Google Sheets d'abord
    if GOOGLE_SHEETS_AVAILABLE:
        try:
            gsheets_success = sauvegarder_post_gsheets(nouveau_post)
            if gsheets_success:
                print(f"✅ Post sauvegardé dans Google Sheets: {nouveau_post.get('titre', 'N/A')}")
            else:
                print("⚠️ Échec sauvegarde Google Sheets, fallback local uniquement")
        except Exception as e:
            print(f"⚠️ Erreur Google Sheets: {e}, fallback local uniquement")
            gsheets_success = False
    
    # TOUJOURS sauvegarder localement
    try:
        try:
            df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        except FileNotFoundError:
            df = pd.DataFrame(columns=[
                "titre", "theme", "service", "style",
                "texte_marketing", "script_video",
                "reaction_positive", "reaction_negative",
                "taux_conversion_estime", "publication_effective",
                "nom_plateforme", "suggestion", "date",
                "score_performance_final", "image_path", "image_auteur", "type_publication",
                "agent_responsable",
                "image_drive_id", "image_drive_filename", "image_drive_url",
                "image_public_link", "image_direct_link"
            ])
        
        nouveau_df = pd.DataFrame([nouveau_post])
        
        for col in df.columns:
            if col not in nouveau_df.columns:
                nouveau_df[col] = ""
        
        df = pd.concat([df, nouveau_df], ignore_index=True)
        
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        if not GOOGLE_SHEETS_AVAILABLE or not gsheets_success:
            print(f"✅ Post sauvegardé localement uniquement: {nouveau_post.get('titre', 'Sans titre')}")
        else:
            print(f"✅ Post sauvegardé localement (backup): {nouveau_post.get('titre', 'Sans titre')}")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde locale: {e}")
        try:
            df = pd.DataFrame([nouveau_post])
            df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
            print("⚠️ Sauvegarde d'urgence réussie")
        except Exception as e2:
            print(f"❌ Erreur critique sauvegarde: {e2}")

# ---------------------------
# 2. Services list
# ---------------------------
SERVICES_BEN_TECH = [
    "Création de sites web",
    "Développement d'applications web",
    "Développement d'applications mobiles",
    "Création d'applications desktop",
    "Création d'agents IA",
    "Automatisation des entreprises",
    "Formations en informatique",
    "Consulting web",
    "Maintenance systèmes & sécurité"
]

# ---------------------------
# 3. Analyse IA avancée - PROMPT PROFESSIONNEL
# ---------------------------
def analyse_ia_avance(df: pd.DataFrame) -> str:
    if df.empty:
        return """📊 STRATÉGIE INITIALE BEN TECH - MARKETING DIGITAL

🎯 OBJECTIFS POUR DÉMARRAGE FORT :
1. Équilibre contenu/service : 70% valeur ajoutée / 30% promotion service
2. Positionnement : Expert en transformation digitale congolais
3. Tonalité : Mix autorité technique + accessibilité entrepreneuriale

📈 RECOMMANDATIONS IMMÉDIATES :
• Contenu pédagogique : Tutoriels tech adaptés marché local
• Preuve sociale : Études de cas clients africains
• Format optimal : Vidéos 45-60s + posts LinkedIn détaillés
• Fréquence : 3-4 posts/semaine (2 valeur, 1 service, 1 témoignage)

🎨 STYLE RECOMMANDÉ :
« Pédagogie technique avec impact entrepreneurial - La référence tech qui parle business »
"""
    
    sample = df.sort_values(by="date", ascending=False).head(60)
    rows = sample[["theme", "service", "style", "reaction_positive", "reaction_negative", "taux_conversion_estime", "suggestion", "type_publication"]]
    records = rows.fillna("").to_dict(orient="records")

    prompt = f"""
# RÔLE : STRATÈGE MARKETING DIGITAL SENIOR - AGENCE BEN TECH
Vous êtes le Directeur Marketing de Ben Tech, une agence tech leader en RDC.
Votre mission : Analyser les performances passées et développer une stratégie gagnante.

## CONTEXTE ENTREPRISE :
- Entreprise : Ben Tech - Agence de transformation digitale
- Positionnement : Expert tech pour PME/entrepreneurs africains
- Valeurs : Excellence technique, Impact local, Accessibilité
- Objectif business : Devenir la référence tech en RDC francophone

## DONNÉES HISTORIQUES À ANALYSER :
{records}

## COMMANDES D'ANALYSE STRATÉGIQUE :

1. DIAGNOSTIC PERFORMANCE (Format tableau mental) :
   • 3 Forces à capitaliser (thèmes/services/formats qui convertissent)
   • 3 Points d'amélioration critiques
   • Taux d'engagement vs objectifs sectoriels
   • ROI contenu (valeur vs service)

2. RECOMMANDATIONS OPÉRATIONNELLES (5 actions concrètes) :
   • Adaptation thématique pour marché local
   • Optimisation funnel de conversion
   • Amélioration taux d'engagement
   • Innovation formats (nouveaux canaux/formats)
   • Personnalisation pour segments clients

3. POSITIONNEMENT TONALITÉ :
   • Définir le "Ton Ben Tech" unique (mix autorité + proximité)
   • Axes de différenciation vs concurrents
   • Messaging clé pour chaque service

4. ROADMAP CONTENU 30 JOURS :
   • Répartition idéale types de contenu
   • Calendrier éditorial suggéré
   • KPIs à suivre quotidiennement

## FORMAT DE RÉPONSE :
Structure professionnelle avec sections claires, bullet points actionnables, chiffres quand possible.
Ton : Expert, stratégique, orienté résultats, adapté marché africain.
"""
    response = openai_chat_request([{"role": "user", "content": prompt}])
    return response["choices"][0]["message"]["content"].strip()

# ---------------------------
# 4. Choix automatique (thème/service/style/type)
# ---------------------------
def choisir_theme(df: pd.DataFrame) -> str:
    if df.empty:
        seeds = [
            "Transformation digitale des PME congolaises",
            "Solutions tech pour entrepreneur africain",
            "Cybersécurité pour entreprises locales",
            "Automatisation intelligente en RDC",
            "Développement web optimisé marché africain",
            "Applications mobiles qui transforment le business",
            "Formation tech accessible à tous"
        ]
        return random.choice(seeds)
    
    themes_valides = df["theme"].dropna()
    if themes_valides.empty:
        return random.choice(seeds)
    
    scores = themes_valides.groupby(themes_valides).size()
    if scores.sum() > 0:
        return scores.idxmax()
    return random.choice(themes_valides.tolist() or ["Transformation digitale des PME congolaises"])

def choisir_service(df: pd.DataFrame) -> str:
    if df.empty:
        return random.choice(SERVICES_BEN_TECH)
    
    services_valides = df["service"].dropna()
    if services_valides.empty:
        return random.choice(SERVICES_BEN_TECH)
    
    scores = services_valides.groupby(services_valides).size()
    if scores.sum() > 0:
        return scores.idxmax()
    return random.choice(SERVICES_BEN_TECH)

def choisir_style(df: pd.DataFrame) -> str:
    styles = ["pédagogique", "énergique", "direct", "storytelling", "technique", "influenceur", "entrepreneurial"]
    if df.empty:
        return "entrepreneurial"
    
    styles_valides = df["style"].dropna()
    if styles_valides.empty:
        return random.choice(styles)
    
    scores = styles_valides.groupby(styles_valides).size()
    if scores.sum() > 0:
        best = scores.idxmax()
        if best in styles:
            return best
    return random.choice(styles)

def choisir_type_publication(df: pd.DataFrame) -> str:
    if df.empty:
        return "contenu"
    
    if "type_publication" not in df.columns:
        return "contenu" if random.random() < 0.7 else "service"
    
    recent = df.tail(12)
    contenu_score = recent[recent["type_publication"] == "contenu"]["reaction_positive"].sum() if "type_publication" in recent.columns else 0
    service_score = recent[recent["type_publication"] == "service"]["reaction_positive"].sum() if "type_publication" in recent.columns else 0
    
    if contenu_score > service_score:
        return "contenu" if random.random() < 0.75 else "service"
    return "service" if random.random() < 0.6 else "contenu"

# ---------------------------
# 5. Génération image via Unsplash avec sauvegarde UNIQUEMENT Google Drive
# ---------------------------
def trouver_image_unsplash(theme: str, commentaires: Optional[list[str]] = None) -> Tuple[Optional[str], Optional[dict]]:
    """
    Recherche une image sur Unsplash et la sauvegarde UNIQUEMENT dans Google Drive
    
    Returns:
        Tuple: (auteur, infos_google_drive)
    """
    if not UNSPLASH_API_KEY:
        print("❌ Aucun UNSPLASH_API_KEY défini.")
        return None, None

    def _upload_to_google_drive(url: str, theme_safe: str) -> Optional[dict]:
        """
        Télécharge une image depuis une URL et l'upload UNIQUEMENT vers Google Drive
        
        Returns:
            dict: Informations Google Drive ou None
        """
        try:
            # Télécharger l'image depuis l'URL
            img_resp = requests.get(url, timeout=20)
            img_resp.raise_for_status()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_theme = "".join(c if c.isalnum() else "_" for c in theme)[:30]
            filename = f"ben_tech_{safe_theme}_{timestamp}.jpg"
            
            # Vérifier si Google Drive est disponible
            if not GOOGLE_DRIVE_AVAILABLE or not drive_manager or not drive_manager.service:
                print("❌ Google Drive non disponible pour l'upload")
                return None
            
            # Préparer la description
            description = f"""
Image pour Ben Tech Pro
Thème: {theme}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Source: Unsplash
Usage: Marketing digital et réseaux sociaux
Entreprise: Ben Tech - Agence de Transformation Digitale
"""
            
            # Upload DIRECT vers Google Drive
            print(f"⬆️ Upload vers Google Drive: {filename}")
            drive_info = drive_manager.upload_image_from_url(
                image_url=url,
                filename=filename,
                description=description.strip()
            )
            
            if drive_info:
                print(f"✅ Image uploadée avec succès vers Google Drive")
                
                # Rendre le fichier public pour pouvoir l'afficher
                public_link = drive_manager.create_public_link(drive_info['id'])
                if public_link:
                    drive_info['public_link'] = public_link
                    print(f"🔗 Lien public créé: {public_link}")
                
                # Ajouter le lien d'affichage direct (pour embed dans les sites)
                drive_info['direct_image_link'] = f"https://drive.google.com/uc?id={drive_info['id']}"
                
                return drive_info
            else:
                print("❌ Échec de l'upload vers Google Drive")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de l'upload Google Drive : {e}")
            return None

    # Reformulation du thème avec contexte Ben Tech
    try:
        prompt_reformulation = f"""
En tant qu'expert en marketing digital pour Ben Tech (agence tech en RDC), 
reformulez ce thème pour une recherche d'image professionnelle sur Unsplash.

THÈME ORIGINAL : "{theme}"

CONTEXTE BEN TECH :
- Agence de transformation digitale
- Clients : PME et entrepreneurs africains
- Positionnement : Tech d'excellence accessible

Retournez 3 mots-clés maximum pour la recherche d'image, en français.
Format : "mot1 mot2 mot3"
"""
        resp = openai_chat_request([{"role": "user", "content": prompt_reformulation}])
        keywords = resp["choices"][0]["message"]["content"].strip()
        print(f"🔹 Mots-clés image : {keywords}")
        theme_reformule = keywords
    except Exception as e:
        print(f"❌ Erreur reformulation IA : {e}")
        theme_reformule = theme

    try:
        # Recherche d'image sur Unsplash avec les mots-clés reformulés
        query = quote(theme_reformule)
        url_api = f"https://api.unsplash.com/search/photos?query={query}&per_page=5"
        headers = {"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
        resp = requests.get(url_api, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        
        # Fallback au thème original si pas de résultats
        if not results:
            print("⚠️ Aucun résultat sur Unsplash pour :", theme_reformule)
            query = quote(theme)
            url_api = f"https://api.unsplash.com/search/photos?query={query}&per_page=5"
            resp = requests.get(url_api, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            
            if not results:
                print("⚠️ Aucun résultat même avec le thème original")
                return None, None

        # Sélection aléatoire d'une photo
        photo = random.choice(results)
        image_url = photo.get("urls", {}).get("regular") or photo.get("urls", {}).get("small")
        auteur = photo.get("user", {}).get("name", "Unsplash")
        
        # Informations supplémentaires sur la photo
        photo_description = photo.get("description", theme)
        photo_alt = photo.get("alt_description", f"Image pour {theme}")

        if not image_url:
            print("❌ Pas d'URL image valide dans Unsplash.")
            return None, None

        # Upload DIRECT vers Google Drive (pas de sauvegarde locale)
        safe_theme = "".join(c if c.isalnum() else "_" for c in theme)[:30]
        drive_info = _upload_to_google_drive(image_url, safe_theme)
        
        if drive_info:
            # Ajouter les infos Unsplash aux infos Drive
            drive_info['unsplash_author'] = auteur
            drive_info['unsplash_description'] = photo_description
            drive_info['unsplash_alt'] = photo_alt
            
            print(f"\n✅ Image traitée avec succès")
            print(f"   👤 Auteur Unsplash: {auteur}")
            print(f"   📁 Google Drive: {drive_info.get('name', 'N/A')}")
            print(f"   🔗 Lien public: {drive_info.get('public_link', 'N/A')}")
            print(f"   🖼️ Lien direct: {drive_info.get('direct_image_link', 'N/A')}")
            
            return auteur, drive_info
        else:
            print("❌ Échec de l'upload vers Google Drive")
            return None, None
        
    except Exception as e:
        print(f"❌ Erreur API Unsplash : {e}")
        return None, None

# ---------------------------
# 6. Génération du prompt personnalisé PROFESSIONNEL
# ---------------------------
INFLUENCEUR_EXEMPLES = [
    "Gary Vaynerchuk (énergie + valeur immédiate + appel à l'action fort)",
    "Neil Patel (pédagogie technique + data + preuve sociale)",
    "Marie Forleo (storytelling entrepreneur + transformation personnelle)",
    "HubSpot (marketing inbound + valeur éducative + CTA doux)",
    "TechCrunch (autorité sectorielle + analyse stratégique + tendances)"
]

def generer_prompt_personnalise(service: str, theme: str, style: str, analyse: str, type_publication: str) -> Tuple[str, str]:
    influencer_mix = random.sample(INFLUENCEUR_EXEMPLES, k=2)
    
    if type_publication == "service":
        objectif = """VENDRE AVEC VALEUR : Présenter le service comme solution à un problème client spécifique, 
        générer des leads qualifiés, inviter à une consultation découverte gratuite. 
        Focus : Résultat client + preuve sociale + appel à l'action clair."""
    else:
        objectif = """ÉDUQUER POUR GAGNER LA CONFIANCE : Fournir une valeur éducative immédiate, 
        positionner Ben Tech comme autorité, construire une audience engagée, 
        préparer le terrain pour futures conversions. Focus : Expertise + pédagogie + engagement."""

    # PROMPT TEXTE MARKETING PROFESSIONNEL
    prompt_texte = f"""
# MISSION : CRÉATEUR DE CONTENU SENIOR - BEN TECH AGENCY

## CONTEXTE STRATÉGIQUE :
- Entreprise : Ben Tech - Agence de transformation digitale (RDC)
- Positionnement : L'expert tech qui comprend vos défis business
- Audience Cible : Entrepreneurs, PME, startups africaines
- Canal : LinkedIn/Facebook (professionnels décisionnaires)

## PARAMÈTRES CRÉATIFS :
• Service : {service}
• Thème : {theme}
• Style tonal : {style}
• Type publication : {type_publication}
• Objectif principal : {objectif}
• Inspiration : {influencer_mix[0]}

## DONNÉES D'ANALYSE (pour contextualiser) :
{analyse[:500]}...

## COMMANDES CRÉATIVES :

1. HOOK (Ligne 1 - Accroche irrésistible) :
   - Maximum 8 mots
   - Provoque curiosité/identification
   - Lien avec problématique client

2. CORPS (Valeur concrète + expertise) :
   - 2-3 paragraphes maximum
   - Mix : Insight technique + application business
   - Inclure preuve sociale subtile (sans être arrogant)
   - Langage : Professionnel mais accessible

3. APPEL À L'ACTION (CTA stratégique) :
   - Naturel, pas agressif
   - Offre valeur ajoutée (guide, consultation, audit)
   - Lien avec thème/service

## CONTRAINTES TECHNIQUES :
- Longueur : 120-180 mots (optimisé réseaux sociaux)
- Emojis : 3-5 stratégiquement placés (éviter le spam)
- Hashtags : 3-5 pertinents (mix #BenTech + sectoriels)
- Format : Paragraphes courts, aérés
- Éviter : Listes à puces, texte compact

## TON SPÉCIFIQUE "VOIX BEN TECH" :
« Expertise technique avec cœur entrepreneurial - On parle tech, vous pensez business. »

Retournez uniquement le contenu final, prêt à publier.
"""

    # PROMPT SCRIPT VIDÉO PROFESSIONNEL
    prompt_script = f"""
# MISSION : RÉALISATEUR CONTENU VIDÉO - BEN TECH

## SPÉCIFICATIONS VIDÉO :
- Format : Reels/TikTok (30-45 secondes)
- Style : {style}
- Inspiration : {influencer_mix[1]}
- Objectif : {objectif}

## STRUCTURE VIDÉO (storyboard) :

[0-5s] - HOOK VISUEL :
• Plan : Gros plan visage expressif ou écran démo
• Texte à l'écran : Question choc ou statistique surprenante
• Audio : Musique d'ambiance tech/entrepreneuriale

[5-25s] - VALEUR PRINCIPALE :
• Plan : Alternance speaker + écran démo/visuels
• Contenu : 1 insight concret + 1 application pratique
• Technique : Jump cuts dynamiques, textes animés

[25-40s] - PREUVE + CTA :
• Plan : Speaker face caméra (connexion directe)
• Contenu : Témoignage court ou résultat chiffré
• CTA : Invitation claire avec bénéfice immédiat

[40-45s] - FINAL PROFESSIONNEL :
• Plan : Logo Ben Tech + coordonnées
• Superposition : Nom, poste, département (selon agent)
• Hashtags animés

## INDICATIONS DE RÉALISATION :
• Cut toutes les 3-5 secondes
• Zoom ins/out pour dynamisme
• Sous-titres automatiques activés
• Transitions propres (pas d'effets exagérés)

## TEXTE DU SPEAKER (à enregistrer) :
[Fournir le dialogue complet avec indications de ton]
"""
    return prompt_texte.strip(), prompt_script.strip()

# ---------------------------
# 7. RÉPONSE AUX COMMENTAIRES AVEC AGENT + DÉPARTEMENT
# ---------------------------
def generer_reponse_commentaire(commentaire: str) -> str:
    """Génère une réponse professionnelle avec signature agent + département"""
    
    agent = get_agent_aleatoire()
    
    prompt = f"""
# RÔLE : AGENT DE SERVICE CLIENT BEN TECH - RÉPONSE PROFESSIONNELLE

## INFORMATIONS AGENT :
- Nom complet : {agent['prenom']} {agent['nom']}
- Poste : {agent['poste']}
- Département : {agent['departement']}
- Spécialité : {agent['specialite']}
- Signature : {agent['signature']}

## COMMENTAIRE CLIENT À TRAITER :
"{commentaire}"

## PROTOCOLE DE RÉPONSE BEN TECH :

1. ACCUEIL PERSONNALISÉ (chaleureux mais professionnel) :
   - Remercier spécifiquement pour le commentaire
   - Reconnaître la pertinence/sentiment exprimé
   - Établir connexion humaine

2. VALEUR AJOUTÉE (expertise Ben Tech) :
   - Apporter une mini-valeur (conseil, insight, ressource)
   - Montrer expertise sans être technique excessif
   - Lier à notre philosophie d'entreprise

3. ORIENTATION CONVERSION (naturelle) :
   - Proposition de poursuite conversation (message privé, WhatsApp)
   - Offre pertinente selon commentaire (guide, consultation, démo)
   - Timing doux (pas de pression)

4. SIGNATURE COMPLÈTE :
   - Nom + poste + département
   - Signature personnelle (ci-dessous)
   - Coordonnées de contact pertinentes

## CONTRAINTES :
- Longueur : 40-80 mots
- Emojis : 1-2 maximum (professionnels)
- Ton : Mix expertise + chaleur humaine
- Éviter : Jargon excessif, réponse générique, agressivité commerciale

## TON "VOIX BEN TECH" SERVICE CLIENT :
« Professionnel qui comprend vos défis, humain qui valorise votre temps. »

Retournez uniquement la réponse finale avec signature complète.
"""
    
    try:
        resp = openai_chat_request([{"role": "user", "content": prompt}])
        reponse_ia = resp["choices"][0]["message"]["content"].strip()
        
        # Vérifier si la signature est déjà incluse
        if agent['prenom'] not in reponse_ia or agent['departement'] not in reponse_ia:
            # Ajouter signature standardisée
            signature = f"\n\n{agent['prenom']} {agent['nom']}\n{agent['poste']} | {agent['departement']}\n{agent['signature']}"
            reponse_ia += signature
        
        return reponse_ia
        
    except Exception as e:
        print(f"❌ Erreur génération réponse commentaire: {e}")
        # Fallback avec agent
        return f"""Merci pour votre commentaire ! Nous apprécions vraiment vos retours. 💬

Je serais ravi d'échanger plus en détail sur ce sujet. Notre équipe d'experts peut vous proposer des solutions adaptées spécifiquement à vos besoins.

N'hésitez pas à nous contacter sur WhatsApp pour une consultation personnalisée : +243990530518

{agent['prenom']} {agent['nom']}
{agent['poste']} | {agent['departement']}
{agent['signature']}"""

# ---------------------------
# 8. Chat IA pour analyse et recommandations - PROMPT PRO
# ---------------------------
def chat_ia_analyse(question: str, contexte: str = "") -> str:
    df = lire_historique()
    
    if df.empty:
        contexte_data = """
📊 BEN TECH - PREMIÈRE STRATÉGIE MARKETING

🎯 OBJECTIFS FONDATEURS :
• Établir l'autorité tech en RDC francophone
• Générer 50+ leads qualifiés/mois
• Taux d'engagement > 5% sur LinkedIn
• Positionnement : "La tech qui parle business"

📈 PLAN D'ACTION RECOMMANDÉ :
1. Phase 1 (Mois 1-2) : Contenu pédagogique (70%) - Tutoriels, tendances, insights
2. Phase 2 (Mois 3-4) : Preuve sociale (50%) - Études de cas, témoignages
3. Phase 3 (Mois 5-6) : Conversion accélérée (40%) - Offres ciblées, démos

💡 CONSEILS IMMÉDIATS :
• Focus qualité > quantité (3 posts/semaine max)
• Vidéo comme format prioritaire
• Personnalisation marché local indispensable
"""
    else:
        total_posts = len(df)
        derniers_posts = df.tail(3)[["titre", "theme", "service", "reaction_positive", "reaction_negative"]].to_dict('records')
        
        try:
            meilleur_theme = df.groupby("theme")["reaction_positive"].sum().idxmax() if not df["theme"].empty and "reaction_positive" in df.columns else "Aucun"
        except:
            meilleur_theme = "Aucun"
            
        try:
            meilleur_service = df.groupby("service")["reaction_positive"].sum().idxmax() if not df["service"].empty and "reaction_positive" in df.columns else "Aucun"
        except:
            meilleur_service = "Aucun"
            
        try:
            taux_moyen_conversion = df["taux_conversion_estime"].mean() if "taux_conversion_estime" in df.columns and not df["taux_conversion_estime"].empty else 0
        except:
            taux_moyen_conversion = 0
        
        contexte_data = f"""
📊 DASHBOARD PERFORMANCE BEN TECH :

• Posts totaux : {total_posts}
• Thème le plus performant : {meilleur_theme}
• Service le plus demandé : {meilleur_service}
• Taux conversion moyen : {taux_moyen_conversion:.1f}%
• 3 derniers posts : {derniers_posts}

🎯 TENDANCES IDENTIFIÉES :
{analyser_tendances_avancees(df) if not df.empty else "Aucune donnée pour analyse"}
"""
    
    prompt = f"""
# RÔLE : CONSULTANT STRATÉGIE DIGITALE SENIOR - BEN TECH

## CONTEXTE ENTREPRISE :
- Agence : Ben Tech - Transformation digitale
- Marché : RDC & Afrique francophone
- Clients cibles : PME, entrepreneurs, institutions
- Objectif business : Leadership tech régional

## DONNÉES PERFORMANCE ACTUELLES :
{contexte_data}

## QUESTION DU CLIENT/DIRECTION :
"{question}"

{contexte}

## DIRECTIVES D'ANALYSE :

1. DIAGNOSTIC STRATÉGIQUE (objectif, mesure, action) :
   - Identifier le vrai besoin derrière la question
   - Analyser impact sur objectifs business
   - Évaluer risques/opportunités

2. RECOMMANDATIONS ACTIONNABLES (format SMART) :
   - Spécifique : Action concrète, responsable identifié
   - Mesurable : KPI de succès, délai
   - Atteignable : Ressources nécessaires
   - Pertinent : Alignement objectifs Ben Tech
   - Temporel : Échéancier clair

3. PLAN D'EXÉCUTION (étapes, timing, responsabilités) :
   - Phase 1 : Actions immédiates (0-7 jours)
   - Phase 2 : Moyen terme (8-30 jours)
   - Phase 3 : Long terme (1-3 mois)

4. SUIVI & MESURE (tableau de bord) :
   - Métriques à suivre quotidiennement
   - Points de contrôle hebdomadaires
   - Ajustements possibles

## FORMAT DE RÉPONSE :
- Structure professionnelle avec sections
- Ton : Expert, stratégique, orienté résultats
- Langage : Français professionnel, adapté direction
- Focus : ROI, croissance, différenciation

Retournez l'analyse stratégique complète.
"""
    
    try:
        response = openai_chat_request([{"role": "user", "content": prompt}])
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse chat IA: {e}")
        return f"""❌ Erreur système d'analyse

Veuillez réessayer ou contacter notre équipe technique.

Pour assistance immédiate :
📱 WhatsApp : +243990530518
✉️ Email : benybadibanga13@gmail.com

Beny
CEO & Fondateur | Direction Générale
Ensemble, créons l'avenir digital de votre entreprise. 💼"""

# ---------------------------
# 9. Génération complète du contenu PROFESSIONNEL (version Google Drive uniquement)
# ---------------------------
def generer_contenu() -> Dict[str, Any]:
    """Génère un contenu professionnel complet pour Ben Tech"""
    try:
        df = lire_historique()
        
        # Analyse IA avancée
        try:
            analyse = analyse_ia_avance(df)
        except Exception as e:
            print(f"⚠️ Erreur analyse IA: {e}")
            analyse = """STRATÉGIE PAR DÉFAUT BEN TECH :
1. Contenu : 70% valeur éducative, 30% service
2. Ton : Expertise technique + accessibilité entrepreneuriale
3. Format : Mix vidéo court + posts détaillés
4. Fréquence : 3-4 publications/semaine"""
        
        # Choix des paramètres
        theme = choisir_theme(df)
        service = choisir_service(df)
        style = choisir_style(df)
        type_publication = choisir_type_publication(df)
        
        print(f"🎯 GÉNÉRATION PRO BEN TECH: {service} | Thème: {theme} | Style: {style} | Type: {type_publication}")
        print(f"{'='*60}")
        
        # Recherche d'image (UNIQUEMENT dans Google Drive)
        image_auteur, drive_info = trouver_image_unsplash(theme)
        
        # Récupérer les infos Google Drive
        image_drive_url = drive_info.get('webViewLink') if drive_info else ""
        image_drive_id = drive_info.get('id') if drive_info else ""
        image_drive_filename = drive_info.get('name') if drive_info else ""
        image_public_link = drive_info.get('public_link') if drive_info else ""
        image_direct_link = drive_info.get('direct_image_link') if drive_info else ""
        
        # Génération des prompts pro
        prompt_texte, prompt_script = generer_prompt_personnalise(service, theme, style, analyse, type_publication)
        
        # Texte marketing pro
        texte_marketing = ""
        try:
            resp_text = openai_chat_request([{"role": "user", "content": prompt_texte}])
            texte_marketing = resp_text["choices"][0]["message"]["content"].strip()
            print(f"✅ Texte marketing généré ({len(texte_marketing)} caractères)")
        except Exception as e:
            print(f"❌ Erreur génération texte: {e}")
            texte_marketing = f"""🚀 {service} - {theme}

💡 Expert en {service.lower()} chez Ben Tech, je partage des stratégies éprouvées pour transformer votre présence digitale.

📊 Notre approche unique combine expertise technique et compréhension profonde du marché africain.

🔍 Besoin d'une analyse personnalisée ? Contactez notre équipe pour une consultation gratuite.

📱 WhatsApp : +243990530518

#BenTech #{service.replace(' ', '')} #DigitalAfrica #{theme.replace(' ', '')}"""
        
        # Script vidéo pro
        script_video = ""
        try:
            resp_script = openai_chat_request([{"role": "user", "content": prompt_script}])
            script_video = resp_script["choices"][0]["message"]["content"].strip()
            print(f"✅ Script vidéo généré ({len(script_video)} caractères)")
        except Exception as e:
            print(f"❌ Erreur génération script: {e}")
            script_video = f"""🎬 HOOK : Vous cherchez à optimiser {theme.lower()} ?

💬 "En tant qu'expert Ben Tech en {service.lower()}, je constate que..."

📈 "La solution ? Une approche personnalisée combinant..."

🔧 "Nos clients ont vu leurs résultats augmenter de..."

📱 ACTION : Messagez-nous "CONSULTATION" sur WhatsApp pour un audit gratuit !

#BenTech #ExpertTech #SolutionDigitale"""

        # Score conversion réaliste
        score_conversion = random.randint(40, 90)
        titre = f"{service} : {theme}"
        
        # Création du post pro avec infos Google Drive uniquement
        nouveau_post = {
            "titre": titre,
            "theme": theme,
            "service": service,
            "style": style,
            "texte_marketing": texte_marketing,
            "script_video": script_video,
            "reaction_positive": 0,
            "reaction_negative": 0,
            "taux_conversion_estime": score_conversion,
            "publication_effective": "non",
            "nom_plateforme": "",
            "suggestion": analyse[:500] if analyse else "",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score_performance_final": "",
            
            # Image info - Google Drive uniquement
            "image_path": "",  # Vide car pas de sauvegarde locale
            "image_auteur": image_auteur or "",
            
            # Champs Google Drive
            "image_drive_id": image_drive_id or "",
            "image_drive_filename": image_drive_filename or "",
            "image_drive_url": image_drive_url or "",
            "image_public_link": image_public_link or "",
            "image_direct_link": image_direct_link or "",  # Lien direct pour affichage
            
            "type_publication": type_publication,
            "agent_responsable": get_agent_aleatoire()['prenom']
        }
        
        # Sauvegarde dans l'historique
        mettre_a_jour_historique(nouveau_post)
        
        print(f"\n{'='*60}")
        print(f"🎉 CONTENU PRO GÉNÉRÉ : {titre}")
        print(f"   📊 Conversion estimée : {score_conversion}%")
        print(f"   🎭 Style : {style}")
        print(f"   📸 Stockage : {'✅ Google Drive uniquement' if drive_info else '❌ Aucune image'}")
        
        if drive_info:
            print(f"   👤 Auteur : {image_auteur}")
            print(f"   📁 Fichier : {image_drive_filename}")
            print(f"   🔗 Lien Drive : {image_drive_url}")
            if image_public_link:
                print(f"   🌐 Lien public : {image_public_link}")
            if image_direct_link:
                print(f"   🖼️ Lien direct image : {image_direct_link}")
        
        print(f"{'='*60}")
        
        return nouveau_post
        
    except Exception as e:
        print(f"❌ Erreur critique dans generer_contenu: {e}")
        import traceback
        traceback.print_exc()
        
        agent = get_agent_aleatoire()
        return {
            "titre": "Contenu Ben Tech - Expertise Digitale",
            "theme": "Transformation digitale",
            "service": "Consulting web",
            "style": "professionnel",
            "texte_marketing": f"""🚀 Ben Tech - Votre partenaire en transformation digitale

💼 Spécialisés dans l'accompagnement des entreprises africaines vers l'excellence digitale.

📈 Nos experts analysent vos besoins et proposent des solutions sur mesure pour booster votre croissance.

🔗 Contactez-nous pour une consultation stratégique gratuite.

📱 WhatsApp : +243990530518
✉️ Email : benybadibanga13@gmail.com

{agent['prenom']} {agent['nom']}
{agent['poste']} | Ben Tech
{agent['signature']}""",
            "script_video": "🎬 Ben Tech - L'excellence tech au service de votre business",
            "reaction_positive": 0,
            "reaction_negative": 0,
            "taux_conversion_estime": 65,
            "publication_effective": "non",
            "nom_plateforme": "",
            "suggestion": "Génération système - Contenu de secours",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score_performance_final": "",
            "image_path": "",
            "image_auteur": "",
            "image_drive_id": "",
            "image_drive_filename": "",
            "image_drive_url": "",
            "image_public_link": "",
            "image_direct_link": "",
            "type_publication": "contenu",
            "agent_responsable": agent['prenom']
        }

# ---------------------------
# 10. Fonctions d'export pour le dashboard
# ---------------------------
def get_statistiques_globales() -> Dict[str, Any]:
    df = lire_historique()
    
    if df.empty:
        return {
            "total_posts": 0,
            "moyenne_reactions_positives": 0,
            "moyenne_reactions_negatives": 0,
            "taux_conversion_moyen": 0,
            "meilleur_theme": "Aucun",
            "meilleur_service": "Aucun",
            "recommandations": generer_recommandations_proactives(),
            "dernier_post": None,
            "data_source": "Excel local" if not GOOGLE_SHEETS_AVAILABLE else "Google Sheets",
            "gsheets_available": GOOGLE_SHEETS_AVAILABLE,
            "agents_disponibles": len(AGENTS_BEN_TECH),
            "google_drive_available": GOOGLE_DRIVE_AVAILABLE
        }
    
    try:
        total_posts = len(df)
        
        moyenne_pos = 0
        if "reaction_positive" in df.columns:
            moyenne_pos = float(df["reaction_positive"].mean()) if not df["reaction_positive"].empty else 0
        
        moyenne_neg = 0
        if "reaction_negative" in df.columns:
            moyenne_neg = float(df["reaction_negative"].mean()) if not df["reaction_negative"].empty else 0
        
        taux_moyen = 0
        if "taux_conversion_estime" in df.columns:
            taux_moyen = float(df["taux_conversion_estime"].mean()) if not df["taux_conversion_estime"].empty else 0
        
        meilleur_theme = "Aucun"
        if "theme" in df.columns and "reaction_positive" in df.columns:
            try:
                theme_data = df[["theme", "reaction_positive"]].dropna()
                if not theme_data.empty:
                    meilleur_theme = theme_data.groupby("theme")["reaction_positive"].sum().idxmax()
            except:
                meilleur_theme = "Aucun"
        
        meilleur_service = "Aucun"
        if "service" in df.columns and "reaction_positive" in df.columns:
            try:
                service_data = df[["service", "reaction_positive"]].dropna()
                if not service_data.empty:
                    meilleur_service = service_data.groupby("service")["reaction_positive"].sum().idxmax()
            except:
                meilleur_service = "Aucun"
        
        dernier_post = None
        if "date" in df.columns and "titre" in df.columns:
            try:
                df["date_dt"] = pd.to_datetime(df["date"], errors='coerce')
                dernier = df.sort_values("date_dt", ascending=False).iloc[0]
                dernier_post = {
                    "titre": dernier.get("titre", "Sans titre"),
                    "date": dernier.get("date", ""),
                    "theme": dernier.get("theme", ""),
                    "service": dernier.get("service", ""),
                    "agent": dernier.get("agent_responsable", "Non attribué"),
                    "image_storage": "Google Drive" if dernier.get("image_drive_id") else "Local" if dernier.get("image_path") else "Aucune"
                }
            except:
                dernier_post = None
        
        stats = {
            "total_posts": total_posts,
            "moyenne_reactions_positives": round(moyenne_pos, 1),
            "moyenne_reactions_negatives": round(moyenne_neg, 1),
            "taux_conversion_moyen": round(taux_moyen, 1),
            "meilleur_theme": meilleur_theme,
            "meilleur_service": meilleur_service,
            "recommandations": generer_recommandations_proactives(),
            "dernier_post": dernier_post,
            "data_source": "Excel local" if not GOOGLE_SHEETS_AVAILABLE else "Google Sheets",
            "gsheets_available": GOOGLE_SHEETS_AVAILABLE,
            "google_drive_available": GOOGLE_DRIVE_AVAILABLE,
            "agents_disponibles": len(AGENTS_BEN_TECH),
            "entreprise": "Ben Tech - Agence de Transformation Digitale",
            "positionnement": "Expertise tech avec impact business"
        }
        
        return stats
        
    except Exception as e:
        print(f"❌ Erreur calcul statistiques: {e}")
        return {
            "total_posts": len(df),
            "moyenne_reactions_positives": 0,
            "moyenne_reactions_negatives": 0,
            "taux_conversion_moyen": 0,
            "meilleur_theme": "Erreur",
            "meilleur_service": "Erreur",
            "recommandations": [],
            "dernier_post": None,
            "data_source": "Erreur",
            "gsheets_available": GOOGLE_SHEETS_AVAILABLE,
            "google_drive_available": GOOGLE_DRIVE_AVAILABLE,
            "agents_disponibles": len(AGENTS_BEN_TECH)
        }

# ---------------------------
# 11. Fonctions auxiliaires (à compléter selon vos besoins)
# ---------------------------
def analyser_tendances_avancees(df: pd.DataFrame) -> str:
    """Analyse les tendances avancées des posts"""
    if df.empty:
        return "Aucune donnée pour analyse"
    
    try:
        # Analyse simple des tendances
        recent_posts = df.tail(10)
        if recent_posts.empty:
            return "Données récentes insuffisantes"
        
        tendances = []
        
        # Analyse par type de publication
        if "type_publication" in recent_posts.columns:
            types = recent_posts["type_publication"].value_counts()
            for type_pub, count in types.items():
                tendances.append(f"• {type_pub}: {count} posts")
        
        # Analyse par style
        if "style" in recent_posts.columns:
            styles = recent_posts["style"].value_counts().head(3)
            tendances.append(f"Styles dominants: {', '.join(styles.index)}")
        
        return "\n".join(tendances) if tendances else "Tendances non identifiables"
        
    except Exception as e:
        return f"Erreur analyse tendances: {e}"

def generer_recommandations_proactives() -> List[str]:
    """Génère des recommandations proactives basées sur l'analyse"""
    df = lire_historique()
    
    if df.empty:
        return [
            "🏁 Commencez par générer votre premier contenu",
            "🎯 Ciblez 'Transformation digitale des PME' comme premier thème",
            "📊 Suivez les réactions pour ajuster votre stratégie"
        ]
    
    recommandations = []
    
    try:
        # Recommandation basée sur le dernier post
        if not df.empty:
            dernier = df.iloc[-1]
            if "type_publication" in dernier:
                if dernier["type_publication"] == "contenu":
                    recommandations.append("🔄 Générer un post de service pour équilibrer")
                else:
                    recommandations.append("📚 Créer du contenu éducatif pour établir l'autorité")
        
        # Recommandation basée sur les performances
        if "reaction_positive" in df.columns and not df["reaction_positive"].empty:
            moyenne = df["reaction_positive"].mean()
            if moyenne < 10:
                recommandations.append("🔥 Augmenter l'engagement avec des questions directes")
        
        # Recommandations générales
        recommandations.append("⏰ Maintenir une fréquence de 3-4 posts par semaine")
        recommandations.append("🎥 Prioriser le format vidéo (30-45 secondes)")
        recommandations.append("🤝 Inclure des témoignages clients pour crédibilité")
        
    except Exception as e:
        recommandations = [
            "📝 Analyser régulièrement vos performances",
            "🎯 Adapter le contenu aux besoins de votre audience",
            "🚀 Expérimenter avec différents formats et styles"
        ]
    
    return recommandations[:5]  # Retourne max 5 recommandations