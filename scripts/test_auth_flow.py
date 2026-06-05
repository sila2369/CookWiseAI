#!/usr/bin/env python3
"""
Auth Akış Test Scripti
======================

Test sırası:
1. Register (normal kullanıcı)
2. Register (admin kullanıcı - MongoDB'de is_admin yapılır)
3. Login
4. Authorize (token ile)
5. GET /users/me
6. GET /admin/test (normal user → 403, admin user → 200)

Kullanım:
    python scripts/test_auth_flow.py
    # veya
    cd c:/Users/silae/OneDrive/Masaüstü/CookWise && python scripts/test_auth_flow.py
"""

import os
import sys
from pathlib import Path

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)

import requests

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
USE_FIREBASE_AUTH = os.getenv("USE_FIREBASE_AUTH", "false").lower() == "true"


def test_auth_flow():
    """Tam auth akışını test et."""
    print("=" * 60)
    print("CookWise Auth Akis Testi")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print()

    # 1. REGISTER - Normal kullanıcı
    print("1) REGISTER (normal user)")
    reg_data = {
        "full_name": "Test User",
        "email": "testuser@example.com",
        "password": "SecurePass123",
        "phone": "+905551234567",
    }
    r = requests.post(f"{BASE_URL}{API_PREFIX}/auth/register", json=reg_data)
    if r.status_code in (201, 409):  # 409 = zaten kayıtlı
        print(f"   [OK] {r.status_code} - User kayitli veya zaten var")
    else:
        print(f"   [ERR] {r.status_code} - {r.text}")
        return
    print()

    # 2. REGISTER - Admin kullanıcı
    print("2) REGISTER (admin user)")
    admin_reg = {
        "full_name": "Admin User",
        "email": "admin@example.com",
        "password": "AdminPass123",
        "phone": "+905559999999",
    }
    r = requests.post(f"{BASE_URL}{API_PREFIX}/auth/register", json=admin_reg)
    if r.status_code in (201, 409):
        print(f"   [OK] {r.status_code} - Admin user kayitli veya zaten var")
        # Admin yapmak için MongoDB'de is_admin=true güncelle
        try:
            from pymongo import MongoClient
            from app.core.config import settings
            client = MongoClient(settings.MONGODB_URL)
            db = client[settings.MONGODB_DB]
            db.users.update_one(
                {"email": "admin@example.com"},
                {"$set": {"is_admin": True}}
            )
            print("   [OK] MongoDB: admin@example.com -> is_admin=True")
        except Exception as e:
            print(f"   [WARN] is_admin manuel ayarlanmali: {e}")
    else:
        print(f"   [ERR] {r.status_code} - {r.text}")
    print()

    # 3. LOGIN - Normal user
    print("3) LOGIN (normal user)")
    login_data = {"email": "testuser@example.com", "password": "SecurePass123"}
    r = requests.post(f"{BASE_URL}{API_PREFIX}/auth/login", json=login_data)
    if r.status_code != 200:
        print(f"   [ERR] {r.status_code} - {r.text}")
        return
    token_normal = r.json()["access_token"]
    print(f"   [OK] Token alindi ({len(token_normal)} chars)")
    print()

    # 4. AUTHORIZE + 5. GET /users/me (normal user)
    print("4-5) AUTHORIZE + GET /users/me (normal user)")
    headers = {"Authorization": f"Bearer {token_normal}"}
    r = requests.get(f"{BASE_URL}{API_PREFIX}/users/me", headers=headers)
    if r.status_code == 200:
        data = r.json()
        print(f"   [OK] 200 - {data.get('email')} (is_admin={data.get('is_admin')})")
    else:
        print(f"   [ERR] {r.status_code} - {r.text}")
    print()

    # 6. GET /admin/test (normal user → 403)
    print("6) GET /admin/test (normal user - 403 beklenir)")
    r = requests.get(f"{BASE_URL}{API_PREFIX}/admin/test", headers=headers)
    if r.status_code == 403:
        print(f"   [OK] 403 - Admin erisimi reddedildi (beklenen)")
    else:
        print(f"   [ERR] {r.status_code} - {r.text} (403 bekleniyordu)")
    print()

    # 7. LOGIN - Admin user
    print("7) LOGIN (admin user)")
    admin_login = {"email": "admin@example.com", "password": "AdminPass123"}
    r = requests.post(f"{BASE_URL}{API_PREFIX}/auth/login", json=admin_login)
    if r.status_code != 200:
        print(f"   [ERR] {r.status_code} - {r.text}")
        return
    token_admin = r.json()["access_token"]
    print(f"   [OK] Admin token alindi")
    print()

    # 8. GET /admin/test (admin user → 200)
    print("8) GET /admin/test (admin user - 200 beklenir)")
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    r = requests.get(f"{BASE_URL}{API_PREFIX}/admin/test", headers=headers_admin)
    if r.status_code == 200:
        data = r.json()
        print(f"   [OK] 200 - {data.get('message')} ({data.get('user_email')})")
    elif r.status_code == 403 and USE_FIREBASE_AUTH:
        print("   [WARN] 403 - Firebase modunda admin yetkisi custom claim/role gerektirir")
        print("   [WARN] test scripti MongoDB is_admin guncellemesi ile admin olusturamaz")
    else:
        print(f"   [ERR] {r.status_code} - {r.text} (200 bekleniyordu)")
        print("   [WARN] admin@example.com icin MongoDB'de is_admin=true olmali")
    print()

    print("=" * 60)
    print("[OK] Test akisi tamamlandi")
    print("=" * 60)


if __name__ == "__main__":
    test_auth_flow()
