# test_facebook_diagnostic.py
import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("🔍 DIAGNOSTIC FACEBOOK COMPLET")
print("=" * 50)

# 1. Vérifier les variables d'environnement
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")

print(f"1. Variables d'environnement:")
print(f"   FACEBOOK_PAGE_ID: {'✅' if FACEBOOK_PAGE_ID else '❌'} {FACEBOOK_PAGE_ID}")
print(f"   FACEBOOK_ACCESS_TOKEN: {'✅' if FACEBOOK_ACCESS_TOKEN else '❌'} {FACEBOOK_ACCESS_TOKEN[:20]}...")

# 2. Tester la connexion Internet
print(f"\n2. Test de connexion Internet:")
import requests
try:
    response = requests.get("https://graph.facebook.com", timeout=10)
    print(f"   Connexion à Facebook API: ✅ ({response.status_code})")
except Exception as e:
    print(f"   Connexion à Facebook API: ❌ {e}")

# 3. Tester le token
print(f"\n3. Test du token Facebook:")
if FACEBOOK_ACCESS_TOKEN:
    try:
        url = f"https://graph.facebook.com/v19.0/me"
        params = {"access_token": FACEBOOK_ACCESS_TOKEN}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   Token valide: ✅")
            print(f"   Compte: {data.get('name')} (ID: {data.get('id')})")
        else:
            print(f"   Token invalide: ❌ Code {response.status_code}")
            print(f"   Erreur: {response.text}")
    except Exception as e:
        print(f"   Erreur test token: ❌ {e}")

# 4. Tester la page
print(f"\n4. Test de la page Facebook:")
if FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN:
    try:
        url = f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}"
        params = {"access_token": FACEBOOK_ACCESS_TOKEN, "fields": "name,id"}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   Page accessible: ✅")
            print(f"   Nom page: {data.get('name')}")
            print(f"   ID page: {data.get('id')}")
        else:
            print(f"   Page inaccessible: ❌ Code {response.status_code}")
            print(f"   Erreur: {response.text}")
    except Exception as e:
        print(f"   Erreur test page: ❌ {e}")

print("\n" + "=" * 50)
print("📋 RECOMMANDATIONS:")

if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
    print("1. Ajoutez ces variables à votre .env:")
    print("   FACEBOOK_PAGE_ID=votre_page_id")
    print("   FACEBOOK_ACCESS_TOKEN=votre_token_long_lived")

print("2. Pour obtenir un token valide:")
print("   - Allez sur: https://developers.facebook.com/tools/explorer/")
print("   - Sélectionnez votre App")
print("   - Cliquez sur 'Generate Access Token'")
print("   - Ajoutez les permissions: pages_manage_posts, pages_read_engagement")
print("   - Utilisez le token généré dans .env")

print("3. Si problèmes de réseau:")
print("   - Vérifiez votre firewall/proxy")
print("   - Testez: ping graph.facebook.com")
print("   - Essayez avec un VPN si nécessaire")