import pandas as pd
from datetime import datetime
import threading
import time
from modules.plateformes.facebook import (
    publier_sur_facebook,
    lire_reactions,
    traiter_commentaires
)

EXCEL_FILE = "historique_posts.xlsx"
INTERVALLE_ANALYSE = 10  # secondes

# -----------------------------
# Lire posts non publiés
# -----------------------------
def lire_posts_non_publies():
    df = pd.read_excel(EXCEL_FILE)
    return df[df["nom_plateforme"].isna() | (df["nom_plateforme"] == "")]

# -----------------------------
# Mettre à jour un post dans Excel
# -----------------------------
def mettre_a_jour_post(index, infos):
    df = pd.read_excel(EXCEL_FILE)
    for cle, val in infos.items():
        df.loc[index, cle] = val
    df.to_excel(EXCEL_FILE, index=False)

# -----------------------------
# Publier tous les posts non publiés
# -----------------------------
def publier_tous():
    df = lire_posts_non_publies()

    for index, row in df.iterrows():
        post = row.to_dict()
        contenu = post.get("texte_marketing", "")
        image_path = post.get("image_path", None)

        if not contenu or str(contenu).strip() == "":
            print(f"[Erreur] Aucun texte marketing pour l’index {index}.")
            continue

        # Décider si on publie avec l'image
        publish_with_image = bool(image_path and str(image_path).strip() != "")
        resultat = publier_sur_facebook({"contenu": contenu, "image_path": image_path}, with_image=publish_with_image)

        if resultat.get("status") != "publié":
            print(f"[Erreur] Publication échouée à l’index {index} : {resultat.get('message')}")
            continue

        post_id = resultat.get("post_id")
        print(f"[Succès] Post publié avec ID : {post_id} | Avec image : {publish_with_image}")

        # Lire réactions
        reaction_count = lire_reactions(post_id)

        # Traiter commentaires (réponse IA + MP)
        interactions = traiter_commentaires(post_id)

        # Mise à jour Excel
        mettre_a_jour_post(
            index,
            {
                "nom_plateforme": "Facebook",
                "post_id": post_id,
                "reaction_positive": reaction_count,
                "commentaires": len(interactions),
                "date_publication": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )

    print("✓ Tous les posts non publiés ont été traités.")

# -----------------------------
# Thread automatique
# -----------------------------
def thread_automatisation():
    while True:
        try:
            publier_tous()
        except Exception as e:
            print(f"[Thread ERROR] {e}")
        time.sleep(INTERVALLE_ANALYSE)

# -----------------------------
# Démarrage de l'automatisation
# -----------------------------
def demarrer_automatisation():
    t = threading.Thread(target=thread_automatisation, daemon=True)
    t.start()
    print(f"🟢 Automatisation Facebook lancée (analyse toutes les {INTERVALLE_ANALYSE} secondes).")
