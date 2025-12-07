# modules/publier.py - VERSION COMPLÈTE MIS À JOUR
import time
import threading
import pandas as pd
from datetime import datetime, timedelta
import os
from modules.plateformes.facebook import (
    publier_sur_facebook,
    lire_reactions,
    traiter_commentaires,
    comment_service,
    demarrer_service_commentaires,
    arreter_service_commentaires,
    get_statut_service_commentaires,
    executer_traitement_manuel
)
from modules.google_sheets_db import (
    mettre_a_jour_post_gsheets,
    lire_historique_gsheets,
    gsheets_db
)

INTERVALLE_ANALYSE = 60  # secondes
MINUTES_ENTRE_PUBLICATIONS = 30  # Attente minimum entre publications
HEURES_OUVERTURE = (8, 22)  # Publier seulement entre 8h et 22h

# -----------------------------
# Configuration du logging
# -----------------------------
def setup_logging():
    """Configure le système de logging"""
    log_dirs = ['logs', 'logs/publications', 'logs/errors', 'logs/comments']
    for dir_path in log_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

def log_message(category: str, message: str, level: str = "INFO"):
    """Enregistre un message dans les logs"""
    setup_logging()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    # Fichier principal
    with open(f'logs/system.log', 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    # Fichier par catégorie
    if category:
        with open(f'logs/{category}.log', 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    # Affichage console
    if level == "ERROR":
        print(f"❌ {message}")
    elif level == "WARNING":
        print(f"⚠️ {message}")
    elif level == "SUCCESS":
        print(f"✅ {message}")
    else:
        print(f"📝 {message}")

# -----------------------------
# Gestion des publications
# -----------------------------
def est_deja_publie(post_data):
    """Vérifie si un post est déjà publié"""
    nom_plateforme = post_data.get("nom_plateforme", "")
    publication_effective = post_data.get("publication_effective", "")
    post_id = post_data.get("post_id", "")
    
    if (nom_plateforme and nom_plateforme != "") or \
       (publication_effective and publication_effective.lower() in ["oui", "yes", "true"]) or \
       (post_id and post_id != ""):
        return True
    return False

def lire_posts_non_publies():
    """Récupère les posts non publiés depuis Google Sheets"""
    try:
        df = lire_historique_gsheets()
        
        if df.empty:
            log_message("publications", "Aucun post dans Google Sheets", "INFO")
            return []
        
        posts_non_publies = []
        
        for index, row in df.iterrows():
            post_data = row.to_dict()
            
            if not est_deja_publie(post_data):
                # Vérifier si le post a déjà été tenté et a échoué
                last_attempt = post_data.get("derniere_tentative", "")
                if last_attempt:
                    try:
                        last_attempt_dt = datetime.strptime(last_attempt, "%Y-%m-%d %H:%M:%S")
                        if (datetime.now() - last_attempt_dt).total_seconds() < 3600:  # 1 heure
                            continue  # Ne pas retenter tout de suite
                    except:
                        pass
                
                posts_non_publies.append({
                    'index': index,
                    'data': post_data
                })
        
        log_message("publications", f"{len(posts_non_publies)} posts non publiés trouvés", "INFO")
        return posts_non_publies
        
    except Exception as e:
        log_message("errors", f"Erreur lecture Google Sheets: {e}", "ERROR")
        return []

def verifier_heure_publication():
    """Vérifie si c'est une bonne heure pour publier"""
    maintenant = datetime.now()
    heure = maintenant.hour
    
    # Vérifier si c'est dans les heures d'ouverture
    if HEURES_OUVERTURE[0] <= heure <= HEURES_OUVERTURE[1]:
        return True
    else:
        log_message("publications", f"Heure nocturne ({heure}h) - Publication suspendue", "WARNING")
        return False

def publier_post_facebook(post_data, index):
    """Publie un post sur Facebook et met à jour Google Sheets"""
    try:
        contenu = post_data.get("texte_marketing", "")
        image_path = post_data.get("image_path", "")
        titre = post_data.get("titre", "Sans titre")
        theme = post_data.get("theme", "Général")
        
        if not contenu or str(contenu).strip() == "":
            log_message("errors", f"Aucun texte marketing pour '{titre}'", "ERROR")
            return False
        
        log_message("publications", f"Publication en cours: '{titre}' (Thème: {theme})", "INFO")
        
        # Décider si on publie avec l'image
        publish_with_image = False
        if image_path and str(image_path).strip() != "":
            if image_path.startswith('http') or os.path.exists(image_path):
                publish_with_image = True
                log_message("publications", f"Image détectée: {image_path}", "INFO")
        
        # Préparer les données pour Facebook
        facebook_data = {
            "contenu": contenu,
            "image_path": image_path if publish_with_image else None,
            "titre": titre,
            "theme": theme
        }
        
        # Publier sur Facebook
        resultat = publier_sur_facebook(facebook_data, with_image=publish_with_image)
        
        if resultat.get("status") not in ["success", "publié"]:
            error_msg = resultat.get("message", "Erreur inconnue")
            log_message("errors", f"Publication échouée: {error_msg}", "ERROR")
            
            # Enregistrer l'échec dans Google Sheets
            mettre_a_jour_post_gsheets(index, {
                "derniere_tentative": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "statut_publication": "échec",
                "erreur_publication": error_msg[:100]  # Limiter la longueur
            })
            return False
        
        post_id = resultat.get("post_id", "")
        log_message("publications", f"Post publié avec ID: {post_id} | Avec image: {publish_with_image}", "SUCCESS")
        
        # Attendre un peu pour que les réactions arrivent
        time.sleep(8)
        
        # Lire réactions
        reaction_count = lire_reactions(post_id)
        
        # Traiter commentaires initiaux
        interactions = traiter_commentaires(post_id)
        
        # Préparer les mises à jour Google Sheets
        updates = {
            "nom_plateforme": "Facebook",
            "post_id": post_id,
            "reaction_positive": reaction_count,
            "publication_effective": "oui",
            "date_publication": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "commentaires_traites": len(interactions),
            "statut_publication": "publié",
            "derniere_mise_a_jour": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lien_post": f"https://facebook.com/{post_id}" if post_id else "",
            "heure_publication": datetime.now().strftime("%H:%M"),
            "jour_publication": datetime.now().strftime("%A")
        }
        
        # Mettre à jour dans Google Sheets
        success = mettre_a_jour_post_gsheets(index, updates)
        
        if success:
            log_message("publications", f"Google Sheets mis à jour pour '{titre}'", "SUCCESS")
            log_publication_details(titre, post_id, reaction_count, len(interactions))
            
            # Démarrer le service de commentaires si ce n'est pas déjà fait
            if not comment_service.running:
                log_message("comments", "Démarrage du service de commentaires...", "INFO")
                demarrer_service_commentaires()
            
            return True
        else:
            log_message("errors", "Publication réussie mais échec mise à jour Google Sheets", "WARNING")
            return False
            
    except Exception as e:
        log_message("errors", f"Erreur publication Facebook: {e}", "ERROR")
        return False

def log_publication_details(titre, post_id, reactions, commentaires):
    """Enregistre les détails d'une publication"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = {
        "timestamp": timestamp,
        "titre": titre,
        "post_id": post_id,
        "reactions": reactions,
        "commentaires": commentaires,
        "lien": f"https://facebook.com/{post_id}" if post_id else ""
    }
    
    # Log dans fichier JSON
    log_file = 'logs/publications/details.json'
    existing_data = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            existing_data = []
    
    existing_data.append(details)
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    # Log texte simple
    log_entry = f"[{timestamp}] ✅ PUBLIÉ: '{titre}' | ID: {post_id} | Réactions: {reactions} | Commentaires: {commentaires}\n"
    with open('logs/publications.log', 'a', encoding='utf-8') as f:
        f.write(log_entry)

def publier_tous():
    """Publie tous les posts non publiés"""
    log_message("publications", "=" * 60, "INFO")
    log_message("publications", "Vérification des posts à publier...", "INFO")
    
    # Vérifier l'heure de publication
    if not verifier_heure_publication():
        return {"status": "suspended", "message": "Heure nocturne", "published": 0}
    
    posts_non_publies = lire_posts_non_publies()
    
    if not posts_non_publies:
        log_message("publications", "✅ Aucun post à publier", "INFO")
        return {"status": "completed", "published": 0}
    
    publies = 0
    echecs = 0
    skipped = 0
    
    # Vérifier quand était la dernière publication
    last_publication = getattr(publier_tous, 'last_publication', None)
    if last_publication:
        time_since_last = (datetime.now() - last_publication).total_seconds() / 60
        if time_since_last < MINUTES_ENTRE_PUBLICATIONS:
            log_message("publications", f"⏳ Attente requise: {MINUTES_ENTRE_PUBLICATIONS - int(time_since_last)} min restantes", "INFO")
            return {"status": "waiting", "minutes_remaining": MINUTES_ENTRE_PUBLICATIONS - int(time_since_last)}
    
    for post_info in posts_non_publies:
        index = post_info['index']
        post_data = post_info['data']
        
        titre = post_data.get('titre', 'Sans titre')
        log_message("publications", f"Traitement post #{index + 1}: '{titre}'", "INFO")
        
        if publier_post_facebook(post_data, index):
            publies += 1
            publier_tous.last_publication = datetime.now()  # Mettre à jour le timestamp
            
            # Attendre avant la prochaine publication
            if publies < len(posts_non_publies):
                wait_time = 60  # 1 minute entre publications
                log_message("publications", f"⏳ Attente {wait_time}s avant prochaine publication...", "INFO")
                time.sleep(wait_time)
        else:
            echecs += 1
    
    log_message("publications", f"📊 Résumé: {publies} publiés, {echecs} échecs", "INFO")
    log_message("publications", "=" * 60, "INFO")
    
    return {
        "status": "completed",
        "published": publies,
        "failed": echecs,
        "total": len(posts_non_publies)
    }

# -----------------------------
# Service de commentaires intégré
# -----------------------------
def traiter_anciens_commentaires_manuellement():
    """Exécute un traitement manuel des anciens commentaires"""
    log_message("comments", "Démarrage traitement manuel des anciens commentaires...", "INFO")
    
    result = executer_traitement_manuel()
    
    if result.get('status') == 'success':
        stats = result.get('stats', {})
        log_message("comments", 
            f"Traitement manuel terminé: {stats.get('comments_replied', 0)} commentaires répondu(s)", 
            "SUCCESS")
    else:
        log_message("errors", f"Erreur traitement manuel: {result.get('message', 'Inconnue')}", "ERROR")
    
    return result

# -----------------------------
# Thread automatique amélioré
# -----------------------------
def thread_automatisation():
    """Thread principal d'automatisation"""
    log_message("system", "🤖 Thread d'automatisation démarré", "INFO")
    
    while getattr(thread_automatisation, 'running', True):
        try:
            # Publication des posts
            if verifier_heure_publication():
                resultat = publier_tous()
                
                if resultat.get("published", 0) > 0:
                    log_message("publications", 
                        f"🎉 {resultat['published']} nouveaux posts publiés!", 
                        "SUCCESS")
                
                # Attendre selon le résultat
                if resultat.get("status") == "completed" and resultat.get("published", 0) > 0:
                    time.sleep(600)  # 10 minutes après publication
                elif resultat.get("status") == "waiting":
                    minutes = resultat.get("minutes_remaining", 30)
                    time.sleep(minutes * 60)
                else:
                    time.sleep(INTERVALLE_ANALYSE)
            else:
                # La nuit, faire d'autres tâches (commentaires, stats)
                try:
                    # Traiter les anciens commentaires
                    comment_stats = get_statut_service_commentaires()
                    if not comment_stats.get('running', False):
                        log_message("comments", "Démarrage service commentaires nocturne...", "INFO")
                        demarrer_service_commentaires()
                    
                    time.sleep(1800)  # 30 minutes la nuit
                    
                except Exception as e:
                    log_message("errors", f"Erreur tâches nocturnes: {e}", "ERROR")
                    time.sleep(900)  # 15 minutes en cas d'erreur
                
        except Exception as e:
            log_message("errors", f"Erreur dans thread d'automatisation: {e}", "ERROR")
            time.sleep(300)  # Attendre 5 minutes en cas d'erreur

# -----------------------------
# Système de statistiques
# -----------------------------
def verifier_etat_publications():
    """Vérifie l'état des publications récentes"""
    try:
        df = lire_historique_gsheets()
        
        if df.empty:
            return {"status": "no_data", "message": "Aucune donnée disponible"}
        
        # Statistiques de base
        total = df.shape[0]
        publies = df[df["publication_effective"] == "oui"].shape[0]
        non_publies = df[df["publication_effective"] != "oui"].shape[0]
        
        # Statistiques avancées
        stats = {
            "total_posts": total,
            "posts_publies": publies,
            "posts_non_publies": non_publies,
            "taux_publication": f"{(publies/total*100):.1f}%" if total > 0 else "0%",
            "reactions_moyennes": 0,
            "commentaires_moyens": 0,
            "meilleur_post": None,
            "dernieres_publications": []
        }
        
        if publies > 0:
            # Calculer les moyennes
            if "reaction_positive" in df.columns:
                reactions = pd.to_numeric(df["reaction_positive"], errors='coerce').fillna(0)
                stats["reactions_moyennes"] = reactions.mean()
            
            if "commentaires_traites" in df.columns:
                commentaires = pd.to_numeric(df["commentaires_traites"], errors='coerce').fillna(0)
                stats["commentaires_moyens"] = commentaires.mean()
            
            # Trouver le meilleur post
            if "reaction_positive" in df.columns:
                best_idx = df["reaction_positive"].astype(str).str.extract('(\d+)').fillna(0).astype(int).idxmax()
                if pd.notna(best_idx):
                    best_post = df.loc[best_idx]
                    stats["meilleur_post"] = {
                        "titre": best_post.get("titre", "N/A"),
                        "reactions": best_post.get("reaction_positive", 0),
                        "date": best_post.get("date_publication", "N/A")
                    }
        
        # Dernières publications
        if "date_publication" in df.columns:
            df_publies = df[df["publication_effective"] == "oui"].copy()
            if not df_publies.empty:
                df_publies["date_publication"] = pd.to_datetime(df_publies["date_publication"], errors='coerce')
                df_publies = df_publies.sort_values("date_publication", ascending=False)
                
                dernieres = df_publies.head(5).to_dict('records')
                stats["dernieres_publications"] = [
                    {
                        "titre": p.get("titre", "N/A"),
                        "date": p.get("date_publication", "N/A"),
                        "reactions": p.get("reaction_positive", 0),
                        "commentaires": p.get("commentaires_traites", 0)
                    }
                    for p in dernieres
                ]
        
        # Ajouter les statistiques du service de commentaires
        stats["service_commentaires"] = get_statut_service_commentaires()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_message("errors", f"Erreur vérification état publications: {e}", "ERROR")
        return {"status": "error", "message": str(e)}

# -----------------------------
# API de contrôle principal
# -----------------------------
def demarrer_automatisation_complete():
    """Démarre le système d'automatisation complet"""
    if getattr(demarrer_automatisation_complete, 'running', False):
        log_message("system", "⚠️ Automatisation déjà en cours", "WARNING")
        return {"status": "already_running", "message": "Système déjà démarré"}
    
    try:
        # Vérifier la connexion Google Sheets
        info = gsheets_db.get_sheet_info()
        
        if info.get('status') != 'initialisé':
            log_message("errors", "❌ Google Sheets non connecté", "ERROR")
            return {"status": "error", "message": "Google Sheets non connecté"}
        
        # Configurer le logging
        setup_logging()
        
        # Démarrer le thread principal
        thread_automatisation.running = True
        t = threading.Thread(target=thread_automatisation, daemon=True)
        t.start()
        demarrer_automatisation_complete.running = True
        
        # Démarrer le service de commentaires
        comment_service_result = demarrer_service_commentaires()
        
        log_message("system", "=" * 60, "INFO")
        log_message("system", "🚀 SYSTÈME D'AUTOMATISATION COMPLET DÉMARRÉ", "SUCCESS")
        log_message("system", f"   • Publication: {HEURES_OUVERTURE[0]}h-{HEURES_OUVERTURE[1]}h", "INFO")
        log_message("system", f"   • Vérification: {INTERVALLE_ANALYSE}s", "INFO")
        log_message("system", f"   • Google Sheets: {info.get('title', 'Inconnu')}", "INFO")
        log_message("system", f"   • Service commentaires: {'ACTIVÉ' if comment_service.running else 'DÉSACTIVÉ'}", "INFO")
        log_message("system", "=" * 60, "INFO")
        
        return {
            "status": "started",
            "message": "Système d'automatisation démarré avec succès",
            "details": {
                "publication_hours": f"{HEURES_OUVERTURE[0]}h-{HEURES_OUVERTURE[1]}h",
                "check_interval": f"{INTERVALLE_ANALYSE}s",
                "google_sheets": info.get('title'),
                "comment_service": comment_service.running
            }
        }
        
    except Exception as e:
        log_message("errors", f"❌ Erreur démarrage automatisation: {e}", "ERROR")
        return {"status": "error", "message": str(e)}

def arreter_automatisation():
    """Arrête le système d'automatisation"""
    try:
        # Arrêter le thread principal
        thread_automatisation.running = False
        
        # Arrêter le service de commentaires
        arreter_service_commentaires()
        
        demarrer_automatisation_complete.running = False
        
        log_message("system", "🛑 Système d'automatisation arrêté", "INFO")
        
        return {
            "status": "stopped",
            "message": "Système d'automatisation arrêté avec succès",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_message("errors", f"Erreur arrêt automatisation: {e}", "ERROR")
        return {"status": "error", "message": str(e)}

def get_statut_complet():
    """Retourne le statut complet du système"""
    try:
        # Statut publication
        publication_status = {
            "running": getattr(demarrer_automatisation_complete, 'running', False),
            "intervalle": INTERVALLE_ANALYSE,
            "heure_limite": f"{HEURES_OUVERTURE[0]}h-{HEURES_OUVERTURE[1]}h",
            "derniere_verification": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Statut Google Sheets
        sheets_info = gsheets_db.get_sheet_info()
        
        # Statut service commentaires
        comment_status = get_statut_service_commentaires()
        
        # Statistiques
        stats = verifier_etat_publications()
        
        return {
            "status": "success",
            "publication": publication_status,
            "google_sheets": sheets_info,
            "comment_service": comment_status,
            "statistics": stats.get("stats", {}) if stats.get("status") == "success" else {},
            "timestamp": datetime.now().isoformat(),
            "system": {
                "uptime": "N/A",  # À implémenter si besoin
                "memory_usage": "N/A",
                "active_threads": threading.active_count()
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Initialisation
setup_logging()