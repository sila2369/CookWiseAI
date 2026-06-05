#!/usr/bin/env python3
"""
3. Hafta Ürün & Kategori Modülleri Test Akışı
==============================================

Test sırası:
1. Admin login
2. Kategori oluştur
3. Ürün oluştur (oluşturulan kategori ile)
4. Ürünleri listele
5. Ürün detay getir
6. Ürün filtrele (category_id, search, min_price, max_price)
7. Ürünü pasife çek (soft delete)

Kullanım:
    python scripts/test_week3_flow.py
    # veya
    cd c:/Users/silae/OneDrive/Masaüstü/CookWise && python scripts/test_week3_flow.py

Ön koşul:
    - Uygulama çalışıyor (uvicorn)
    - admin@example.com kayıtlı ve is_admin=True (test_auth_flow.py ile)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# Test verisi - flow içinde güncellenir
ADMIN_TOKEN = None
CATEGORY_ID = None
PRODUCT_ID = None


def admin_login():
    """1. Admin login."""
    global ADMIN_TOKEN
    print("1️⃣ Admin Login")
    r = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123"},
    )
    if r.status_code != 200:
        print(f"   ✗ {r.status_code} - {r.text}")
        return False
    ADMIN_TOKEN = r.json()["access_token"]
    print("   ✓ Admin token alındı")
    return True


def create_category():
    """2. Kategori oluştur."""
    global CATEGORY_ID
    print("\n2️⃣ Kategori Oluştur")
    data = {
        "name": "Süt Ürünleri",
        "slug": "sut-urunleri",
        "description": "Süt, yoğurt, peynir ve diğer süt ürünleri",
        "is_active": True,
    }
    r = requests.post(
        f"{BASE_URL}{API_PREFIX}/categories",
        json=data,
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    if r.status_code not in (200, 201):
        print(f"   ✗ {r.status_code} - {r.text}")
        return False
    res = r.json()
    CATEGORY_ID = res["id"]
    print(f"   ✓ Kategori oluşturuldu: {res['name']} (id={CATEGORY_ID[:12]}...)")
    return True


def create_product():
    """3. Ürün oluştur."""
    global PRODUCT_ID
    print("\n3️⃣ Ürün Oluştur")
    data = {
        "name": "Günlük Süt 1 Litre",
        "slug": "gunluk-sut-1-litre",
        "description": "Günlük taze süt, 1 litre",
        "price": 24.99,
        "stock": 50,
        "category_id": CATEGORY_ID,
        "brand": "Pınar",
        "unit": "litre",
        "is_active": True,
    }
    r = requests.post(
        f"{BASE_URL}{API_PREFIX}/products",
        json=data,
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    if r.status_code not in (200, 201):
        print(f"   ✗ {r.status_code} - {r.text}")
        return False
    res = r.json()
    PRODUCT_ID = res["id"]
    print(f"   ✓ Ürün oluşturuldu: {res['name']} (id={PRODUCT_ID[:12]}...)")
    return True


def list_products():
    """4. Ürünleri listele."""
    print("\n4️⃣ Ürünleri Listele")
    r = requests.get(f"{BASE_URL}{API_PREFIX}/products?skip=0&limit=20")
    if r.status_code != 200:
        print(f"   ✗ {r.status_code} - {r.text}")
        return False
    res = r.json()
    total = res.get("total", 0)
    items = res.get("items", [])
    print(f"   ✓ {total} ürün bulundu (ilk {len(items)} gösteriliyor)")
    for p in items[:3]:
        print(f"      - {p['name']} ({p['price']} TL)")
    return True


def get_product_detail():
    """5. Ürün detay getir."""
    print("\n5️⃣ Ürün Detay Getir")
    r = requests.get(f"{BASE_URL}{API_PREFIX}/products/{PRODUCT_ID}")
    if r.status_code != 200:
        print(f"   ✗ {r.status_code} - {r.text}")
        return False
    p = r.json()
    print(f"   ✓ {p['name']} - {p['price']} TL, stok: {p['stock']}")
    return True


def filter_products():
    """6. Ürün filtrele."""
    print("\n6️⃣ Ürün Filtrele")
    params = f"category_id={CATEGORY_ID}&search=süt&min_price=10&max_price=100"
    r = requests.get(f"{BASE_URL}{API_PREFIX}/products?{params}")
    if r.status_code != 200:
        print(f"   ✗ {r.status_code} - {r.text}")
        return False
    res = r.json()
    print(f"   ✓ Filtrelenmiş: {res['total']} ürün (category + search + fiyat)")
    return True


def soft_delete_product():
    """7. Ürünü pasife çek (soft delete)."""
    print("\n7️⃣ Ürünü Pasife Çek (Soft Delete)")
    r = requests.delete(
        f"{BASE_URL}{API_PREFIX}/products/{PRODUCT_ID}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    if r.status_code != 200:
        print(f"   ✗ {r.status_code} - {r.text}")
        return False
    res = r.json()
    print(f"   ✓ is_active=False yapıldı: {res['name']}")
    # Doğrulama: public listede görünmemeli
    r2 = requests.get(f"{BASE_URL}{API_PREFIX}/products/{PRODUCT_ID}")
    if r2.status_code == 404:
        print("   ✓ Public GET /products/{id} artık 404 (beklenen)")
    return True


def run_flow():
    """Tam test akışını çalıştır."""
    print("=" * 60)
    print("📦 CookWise 3. Hafta - Ürün & Kategori Modülleri Testi")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print()

    steps = [
        admin_login,
        create_category,
        create_product,
        list_products,
        get_product_detail,
        filter_products,
        soft_delete_product,
    ]
    for step in steps:
        if not step():
            print("\n❌ Test akışı hata ile durdu.")
            return
    print("\n" + "=" * 60)
    print("✅ 3. Hafta test akışı tamamlandı")
    print("=" * 60)


if __name__ == "__main__":
    run_flow()
