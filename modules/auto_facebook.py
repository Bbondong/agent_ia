import threading
import time
import pandas as pd
from modules.plateformes.facebook import traiter_commentaires, envoyer_message_prive

CHECK_INTERVAL = 10  # secondes
EXCEL_FILE = "historique_posts.xlsx"

def auto_check_comments():
    while True:
        try:
            df = pd.read_excel(EXCEL_FILE)
            for _, row in df.iterrows():
                post_id = row.get("post_id")
                if post_id:
                    interactions = traiter_commentaires(post_id)
                    if interactions:
                        print(f"[Auto] Réponses envoyées pour post {post_id} : {len(interactions)}")
        except Exception as e:
            print(f"[Auto] Erreur auto_check_comments: {e}")

        time.sleep(CHECK_INTERVAL)

# Démarrage automatique du thread
thread = threading.Thread(target=auto_check_comments, daemon=True)
thread.start()
