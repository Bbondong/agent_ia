# modules/plateformes/facebook.py - VERSION AMÉLIORÉE
import os
import time
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from modules.ia import generer_reponse_commentaire
from config import FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN

API_URL = "https://graph.facebook.com/v19.0"

# -----------------------------
# Configuration
# -----------------------------
DEBUG = True
MAX_DAYS_OLD = 30  # Traiter les posts jusqu'à 30 jours
COMMENT_DAYS_LIMIT = 7  # Répondre aux commentaires jusqu'à 7 jours

def debug_log(message: str):
    """Journalisation de debugging"""
    if DEBUG:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[FACEBOOK DEBUG {timestamp}] {message}")

# -----------------------------
# Helpers avec retry et gestion d'erreurs améliorée
# -----------------------------
def request_post(url: str, data: Optional[Dict] = None, files: Optional[Dict] = None, 
                 retries: int = 3, delay: int = 5, timeout: int = 30) -> Optional[Dict]:
    """Requête POST avec retry et meilleure gestion d'erreurs"""
    for attempt in range(1, retries + 1):
        try:
            debug_log(f"POST attempt {attempt}/{retries} to {url}")
            
            headers = {'Content-Type': 'application/json'}
            json_data = json.dumps(data) if data else None
            
            resp = requests.post(url, data=json_data, files=files, 
                                 headers=headers, timeout=timeout)
            debug_log(f"Response status: {resp.status_code}")
            
            resp.raise_for_status()
            result = resp.json()
            return result
            
        except requests.exceptions.Timeout as e:
            debug_log(f"Timeout error: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
        except requests.exceptions.HTTPError as e:
            debug_log(f"HTTP error: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
        except Exception as e:
            debug_log(f"Other error: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
    return None

def request_get(url: str, params: Optional[Dict] = None, 
                retries: int = 3, delay: int = 5, timeout: int = 30) -> Optional[Dict]:
    """Requête GET avec retry"""
    for attempt in range(1, retries + 1):
        try:
            debug_log(f"GET attempt {attempt}/{retries} to {url}")
            resp = requests.get(url, params=params, timeout=timeout)
            debug_log(f"Response status: {resp.status_code}")
            
            resp.raise_for_status()
            return resp.json()
            
        except Exception as e:
            debug_log(f"Error: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
    return None

# -----------------------------
# Gestion des anciens posts et commentaires
# -----------------------------
def obtenir_posts_recents(days_back: int = MAX_DAYS_OLD) -> List[Dict]:
    """Récupère les posts récents de la page Facebook"""
    try:
        debug_log(f"Fetching posts from last {days_back} days...")
        
        # Calculer la date limite
        since_date = (datetime.now() - timedelta(days=days_back)).timestamp()
        
        url = f"{API_URL}/{FACEBOOK_PAGE_ID}/posts"
        params = {
            "access_token": FACEBOOK_ACCESS_TOKEN,
            "fields": "id,message,created_time,permalink_url",
            "since": str(int(since_date)),
            "limit": 100
        }
        
        data = request_get(url, params=params)
        
        if not data or 'data' not in data:
            debug_log("No posts data received")
            return []
        
        posts = []
        for post in data['data']:
            posts.append({
                'id': post.get('id'),
                'message': post.get('message', ''),
                'created_time': post.get('created_time'),
                'permalink_url': post.get('permalink_url', ''),
                'age_days': (datetime.now() - datetime.strptime(
                    post.get('created_time'), '%Y-%m-%dT%H:%M:%S%z'
                )).days if post.get('created_time') else 0
            })
        
        debug_log(f"Found {len(posts)} recent posts")
        return posts
        
    except Exception as e:
        debug_log(f"Error fetching posts: {e}")
        return []

def obtenir_commentaires_non_repondus(post_id: str, hours_limit: int = 24) -> List[Dict]:
    """Récupère les commentaires non répondus d'un post"""
    try:
        debug_log(f"Fetching un-replied comments for post: {post_id}")
        
        # Récupérer tous les commentaires
        url = f"{API_URL}/{post_id}/comments"
        params = {
            "access_token": FACEBOOK_ACCESS_TOKEN,
            "fields": "id,message,created_time,from,comment_count",
            "filter": "stream",  # Tous les commentaires
            "limit": 100
        }
        
        data = request_get(url, params=params)
        
        if not data or 'data' not in data:
            return []
        
        un_replied_comments = []
        
        for comment in data['data']:
            comment_id = comment.get('id')
            
            # Vérifier si le commentaire a des réponses
            has_replies = comment.get('comment_count', 0) > 0
            
            # Vérifier l'âge du commentaire
            created_time = comment.get('created_time')
            if created_time:
                comment_date = datetime.strptime(created_time, '%Y-%m-%dT%H:%M:%S%z')
                age_hours = (datetime.now(comment_date.tzinfo) - comment_date).total_seconds() / 3600
                
                # Ne traiter que les commentaires récents (dans la limite d'heures)
                if age_hours <= hours_limit and not has_replies:
                    un_replied_comments.append({
                        'comment_id': comment_id,
                        'post_id': post_id,
                        'message': comment.get('message', ''),
                        'created_time': created_time,
                        'user': comment.get('from', {}).get('name', 'Inconnu'),
                        'user_id': comment.get('from', {}).get('id', ''),
                        'age_hours': age_hours
                    })
        
        debug_log(f"Found {len(un_replied_comments)} un-replied comments for post {post_id}")
        return un_replied_comments
        
    except Exception as e:
        debug_log(f"Error fetching comments: {e}")
        return []

def repondre_au_commentaire(comment_id: str, message: str) -> bool:
    """Répond à un commentaire spécifique"""
    try:
        debug_log(f"Replying to comment {comment_id}")
        
        url = f"{API_URL}/{comment_id}/comments"
        data = {
            "message": message,
            "access_token": FACEBOOK_ACCESS_TOKEN
        }
        
        response = request_post(url, data=data)
        
        if response and 'id' in response:
            debug_log(f"Reply successful: {response['id']}")
            return True
        else:
            debug_log(f"Reply failed: {response}")
            return False
            
    except Exception as e:
        debug_log(f"Error replying to comment: {e}")
        return False

# -----------------------------
# NOUVEAU : Traitement des anciens posts
# -----------------------------
def traiter_anciens_posts_et_commentaires() -> Dict[str, Any]:
    """
    Traite les anciens posts et répond aux commentaires non traités
    Retourne les statistiques de traitement
    """
    debug_log("Starting processing of old posts and comments...")
    
    stats = {
        'posts_checked': 0,
        'comments_found': 0,
        'comments_replied': 0,
        'errors': 0,
        'posts': []
    }
    
    try:
        # 1. Récupérer les posts récents
        posts = obtenir_posts_recents(days_back=MAX_DAYS_OLD)
        stats['posts_checked'] = len(posts)
        
        for post in posts:
            post_id = post.get('id')
            post_stats = {
                'post_id': post_id,
                'age_days': post.get('age_days', 0),
                'comments_checked': 0,
                'comments_replied': 0
            }
            
            # 2. Récupérer les commentaires non répondus
            un_replied_comments = obtenir_commentaires_non_repondus(
                post_id, 
                hours_limit=COMMENT_DAYS_LIMIT * 24
            )
            
            post_stats['comments_checked'] = len(un_replied_comments)
            stats['comments_found'] += len(un_replied_comments)
            
            # 3. Traiter chaque commentaire non répondu
            for comment in un_replied_comments:
                try:
                    # Générer une réponse IA
                    reponse_ia = generer_reponse_commentaire(comment['message'])
                    
                    # Répondre au commentaire
                    if repondre_au_commentaire(comment['comment_id'], reponse_ia):
                        post_stats['comments_replied'] += 1
                        stats['comments_replied'] += 1
                        
                        # Log de la réponse
                        debug_log(f"Replied to comment from {comment['user']} on post {post_id}")
                        
                        # Attendre un peu entre les réponses pour éviter le spam
                        time.sleep(2)
                        
                except Exception as e:
                    stats['errors'] += 1
                    debug_log(f"Error processing comment {comment['comment_id']}: {e}")
            
            stats['posts'].append(post_stats)
        
        debug_log(f"Processing completed: {stats}")
        return {
            'status': 'success',
            'message': f'Traitement terminé: {stats["comments_replied"]}/{stats["comments_found"]} commentaires répondu(s)',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error in traiter_anciens_posts_et_commentaires: {e}"
        debug_log(error_msg)
        return {
            'status': 'error',
            'message': error_msg,
            'stats': stats
        }

# -----------------------------
# NOUVEAU : Service automatique de traitement
# -----------------------------
class FacebookCommentService:
    """Service pour gérer automatiquement les commentaires Facebook"""
    
    def __init__(self):
        self.last_processed = None
        self.running = False
        self.processing_thread = None
        
    def demarrer_service(self):
        """Démarre le service de traitement automatique"""
        if self.running:
            return {"status": "already_running"}
        
        self.running = True
        
        # Lancer un traitement immédiat
        import threading
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        return {
            "status": "started",
            "message": "Service de traitement des commentaires démarré",
            "check_interval_hours": 6
        }
    
    def arreter_service(self):
        """Arrête le service"""
        self.running = False
        return {"status": "stopped", "message": "Service arrêté"}
    
    def _processing_loop(self):
        """Boucle de traitement automatique"""
        import time
        
        while self.running:
            try:
                debug_log("Starting automatic comment processing...")
                
                # Traiter les anciens posts et commentaires
                result = traiter_anciens_posts_et_commentaires()
                
                self.last_processed = datetime.now()
                
                debug_log(f"Processing completed: {result.get('message', 'No message')}")
                
                # Attendre 6 heures avant le prochain traitement
                for _ in range(6 * 60):  # 6 heures = 360 minutes
                    if not self.running:
                        break
                    time.sleep(60)  # Vérifier toutes les minutes
                    
            except Exception as e:
                debug_log(f"Error in processing loop: {e}")
                time.sleep(300)  # Attendre 5 minutes en cas d'erreur
    
    def get_status(self):
        """Retourne le statut du service"""
        return {
            "running": self.running,
            "last_processed": self.last_processed.isoformat() if self.last_processed else None,
            "next_check_in": self._calculate_next_check() if self.last_processed else None
        }
    
    def _calculate_next_check(self):
        """Calcule le prochain traitement"""
        if self.last_processed:
            next_check = self.last_processed + timedelta(hours=6)
            return next_check.isoformat()
        return None

# Instance globale du service
comment_service = FacebookCommentService()

# -----------------------------
# Fonctions existantes (gardées pour compatibilité)
# -----------------------------
def test_connexion_facebook() -> Dict[str, Any]:
    """Teste la connexion à l'API Facebook"""
    debug_log("Testing Facebook connection...")
    
    # Test 1: Vérifier le token
    print("\n🔍 Test 1/3: Vérification du token...")
    url = f"{API_URL}/me"
    params = {"access_token": FACEBOOK_ACCESS_TOKEN, "fields": "id,name"}
    result = request_get(url, params=params, timeout=10)
    
    if not result:
        return {"status": "error", "message": "Token invalide ou expiré", "step": "token_test"}
    
    print(f"✅ Token OK - Compte: {result.get('name', 'N/A')} (ID: {result.get('id', 'N/A')})")
    
    # Test 2: Vérifier la page
    print("\n🔍 Test 2/3: Vérification de la page...")
    url = f"{API_URL}/{FACEBOOK_PAGE_ID}"
    params = {"access_token": FACEBOOK_ACCESS_TOKEN, "fields": "id,name,access_token"}
    result = request_get(url, params=params, timeout=10)
    
    if not result:
        return {"status": "error", "message": "Page non accessible", "step": "page_test"}
    
    print(f"✅ Page OK - {result.get('name', 'N/A')} (ID: {result.get('id', 'N/A')})")
    
    return {"status": "success", "message": "Connexion Facebook OK"}

def publier_sur_facebook(post: Dict[str, Any], with_image: bool = True) -> Dict[str, Any]:
    """Publie un post sur Facebook avec gestion robuste des erreurs"""
    debug_log(f"Starting publication for post: {post.get('titre', 'No title')}")
    
    # Vérifier les credentials
    if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
        error_msg = "Credentials Facebook manquants dans .env"
        debug_log(error_msg)
        return {"status": "error", "message": error_msg}
    
    # Préparer le message
    message = post.get("texte_marketing", "") or post.get("contenu", "")
    if not message:
        message = f"{post.get('titre', 'Nouveau post')}\n\n{post.get('service', 'Ben Tech Services')}"
    
    # Gestion de l'image
    image_path = None
    if with_image:
        image_path = post.get("image_path", "")
        if image_path and isinstance(image_path, str) and os.path.isfile(image_path):
            debug_log(f"Image found: {image_path} ({os.path.getsize(image_path)} bytes)")
        else:
            debug_log(f"No valid image: {image_path}")
            image_path = None
    
    try:
        # Option 1: Publier avec image
        if image_path:
            debug_log("Publishing with image...")
            url = f"{API_URL}/{FACEBOOK_PAGE_ID}/photos"
            
            # Ouvrir l'image
            with open(image_path, "rb") as img_file:
                files = {"source": img_file}
                data = {
                    "caption": message,
                    "access_token": FACEBOOK_ACCESS_TOKEN,
                    "published": "true"
                }
                
                debug_log("Sending POST request with image...")
                response = request_post(url, data=data, files=files, timeout=45)
        
        # Option 2: Publier sans image
        else:
            debug_log("Publishing without image...")
            url = f"{API_URL}/{FACEBOOK_PAGE_ID}/feed"
            data = {
                "message": message,
                "access_token": FACEBOOK_ACCESS_TOKEN
            }
            debug_log("Sending POST request...")
            response = request_post(url, data=data, timeout=30)
        
        # Analyser la réponse
        if not response:
            error_msg = "Aucune réponse de l'API Facebook"
            debug_log(error_msg)
            return {"status": "error", "message": error_msg}
        
        if "id" not in response:
            error_msg = f"Réponse incomplète: {response}"
            debug_log(error_msg)
            return {"status": "error", "message": error_msg}
        
        post_id = response.get("id", "")
        debug_log(f"Publication réussie! Post ID: {post_id}")
        
        # Démarrer automatiquement le service de commentaires pour ce nouveau post
        if comment_service.running:
            debug_log(f"Comment service will monitor new post: {post_id}")
        
        return {
            "status": "success", 
            "message": "Publication réussie",
            "post_id": post_id,
            "plateforme": "Facebook",
            "comment_service": comment_service.running
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la publication: {str(e)}"
        debug_log(error_msg)
        return {"status": "error", "message": error_msg}

def traiter_commentaires(post_id: str) -> List[Dict]:
    """Traite et répond aux commentaires d'un post (version simplifiée)"""
    debug_log(f"Processing comments for post: {post_id}")
    
    un_replied = obtenir_commentaires_non_repondus(post_id, hours_limit=24)
    results = []
    
    for comment in un_replied:
        try:
            # Générer réponse IA
            reponse = generer_reponse_commentaire(comment['message'])
            
            # Répondre
            if repondre_au_commentaire(comment['comment_id'], reponse):
                results.append({
                    "user": comment['user'],
                    "commentaire_recu": comment['message'],
                    "reponse_envoyee": reponse,
                    "timestamp": datetime.now().isoformat(),
                    "status": "replied"
                })
                
        except Exception as e:
            results.append({
                "user": comment['user'],
                "commentaire_recu": comment['message'],
                "error": str(e),
                "status": "error"
            })
    
    return results

# -----------------------------
# API pour le contrôle du service
# -----------------------------
def demarrer_service_commentaires():
    """Démarre le service automatique de commentaires"""
    return comment_service.demarrer_service()

def arreter_service_commentaires():
    """Arrête le service automatique de commentaires"""
    return comment_service.arreter_service()

def get_statut_service_commentaires():
    """Retourne le statut du service de commentaires"""
    return comment_service.get_status()

def executer_traitement_manuel():
    """Exécute un traitement manuel des anciens posts"""
    return traiter_anciens_posts_et_commentaires()