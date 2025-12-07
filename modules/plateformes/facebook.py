# platforme/facebook.py - CORRIGÉ
import os
import time
import requests
import sys
from typing import Dict, List, Optional, Any
from modules.ia import generer_reponse_commentaire
from config import FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN

API_URL = "https://graph.facebook.com/v19.0"

# -----------------------------
# Configuration de debugging
# -----------------------------
DEBUG = True  # Mettez à False en production

def debug_log(message: str):
    """Journalisation de debugging"""
    if DEBUG:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[FACEBOOK DEBUG {timestamp}] {message}")

# -----------------------------
# Helpers avec retry, timeout et meilleure gestion d'erreurs
# -----------------------------
def request_post(url: str, data: Optional[Dict] = None, files: Optional[Dict] = None, 
                 retries: int = 3, delay: int = 5, timeout: int = 30) -> Optional[Dict]:
    """Requête POST avec retry et meilleure gestion d'erreurs"""
    for attempt in range(1, retries + 1):
        try:
            debug_log(f"POST attempt {attempt}/{retries} to {url}")
            debug_log(f"Data keys: {list(data.keys()) if data else 'None'}")
            
            resp = requests.post(url, data=data, files=files, timeout=timeout)
            debug_log(f"Response status: {resp.status_code}")
            
            resp.raise_for_status()
            result = resp.json()
            debug_log(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not dict'}")
            return result
            
        except requests.exceptions.Timeout as e:
            debug_log(f"Timeout error: {e}")
            print(f"[POST TIMEOUT] {e} | tentative {attempt}/{retries}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
        except requests.exceptions.ConnectionError as e:
            debug_log(f"Connection error: {e}")
            print(f"[POST CONNECTION ERROR] {e} | tentative {attempt}/{retries}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
        except requests.exceptions.HTTPError as e:
            debug_log(f"HTTP error: {e}")
            print(f"[POST HTTP ERROR {resp.status_code}] {e} | tentative {attempt}/{retries}")
            
            # Essayez de lire le message d'erreur Facebook
            try:
                error_data = resp.json()
                print(f"Facebook error: {error_data}")
            except:
                pass
                
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
        except Exception as e:
            debug_log(f"Other error: {e}")
            print(f"[POST ERROR] {e} | tentative {attempt}/{retries}")
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
            
        except requests.exceptions.Timeout as e:
            debug_log(f"Timeout error: {e}")
            print(f"[GET TIMEOUT] {e} | tentative {attempt}/{retries}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
        except Exception as e:
            debug_log(f"Error: {e}")
            print(f"[GET ERROR] {e} | tentative {attempt}/{retries}")
            if attempt < retries:
                time.sleep(delay)
            else:
                return None
                
    return None

# -----------------------------
# Test de connexion Facebook
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
    
    # Test 3: Vérifier les permissions
    print("\n🔍 Test 3/3: Vérification des permissions...")
    url = f"{API_URL}/me/permissions"
    params = {"access_token": FACEBOOK_ACCESS_TOKEN}
    result = request_get(url, params=params, timeout=10)
    
    if result and 'data' in result:
        permissions = [p['permission'] for p in result['data'] if p['status'] == 'granted']
        print(f"✅ Permissions: {', '.join(permissions)}")
        
        permissions_requises = ['pages_manage_posts', 'pages_read_engagement']
        manquantes = [p for p in permissions_requises if p not in permissions]
        
        if manquantes:
            return {
                "status": "warning", 
                "message": f"Permissions manquantes: {', '.join(manquantes)}",
                "permissions": permissions
            }
    
    return {"status": "success", "message": "Connexion Facebook OK"}

# -----------------------------
# Publication d'un post (CORRIGÉ)
# -----------------------------
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
            
            # Préparer les données
            data = {
                "caption": message,
                "access_token": FACEBOOK_ACCESS_TOKEN,
                "published": "true"
            }
            
            # Ouvrir l'image en mode binaire
            with open(image_path, "rb") as img_file:
                files = {"source": img_file}
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
        
        return {
            "status": "success", 
            "message": "Publication réussie",
            "post_id": post_id,
            "plateforme": "Facebook",
            "response": response
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la publication: {str(e)}"
        debug_log(error_msg)
        return {"status": "error", "message": error_msg}

# -----------------------------
# Publication en mode simulation (pour tests)
# -----------------------------
def publier_simulation(post: Dict[str, Any]) -> Dict[str, Any]:
    """Mode simulation pour tests sans connexion réelle"""
    debug_log("SIMULATION MODE - No actual Facebook publication")
    
    message = post.get("texte_marketing", "") or post.get("contenu", "")
    image_path = post.get("image_path", "")
    
    return {
        "status": "simulated",
        "message": "Publication simulée (mode test)",
        "post_id": f"simulated_{int(time.time())}",
        "plateforme": "Facebook (simulé)",
        "image_used": bool(image_path and os.path.exists(image_path)),
        "text_length": len(message) if message else 0
    }

# -----------------------------
# Lire réactions
# -----------------------------
def lire_reactions(post_id: str) -> List[Dict]:
    """Lit les réactions d'un post Facebook"""
    debug_log(f"Reading reactions for post: {post_id}")
    
    url = f"{API_URL}/{post_id}/reactions"
    params = {"access_token": FACEBOOK_ACCESS_TOKEN, "fields": "id,name,type"}
    data = request_get(url, params=params)
    
    if not data:
        debug_log("No reactions data received")
        return []
    
    reactions = data.get("data", [])
    debug_log(f"Found {len(reactions)} reactions")
    return reactions

# -----------------------------
# Traiter commentaires automatiquement
# -----------------------------
def traiter_commentaires(post_id: str) -> List[Dict]:
    """Traite et répond aux commentaires d'un post"""
    debug_log(f"Processing comments for post: {post_id}")
    
    url = f"{API_URL}/{post_id}/comments"
    params = {"access_token": FACEBOOK_ACCESS_TOKEN, "fields": "id,message,from"}
    data = request_get(url, params=params)
    
    if not data:
        debug_log("No comments data received")
        return []
    
    commentaires = data.get("data", [])
    debug_log(f"Found {len(commentaires)} comments")
    resultats = []
    
    for com in commentaires:
        commentaire = com.get("message", "")
        com_id = com.get("id", "")
        user_info = com.get("from", {})
        user_id = user_info.get("id", "")
        user_name = user_info.get("name", "Utilisateur")
        
        if not commentaire or not com_id:
            continue
        
        debug_log(f"Processing comment from {user_name}: {commentaire[:50]}...")
        
        try:
            # Générer réponse IA
            reponse = generer_reponse_commentaire(commentaire)
            
            # Publier réponse (optionnel - commenter le code si vous voulez désactiver)
            rep_url = f"{API_URL}/{com_id}/comments"
            rep_data = {"message": reponse, "access_token": FACEBOOK_ACCESS_TOKEN}
            response = request_post(rep_url, data=rep_data)
            
            if response:
                debug_log(f"Reply posted successfully")
            
            resultats.append({
                "user": user_name,
                "commentaire_recu": commentaire,
                "reponse_envoyee": reponse,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
        except Exception as e:
            debug_log(f"Error processing comment: {e}")
            resultats.append({
                "user": user_name,
                "commentaire_recu": commentaire,
                "error": str(e)
            })
    
    return resultats

# -----------------------------
# Envoyer un message privé
# -----------------------------
def envoyer_message_prive(user_id: str, message: str) -> Optional[Dict]:
    """Envoie un message privé sur Facebook Messenger"""
    debug_log(f"Sending private message to user: {user_id}")
    
    # Vérifier si on a la permission 'pages_messaging'
    url = f"{API_URL}/me/messages"
    data = {
        "recipient": {"id": user_id},
        "message": {"text": message},
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    return request_post(url, data=data)