# modules/ia.py - Générateur de contenu Ben Tech avec Google Sheets
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
# CONFIGURATION DES APIS
# -----------------------------------------------------------------
try:
    from config import OPENAI_API_KEY, OPENAI_MODEL, UNSPLASH_API_KEY
except ImportError:
    # Fallback pour les variables d'environnement directes
    import os
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY", "")

EXCEL_FILE = "historique_posts.xlsx"
IMAGE_FOLDER = "images_posts"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

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
        # Spécifier l'engine openpyxl pour mieux gérer les fichiers Excel
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        
        # Vérifier que toutes les colonnes nécessaires existent
        colonnes_requises = [
            "titre", "theme", "service", "style",
            "texte_marketing", "script_video",
            "reaction_positive", "reaction_negative",
            "taux_conversion_estime", "publication_effective",
            "nom_plateforme", "suggestion", "date",
            "score_performance_final", "image_path", "image_auteur", "type_publication"
        ]
        
        for col in colonnes_requises:
            if col not in df.columns:
                df[col] = ""
        
        print(f"📊 {len(df)} posts chargés depuis Excel local")
        return df
        
    except FileNotFoundError:
        # Créer un DataFrame avec toutes les colonnes nécessaires
        df = pd.DataFrame(columns=[
            "titre", "theme", "service", "style",
            "texte_marketing", "script_video",
            "reaction_positive", "reaction_negative",
            "taux_conversion_estime", "publication_effective",
            "nom_plateforme", "suggestion", "date",
            "score_performance_final", "image_path", "image_auteur", "type_publication"
        ])
        # Sauvegarder avec openpyxl engine
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        print("📝 Fichier Excel créé avec colonnes")
        return df
    except Exception as e:
        print(f"❌ Erreur lecture Excel: {e}")
        # Retourner DataFrame vide
        return pd.DataFrame(columns=[
            "titre", "theme", "service", "style",
            "texte_marketing", "script_video",
            "reaction_positive", "reaction_negative",
            "taux_conversion_estime", "publication_effective",
            "nom_plateforme", "suggestion", "date",
            "score_performance_final", "image_path", "image_auteur", "type_publication"
        ])

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
    
    # TOUJOURS sauvegarder localement (même si Google Sheets marche)
    try:
        # Lire l'historique existant
        try:
            df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        except FileNotFoundError:
            df = pd.DataFrame(columns=[
                "titre", "theme", "service", "style",
                "texte_marketing", "script_video",
                "reaction_positive", "reaction_negative",
                "taux_conversion_estime", "publication_effective",
                "nom_plateforme", "suggestion", "date",
                "score_performance_final", "image_path", "image_auteur", "type_publication"
            ])
        
        # Convertir le dictionnaire en DataFrame
        nouveau_df = pd.DataFrame([nouveau_post])
        
        # S'assurer que toutes les colonnes existent
        for col in df.columns:
            if col not in nouveau_df.columns:
                nouveau_df[col] = ""
        
        # Ajouter le nouveau post
        df = pd.concat([df, nouveau_df], ignore_index=True)
        
        # Sauvegarder avec openpyxl pour mieux gérer les données
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        if not GOOGLE_SHEETS_AVAILABLE or not gsheets_success:
            print(f"✅ Post sauvegardé localement uniquement: {nouveau_post.get('titre', 'Sans titre')}")
        else:
            print(f"✅ Post sauvegardé localement (backup): {nouveau_post.get('titre', 'Sans titre')}")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde locale: {e}")
        # Dernier recours : sauvegarde simple
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
# 3. Analyse IA avancée
# ---------------------------
def analyse_ia_avance(df: pd.DataFrame) -> str:
    if df.empty:
        return ("Aucun historique disponible. Recommandation initiale : alterner contenu pédagogique (60%) "
                "et posts service (40%), privilégier courts scripts vidéos (30-45s), ton 'influenceur tech' mix pédagogique + direct.")

    # Réduire l'historique pour transmettre proprement
    sample = df.sort_values(by="date", ascending=False).head(60)  # limiter la quantité
    rows = sample[["theme", "service", "style", "reaction_positive", "reaction_negative", "taux_conversion_estime", "suggestion", "type_publication"]]
    records = rows.fillna("").to_dict(orient="records")

    prompt = f"""
Tu es un expert en marketing digital et contenu social media spécialisé tech. Analyse la liste d'items suivante (format JSON) qui représente l'historique des posts.
- Identifie 3 tendances qui performent (thèmes/services/styles/type_publication/reaction_positive).
- Identifie 3 points faibles récurrents(reaction_negative).
- Propose 5 recommandations actionnables (titres courts) pour améliorer l'engagement et la conversion.
- Propose un profil de ton / style mixé inspiré par influenceurs tech contemporains (énergie + pédagogie + preuve sociale) en 2 phrases.
Retourne la réponse en texte clair, structuré (sections séparées), pas de JSON.
Historique (extraits): {records}
"""
    response = openai_chat_request([{"role": "user", "content": prompt}])
    return response["choices"][0]["message"]["content"].strip()

# ---------------------------
# 4. Choix automatique (thème/service/style/type)
# ---------------------------
def choisir_theme(df: pd.DataFrame) -> str:
    if df.empty:
        seeds = [
            "Comment la technologie peut transformer ton business",
            "Automatiser pour réduire les coûts",
            "Sécurité basique pour PME",
            "Applications mobiles qui convertissent clients"
        ]
        return random.choice(seeds)
    
    # Filtrer les valeurs NaN
    themes_valides = df["theme"].dropna()
    if themes_valides.empty:
        return random.choice(seeds)
    
    scores = themes_valides.groupby(themes_valides).size()
    if scores.sum() > 0:
        return scores.idxmax()
    return random.choice(themes_valides.tolist() or ["Comment la technologie peut transformer ton business"])

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
    # styles inspirés des créateurs tech : pédagogique, énergique, direct, storytelling, technique
    styles = ["pédagogique", "énergique", "direct", "storytelling", "technique", "influenceur"]
    if df.empty:
        return "influenceur"
    
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
    # alterne entre 'service' (promo) et 'contenu' (valeur / actu)
    if df.empty:
        return "contenu"
    
    if "type_publication" not in df.columns:
        return "contenu" if random.random() < 0.7 else "service"
    
    recent = df.tail(12)
    contenu_score = recent[recent["type_publication"] == "contenu"]["reaction_positive"].sum() if "type_publication" in recent.columns else 0
    service_score = recent[recent["type_publication"] == "service"]["reaction_positive"].sum() if "type_publication" in recent.columns else 0
    
    # si contenu marche mieux -> continuer contenu, sinon mixer
    if contenu_score > service_score:
        return "contenu" if random.random() < 0.75 else "service"
    return "service" if random.random() < 0.6 else "contenu"

# ---------------------------
# 5. Génération image via Unsplash (CORRIGÉ)
# ---------------------------
def trouver_image_unsplash(theme: str, commentaires: Optional[list[str]] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Récupère et télécharge une image depuis Unsplash pour un thème donné.
    """
    if not UNSPLASH_API_KEY:
        print("❌ Aucun UNSPLASH_API_KEY défini.")
        return None, None

    def _save_image_from_url(url: str, theme_safe: str) -> Optional[str]:
        try:
            img_resp = requests.get(url, timeout=20)
            img_resp.raise_for_status()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Extraire l'extension du fichier
            url_clean = url.split('?')[0]
            ext = os.path.splitext(url_clean)[1]
            if not ext or len(ext) > 5:  # Si pas d'extension ou trop longue
                ext = ".jpg"
            
            # Nettoyer le nom du thème pour le nom de fichier
            safe_theme = "".join(c if c.isalnum() else "_" for c in theme)[:30]
            filename = f"{safe_theme}_{timestamp}{ext}"
            filepath = os.path.join(IMAGE_FOLDER, filename)
            
            with open(filepath, "wb") as f:
                f.write(img_resp.content)
            return filepath
        except Exception as e:
            print(f"❌ Erreur téléchargement image : {e}")
            return None

    # --------- 1. Reformulation du thème via IA ---------
    try:
        prompt_reformulation = f"""
Tu es un assistant spécialisé en tech et marketing digital.
Reformule ce thème pour qu'il soit précis et visuellement clair pour générer une image sur Unsplash.
Thème original : "{theme}"
Retourne uniquement une phrase courte, liée au domaine tech.
"""
        resp = openai_chat_request([{"role": "user", "content": prompt_reformulation}])
        theme_reformule = resp["choices"][0]["message"]["content"].strip()
        print("🔹 Thème reformulé :", theme_reformule)
    except Exception as e:
        print(f"❌ Erreur reformulation IA : {e}")
        theme_reformule = theme  # fallback

    # --------- 2. Recherche image Unsplash ---------
    try:
        query = quote(theme_reformule)
        url_api = f"https://api.unsplash.com/search/photos?query={query}&per_page=5"
        headers = {"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
        resp = requests.get(url_api, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        
        if not results:
            print("⚠️ Aucun résultat sur Unsplash pour :", theme_reformule)
            # Essayer avec le thème original
            query = quote(theme)
            url_api = f"https://api.unsplash.com/search/photos?query={query}&per_page=5"
            resp = requests.get(url_api, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            
            if not results:
                print("⚠️ Aucun résultat même avec le thème original")
                return None, None

        photo = random.choice(results)
        image_url = photo.get("urls", {}).get("regular") or photo.get("urls", {}).get("small")
        auteur = photo.get("user", {}).get("name", "Unsplash AI")

        if not image_url:
            print("❌ Pas d'URL image valide dans Unsplash.")
            return None, None

        # Nettoyer le nom du thème pour le nom de fichier
        safe_theme = "".join(c if c.isalnum() else "_" for c in theme)[:30]
        filepath = _save_image_from_url(image_url, safe_theme)
        
    except Exception as e:
        print(f"❌ Erreur API Unsplash : {e}")
        return None, None

    if filepath:
        print(f"✅ Image téléchargée : {os.path.basename(filepath)}")
        return filepath, auteur

    print("❌ Impossible de récupérer une image pertinente pour :", theme)
    return None, None

# ---------------------------
# 6. Génération du prompt personnalisé (mix styles)
# ---------------------------
INFLUENCEUR_EXEMPLES = [
    "énergie directe, appels à l'action forts, preuve sociale courte",
    "pédagogie claire, analogies, démonstrations simples",
    "raconter une micro-histoire (hook) + révéler une leçon/action",
    "format court, visuel, phrases punchy, perso",
    "mise en avant de résultats chiffrés (social proof)"
]

def generer_prompt_personnalise(service: str, theme: str, style: str, analyse: str, type_publication: str) -> Tuple[str, str]:
    influencer_mix = random.sample(INFLUENCEUR_EXEMPLES, k=3)
    
    if type_publication == "service":
        objectif = "Vendre le service, obtenir des prospects, invitation à conversation (WhatsApp/DM)."
    else:
        objectif = "Donner de la valeur, montrer expertise, générer confiance et sauvegarder prospects."

    prompt_texte = f"""
Tu es le créateur de contenu officiel de Ben Tech. Crée un post social optimisé pour LinkedIn/Instagram/TikTok/Facebook (texte principal + description)

Caractéristiques :
- Style mixé (inspiré par influenceurs tech) : {', '.join(influencer_mix)}
- Ton demandé : {style}
- Objectif principal : {objectif}
- Service : {service}
- Thème : {theme}
- Analyse historique et recommandations : {analyse}

Contraintes :
- Texte fluide, impactant, pas de listes ni tirets.
- 2-5 emojis modernes intégrés naturellement.
- Inclure un hook en première phrase (2-8 mots), valeur claire, preuve sociale (si possible), et CTA final.
- Si c'est un post 'service', insérer une phrase courte qui décrit l'offre et invite à WhatsApp.
- Longueur : 100-250 mots.

Retourne uniquement le texte final.
"""

    prompt_script = f"""
Écris un script vidéo TikTok/Reels (30-45s) pour Ben Tech.

Ton : {style}. 
Inspiré par : {', '.join(influencer_mix)}.
Objectif : {objectif}
Service : {service}
Thème : {theme}

Structure attendue :
1. Hook (1 ligne - accroche)
2. 2-3 lignes de valeur/explication
3. Preuve ou exemple court
4. CTA fort (appel à l'action)

Ajoute des indications de cut/plan entre crochets si utile. 
Inclure 2-3 emojis appropriés.
Retourne uniquement le script.
"""
    return prompt_texte.strip(), prompt_script.strip()

# ---------------------------
# 7. Réponse aux commentaires (améliorée)
# ---------------------------
def generer_reponse_commentaire(commentaire: str) -> str:
    agents = ["Sarah", "Daniel", "David", "Paul", "Ben", "Dercy", "Anderson"]
    name_agent = random.choice(agents)
    prompt = f"""
Tu es {name_agent}, conseiller commercial Ben Tech.
Rédige une réponse courte, chaleureuse et orientée conversion au commentaire suivant.

Essaie de créer une relation et de pousser le client à être intéressé par nos services.
Pose des questions pertinentes.

Inclure invitation à discuter en message privé ou sur WhatsApp.
Utilise 1-2 emojis appropriés.
Ajoute ton nom à la fin avec ton poste et département.

Commentaire: "{commentaire}"

Retourne uniquement la réponse.
"""
    try:
        resp = openai_chat_request([{"role": "user", "content": prompt}])
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Erreur génération réponse commentaire: {e}")
        return f"Merci pour ton message ! 💬 Dispo pour en parler sur WhatsApp +243990530518 😊"

# ---------------------------
# 8. Chat IA pour analyse et recommandations (CORRIGÉ)
# ---------------------------
def chat_ia_analyse(question: str, contexte: str = "") -> str:
    """
    Analyse le fichier Excel et répond aux questions avec des recommandations.
    """
    df = lire_historique()
    
    if df.empty:
        contexte_data = "📊 Aucune donnée historique disponible."
    else:
        total_posts = len(df)
        derniers_posts = df.tail(3)[["titre", "theme", "service", "reaction_positive", "reaction_negative"]].to_dict('records')
        
        # Calculer statistiques avec gestion des erreurs
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
📊 Données historiques :
- Total posts : {total_posts}
- Meilleur thème : {meilleur_theme}
- Meilleur service : {meilleur_service}
- Taux de conversion moyen : {taux_moyen_conversion:.1f}%
- 3 derniers posts : {derniers_posts}
        """
    
    # Analyser les tendances
    tendances = analyser_tendances_avancees(df) if not df.empty else "📈 Aucune donnée pour analyse des tendances."
    
    prompt = f"""
Tu es un expert en marketing digital et analyse de données pour Ben Tech.
Tu as accès aux données historiques des posts marketing.

CONTEXTE DES DONNÉES :
{contexte_data}

ANALYSE DES TENDANCES :
{tendances}

QUESTION DE L'UTILISATEUR :
"{question}"

{contexte}

INSTRUCTIONS :
1. Analyse la question en lien avec les données disponibles
2. Donne des recommandations concrètes et actionnables
3. Propose des approches spécifiques basées sur les performances historiques
4. Si la question concerne un problème, propose des solutions
5. Sois précis, utilise des chiffres quand c'est possible
6. Structure ta réponse clairement avec des sections
7. Réponds en français, de manière professionnelle mais accessible

Réponds uniquement avec l'analyse et les recommandations.
"""
    
    try:
        response = openai_chat_request([{"role": "user", "content": prompt}])
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse chat IA: {e}")
        return f"❌ Erreur lors de l'analyse : {str(e)}"

def analyser_tendances_avancees(df: pd.DataFrame) -> str:
    """
    Analyse avancée des tendances à partir des données - CORRIGÉ pour éviter les avertissements.
    """
    if df.empty or len(df) < 2:
        return "📊 Données insuffisantes pour une analyse avancée (minimum 2 posts requis)."
    
    analyses = []
    
    try:
        # 1. Analyse par type de publication
        if "type_publication" in df.columns and len(df["type_publication"].dropna()) > 0:
            type_stats = df.groupby("type_publication").agg({
                "reaction_positive": "mean",
                "reaction_negative": "mean",
                "taux_conversion_estime": "mean"
            }).round(2)
            analyses.append(f"📊 Performance par type :\n{type_stats.to_string()}")
    except Exception as e:
        analyses.append("📊 Analyse par type : Données insuffisantes")
    
    try:
        # 2. Analyse par service
        if "service" in df.columns and len(df["service"].dropna()) > 0:
            service_stats = df.groupby("service").agg({
                "reaction_positive": ["count", "mean"],
                "reaction_negative": "mean"
            }).round(2)
            analyses.append(f"🎯 Performance par service :\n{service_stats.to_string()}")
    except Exception as e:
        analyses.append("🎯 Analyse par service : Données insuffisantes")
    
    try:
        # 3. Analyse temporelle (si assez de données)
        if len(df) > 5 and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
            df = df.dropna(subset=["date"])
            if len(df) > 2:
                df["mois"] = df["date"].dt.to_period("M")
                mensuel = df.groupby("mois").agg({
                    "reaction_positive": "sum",
                    "reaction_negative": "sum"
                }).tail(3)
                analyses.append(f"📈 Tendances mensuelles (3 derniers mois) :\n{mensuel.to_string()}")
    except Exception as e:
        pass  # Ignorer si l'analyse temporelle échoue
    
    try:
        # 4. Corrélations (uniquement si assez de données variées)
        if "taux_conversion_estime" in df.columns and len(df["taux_conversion_estime"].dropna()) > 2:
            correlations = []
            for col in ["reaction_positive", "reaction_negative"]:
                if col in df.columns and len(df[col].dropna()) > 2:
                    # Filtrer les NaN
                    valid_data = df[[col, "taux_conversion_estime"]].dropna()
                    if len(valid_data) > 2:
                        try:
                            corr = valid_data[col].corr(valid_data["taux_conversion_estime"])
                            if pd.notna(corr):  # Vérifier que la corrélation n'est pas NaN
                                correlations.append(f"{col} ↔ conversion: {corr:.2f}")
                        except:
                            pass
            if correlations:
                analyses.append(f"🔗 Corrélations : {', '.join(correlations)}")
    except Exception as e:
        pass  # Ignorer les erreurs de corrélation
    
    if not analyses:
        return "📊 Pas assez de données pour générer des analyses avancées."
    
    return "\n\n".join(analyses)

def generer_recommandations_proactives() -> List[Dict[str, str]]:
    """
    Génère des recommandations proactives basées sur l'analyse des données - CORRIGÉ.
    """
    df = lire_historique()
    
    if df.empty or len(df) < 2:
        return [{
            "titre": "🚀 Premier pas",
            "description": "Commencez par générer du contenu pour construire votre historique",
            "action": "Utilisez la fonction 'Générer du contenu'",
            "urgence": "Élevée"
        }]
    
    recommendations = []
    
    try:
        # 1. Check des services sous-performants
        if "service" in df.columns and "reaction_positive" in df.columns:
            service_data = df[["service", "reaction_positive"]].dropna()
            if len(service_data) > 2:
                service_perf = service_data.groupby("service")["reaction_positive"].mean()
                if len(service_perf) > 1:
                    services_faibles = service_perf[service_perf < service_perf.quantile(0.3)]
                    for service in services_faibles.index:
                        recommendations.append({
                            "titre": f"📉 Service sous-performant : {service[:30]}...",
                            "description": f"Moyenne: {service_perf[service]:.1f} réactions (moyenne: {service_perf.mean():.1f})",
                            "action": "Revoir la stratégie de contenu",
                            "urgence": "Moyenne"
                        })
    except Exception:
        pass
    
    try:
        # 2. Check du ratio contenu/service
        if "type_publication" in df.columns:
            type_counts = df["type_publication"].value_counts()
            if len(type_counts) > 1:
                ratio = type_counts.get("contenu", 0) / max(type_counts.get("service", 1), 1)
                if ratio < 1.5:
                    recommendations.append({
                        "titre": "⚖️ Équilibre contenu/service",
                        "description": f"Ratio contenu/service : {ratio:.1f} (idéal: 2-3)",
                        "action": "Augmenter le contenu éducatif",
                        "urgence": "Basse"
                    })
    except Exception:
        pass
    
    try:
        # 3. Check de la fréquence de publication
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
            df = df.dropna(subset=["date"])
            if len(df) > 0:
                dernier_post = df["date"].max()
                jours_sans_post = (datetime.now() - dernier_post).days
                if jours_sans_post > 3:
                    recommendations.append({
                        "titre": f"⏰ {jours_sans_post} jours sans publication",
                        "description": f"Dernier post le {dernier_post.strftime('%d/%m/%Y')}",
                        "action": "Planifier une nouvelle publication",
                        "urgence": "Élevée"
                    })
    except Exception:
        pass
    
    try:
        # 4. Recommandation basée sur les meilleures performances
        if "theme" in df.columns and "reaction_positive" in df.columns:
            theme_data = df[["theme", "reaction_positive"]].dropna()
            if len(theme_data) > 2:
                meilleurs_themes = theme_data.groupby("theme")["reaction_positive"].sum().nlargest(2)
                for theme, score in meilleurs_themes.items():
                    recommendations.append({
                        "titre": f"⭐ Thème performant : {theme[:30]}...",
                        "description": f"{score:.0f} réactions positives totales",
                        "action": "Créer plus de contenu sur ce thème",
                        "urgence": "Moyenne"
                    })
    except Exception:
        pass
    
    # Limiter à 5 recommandations et ajouter une par défaut si vide
    if not recommendations:
        recommendations.append({
            "titre": "📈 Génération de contenu",
            "description": "Continuez à générer du contenu pour enrichir les données d'analyse",
            "action": "Utiliser 'Générer du contenu' régulièrement",
            "urgence": "Moyenne"
        })
    
    return recommendations[:5]

# ---------------------------
# 9. Génération complète du contenu (CORRIGÉ)
# ---------------------------
def generer_contenu() -> Dict[str, Any]:
    """Génère un contenu complet avec gestion robuste des erreurs"""
    try:
        df = lire_historique()
        
        # Analyse IA avancée
        try:
            analyse = analyse_ia_avance(df)
        except Exception as e:
            print(f"⚠️ Erreur analyse IA: {e}")
            analyse = "Analyse indisponible. Stratégie par défaut : posts mixtes, ton pédagogique+énergique."
        
        # Choix des paramètres
        theme = choisir_theme(df)
        service = choisir_service(df)
        style = choisir_style(df)
        type_publication = choisir_type_publication(df)
        
        print(f"🎯 Génération pour: {service} | Thème: {theme} | Style: {style} | Type: {type_publication}")
        
        # Recherche d'image
        image_path, image_auteur = trouver_image_unsplash(theme)
        
        # Génération des prompts
        prompt_texte, prompt_script = generer_prompt_personnalise(service, theme, style, analyse, type_publication)
        
        # Appels OpenAI pour le texte marketing
        texte_marketing = ""
        try:
            resp_text = openai_chat_request([{"role": "user", "content": prompt_texte}])
            texte_marketing = resp_text["choices"][0]["message"]["content"].strip()
            print(f"✅ Texte marketing généré ({len(texte_marketing)} caractères)")
        except Exception as e:
            print(f"❌ Erreur génération texte: {e}")
            texte_marketing = f"""🚀 {service} - {theme}

💡 En tant qu'expert en {service.lower()}, je partage avec vous des insights précieux pour optimiser votre présence digitale.

🔍 Analyse personnalisée disponible sur WhatsApp : https://wa.me/qr/IYM7JZ4P3VFLB1

#BenTech #{service.replace(' ', '')} #DigitalTransformation"""
        
        # Appels OpenAI pour le script vidéo
        script_video = ""
        try:
            resp_script = openai_chat_request([{"role": "user", "content": prompt_script}])
            script_video = resp_script["choices"][0]["message"]["content"].strip()
            print(f"✅ Script vidéo généré ({len(script_video)} caractères)")
        except Exception as e:
            print(f"❌ Erreur génération script: {e}")
            script_video = f"""🎬 HOOK: Découvrez comment {service.lower()} peut transformer votre business!

💬 "Saviez-vous que... [insight clé sur {theme}]"

📱 CTA: Contactez-nous sur WhatsApp pour une consultation gratuite!"""

        # Estimation
        score_conversion = random.randint(30, 95)
        titre = f"{service} — {theme}"
        
        # Création du post
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
            "suggestion": analyse[:500] if analyse else "",  # Limiter la longueur
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score_performance_final": "",
            "image_path": image_path or "",
            "image_auteur": image_auteur or "",
            "type_publication": type_publication
        }
        
        # Sauvegarde
        mettre_a_jour_historique(nouveau_post)
        
        print(f"🎉 Contenu généré avec succès: {titre}")
        return nouveau_post
        
    except Exception as e:
        print(f"❌ Erreur critique dans generer_contenu: {e}")
        # Retourner un post minimal en cas d'erreur
        return {
            "titre": "Erreur de génération",
            "theme": "Technologie",
            "service": "Maintenance systèmes & sécurité",
            "style": "pédagogique",
            "texte_marketing": "Une erreur est survenue lors de la génération. Veuillez réessayer.",
            "script_video": "",
            "reaction_positive": 0,
            "reaction_negative": 0,
            "taux_conversion_estime": 50,
            "publication_effective": "non",
            "nom_plateforme": "",
            "suggestion": "Erreur système",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score_performance_final": "",
            "image_path": "",
            "image_auteur": "",
            "type_publication": "contenu"
        }

# ---------------------------
# 10. Fonctions d'export pour le dashboard (CORRIGÉ)
# ---------------------------
def get_statistiques_globales() -> Dict[str, Any]:
    """
    Retourne les statistiques globales pour le dashboard - CORRIGÉ.
    """
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
            "data_source": "Excel local" if not GOOGLE_SHEETS_AVAILABLE else "Google Sheets"
        }
    
    try:
        # Calculs avec gestion des erreurs
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
        
        # Meilleur thème
        meilleur_theme = "Aucun"
        if "theme" in df.columns and "reaction_positive" in df.columns:
            try:
                theme_data = df[["theme", "reaction_positive"]].dropna()
                if not theme_data.empty:
                    meilleur_theme = theme_data.groupby("theme")["reaction_positive"].sum().idxmax()
            except:
                meilleur_theme = "Aucun"
        
        # Meilleur service
        meilleur_service = "Aucun"
        if "service" in df.columns and "reaction_positive" in df.columns:
            try:
                service_data = df[["service", "reaction_positive"]].dropna()
                if not service_data.empty:
                    meilleur_service = service_data.groupby("service")["reaction_positive"].sum().idxmax()
            except:
                meilleur_service = "Aucun"
        
        # Dernier post
        dernier_post = None
        if "date" in df.columns and "titre" in df.columns:
            try:
                df["date_dt"] = pd.to_datetime(df["date"], errors='coerce')
                dernier = df.sort_values("date_dt", ascending=False).iloc[0]
                dernier_post = {
                    "titre": dernier.get("titre", "Sans titre"),
                    "date": dernier.get("date", ""),
                    "theme": dernier.get("theme", ""),
                    "service": dernier.get("service", "")
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
            "gsheets_available": GOOGLE_SHEETS_AVAILABLE
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
            "gsheets_available": GOOGLE_SHEETS_AVAILABLE
        }