# flask_app.py - Agent IA Ben Tech Marketing - VERSION FINALE AVEC AUTHENTIFICATION
from flask import Flask, jsonify, request, render_template, session, redirect, url_for, send_from_directory
import os
import sys
import json
import datetime
from datetime import timedelta
import time
import threading
import schedule
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# ============================================
# CONFIGURATION - CHARGEMENT DU .ENV
# ============================================

# Charger les variables d'environnement depuis .env
load_dotenv()

# Variables d'environnement
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
UNSPLASH_API_KEY = os.getenv('UNSPLASH_API_KEY')
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')
FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Agent IA Ben Tech - Historique')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
YOUR_EMAIL = os.getenv('YOUR_EMAIL')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
PORT = int(os.getenv('PORT', 5000))
SECRET_KEY = os.getenv('SECRET_KEY', 'agent-ia-ben-tech-secret-key-prod-2024')

# Configuration d'authentification
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'benybadibanga13@gmail.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Mukulubentech13@')

# 1. Ajouter le chemin des modules
current_dir = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.join(current_dir, 'modules')
interface_path = os.path.join(current_dir, 'interface')
if modules_path not in sys.path:
    sys.path.append(modules_path)
if interface_path not in sys.path:
    sys.path.append(interface_path)

# 2. Configurer les variables d'environnement pour les modules
if GOOGLE_CREDENTIALS_JSON:
    os.environ['GOOGLE_CREDENTIALS_JSON'] = GOOGLE_CREDENTIALS_JSON
if GOOGLE_SHEET_ID:
    os.environ['GOOGLE_SHEET_ID'] = GOOGLE_SHEET_ID
os.environ['GOOGLE_SHEET_NAME'] = GOOGLE_SHEET_NAME

# ============================================
# VÉRIFICATION DES MODULES
# ============================================

MODULES_STATUS = {
    'ia': False,
    'publier': False,
    'google_sheets_db': False,
    'plateformes.facebook': False
}

try:
    from modules.ia import generer_contenu, get_statistiques_globales, audit_complet_performance
    MODULES_STATUS['ia'] = True
    print("✅ Module IA chargé")
except ImportError as e:
    print(f"❌ Erreur chargement module IA: {e}")

try:
    from modules.publier import (
        demarrer_automatisation_complete, 
        arreter_automatisation,
        get_statut_complet,
        publier_tous,
        verifier_etat_publications,
        traiter_anciens_commentaires_manuellement
    )
    MODULES_STATUS['publier'] = True
    print("✅ Module Publication chargé")
except ImportError as e:
    print(f"⚠️ Module Publication non disponible: {e}")

try:
    from modules.google_sheets_db import gsheets_db, lire_historique_gsheets
    MODULES_STATUS['google_sheets_db'] = True
    print("✅ Module Google Sheets chargé")
except ImportError as e:
    print(f"⚠️ Module Google Sheets non disponible: {e}")

try:
    from modules.plateformes.facebook import test_connexion_facebook
    MODULES_STATUS['plateformes.facebook'] = True
    print("✅ Module Facebook chargé")
except ImportError as e:
    print(f"⚠️ Module Facebook non disponible: {e}")

# ============================================
# APPLICATION FLASK
# ============================================

app = Flask(__name__, 
           template_folder='interface',
           static_folder='interface')
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=24)  # Session de 24h

# Variables globales pour le système automatique
AUTOMATIC_SYSTEM = {
    'running': False,
    'schedule_thread': None,
    'last_generation': None,
    'generation_count': 0,
    'next_generation': None,
    'generated_today': 0,
    'daily_limit': 3,
    'publication_running': False
}

# Système de vérification
VERIFICATION_SYSTEM = {
    'running': False,
    'check_thread': None,
    'last_check': None,
    'check_interval': 10,  # Vérifier toutes les 10 secondes
    'check_count': 0,
    'last_messages': []
}

# ============================================
# SYSTÈME DE VÉRIFICATION CHAQUE 10 SECONDES
# ============================================

def verifier_systeme_periodiquement():
    """Vérifie l'état du système toutes les 10 secondes"""
    while VERIFICATION_SYSTEM['running']:
        try:
            # Enregistrer la vérification
            now = datetime.datetime.now()
            VERIFICATION_SYSTEM['last_check'] = now.strftime("%Y-%m-%d %H:%M:%S")
            VERIFICATION_SYSTEM['check_count'] += 1
            
            # Vérifier l'état des modules
            messages = []
            
            # 1. Vérifier le système automatique
            if AUTOMATIC_SYSTEM['running'] and not VERIFICATION_SYSTEM['running']:
                messages.append("⚠️ Système automatique en marche mais vérification inactive")
            
            # 2. Vérifier les modules
            for module_name, status in MODULES_STATUS.items():
                if not status:
                    messages.append(f"❌ Module {module_name} non chargé")
            
            # 3. Vérifier la connexion aux APIs
            if not OPENAI_API_KEY:
                messages.append("⚠️ OpenAI API non configurée")
            
            if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
                messages.append("⚠️ Facebook non configuré")
            
            # 4. Vérifier le dernier log
            log_file = 'logs/system_check.log'
            os.makedirs('logs', exist_ok=True)
            
            # Enregistrer la vérification
            check_log = f"[{now}] Vérification #{VERIFICATION_SYSTEM['check_count']} - {len(messages)} messages\n"
            if messages:
                for msg in messages:
                    check_log += f"  • {msg}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(check_log)
            
            # Garder les derniers messages
            if messages:
                VERIFICATION_SYSTEM['last_messages'] = messages[-5:]  # Garder les 5 derniers
            
            # Afficher en console si debug
            if DEBUG and messages:
                print(f"[{now.strftime('%H:%M:%S')}] Vérification: {len(messages)} alertes")
            
        except Exception as e:
            error_msg = f"[{datetime.datetime.now()}] ❌ Erreur vérification système: {str(e)}\n"
            print(error_msg)
            
            os.makedirs('logs', exist_ok=True)
            with open('logs/system_check_errors.log', 'a', encoding='utf-8') as f:
                f.write(error_msg)
        
        # Attendre 10 secondes
        time.sleep(VERIFICATION_SYSTEM['check_interval'])

def demarrer_verification_systeme():
    """Démarrer le système de vérification"""
    if VERIFICATION_SYSTEM['running']:
        print("⚠️ Système de vérification déjà en cours d'exécution")
        return False
    
    try:
        VERIFICATION_SYSTEM['running'] = True
        VERIFICATION_SYSTEM['last_check'] = None
        VERIFICATION_SYSTEM['check_count'] = 0
        VERIFICATION_SYSTEM['last_messages'] = []
        
        # Démarrer le thread de vérification
        thread = threading.Thread(target=verifier_systeme_periodiquement, daemon=True)
        thread.start()
        VERIFICATION_SYSTEM['check_thread'] = thread
        
        print(f"🔍 Système de vérification démarré (vérification toutes les {VERIFICATION_SYSTEM['check_interval']}s)")
        return True
        
    except Exception as e:
        print(f"❌ Erreur démarrage vérification système: {e}")
        return False

def arreter_verification_systeme():
    """Arrêter le système de vérification"""
    VERIFICATION_SYSTEM['running'] = False
    print("🛑 Système de vérification arrêté")
    return True

# ============================================
# SYSTÈME AUTOMATIQUE AMÉLIORÉ
# ============================================

def generer_contenu_automatique():
    """Fonction pour générer du contenu automatiquement"""
    try:
        # Vérifier la limite quotidienne
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if 'last_reset' not in AUTOMATIC_SYSTEM or AUTOMATIC_SYSTEM.get('last_reset') != today:
            AUTOMATIC_SYSTEM['generated_today'] = 0
            AUTOMATIC_SYSTEM['last_reset'] = today
        
        if AUTOMATIC_SYSTEM['generated_today'] >= AUTOMATIC_SYSTEM['daily_limit']:
            print(f"⚠️ Limite quotidienne atteinte ({AUTOMATIC_SYSTEM['daily_limit']}/jour)")
            return None
        
        print(f"🤖 [{datetime.datetime.now()}] Génération automatique #{AUTOMATIC_SYSTEM['generated_today'] + 1}/3...")
        
        # Importer la fonction de génération
        if MODULES_STATUS['ia']:
            contenu = generer_contenu()
        else:
            # Fallback: créer un contenu basique
            contenu = {
                'titre': f'Contenu automatique {datetime.datetime.now().strftime("%H:%M")}',
                'theme': 'Automatique',
                'service': 'Service généré',
                'texte_marketing': 'Ce contenu a été généré automatiquement par le système.',
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'agent_responsable': 'Système'
            }
        
        # Sauvegarder les statistiques
        AUTOMATIC_SYSTEM['last_generation'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        AUTOMATIC_SYSTEM['generation_count'] += 1
        AUTOMATIC_SYSTEM['generated_today'] += 1
        
        # Calculer la prochaine génération
        maintenant = datetime.datetime.now()
        heures = [9, 14, 19]  # 9h, 14h, 19h
        prochaine = None
        
        for heure in heures:
            dt = maintenant.replace(hour=heure, minute=0, second=0, microsecond=0)
            if dt > maintenant:
                prochaine = dt
                break
        
        if not prochaine:  # Si toutes les heures sont passées aujourd'hui
            dt = (maintenant + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            prochaine = dt
        
        AUTOMATIC_SYSTEM['next_generation'] = prochaine.strftime("%Y-%m-%d %H:%M:%S")
        
        # Log dans un fichier
        log_entry = f"[{datetime.datetime.now()}] Génération #{AUTOMATIC_SYSTEM['generated_today']}/3: {contenu.get('titre', 'Sans titre')}\n"
        
        # Créer dossier logs si nécessaire
        os.makedirs('logs', exist_ok=True)
        
        with open('logs/auto_generation.log', 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"✅ Contenu généré: {contenu.get('titre', 'Sans titre')}")
        print(f"📊 Aujourd'hui: {AUTOMATIC_SYSTEM['generated_today']}/{AUTOMATIC_SYSTEM['daily_limit']}")
        
        return contenu
        
    except Exception as e:
        error_msg = f"[{datetime.datetime.now()}] ❌ Erreur génération automatique: {str(e)}\n"
        print(error_msg)
        
        os.makedirs('logs', exist_ok=True)
        with open('logs/auto_generation_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
        return None

def planifier_generations():
    """Planifie les générations automatiques 3 fois par jour"""
    # Heures de génération : 9h, 14h, 19h
    schedule.every().day.at("09:00").do(generer_contenu_automatique)
    schedule.every().day.at("14:00").do(generer_contenu_automatique)
    schedule.every().day.at("19:00").do(generer_contenu_automatique)
    
    print("⏰ Planification configurée: 9h, 14h, 19h tous les jours")
    
    # Boucle d'exécution du schedule
    while AUTOMATIC_SYSTEM['running']:
        try:
            schedule.run_pending()
            time.sleep(60)  # Vérifier toutes les minutes
        except Exception as e:
            print(f"❌ Erreur dans planifier_generations: {e}")
            time.sleep(300)  # Attendre 5 minutes en cas d'erreur

def demarrer_systeme_automatique():
    """Démarre le système automatique"""
    if AUTOMATIC_SYSTEM['running']:
        print("⚠️ Système automatique déjà en cours d'exécution")
        return False
    
    try:
        # Créer les dossiers nécessaires
        os.makedirs('logs', exist_ok=True)
        os.makedirs('images_posts', exist_ok=True)
        
        # Réinitialiser le compteur quotidien
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        AUTOMATIC_SYSTEM['last_reset'] = today
        AUTOMATIC_SYSTEM['generated_today'] = 0
        
        AUTOMATIC_SYSTEM['running'] = True
        
        # Démarrer le thread de planification
        thread = threading.Thread(target=planifier_generations, daemon=True)
        thread.start()
        AUTOMATIC_SYSTEM['schedule_thread'] = thread
        
        print("🚀 Système automatique démarré - Génération 3x/jour (9h, 14h, 19h)")
        
        # Démarrer aussi la publication automatique
        if MODULES_STATUS['publier']:
            try:
                result = demarrer_automatisation_complete()
                if result.get('status') == 'started':
                    AUTOMATIC_SYSTEM['publication_running'] = True
                    print("📤 Publication automatique démarrée")
            except Exception as e:
                print(f"⚠️ Impossible de démarrer la publication: {e}")
        
        # Générer immédiatement si c'est l'heure
        maintenant = datetime.datetime.now()
        heures_cibles = [9, 14, 19]
        if maintenant.hour in heures_cibles:
            print("⏰ Heure de génération actuelle - Lancement immédiat...")
            threading.Thread(target=generer_contenu_automatique, daemon=True).start()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur démarrage système automatique: {e}")
        return False

def arreter_systeme_automatique():
    """Arrête le système automatique"""
    AUTOMATIC_SYSTEM['running'] = False
    schedule.clear()
    
    # Arrêter aussi la publication automatique
    if MODULES_STATUS['publier'] and AUTOMATIC_SYSTEM['publication_running']:
        try:
            result = arreter_automatisation()
            if result.get('status') == 'stopped':
                AUTOMATIC_SYSTEM['publication_running'] = False
                print("📤 Publication automatique arrêtée")
        except Exception as e:
            print(f"⚠️ Impossible d'arrêter la publication: {e}")
    
    print("🛑 Système automatique arrêté")
    return True

# ============================================
# MIDDLEWARE D'AUTHENTIFICATION
# ============================================

def verifier_authentification():
    """Vérifier si l'utilisateur est authentifié"""
    if request.endpoint in ['login_page', 'static', 'serve_interface_files', 'home']:
        return None
    
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    return None

@app.before_request
def before_request():
    """Vérifier l'authentification avant chaque requête"""
    return verifier_authentification()

# ============================================
# ROUTES D'AUTHENTIFICATION
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Page de connexion"""
    # Si déjà connecté, rediriger vers le dashboard
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    # GET: Afficher le formulaire
    if request.method == 'GET':
        try:
            return render_template('index.html')  # index.html est la page de login
        except:
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Connexion - Ben Tech Marketing</title>
                <style>
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 50px; }
                    .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    h1 { color: #007bff; text-align: center; margin-bottom: 30px; }
                    .form-group { margin-bottom: 20px; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
                    .btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                    .btn:hover { background: #0056b3; }
                    .error { color: red; text-align: center; margin-top: 10px; }
                </style>
            </head>
            <body>
                <div class="login-container">
                    <h1>🔐 Connexion</h1>
                    <form method="POST">
                        <div class="form-group">
                            <label for="username">Nom d'utilisateur:</label>
                            <input type="text" id="username" name="username" required>
                        </div>
                        <div class="form-group">
                            <label for="password">Mot de passe:</label>
                            <input type="password" id="password" name="password" required>
                        </div>
                        <button type="submit" class="btn">Se connecter</button>
                    </form>
                    {% if error %}
                    <div class="error">{{ error }}</div>
                    {% endif %}
                </div>
            </body>
            </html>
            '''
    
    # POST: Traiter la connexion
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['user'] = username
        session.permanent = True
        print(f"✅ Utilisateur {username} connecté")
        return redirect(url_for('dashboard'))
    else:
        error = "Identifiants incorrects"
        try:
            return render_template('index.html', error=error)
        except:
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Connexion - Ben Tech Marketing</title>
                <style>...</style>
            </head>
            <body>
                <div class="login-container">
                    <h1>🔐 Connexion</h1>
                    <form method="POST">
                        <div class="form-group">
                            <label for="username">Nom d'utilisateur:</label>
                            <input type="text" id="username" name="username" required>
                        </div>
                        <div class="form-group">
                            <label for="password">Mot de passe:</label>
                            <input type="password" id="password" name="password" required>
                        </div>
                        <button type="submit" class="btn">Se connecter</button>
                    </form>
                    <div class="error">Identifiants incorrects</div>
                </div>
            </body>
            </html>
            '''

@app.route('/logout')
def logout():
    """Déconnexion"""
    session.pop('user', None)
    print("👋 Utilisateur déconnecté")
    return redirect(url_for('login_page'))

# ============================================
# ROUTES PRINCIPALES - UTILISANT interface/
# ============================================

@app.route('/')
def home():
    """Page d'accueil - Redirige vers la page de login"""
    return redirect(url_for('login_page'))

@app.route('/dashboard')
def dashboard():
    """Dashboard principal - Nécessite authentification"""
    # Récupérer les données pour le dashboard
    stats_ia = {}
    stats_publication = {}
    posts_recent = []
    
    if MODULES_STATUS['ia']:
        try:
            stats_ia = get_statistiques_globales()
        except:
            stats_ia = {'error': 'Données indisponibles'}
    
    if MODULES_STATUS['publier']:
        try:
            stats_publication = verifier_etat_publications()
        except:
            stats_publication = {'status': 'error'}
    
    # Récupérer les posts récents
    if MODULES_STATUS['google_sheets_db']:
        try:
            df = lire_historique_gsheets()
            if not df.empty:
                posts_recent = df.tail(5).to_dict('records')
        except:
            posts_recent = []
    
    try:
        # Passer les données à ton template dashboard.html existant
        return render_template('dashboard.html',
            system_status=AUTOMATIC_SYSTEM,
            verification_status=VERIFICATION_SYSTEM,
            stats_ia=stats_ia,
            stats_publication=stats_publication,
            posts_recent=posts_recent,
            modules_status=MODULES_STATUS,
            config={
                'google_sheet_name': GOOGLE_SHEET_NAME,
                'facebook_page_id': FACEBOOK_PAGE_ID,
                'openai_configured': bool(OPENAI_API_KEY),
                'unsplash_configured': bool(UNSPLASH_API_KEY)
            },
            now=datetime.datetime.now(),
            user=session.get('user', 'Admin')
        )
    except Exception as e:
        # Fallback si le template n'existe pas
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - Ben Tech</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                .card {{ border: 1px solid #ddd; padding: 20px; margin: 10px; border-radius: 10px; }}
                .status-active {{ color: green; font-weight: bold; }}
                .status-inactive {{ color: red; }}
                .header {{ display: flex; justify-content: space-between; align-items: center; }}
                .user-info {{ color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Dashboard Ben Tech</h1>
                <div class="user-info">
                    Connecté en tant que: {session.get('user', 'Admin')}
                    <a href="/logout" style="margin-left: 20px; color: #007bff;">Déconnexion</a>
                </div>
            </div>
            
            <div class="card">
                <h3>Statut système: <span class="{'status-active' if AUTOMATIC_SYSTEM['running'] else 'status-inactive'}">
                    {'ACTIF' if AUTOMATIC_SYSTEM['running'] else 'INACTIF'}
                </span></h3>
                <p>Générations aujourd'hui: {AUTOMATIC_SYSTEM['generated_today']}/3</p>
                
                <h4>Système de vérification: <span class="{'status-active' if VERIFICATION_SYSTEM['running'] else 'status-inactive'}">
                    {'ACTIF' if VERIFICATION_SYSTEM['running'] else 'INACTIF'}
                </span></h4>
                <p>Dernière vérification: {VERIFICATION_SYSTEM.get('last_check', 'Jamais')}</p>
                <p>Vérifications effectuées: {VERIFICATION_SYSTEM.get('check_count', 0)}</p>
                
                <button onclick="startSystem()">Démarrer tout</button>
                <button onclick="stopSystem()">Arrêter tout</button>
                <button onclick="startVerification()">Démarrer vérification</button>
                <button onclick="stopVerification()">Arrêter vérification</button>
            </div>
            <script>
                function startSystem() {{ 
                    fetch('/api/auto/start', {{method: 'POST'}})
                    .then(() => fetch('/api/verification/start', {{method: 'POST'}}))
                    .then(() => location.reload());
                }}
                function stopSystem() {{ 
                    fetch('/api/auto/stop', {{method: 'POST'}})
                    .then(() => fetch('/api/verification/stop', {{method: 'POST'}}))
                    .then(() => location.reload());
                }}
                function startVerification() {{ 
                    fetch('/api/verification/start', {{method: 'POST'}}).then(() => location.reload()); 
                }}
                function stopVerification() {{ 
                    fetch('/api/verification/stop', {{method: 'POST'}}).then(() => location.reload()); 
                }}
            </script>
        </body>
        </html>
        '''

# ============================================
# SERVIR LES FICHIERS STATIQUES DE interface/
# ============================================

@app.route('/interface/<path:filename>')
def serve_interface_files(filename):
    """Servir les fichiers statiques du dossier interface/"""
    return send_from_directory('interface', filename)

@app.route('/static/<path:filename>')
def serve_static_files(filename):
    """Servir les fichiers statiques (compatibilité)"""
    return send_from_directory('interface', filename)

# ============================================
# ROUTES API (inchangées de ta version)
# ============================================

@app.route('/api/status')
def api_status():
    """Statut complet du système"""
    # Tester la connexion Facebook
    facebook_status = {'status': 'non_configured'}
    if MODULES_STATUS['plateformes.facebook'] and FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN:
        try:
            facebook_status = test_connexion_facebook()
        except:
            facebook_status = {'status': 'error', 'message': 'Test échoué'}
    
    # Statut Google Sheets
    sheets_status = {'status': 'non_configured'}
    if MODULES_STATUS['google_sheets_db']:
        try:
            info = gsheets_db.get_sheet_info()
            sheets_status = info
        except:
            sheets_status = {'status': 'error'}
    
    return jsonify({
        'success': True,
        'system': {
            'automatic_generation': 'running' if AUTOMATIC_SYSTEM['running'] else 'stopped',
            'automatic_publication': 'running' if AUTOMATIC_SYSTEM['publication_running'] else 'stopped',
            'verification_system': 'running' if VERIFICATION_SYSTEM['running'] else 'stopped',
            'generation_count': AUTOMATIC_SYSTEM.get('generation_count', 0),
            'generated_today': AUTOMATIC_SYSTEM.get('generated_today', 0),
            'last_generation': AUTOMATIC_SYSTEM.get('last_generation'),
            'next_generation': AUTOMATIC_SYSTEM.get('next_generation'),
            'last_verification': VERIFICATION_SYSTEM.get('last_check'),
            'verification_count': VERIFICATION_SYSTEM.get('check_count', 0),
            'modules': MODULES_STATUS
        },
        'services': {
            'facebook': facebook_status,
            'google_sheets': sheets_status,
            'openai': 'configured' if OPENAI_API_KEY else 'not_configured',
            'unsplash': 'configured' if UNSPLASH_API_KEY else 'not_configured'
        },
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/generate', methods=['GET', 'POST'])
def api_generate():
    """Générer du contenu manuellement"""
    try:
        if MODULES_STATUS['ia']:
            contenu = generer_contenu()
            
            # Publier automatiquement si configuré
            if MODULES_STATUS['publier'] and request.args.get('publish', 'false').lower() == 'true':
                try:
                    publier_tous()
                except Exception as e:
                    print(f"⚠️ Publication automatique échouée: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Contenu généré avec succès',
                'data': contenu,
                'timestamp': datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Module IA non disponible'
            }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/publish', methods=['POST'])
def api_publish():
    """Publier manuellement les posts non publiés"""
    if not MODULES_STATUS['publier']:
        return jsonify({'success': False, 'message': 'Module publication non disponible'}), 503
    
    try:
        result = publier_tous()
        return jsonify({
            'success': True,
            'message': 'Publication manuelle lancée',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/auto/start', methods=['POST'])
def api_auto_start():
    """Démarrer le système automatique"""
    if demarrer_systeme_automatique():
        return jsonify({
            'success': True,
            'message': 'Système automatique démarré'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Impossible de démarrer le système automatique'
        }), 400

@app.route('/api/auto/stop', methods=['POST'])
def api_auto_stop():
    """Arrêter le système automatique"""
    if arreter_systeme_automatique():
        return jsonify({
            'success': True,
            'message': 'Système automatique arrêté'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Impossible d\'arrêter le système automatique'
        }), 400

@app.route('/api/auto/stats')
def api_auto_stats():
    """Statistiques du système automatique"""
    return jsonify({
        'success': True,
        'stats': {
            'running': AUTOMATIC_SYSTEM['running'],
            'publication_running': AUTOMATIC_SYSTEM['publication_running'],
            'generation_count': AUTOMATIC_SYSTEM.get('generation_count', 0),
            'generated_today': AUTOMATIC_SYSTEM.get('generated_today', 0),
            'daily_limit': AUTOMATIC_SYSTEM.get('daily_limit', 3),
            'last_generation': AUTOMATIC_SYSTEM.get('last_generation'),
            'next_generation': AUTOMATIC_SYSTEM.get('next_generation'),
            'last_reset': AUTOMATIC_SYSTEM.get('last_reset')
        }
    })

# ============================================
# ROUTES API POUR LE SYSTÈME DE VÉRIFICATION
# ============================================

@app.route('/api/verification/start', methods=['POST'])
def api_verification_start():
    """Démarrer le système de vérification"""
    if demarrer_verification_systeme():
        return jsonify({
            'success': True,
            'message': 'Système de vérification démarré'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Impossible de démarrer le système de vérification'
        }), 400

@app.route('/api/verification/stop', methods=['POST'])
def api_verification_stop():
    """Arrêter le système de vérification"""
    if arreter_verification_systeme():
        return jsonify({
            'success': True,
            'message': 'Système de vérification arrêté'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Impossible d\'arrêter le système de vérification'
        }), 400

@app.route('/api/verification/stats')
def api_verification_stats():
    """Statistiques du système de vérification"""
    return jsonify({
        'success': True,
        'stats': {
            'running': VERIFICATION_SYSTEM['running'],
            'check_interval': VERIFICATION_SYSTEM['check_interval'],
            'check_count': VERIFICATION_SYSTEM.get('check_count', 0),
            'last_check': VERIFICATION_SYSTEM.get('last_check'),
            'last_messages': VERIFICATION_SYSTEM.get('last_messages', [])
        }
    })

@app.route('/api/posts')
def api_posts():
    """Récupérer les posts"""
    try:
        if MODULES_STATUS['google_sheets_db']:
            df = lire_historique_gsheets()
            if not df.empty:
                posts = df.to_dict('records')
                return jsonify({
                    'success': True,
                    'posts': posts,
                    'count': len(posts)
                })
            else:
                return jsonify({
                    'success': True,
                    'posts': [],
                    'count': 0,
                    'message': 'Aucun post disponible'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Google Sheets non disponible'
            }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/stats')
def api_stats():
    """Statistiques complètes"""
    try:
        if MODULES_STATUS['ia']:
            stats = get_statistiques_globales()
            return jsonify({
                'success': True,
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Module IA non disponible'
            }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/audit')
def api_audit():
    """Audit complet des performances"""
    try:
        if MODULES_STATUS['ia']:
            audit = audit_complet_performance()
            return jsonify({
                'success': True,
                'audit': audit
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Module IA non disponible'
            }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/comments/process', methods=['POST'])
def api_comments_process():
    """Traiter les anciens commentaires"""
    if not MODULES_STATUS['publier']:
        return jsonify({'success': False, 'message': 'Module publication non disponible'}), 503
    
    try:
        result = traiter_anciens_commentaires_manuellement()
        return jsonify({
            'success': True,
            'message': 'Traitement des commentaires lancé',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/config')
def api_config():
    """Afficher la configuration"""
    return jsonify({
        'success': True,
        'config': {
            'openai_model': OPENAI_MODEL,
            'google_sheet_name': GOOGLE_SHEET_NAME,
            'google_sheet_id': GOOGLE_SHEET_ID if GOOGLE_SHEET_ID else 'Non défini',
            'facebook_page_id': FACEBOOK_PAGE_ID if FACEBOOK_PAGE_ID else 'Non défini',
            'your_email': YOUR_EMAIL if YOUR_EMAIL else 'Non défini',
            'automatic_schedule': '9h, 14h, 19h (3x/jour)',
            'daily_limit': 3,
            'verification_interval': f'{VERIFICATION_SYSTEM["check_interval"]} secondes',
            'port': PORT,
            'debug': DEBUG
        },
        'modules': MODULES_STATUS
    })

@app.route('/api/health')
def api_health():
    """Vérification de santé de l'API"""
    health_status = {
        'status': 'healthy',
        'service': 'Agent IA Ben Tech Marketing',
        'version': '3.0.0',
        'timestamp': datetime.datetime.now().isoformat(),
        'components': {
            'flask': 'running',
            'automatic_generation': 'running' if AUTOMATIC_SYSTEM['running'] else 'stopped',
            'verification_system': 'running' if VERIFICATION_SYSTEM['running'] else 'stopped',
            'modules': {k: 'loaded' if v else 'missing' for k, v in MODULES_STATUS.items()}
        }
    }
    
    # Vérifier les services externes
    if OPENAI_API_KEY:
        health_status['components']['openai'] = 'configured'
    else:
        health_status['components']['openai'] = 'not_configured'
        health_status['status'] = 'degraded'
    
    if FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN:
        health_status['components']['facebook'] = 'configured'
    else:
        health_status['components']['facebook'] = 'not_configured'
    
    return jsonify(health_status)

# ============================================
# UTILITAIRES
# ============================================

@app.route('/api/logs/<log_type>')
def api_logs(log_type):
    """Lire les logs"""
    valid_logs = ['auto_generation', 'auto_generation_errors', 'system', 'publications', 'system_check', 'system_check_errors']
    
    if log_type not in valid_logs:
        return jsonify({'success': False, 'message': 'Type de log invalide'}), 400
    
    log_file = f'logs/{log_type}.log'
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()[-100:]  # 100 dernières lignes
        else:
            logs = [f"Fichier {log_file} non trouvé"]
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/reset/counter', methods=['POST'])
def api_reset_counter():
    """Réinitialiser le compteur quotidien"""
    AUTOMATIC_SYSTEM['generated_today'] = 0
    AUTOMATIC_SYSTEM['last_reset'] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    return jsonify({
        'success': True,
        'message': 'Compteur quotidien réinitialisé',
        'generated_today': 0
    })

# ============================================
# GESTION D'ERREURS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Route non trouvée'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'message': 'Erreur interne du serveur'}), 500

# ============================================
# DÉMARRAGE DE L'APPLICATION
# ============================================

def init_application():
    """Initialiser l'application"""
    print("=" * 70)
    print("🤖 AGENT IA BEN TECH MARKETING - VERSION FINALE AVEC AUTH")
    print("=" * 70)
    print(f"📅 Démarrage: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL: http://localhost:{PORT}")
    print(f"🔐 Login: http://localhost:{PORT}/login")
    print(f"👤 Utilisateur: {ADMIN_USERNAME}")
    print(f"⚡ Mode auto: {'ACTIVÉ' if DEBUG else 'DÉSACTIVÉ'}")
    print(f"🎯 Génération: 3x/jour à 9h, 14h, 19h")
    print(f"🔍 Vérification: toutes les {VERIFICATION_SYSTEM['check_interval']}s")
    print("-" * 70)
    print("📦 MODULES CHARGÉS:")
    for module, status in MODULES_STATUS.items():
        print(f"  • {module}: {'✅' if status else '❌'}")
    print("-" * 70)
    print("🔧 CONFIGURATION:")
    print(f"  • OpenAI: {'✅' if OPENAI_API_KEY else '❌'} {OPENAI_MODEL}")
    print(f"  • Google Sheets: {'✅' if GOOGLE_CREDENTIALS_JSON else '❌'} {GOOGLE_SHEET_NAME}")
    print(f"  • Facebook: {'✅' if FACEBOOK_PAGE_ID else '❌'}")
    print(f"  • Unsplash: {'✅' if UNSPLASH_API_KEY else '❌'}")
    print("-" * 70)
    print("📋 ENDPOINTS PRINCIPAUX:")
    print(f"  • http://localhost:{PORT}/login - Page de connexion")
    print(f"  • http://localhost:{PORT}/dashboard - Dashboard (après login)")
    print(f"  • http://localhost:{PORT}/api/status - Statut complet")
    print(f"  • http://localhost:{PORT}/api/verification/stats - Statut vérification")
    print(f"  • http://localhost:{PORT}/api/health - Santé système")
    print("=" * 70)
    
    # Créer les dossiers nécessaires
    os.makedirs('logs', exist_ok=True)
    os.makedirs('images_posts', exist_ok=True)
    
    # Vérifier que le dossier interface existe
    if not os.path.exists('interface'):
        print("⚠️ Dossier 'interface' non trouvé - création...")
        os.makedirs('interface', exist_ok=True)
    
    # Démarrer automatiquement en mode debug
    if DEBUG:
        print("🔍 Démarrage automatique du système de vérification...")
        demarrer_verification_systeme()
        
        if not AUTOMATIC_SYSTEM['running']:
            print("🚀 Démarrage automatique du système...")
            demarrer_systeme_automatique()

if __name__ == '__main__':
    # Initialiser l'application
    init_application()
    
    # Démarrer le serveur Flask
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        threaded=True,
        use_reloader=False  # Important pour éviter les doubles threads
    )