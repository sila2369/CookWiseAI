#!/usr/bin/env python3
"""
Migros CSV verisini MongoDB'ye aktarir.

Kullanim:
    python scripts/import_migros_csv_to_db.py
    python scripts/import_migros_csv_to_db.py --csv migros_urunler.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from typing import Dict, List
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.models.category import Category, generate_slug  # noqa: E402


def normalize_category_slug(category_slug: str) -> str:
    normalized = str(category_slug or "").strip().lower()
    aliases = {
        "deterjan-temizlik": "temizlik",
        "deterjan temizlik": "temizlik",
        "sut-kahvaltilik": "sut-urunleri",
        "sut kahvaltilik": "sut-urunleri",
    }
    return aliases.get(normalized, normalized)


def category_display_name(category_slug: str) -> str:
    return category_slug.replace("-", " ").title()


def build_product_slug(category_slug: str, product_name: str) -> str:
    return generate_slug(f"{category_slug}-{product_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migros CSV -> MongoDB importer")
    parser.add_argument("--csv", default="migros_urunler.csv", help="CSV dosya yolu")
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"CSV bulunamadi: {args.csv}")
        sys.exit(1)

    with open(args.csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = list(reader)
        fieldnames = set(reader.fieldnames or [])

    required_cols = {"name", "price", "isStock", "image_url", "category"}
    missing = required_cols.difference(fieldnames)
    if missing:
        print(f"CSV eksik kolonlar: {sorted(missing)}")
        sys.exit(1)

    client = MongoClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    categories_col = db["categories"]
    products_col = db["products"]

    category_id_map: Dict[str, ObjectId] = {}
    now = datetime.utcnow()

    inserted_categories = 0
    inserted_products = 0
    updated_products = 0

    # 1) Kategorileri hazırla
    category_slugs = sorted(
        {
            normalize_category_slug(str(row.get("category", "")).strip())
            for row in rows
            if row.get("category")
        }
    )
    for category_slug in category_slugs:
        existing = categories_col.find_one({"slug": category_slug})
        if existing:
            category_id_map[category_slug] = existing["_id"]
            continue

        doc = Category.create_document(
            name=category_display_name(category_slug),
            slug=category_slug,
            description=f"Migros import kategorisi: {category_slug}",
            is_active=True,
        )
        result = categories_col.insert_one(doc)
        category_id_map[category_slug] = result.inserted_id
        inserted_categories += 1

    # 2) Ürünleri upsert et
    for row in rows:
        name = str(row.get("name", "")).strip()
        category_slug = normalize_category_slug(str(row.get("category", "")).strip())
        if not name or not category_slug:
            continue

        category_id = category_id_map.get(category_slug)
        if not category_id:
            continue

        try:
            price = float(row.get("price", 0) or 0)
        except Exception:
            price = 0.0
        is_stock_raw = str(row.get("isStock", "")).strip().lower()
        is_stock = is_stock_raw in {"true", "1", "yes"}
        image_url = str(row.get("image_url", "")).strip() or None

        slug = build_product_slug(category_slug, name)
        payload = {
            "name": name,
            "slug": slug,
            "description": f"Migros import urunu ({category_slug})",
            "price": round(max(0.0, price), 2),
            "stock": 100 if is_stock else 0,
            "image_url": image_url,
            "category_id": category_id,
            "brand": "Migros",
            "unit": "adet",
            "is_active": True,
            "updated_at": now,
        }

        existing = products_col.find_one({"slug": slug})
        if existing:
            products_col.update_one({"_id": existing["_id"]}, {"$set": payload})
            updated_products += 1
        else:
            payload["created_at"] = now
            products_col.insert_one(payload)
            inserted_products += 1

    print("Migros import tamamlandi.")
    print(f"Kategori eklendi: {inserted_categories}")
    print(f"Yeni urun eklendi: {inserted_products}")
    print(f"Guncellenen urun: {updated_products}")


if __name__ == "__main__":
    main()

