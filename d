import pandas as pd
from datetime import datetime
from modules.plateformes.facebook import (
    publier_sur_facebook,
    lire_reactions,
    traiter_commentaires
)

EXCEL_FILE = "historique_posts.xlsx"


def lire_posts_non_publies():
    """Retourne uniquement les posts sans plateforme renseignée."""
    df = pd.read_excel(EXCEL_FILE)
    return df[df["nom_plateforme"].isna() | (df["nom_plateforme"] == "")]


def mettre_a_jour_post(index, infos):
    """Met à jour un post dans l'Excel."""
    df = pd.read_excel(EXCEL_FILE)
    for cle, val in infos.items():
        df.loc[index, cle] = val
    df.to_excel(EXCEL_FILE, index=False)


def publier_tous():
    """Publie tous les posts non publiés dans l'Excel."""
    df = lire_posts_non_publies()

    for index, row in df.iterrows():
        post = row.to_dict()

        # --- Récupération du texte à publier ---
        contenu = post.get("texte_marketing", "")
        if not contenu or str(contenu).strip() == "":
            print(f"[Erreur] Aucun texte marketing pour l’index {index}. Publication impossible.")
            continue

        # 1) Publication Facebook
        resultat = publier_sur_facebook({"contenu": contenu})

        if resultat.get("status") != "publié":
            print(f"[Erreur] Publication échouée à l’index {index} : {resultat.get('message')}")
            continue

        post_id = resultat.get("post_id")
        if not post_id:
            print(f"[Attention] Post publié mais aucun ID récupéré pour l’index {index}.")
            continue

        # 2) Lecture réactions
        reactions = lire_reactions(post_id)

        # 3) Lecture + réponse commentaires
        interactions = traiter_commentaires(post_id)

        # 4) Mise à jour Excel
        mettre_a_jour_post(
            index,
            {
                "nom_plateforme": "Facebook",
                "post_id": post_id,
                "reaction_positive": reactions.get("total", 0),
                "commentaires": len(interactions),
                "date_publication": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )

    print("✓ Tous les posts ont été publiés et traités.")
