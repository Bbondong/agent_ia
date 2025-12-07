# modules/google_sheets_db.py
"""
Module pour utiliser Google Sheets comme base de données
Compatible Heroku et local

Problèmes courants et solutions :

1. "APIError: 403 - Insufficient permissions"
   - Vérifiez que le service account a accès au sheet
   - Partager le sheet avec l'email du service account

2. "SpreadsheetNotFound"
   - Vérifiez le GOOGLE_SHEET_ID
   - Vérifiez les permissions du service account

3. Lenteur des requêtes
   - Implémentez un cache local
   - Utilisez batch updates pour multiples écritures
"""

import os
import pandas as pd
from typing import Dict, List, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import sys
import time
from functools import wraps

# Configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Colonnes du sheet (mêmes que votre Excel)
COLUMNS = [
    "titre", "theme", "service", "style",
    "texte_marketing", "script_video", "reaction_positive", 
    "reaction_negative", "taux_conversion_estime", "publication_effective",
    "nom_plateforme", "suggestion", "date", "score_performance_final",
    "image_path", "image_auteur", "type_publication"
]

def retry_on_failure(max_retries=3, delay=1):
    """Décorateur pour réessayer en cas d'échec API"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"⚠️ Tentative {attempt + 1}/{max_retries} échouée: {e}")
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator

class GoogleSheetsDB:
    """Classe pour gérer Google Sheets comme DB"""
    
    def __init__(self):
        self.client = None
        self.sheet = None
        self.worksheet = None
        self.initialized = False
        self._init_client()
    
    def _init_client(self):
        """Initialise le client Google Sheets"""
        try:
            # Mode Heroku : credentials dans les variables d'environnement
            if 'GOOGLE_CREDENTIALS_JSON' in os.environ:
                creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
                if creds_json:
                    creds_dict = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                else:
                    print("⚠️ GOOGLE_CREDENTIALS_JSON vide")
                    return
            
            # Mode local : fichier credentials.json
            elif os.path.exists('credentials.json'):
                creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            
            else:
                print("ℹ️ Aucune configuration Google Sheets trouvée - mode local uniquement")
                return
            
            self.client = gspread.authorize(creds)
            print("✅ Client Google Sheets initialisé")
            
        except Exception as e:
            print(f"❌ Erreur initialisation Google Sheets: {e}")
            self.client = None
    
    def get_or_create_sheet(self, sheet_name: str = None, sheet_id: str = None):
        """Récupère ou crée le sheet"""
        if not self.client:
            print("❌ Client Google Sheets non initialisé")
            return None
        
        try:
            sheet_name = sheet_name or os.environ.get('GOOGLE_SHEET_NAME', 'Agent IA Ben Tech - Historique')
            sheet_id = sheet_id or os.environ.get('GOOGLE_SHEET_ID')
            
            # Essayer d'ouvrir par ID si fourni
            if sheet_id and sheet_id != "YOUR_SHEET_ID":
                self.sheet = self.client.open_by_key(sheet_id)
                print(f"✅ Sheet ouvert par ID: {self.sheet.title}")
            
            else:
                # Chercher par nom
                try:
                    self.sheet = self.client.open(sheet_name)
                    print(f"✅ Sheet trouvé par nom: {self.sheet.title}")
                except gspread.SpreadsheetNotFound:
                    # Créer un nouveau sheet
                    print(f"📝 Création d'un nouveau sheet: {sheet_name}")
                    self.sheet = self.client.create(sheet_name)
                    
                    # Partager avec votre email (optionnel)
                    your_email = os.environ.get('YOUR_EMAIL')
                    if your_email:
                        self.sheet.share(your_email, perm_type='user', role='writer')
                    
                    print(f"✅ Nouveau sheet créé: {self.sheet.title}")
                    print(f"📊 Sheet ID: {self.sheet.id}")
                    print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{self.sheet.id}")
            
            # Utiliser la première feuille
            self.worksheet = self.sheet.sheet1
            
            # Vérifier/initialiser les en-têtes
            headers = self.worksheet.row_values(1)
            if not headers or len(headers) < len(COLUMNS):
                print("📋 Initialisation des colonnes...")
                self.worksheet.update('A1:R1', [COLUMNS])
                self.worksheet.format('A1:R1', {'textFormat': {'bold': True}})
                print("✅ Colonnes initialisées")
            
            self.initialized = True
            return self.sheet
            
        except Exception as e:
            print(f"❌ Erreur lors de l'accès au sheet: {e}")
            return None
    
    @retry_on_failure(max_retries=3, delay=2)
    def lire_historique(self) -> pd.DataFrame:
        """Lit l'historique depuis Google Sheets"""
        if not self.initialized:
            self.get_or_create_sheet()
        
        if not self.initialized or not self.worksheet:
            print("⚠️ Google Sheets non disponible, retour DataFrame vide")
            return pd.DataFrame(columns=COLUMNS)
        
        try:
            # Récupérer toutes les données (sauf la ligne d'en-tête)
            data = self.worksheet.get_all_records()
            
            if not data:
                print("📊 Sheet vide, aucune donnée")
                return pd.DataFrame(columns=COLUMNS)
            
            df = pd.DataFrame(data)
            
            # S'assurer que toutes les colonnes existent
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            
            print(f"✅ {len(df)} posts chargés depuis Google Sheets")
            return df[COLUMNS]  # Retourner dans le bon ordre
            
        except Exception as e:
            print(f"❌ Erreur lecture Google Sheets: {e}")
            return pd.DataFrame(columns=COLUMNS)
    
    def valider_post(self, post: Dict[str, Any]) -> List[str]:
        """Valide les données d'un post avant sauvegarde"""
        erreurs = []
        
        # Champs obligatoires
        obligatoires = ['titre', 'theme', 'service']
        for champ in obligatoires:
            if not post.get(champ):
                erreurs.append(f"Le champ '{champ}' est obligatoire")
        
        # Validation des types
        if 'taux_conversion_estime' in post and post['taux_conversion_estime']:
            try:
                taux = float(post['taux_conversion_estime'])
                if not 0 <= taux <= 100:
                    erreurs.append("Le taux de conversion doit être entre 0 et 100")
            except (ValueError, TypeError):
                erreurs.append("Le taux de conversion doit être un nombre")
        
        # Validation de la date si présente
        if 'date' in post and post['date']:
            try:
                if isinstance(post['date'], str):
                    datetime.strptime(post['date'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                erreurs.append("Format de date invalide. Utilisez 'YYYY-MM-DD HH:MM:SS'")
        
        return erreurs
    
    @retry_on_failure(max_retries=3, delay=2)
    def sauvegarder_post(self, post: Dict[str, Any]) -> bool:
        """Sauvegarde un post dans Google Sheets"""
        # Validation des données
        erreurs = self.valider_post(post)
        if erreurs:
            print(f"❌ Erreurs de validation: {erreurs}")
            return False
        
        if not self.initialized:
            self.get_or_create_sheet()
        
        if not self.initialized or not self.worksheet:
            print("⚠️ Google Sheets non disponible, sauvegarde locale uniquement")
            return False
        
        try:
            # Formatage automatique des dates
            if 'date' in post and isinstance(post['date'], datetime):
                post['date'] = post['date'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Préparer la ligne dans l'ordre des colonnes
            row = []
            for col in COLUMNS:
                value = post.get(col, '')
                
                # Gérer les valeurs None
                if value is None:
                    value = ''
                
                # Limiter la longueur des textes longs
                if isinstance(value, str) and len(value) > 50000:
                    value = value[:50000] + "... [truncated]"
                
                row.append(value)
            
            # Ajouter la nouvelle ligne
            self.worksheet.append_row(row)
            
            print(f"✅ Post sauvegardé dans Google Sheets: {post.get('titre', 'N/A')}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde Google Sheets: {e}")
            return False
    
    @retry_on_failure(max_retries=3, delay=2)
    def mettre_a_jour_post(self, index: int, updates: Dict[str, Any]) -> bool:
        """Met à jour un post existant (par index de ligne)"""
        if not self.initialized or not self.worksheet:
            return False
        
        try:
            # Validation partielle des updates
            if 'taux_conversion_estime' in updates and updates['taux_conversion_estime']:
                try:
                    taux = float(updates['taux_conversion_estime'])
                    if not 0 <= taux <= 100:
                        print("❌ Le taux de conversion doit être entre 0 et 100")
                        return False
                except (ValueError, TypeError):
                    print("❌ Le taux de conversion doit être un nombre")
                    return False
            
            # +2 car: ligne 1 = en-têtes, index 0-based => +2
            row_num = index + 2
            
            # Mettre à jour les cellules
            for key, value in updates.items():
                if key in COLUMNS:
                    col_index = COLUMNS.index(key) + 1  # +1 car index 1-based
                    self.worksheet.update_cell(row_num, col_index, value)
            
            print(f"✅ Post ligne {row_num} mis à jour")
            return True
            
        except Exception as e:
            print(f"❌ Erreur mise à jour Google Sheets: {e}")
            return False
    
    def rechercher_posts(self, criteres: Dict[str, Any]) -> pd.DataFrame:
        """Recherche des posts selon des critères"""
        df = self.lire_historique()
        
        if df.empty:
            return df
        
        for champ, valeur in criteres.items():
            if champ in df.columns and valeur:
                if isinstance(valeur, str):
                    # Recherche textuelle insensible à la casse
                    df = df[df[champ].astype(str).str.contains(valeur, case=False, na=False)]
                else:
                    # Recherche exacte pour les autres types
                    df = df[df[champ] == valeur]
        
        print(f"🔍 {len(df)} posts trouvés pour les critères: {criteres}")
        return df
    
    @retry_on_failure(max_retries=2, delay=1)
    def compter_posts(self) -> int:
        """Compte le nombre de posts"""
        if not self.initialized:
            self.get_or_create_sheet()
        
        if not self.initialized or not self.worksheet:
            return 0
        
        try:
            # Nombre de lignes de données (sans l'en-tête)
            values = self.worksheet.get_all_values()
            count = max(0, len(values) - 1)
            print(f"📊 {count} posts dans la base de données")
            return count
        except Exception as e:
            print(f"⚠️ Erreur lors du comptage: {e}")
            return 0
    
    def supprimer_post(self, index: int) -> bool:
        """Supprime un post par son index"""
        if not self.initialized or not self.worksheet:
            return False
        
        try:
            # +2 car: ligne 1 = en-têtes, index 0-based => +2
            row_num = index + 2
            
            # Supprimer la ligne
            self.worksheet.delete_rows(row_num)
            
            print(f"🗑️ Post ligne {row_num} supprimé")
            return True
            
        except Exception as e:
            print(f"❌ Erreur suppression Google Sheets: {e}")
            return False
    
    def vider_base(self) -> bool:
        """Vide toute la base de données (conserve les en-têtes)"""
        if not self.initialized or not self.worksheet:
            return False
        
        try:
            # Compter le nombre de lignes de données
            count = self.compter_posts()
            if count == 0:
                print("📊 Base déjà vide")
                return True
            
            # Supprimer toutes les lignes sauf l'en-tête
            self.worksheet.delete_rows(2, count + 1)
            
            print(f"🗑️ Base vidée: {count} posts supprimés")
            return True
            
        except Exception as e:
            print(f"❌ Erreur vidage base: {e}")
            return False

# Instance globale
gsheets_db = GoogleSheetsDB()

# Fonctions d'interface (pour compatibilité)
def lire_historique_gsheets() -> pd.DataFrame:
    return gsheets_db.lire_historique()

def sauvegarder_post_gsheets(post: Dict[str, Any]) -> bool:
    return gsheets_db.sauvegarder_post(post)

def mettre_a_jour_post_gsheets(index: int, updates: Dict[str, Any]) -> bool:
    return gsheets_db.mettre_a_jour_post(index, updates)

def compter_posts_gsheets() -> int:
    return gsheets_db.compter_posts()

def rechercher_posts_gsheets(criteres: Dict[str, Any]) -> pd.DataFrame:
    return gsheets_db.rechercher_posts(criteres)

def valider_post_gsheets(post: Dict[str, Any]) -> List[str]:
    return gsheets_db.valider_post(post)

def supprimer_post_gsheets(index: int) -> bool:
    return gsheets_db.supprimer_post(index)

def vider_base_gsheets() -> bool:
    return gsheets_db.vider_base()