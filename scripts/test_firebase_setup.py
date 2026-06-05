#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firebase ve API test scripti.
Web + Mobil icin ortak backend testi.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE = os.getenv("API_URL", "http://localhost:8000")
PREFIX = "/api/v1"


def test_health():
    print("1. Health check...")
    r = requests.get(f"{BASE}{PREFIX}/health/", timeout=5)
    assert r.status_code == 200, r.text
    print("   OK")

def test_config():
    print("2. Firebase config...")
    from app.core.config import settings
    from app.core.firebase import is_firebase_enabled
    fb = is_firebase_enabled()
    print(f"   USE_FIREBASE_AUTH: {settings.USE_FIREBASE_AUTH}")
    print(f"   Firebase enabled: {fb}")
    if fb:
        print(f"   FIREBASE_CREDENTIALS: {settings.FIREBASE_CREDENTIALS_PATH}")
        print(f"   FIREBASE_PROJECT_ID: {settings.FIREBASE_PROJECT_ID}")
        print(f"   FIREBASE_API_KEY: {'***' + (settings.FIREBASE_API_KEY or '')[-4:] if settings.FIREBASE_API_KEY else 'yok'}")

def test_register_login():
    print("3. Auth test (register + login)...")
    email = "test_web_mobile@cookwise.com"
    password = "Test123!"
    # Register
    r = requests.post(f"{BASE}{PREFIX}/auth/register", json={
        "full_name": "Test User",
        "email": email,
        "password": password,
        "phone": "+905551234567",
    }, timeout=10)
    if r.status_code in (201, 409):
        print("   Register: OK")
    else:
        print(f"   Register FAIL: {r.status_code} - {r.text[:200]}")
        return
    # Login
    r = requests.post(f"{BASE}{PREFIX}/auth/login", json={"email": email, "password": password}, timeout=10)
    if r.status_code == 200:
        token = r.json().get("access_token")
        print(f"   Login: OK (token: {len(token) if token else 0} chars)")
        # /users/me
        h = {"Authorization": f"Bearer {token}"}
        r2 = requests.get(f"{BASE}{PREFIX}/users/me", headers=h, timeout=5)
        if r2.status_code == 200:
            print(f"   /users/me: OK - {r2.json().get('email')}")
        else:
            print(f"   /users/me: {r2.status_code}")
    else:
        print(f"   Login FAIL: {r.status_code} - {r.text[:200]}")

def test_products():
    print("4. Products (public)...")
    r = requests.get(f"{BASE}{PREFIX}/products?limit=2", timeout=5)
    if r.status_code == 200:
        d = r.json()
        print(f"   OK - {d.get('total', 0)} urun, ilk 2 listelendi")
    else:
        print(f"   FAIL: {r.status_code}")

def main():
    print("=" * 50)
    print("CookWise - Backend Test (Web + Mobil ortak API)")
    print("=" * 50)
    print(f"Base URL: {BASE}")
    print()
    try:
        test_health()
        test_config()
        test_register_login()
        test_products()
        print()
        print("=" * 50)
        print("Test tamamlandi.")
        print("=" * 50)
    except requests.exceptions.ConnectionError:
        print("HATA: Sunucu calismiyor. Once: uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"HATA: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
