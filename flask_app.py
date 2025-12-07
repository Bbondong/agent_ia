# flask_app.py - Agent IA Ben Tech Marketing - COMPLET AVEC .ENV
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
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

# 1. Ajouter le chemin des modules
current_dir = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.join(current_dir, 'modules')
if modules_path not in sys.path:
    sys.path.append(modules_path)

# 2. Configurer les variables d'environnement pour les modules
if GOOGLE_CREDENTIALS_JSON:
    os.environ['GOOGLE_CREDENTIALS_JSON'] = GOOGLE_CREDENTIALS_JSON
if GOOGLE_SHEET_ID:
    os.environ['GOOGLE_SHEET_ID'] = GOOGLE_SHEET_ID
os.environ['GOOGLE_SHEET_NAME'] = GOOGLE_SHEET_NAME

# ============================================
# APPLICATION FLASK
# ============================================

app = Flask(__name__)
app.secret_key = 'agent-ia-ben-tech-secret-key-' + os.urandom(24).hex()

# Variables globales pour le système automatique
AUTOMATIC_SYSTEM = {
    'running': False,
    'schedule_thread': None,
    'last_generation': None,
    'generation_count': 0,
    'next_generation': None,
    'generated_today': 0,
    'daily_limit': 3
}

# ============================================
# SYSTÈME AUTOMATIQUE - GÉNÉRATION 3 FOIS/JOUR
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
        try:
            from modules.ia import generer_contenu
        except ImportError as e:
            print(f"❌ Erreur importation module IA: {e}")
            # Fallback: créer un contenu basique
            contenu = {
                'titre': f'Contenu automatique {datetime.datetime.now().strftime("%H:%M")}',
                'theme': 'Automatique',
                'service': 'Service généré',
                'texte_marketing': 'Ce contenu a été généré automatiquement par le système.',
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            # Générer le contenu
            contenu = generer_contenu()
        
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
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        with open('logs/auto_generation.log', 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"✅ Contenu généré: {contenu.get('titre', 'Sans titre')}")
        print(f"📊 Aujourd'hui: {AUTOMATIC_SYSTEM['generated_today']}/{AUTOMATIC_SYSTEM['daily_limit']}")
        
        return contenu
        
    except Exception as e:
        error_msg = f"[{datetime.datetime.now()}] ❌ Erreur génération automatique: {str(e)}\n"
        print(error_msg)
        
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        with open('logs/auto_generation_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
        return None

def planifier_generations():
    """Planifie les générations automatiques 3 fois par jour"""
    # Heures de génération : 9h, 14h, 19h (ajuste selon ton fuseau horaire)
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
        # Créer le dossier logs si nécessaire
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
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
    print("🛑 Système automatique arrêté")
    return True

# ============================================
# ROUTES PRINCIPALES
# ============================================

@app.route('/')
def home():
    """Page d'accueil"""
    system_status = "ACTIF" if AUTOMATIC_SYSTEM['running'] else "INACTIF"
    next_gen = AUTOMATIC_SYSTEM.get('next_generation', 'Non planifié')
    last_gen = AUTOMATIC_SYSTEM.get('last_generation', 'Aucune')
    today_count = AUTOMATIC_SYSTEM.get('generated_today', 0)
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 Agent IA Ben Tech</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            h1 {{
                color: #667eea;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .status-box {{
                display: inline-block;
                padding: 10px 20px;
                border-radius: 50px;
                font-weight: bold;
                margin: 10px;
            }}
            .status-active {{ background: #d4edda; color: #155724; }}
            .status-inactive {{ background: #f8d7da; color: #721c24; }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 15px;
                text-align: center;
                border-left: 5px solid #667eea;
            }}
            .stat-value {{
                font-size: 2em;
                font-weight: bold;
                color: #764ba2;
                margin: 10px 0;
            }}
            .btn-group {{
                display: flex;
                gap: 10px;
                justify-content: center;
                margin: 30px 0;
                flex-wrap: wrap;
            }}
            .btn {{
                padding: 15px 30px;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
                display: inline-flex;
                align-items: center;
                gap: 10px;
            }}
            .btn-start {{ background: #28a745; color: white; }}
            .btn-stop {{ background: #dc3545; color: white; }}
            .btn-generate {{ background: #17a2b8; color: white; }}
            .btn:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
            .endpoints {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 15px;
                margin-top: 30px;
            }}
            .endpoint-list {{
                list-style: none;
                padding: 0;
            }}
            .endpoint-list li {{
                padding: 10px;
                border-bottom: 1px solid #dee2e6;
            }}
            .endpoint-list li:last-child {{ border-bottom: none; }}
            .config-info {{
                background: #fff3cd;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 5px solid #ffc107;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Agent IA Ben Tech Marketing</h1>
                <div class="status-box {'status-active' if AUTOMATIC_SYSTEM['running'] else 'status-inactive'}">
                    Système automatique: {system_status}
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📊 Aujourd'hui</h3>
                    <div class="stat-value">{today_count}/3</div>
                    <p>Générations quotidiennes</p>
                </div>
                <div class="stat-card">
                    <h3>⏰ Prochaine</h3>
                    <div class="stat-value">{next_gen.split()[1] if next_gen != 'Non planifié' else 'N/A'}</div>
                    <p>{next_gen.split()[0] if next_gen != 'Non planifié' else 'Non planifié'}</p>
                </div>
                <div class="stat-card">
                    <h3>📅 Dernière</h3>
                    <div class="stat-value">{last_gen.split()[1] if last_gen != 'Aucune' else 'N/A'}</div>
                    <p>{last_gen.split()[0] if last_gen != 'Aucune' else 'Aucune génération'}</p>
                </div>
                <div class="stat-card">
                    <h3>🎯 Total</h3>
                    <div class="stat-value">{AUTOMATIC_SYSTEM.get('generation_count', 0)}</div>
                    <p>Générations totales</p>
                </div>
            </div>
            
            <div class="btn-group">
                <button class="btn btn-start" onclick="startSystem()" {'disabled' if AUTOMATIC_SYSTEM['running'] else ''}>
                    ▶️ Démarrer Auto
                </button>
                <button class="btn btn-stop" onclick="stopSystem()" {'disabled' if not AUTOMATIC_SYSTEM['running'] else ''}>
                    ⏹️ Arrêter Auto
                </button>
                <button class="btn btn-generate" onclick="generateNow()">
                    ⚡ Générer Maintenant
                </button>
            </div>
            
            <div class="config-info">
                <h3>🔧 Configuration Actuelle</h3>
                <p><strong>Google Sheets:</strong> {GOOGLE_SHEET_NAME}</p>
                <p><strong>Sheet ID:</strong> {GOOGLE_SHEET_ID if GOOGLE_SHEET_ID else 'Non défini'}</p>
                <p><strong>OpenAI:</strong> {'✅ Configuré' if OPENAI_API_KEY else '❌ Non configuré'}</p>
                <p><strong>Facebook:</strong> {'✅ Page configurée' if FACEBOOK_PAGE_ID else '❌ Non configuré'}</p>
                <p><strong>Unsplash:</strong> {'✅ Configuré' if UNSPLASH_API_KEY else '❌ Non configuré'}</p>
            </div>
            
            <div class="endpoints">
                <h3>🔌 API Endpoints</h3>
                <ul class="endpoint-list">
                    <li><a href="/api/status" target="_blank">/api/status</a> - Statut du système</li>
                    <li><a href="/api/generate" target="_blank">/api/generate</a> - Générer manuellement</li>
                    <li><a href="/api/auto/start" target="_blank">/api/auto/start</a> - Démarrer automatique</li>
                    <li><a href="/api/auto/stop" target="_blank">/api/auto/stop</a> - Arrêter automatique</li>
                    <li><a href="/api/auto/stats" target="_blank">/api/auto/stats</a> - Statistiques auto</li>
                    <li><a href="/api/config" target="_blank">/api/config</a> - Configuration</li>
                    <li><a href="/api/health" target="_blank">/api/health</a> - Santé API</li>
                </ul>
            </div>
        </div>
        
        <script>
            function startSystem() {{
                fetch('/api/auto/start', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        alert(data.message);
                        location.reload();
                    }});
            }}
            
            function stopSystem() {{
                fetch('/api/auto/stop', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        alert(data.message);
                        location.reload();
                    }});
            }}
            
            function generateNow() {{
                fetch('/api/generate/now', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        alert(data.message);
                        location.reload();
                    }});
            }}
            
            // Actualiser toutes les 30 secondes
            setInterval(() => {{
                fetch('/api/auto/stats')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            document.querySelector('.stat-card:nth-child(1) .stat-value').textContent = 
                                data.stats.generated_today + '/3';
                            document.querySelector('.stat-card:nth-child(2) .stat-value').textContent = 
                                data.stats.next_generation ? data.stats.next_generation.split()[1] : 'N/A';
                            document.querySelector('.stat-card:nth-child(3) .stat-value').textContent = 
                                data.stats.last_generation ? data.stats.last_generation.split()[1] : 'N/A';
                        }}
                    }});
            }}, 30000);
        </script>
    </body>
    </html>
    '''

# ============================================
# ROUTES API
# ============================================

@app.route('/api/status')
def api_status():
    """Statut complet du système"""
    config_status = {
        'openai_configured': bool(OPENAI_API_KEY),
        'facebook_configured': bool(FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN),
        'unsplash_configured': bool(UNSPLASH_API_KEY),
        'google_sheets_configured': bool(GOOGLE_CREDENTIALS_JSON or os.path.exists('credentials.json')),
        'sheet_id_configured': bool(GOOGLE_SHEET_ID)
    }
    
    return jsonify({
        'success': True,
        'system': {
            'automatic_system': 'running' if AUTOMATIC_SYSTEM['running'] else 'stopped',
            'generation_count': AUTOMATIC_SYSTEM.get('generation_count', 0),
            'generated_today': AUTOMATIC_SYSTEM.get('generated_today', 0),
            'daily_limit': AUTOMATIC_SYSTEM.get('daily_limit', 3),
            'last_generation': AUTOMATIC_SYSTEM.get('last_generation'),
            'next_generation': AUTOMATIC_SYSTEM.get('next_generation'),
            'last_reset': AUTOMATIC_SYSTEM.get('last_reset')
        },
        'config': config_status,
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/generate', methods=['GET', 'POST'])
def api_generate():
    """Générer du contenu manuellement"""
    try:
        from modules.ia import generer_contenu
        contenu = generer_contenu()
        
        return jsonify({
            'success': True,
            'message': 'Contenu généré avec succès',
            'data': contenu,
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/generate/now', methods=['POST'])
def api_generate_now():
    """Générer du contenu immédiatement (manuel)"""
    contenu = generer_contenu_automatique()
    
    if contenu:
        return jsonify({
            'success': True,
            'message': f'Contenu généré: {contenu.get("titre", "Sans titre")}',
            'data': contenu
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Échec de la génération ou limite quotidienne atteinte'
        }), 400

@app.route('/api/auto/start', methods=['POST'])
def api_auto_start():
    """Démarrer le système automatique"""
    if demarrer_systeme_automatique():
        return jsonify({
            'success': True,
            'message': 'Système automatique démarré - Génération 3x/jour à 9h, 14h, 19h'
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
            'generation_count': AUTOMATIC_SYSTEM.get('generation_count', 0),
            'generated_today': AUTOMATIC_SYSTEM.get('generated_today', 0),
            'daily_limit': AUTOMATIC_SYSTEM.get('daily_limit', 3),
            'last_generation': AUTOMATIC_SYSTEM.get('last_generation'),
            'next_generation': AUTOMATIC_SYSTEM.get('next_generation'),
            'last_reset': AUTOMATIC_SYSTEM.get('last_reset')
        }
    })

@app.route('/api/config')
def api_config():
    """Afficher la configuration"""
    return jsonify({
        'success': True,
        'config': {
            'openai_model': OPENAI_MODEL,
            'google_sheet_name': GOOGLE_SHEET_NAME,
            'google_sheet_id': GOOGLE_SHEET_ID,
            'facebook_page_id': FACEBOOK_PAGE_ID,
            'your_email': YOUR_EMAIL,
            'automatic_schedule': '9h, 14h, 19h (3x/jour)',
            'daily_limit': 3
        },
        'status': {
            'automatic_system': 'running' if AUTOMATIC_SYSTEM['running'] else 'stopped',
            'openai_configured': bool(OPENAI_API_KEY),
            'facebook_configured': bool(FACEBOOK_PAGE_ID),
            'unsplash_configured': bool(UNSPLASH_API_KEY),
            'google_sheets_configured': bool(GOOGLE_CREDENTIALS_JSON)
        }
    })

@app.route('/api/health')
def api_health():
    """Vérification de santé de l'API"""
    return jsonify({
        'status': 'healthy',
        'service': 'Agent IA Ben Tech Marketing',
        'version': '2.0.0',
        'automatic_system': AUTOMATIC_SYSTEM['running'],
        'timestamp': datetime.datetime.now().isoformat(),
        'uptime': 'N/A'  # Tu peux ajouter un calcul d'uptime si tu veux
    })

# ============================================
# UTILITAIRES
# ============================================

@app.route('/api/logs/auto')
def api_logs_auto():
    """Lire les logs de génération automatique"""
    try:
        if os.path.exists('logs/auto_generation.log'):
            with open('logs/auto_generation.log', 'r', encoding='utf-8') as f:
                logs = f.readlines()[-50:]  # 50 dernières lignes
        else:
            logs = ["Aucun log disponible"]
        
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
    """Réinitialiser le compteur quotidien (admin)"""
    AUTOMATIC_SYSTEM['generated_today'] = 0
    AUTOMATIC_SYSTEM['last_reset'] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    return jsonify({
        'success': True,
        'message': 'Compteur quotidien réinitialisé',
        'generated_today': 0
    })

# ============================================
# DÉMARRAGE DE L'APPLICATION
# ============================================

def init_application():
    """Initialiser l'application"""
    print("=" * 60)
    print("🤖 Agent IA Ben Tech Marketing")
    print("=" * 60)
    print(f"📅 Démarrage: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL: http://localhost:{PORT}")
    print(f"⚡ Mode auto: {'ACTIVÉ au démarrage' if DEBUG else 'DÉSACTIVÉ'}")
    print(f"🎯 Génération: 3x/jour à 9h, 14h, 19h")
    print("-" * 60)
    print("🔧 Configuration:")
    print(f"  • OpenAI: {'✅' if OPENAI_API_KEY else '❌'} {OPENAI_MODEL}")
    print(f"  • Google Sheets: {'✅' if GOOGLE_CREDENTIALS_JSON else '❌'} {GOOGLE_SHEET_NAME}")
    print(f"  • Facebook: {'✅' if FACEBOOK_PAGE_ID else '❌'}")
    print(f"  • Unsplash: {'✅' if UNSPLASH_API_KEY else '❌'}")
    print("-" * 60)
    print("📋 Endpoints:")
    print(f"  • http://localhost:{PORT}/ - Dashboard")
    print(f"  • http://localhost:{PORT}/api/status - Statut")
    print(f"  • http://localhost:{PORT}/api/health - Santé")
    print("=" * 60)
    
    # Démarrer automatiquement en mode debug
    if DEBUG and not AUTOMATIC_SYSTEM['running']:
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
        threaded=True
    )