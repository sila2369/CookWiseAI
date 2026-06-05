#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firebase Admin kullanıcı oluşturur (USE_FIREBASE_AUTH=True iken).
Firebase Auth + Firestore'da profil oluşturur.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.firebase import init_firebase, is_firebase_enabled

EMAIL = "admin@cookwise.com"
PASS = "Admin123!"

if not is_firebase_enabled():
    print("Firebase auth devre disi. .env'de USE_FIREBASE_AUTH=True yapin.")
    sys.exit(1)

init_firebase(settings.FIREBASE_CREDENTIALS_PATH, settings.FIREBASE_PROJECT_ID)

from firebase_admin import auth
from firebase_admin import firestore
from datetime import datetime

try:
    user_record = auth.get_user_by_email(EMAIL)
    uid = user_record.uid
    auth.update_user(uid, password=PASS, email_verified=True)
    db = firestore.client()
    db.collection("users").document(uid).update({"is_admin": True, "is_verified": True})
    print(f"Admin guncellendi: {EMAIL} (uid={uid})")
except Exception as e:
    if "no user" in str(e).lower() or "not found" in str(e).lower():
        user_record = auth.create_user(email=EMAIL, password=PASS, display_name="Admin User", email_verified=True)
        uid = user_record.uid
        db = firestore.client()
        now = datetime.utcnow()
        db.collection("users").document(uid).set({
            "full_name": "Admin User",
            "email": EMAIL,
            "phone": "+905559999999",
            "is_active": True,
            "is_admin": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
        })
        print(f"Admin olusturuldu: {EMAIL} / {PASS}")
    else:
        print(f"Hata: {e}")
        sys.exit(1)
