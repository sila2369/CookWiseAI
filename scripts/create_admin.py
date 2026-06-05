#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MongoDB'ye admin kullanici ekler (test icin)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from pymongo import MongoClient
import bcrypt

from app.core.config import settings

EMAIL = "admin@cookwise.com"
PASS = "Admin123!"
hashed = bcrypt.hashpw(PASS.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
DOC = {
    "full_name": "Admin User",
    "email": EMAIL,
    "hashed_password": hashed,
    "phone": "+905559999999",
    "is_active": True,
    "is_admin": True,
    "is_verified": True,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow(),
}

client = MongoClient(settings.MONGODB_URL)
db = client[settings.MONGODB_DB]
col = db["users"]
existing = col.find_one({"email": EMAIL})
if existing:
    col.update_one({"email": EMAIL}, {"$set": {"is_admin": True, "is_verified": True, "hashed_password": hashed}})
    print(f"Admin guncellendi: {EMAIL} / {PASS}")
else:
    col.insert_one(DOC)
    print(f"Admin olusturuldu: {EMAIL} / {PASS}")
