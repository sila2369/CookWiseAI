#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed Data Script - Örnek Kategoriler ve Ürünler
================================================

MongoDB'ye test için örnek kategori ve ürün ekler.
Tekrar çalıştırıldığında mevcut slug varsa atlar (duplicate oluşturmaz).

Kullanım:
    python scripts/seed_data.py
    # veya
    cd CookWise && python scripts/seed_data.py
"""

import os
import sys

# Windows'ta emoji/Turkce karakter icin stdout UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from app.core.config import settings
from app.models.category import Category
from app.models.product import Product

# ==================== ÖRNEK KATEGORİLER ====================

CATEGORIES = [
    {"name": "Meyve & Sebze", "slug": "meyve-sebze", "description": "Taze meyve ve sebzeler"},
    {"name": "İçecek", "slug": "icecek", "description": "Soğuk ve sıcak içecekler"},
    {"name": "Atıştırmalık", "slug": "atistirmalik", "description": "Çikolata, bisküvi, kuruyemiş ve atıştırmalıklar"},
    {"name": "Temizlik", "slug": "temizlik", "description": "Ev temizlik ürünleri ve deterjanlar"},
    {"name": "Süt Ürünleri", "slug": "sut-urunleri", "description": "Süt, yoğurt, peynir ve süt ürünleri"},
]

# ==================== ÖRNEK ÜRÜNLER ====================
# category_slug: kategorinin slug'ı (kategori oluşturulduktan sonra eşleştirilir)
# Her ürün için: name, slug, description, price, stock, category_slug, brand (opsiyonel), unit (opsiyonel)

PRODUCTS = [
    # Meyve & Sebze
    {"name": "Domates 1 kg", "slug": "domates-1-kg", "description": "Taze kırmızı domates", "price": 19.99, "stock": 100, "category_slug": "meyve-sebze", "unit": "kg"},
    {"name": "Salatalık", "slug": "salatalik", "description": "Taze salatalık", "price": 14.99, "stock": 80, "category_slug": "meyve-sebze", "unit": "kg"},
    {"name": "Elma Kırmızı", "slug": "elma-kirmizi", "description": "Kırmızı elma 1 kg", "price": 24.99, "stock": 60, "category_slug": "meyve-sebze", "unit": "kg"},
    {"name": "Muz", "slug": "muz", "description": "Taze muz 1 kg", "price": 34.99, "stock": 70, "category_slug": "meyve-sebze", "unit": "kg"},
    # İçecek
    {"name": "Coca-Cola 1.5L", "slug": "coca-cola-1-5l", "description": "Coca-Cola gazlı içecek", "price": 22.99, "stock": 120, "category_slug": "icecek", "brand": "Coca-Cola", "unit": "adet"},
    {"name": "Su 5L", "slug": "su-5l", "description": "Doğal kaynak suyu 5 litre", "price": 15.99, "stock": 200, "category_slug": "icecek", "brand": "Sırma", "unit": "adet"},
    {"name": "Ayran 1L", "slug": "ayran-1l", "description": "Geleneksel ayran", "price": 18.99, "stock": 90, "category_slug": "icecek", "brand": "Pınar", "unit": "litre"},
    {"name": "Portakal Suyu 1L", "slug": "portakal-suyu-1l", "description": "%100 doğal portakal suyu", "price": 29.99, "stock": 50, "category_slug": "icecek", "brand": "Cappy", "unit": "litre"},
    # Atıştırmalık
    {"name": "Çikolata Sütlü", "slug": "cikolata-sutlu", "description": "Sütlü çikolata 80g", "price": 14.99, "stock": 150, "category_slug": "atistirmalik", "brand": "Ülker"},
    {"name": "Çikolatalı Gofret", "slug": "cikolatali-gofret", "description": "Çikolatalı gofret 6'lı", "price": 19.99, "stock": 100, "category_slug": "atistirmalik", "brand": "Ülker"},
    {"name": "Cips Peynirli", "slug": "cips-peynirli", "description": "Peynir aromalı cips 150g", "price": 24.99, "stock": 80, "category_slug": "atistirmalik", "brand": "Lays"},
    {"name": "Fındık 200g", "slug": "findik-200g", "description": "Kavrulmuş fındık", "price": 49.99, "stock": 60, "category_slug": "atistirmalik", "unit": "adet"},
    # Temizlik
    {"name": "Bulaşık Deterjanı", "slug": "bulasik-deterjani", "description": "Bulaşık makinesi deterjanı 1kg", "price": 89.99, "stock": 40, "category_slug": "temizlik", "brand": "Finish"},
    {"name": "Çamaşır Suyu 5L", "slug": "camasir-suyu-5l", "description": "Beyazlatıcılı çamaşır suyu", "price": 34.99, "stock": 70, "category_slug": "temizlik", "brand": "Domestos"},
    {"name": "Yüzey Temizleyici", "slug": "yuzey-temizleyici", "description": "Çok amaçlı yüzey temizleyici", "price": 44.99, "stock": 50, "category_slug": "temizlik", "brand": "Cif"},
    # Süt Ürünleri
    {"name": "Süt 1L", "slug": "sut-1l", "description": "Günlük süt 1 litre", "price": 24.99, "stock": 150, "category_slug": "sut-urunleri", "brand": "Pınar", "unit": "litre"},
    {"name": "Yoğurt 1kg", "slug": "yogurt-1kg", "description": "Tam yağlı yoğurt", "price": 32.99, "stock": 80, "category_slug": "sut-urunleri", "brand": "Pınar", "unit": "kg"},
    {"name": "Beyaz Peynir", "slug": "beyaz-peynir", "description": "Beyaz peynir 400g", "price": 129.99, "stock": 45, "category_slug": "sut-urunleri", "brand": "Pınar", "unit": "kg"},
    {"name": "Kaşar Peynir 200g", "slug": "kasar-peynir-200g", "description": "Dilimlenmiş kaşar peynir", "price": 79.99, "stock": 55, "category_slug": "sut-urunleri", "brand": "Pınar", "unit": "adet"},
]


def get_db():
    """MongoDB veritabanı bağlantısı. (client, db) döner."""
    client = MongoClient(settings.MONGODB_URL)
    return client, client[settings.MONGODB_DB]


def seed_categories(db) -> dict:
    """
    Kategorileri ekler. slug zaten varsa atlar.
    Döner: {slug: ObjectId} eşlemesi
    """
    col = db[Category.COLLECTION]
    slug_to_id = {}

    for cat in CATEGORIES:
        slug = cat["slug"]
        existing = col.find_one({"slug": slug})
        if existing:
            slug_to_id[slug] = existing["_id"]
            print(f"   [skip] Kategori zaten var: {cat['name']}")
        else:
            doc = Category.create_document(
                name=cat["name"],
                slug=slug,
                description=cat.get("description"),
                is_active=True,
            )
            result = col.insert_one(doc)
            slug_to_id[slug] = result.inserted_id
            print(f"   [ok] Kategori eklendi: {cat['name']} ({slug})")

    return slug_to_id


def seed_products(db, slug_to_id: dict):
    """
    Ürünleri ekler. slug zaten varsa atlar.
    """
    col = db[Product.COLLECTION]

    for p in PRODUCTS:
        slug = p["slug"]
        existing = col.find_one({"slug": slug})
        if existing:
            print(f"   [skip] Ürün zaten var: {p['name']}")
            continue

        cat_slug = p["category_slug"]
        category_id = slug_to_id.get(cat_slug)
        if not category_id:
            print(f"   [err] Kategori bulunamadı '{cat_slug}' için: {p['name']}")
            continue

        doc = Product.create_document(
            name=p["name"],
            description=p.get("description", ""),
            price=p["price"],
            stock=p["stock"],
            category_id=str(category_id),
            slug=slug,
            brand=p.get("brand"),
            unit=p.get("unit"),
            is_active=True,
        )
        col.insert_one(doc)
        print(f"   [ok] Ürün eklendi: {p['name']} ({p['price']} TL)")


def main():
    print("=" * 50)
    print("CookWise - Seed Data")
    print("=" * 50)
    print(f"DB: {settings.MONGODB_DB}")
    print()

    try:
        client, db = get_db()
        client.admin.command("ping")
    except Exception as e:
        print(f"[HATA] MongoDB bağlantı hatası: {e}")
        print("   MongoDB çalışıyor olmalı. Örn: mongod veya Docker ile başlatın.")
        sys.exit(1)

    print("1. Kategoriler")
    slug_to_id = seed_categories(db)
    print()

    print("2. Ürünler")
    seed_products(db, slug_to_id)
    print()

    print("=" * 50)
    print("Seed tamamlandı.")
    print("=" * 50)


if __name__ == "__main__":
    main()
