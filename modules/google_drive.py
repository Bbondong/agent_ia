# modules/google_drive.py - Intégration Google Drive
import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import requests
from datetime import datetime
import mimetypes

class GoogleDriveManager:
    def __init__(self, credentials_path=None, folder_id=None):
        """
        Initialise le gestionnaire Google Drive
        """
        self.credentials_path = credentials_path
        self.folder_id = folder_id
        self.service = None
        self.initialize_service()
    
    def initialize_service(self):
        """
        Initialise le service Google Drive
        """
        try:
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                print("⚠️ Fichier credentials Google Drive non trouvé")
                self.service = None
                return
            
            # Charger les credentials
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            
            # Créer le service
            self.service = build('drive', 'v3', credentials=credentials)
            print("✅ Service Google Drive initialisé")
            
        except Exception as e:
            print(f"❌ Erreur initialisation Google Drive: {e}")
            self.service = None
    
    def upload_image_from_url(self, image_url: str, filename: str, description: str = "") -> dict:
        """
        Télécharge une image depuis une URL et l'upload vers Google Drive
        
        Args:
            image_url: URL de l'image
            filename: Nom du fichier
            description: Description optionnelle
            
        Returns:
            dict: Informations sur le fichier uploadé ou None en cas d'erreur
        """
        if not self.service:
            print("❌ Service Google Drive non disponible")
            return None
        
        try:
            # Télécharger l'image depuis l'URL
            print(f"📥 Téléchargement depuis: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Créer un objet fichier en mémoire
            file_content = io.BytesIO(response.content)
            file_content.seek(0)
            
            # Déterminer le type MIME
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'image/jpeg'
            
            # Métadonnées du fichier
            file_metadata = {
                'name': filename,
                'description': description,
                'parents': [self.folder_id] if self.folder_id else []
            }
            
            # Media pour l'upload
            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload vers Google Drive
            print(f"⬆️ Upload vers Google Drive: {filename}")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink, size'
            ).execute()
            
            print(f"✅ Image uploadée vers Google Drive: {file.get('name')}")
            print(f"🔗 Lien: {file.get('webViewLink')}")
            
            # Données à retourner
            file_info = {
                'id': file.get('id'),
                'name': file.get('name'),
                'webViewLink': file.get('webViewLink'),
                'webContentLink': file.get('webContentLink'),
                'size': file.get('size'),
                'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return file_info
            
        except HttpError as e:
            print(f"❌ Erreur Google Drive API: {e}")
            return None
        except Exception as e:
            print(f"❌ Erreur upload image: {e}")
            return None
    
    def create_public_link(self, file_id: str) -> str:
        """
        Crée un lien public pour un fichier
        
        Args:
            file_id: ID du fichier Google Drive
            
        Returns:
            str: URL publique ou None
        """
        if not self.service:
            return None
        
        try:
            # Permission pour rendre public
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            # Récupérer le lien
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            print(f"❌ Erreur création lien public: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Supprime un fichier de Google Drive
        """
        if not self.service:
            return False
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            print(f"✅ Fichier {file_id} supprimé de Google Drive")
            return True
        except Exception as e:
            print(f"❌ Erreur suppression fichier: {e}")
            return False

# Instance globale
drive_manager = None

def initialize_drive_manager(credentials_path=None, folder_id=None):
    """
    Initialise le gestionnaire Google Drive globalement
    """
    global drive_manager
    drive_manager = GoogleDriveManager(credentials_path, folder_id)
    return drive_manager