import os
from dotenv import load_dotenv

# Chargement du fichier .env
load_dotenv()

# -----------------------------
# 🔐 OpenAI
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# -----------------------------
# 🔐 Facebook API
# -----------------------------
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")

# -----------------------------
# 🔐 UNSPLASH_API_KEY  API
# -----------------------------
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")
# -----------------------------
# 🛑 Vérification des variables essentielles
# -----------------------------
erreurs = []

if not OPENAI_API_KEY:
    erreurs.append("OPENAI_API_KEY manquant")

if not FACEBOOK_PAGE_ID:
    erreurs.append("FACEBOOK_PAGE_ID manquant")

if not FACEBOOK_ACCESS_TOKEN:
    erreurs.append("FACEBOOK_ACCESS_TOKEN manquant")

if not UNSPLASH_API_KEY:
    erreurs.append("UNSPLASH_API_KEY manquant")

if erreurs:
    raise ValueError(
        "❌ Erreur configuration .env :\n- " + "\n- ".join(erreurs) +
        "\n\nVérifie ton fichier .env."
    )
