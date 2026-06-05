"""
Import Migros CSV product data into CookWise MongoDB.

Usage:
    python scripts/import_migros_products.py
    python scripts/import_migros_products.py --per-category 120 --campaign-samples
    python scripts/import_migros_products.py --csv-glob "migros_urunler_temel-gida.csv"
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import glob
import hashlib
import os
import random
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_LABELS = {
    "meyve-sebze": "Meyve & Sebze",
    "temel-gida": "Temel Gida",
    "sut-kahvaltilik": "Sut & Kahvaltilik",
    "et-tavuk-balik": "Et, Tavuk & Balik",
    "icecek": "Icecek",
    "atistirmalik": "Atistirmalik",
    "firin-pastane": "Firin & Pastane",
    "deterjan-temizlik": "Deterjan & Temizlik",
    "kisisel-bakim-kozmetik-saglik": "Kisisel Bakim",
    "kagit-islak-mendil": "Kagit & Islak Mendil",
    "bebek": "Bebek",
    "evcil-hayvan": "Evcil Hayvan",
    "meze-hazir-yemek-donuk": "Meze, Hazir Yemek & Donuk",
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    ascii_value = re.sub(r"-+", "-", ascii_value).strip("-")
    return ascii_value or "urun"


def boolish(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "evet", "var"}


def infer_unit(name: str) -> str:
    lowered = name.lower()
    if " kg" in lowered or lowered.endswith("kg"):
        return "kg"
    if " gr" in lowered or " g" in lowered:
        return "gr"
    if " lt" in lowered or " litre" in lowered or " l" in lowered:
        return "litre"
    if " ml" in lowered:
        return "ml"
    return "adet"


def stable_stock(name: str, in_stock: bool) -> int:
    if not in_stock:
        return 0
    seed = int(hashlib.sha1(name.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.randint(18, 140)


def iter_csv_rows(per_category: int | None, csv_glob: str) -> Iterable[dict[str, str]]:
    paths = sorted(glob.glob(str(ROOT / csv_glob)))
    if not paths and csv_glob != "migros_urunler*.csv":
        paths = sorted(glob.glob(str(ROOT / "migros_urunler*.csv")))

    seen_keys: set[str] = set()
    for csv_path in paths:
        seen_in_file = 0
        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if per_category is not None and seen_in_file >= per_category:
                    break
                if not row.get("name") or not row.get("price") or not row.get("category"):
                    continue
                row_key = f"{row.get('source_id') or ''}|{row.get('category') or ''}|{row.get('name') or ''}".lower()
                if row_key in seen_keys:
                    continue
                seen_keys.add(row_key)
                seen_in_file += 1
                yield row


async def ensure_category(categories, slug: str) -> ObjectId:
    now = datetime.utcnow()
    label = CATEGORY_LABELS.get(slug, slug.replace("-", " ").title())
    existing = await categories.find_one({"slug": slug})
    if existing:
        await categories.update_one(
            {"_id": existing["_id"]},
            {"$set": {"name": label, "is_active": True, "updated_at": now}},
        )
        return existing["_id"]

    result = await categories.insert_one(
        {
            "name": label,
            "slug": slug,
            "description": f"{label} urunleri",
            "image_url": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    return result.inserted_id


async def import_products(per_category: int | None, campaign_samples: bool, csv_glob: str) -> None:
    load_dotenv(ROOT / ".env")
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "cookwise")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    categories = db["categories"]
    products = db["products"]

    category_ids: dict[str, ObjectId] = {}
    imported = 0
    updated = 0
    created = 0

    for row in iter_csv_rows(per_category, csv_glob):
        category_slug = slugify(row["category"])
        if category_slug not in category_ids:
            category_ids[category_slug] = await ensure_category(categories, category_slug)

        name = row["name"].strip()
        price = round(float(str(row["price"]).replace(",", ".")), 2)
        source_id = str(row.get("source_id") or "").strip()
        slug = f"{slugify(name)}-{category_slug}"
        if source_id:
            slug = f"{slugify(source_id)}-{category_slug}"
        now = datetime.utcnow()
        in_stock = boolish(row.get("isStock"))
        should_promote = campaign_samples and imported % 11 == 0 and in_stock

        campaign_fields = {}
        if should_promote:
            campaign_fields = {
                "is_promoted": True,
                "promotion_type": "buy_x_pay_y",
                "promotion_label": "3 Al 2 Ode",
                "promotion_buy_quantity": 3,
                "promotion_pay_quantity": 2,
                "discounted_price": None,
            }

        insert_defaults = {
            "_id": ObjectId(),
            "slug": slug,
            "created_at": now,
            "is_promoted": False,
            "promotion_type": None,
            "promotion_label": None,
            "discounted_price": None,
            "promotion_buy_quantity": None,
            "promotion_pay_quantity": None,
        }
        if should_promote:
            for key in campaign_fields:
                insert_defaults.pop(key, None)

        result = await products.update_one(
            {"slug": slug},
            {
                "$set": {
                    "name": name,
                    "description": f"{CATEGORY_LABELS.get(category_slug, category_slug)} kategorisinden {name}.",
                    "price": price,
                    "stock": stable_stock(name, in_stock),
                    "image_url": (row.get("image_url") or "").strip() or None,
                    "category_id": category_ids[category_slug],
                    "brand": (row.get("brand") or "").strip() or None,
                    "unit": infer_unit(name),
                    "source": "migros",
                    "source_id": source_id or None,
                    "source_url": (row.get("source_url") or "").strip() or None,
                    "subcategory": (row.get("subcategory") or "").strip() or None,
                    "is_active": True,
                    "updated_at": now,
                    **campaign_fields,
                },
                "$setOnInsert": insert_defaults,
            },
            upsert=True,
        )
        if should_promote:
            product_doc = await products.find_one({"slug": slug}, {"_id": 1})
            if product_doc:
                await db["notifications"].update_one(
                    {"dedupe_key": f"campaign:{str(product_doc['_id'])}:3 al 2 ode"},
                    {
                        "$set": {
                            "title": "Yeni kampanya var",
                            "body": f"{name} icin 3 Al 2 Ode kampanyasi basladi.",
                            "type": "campaign",
                            "audience": "all",
                            "product_id": product_doc["_id"],
                            "product_name": name,
                            "promotion_label": "3 Al 2 Ode",
                            "is_active": True,
                            "updated_at": now,
                        },
                        "$setOnInsert": {
                            "created_at": now,
                            "read_by": [],
                        },
                    },
                    upsert=True,
                )
        imported += 1
        if result.upserted_id:
            created += 1
        else:
            updated += result.modified_count

    client.close()
    print(f"Imported {imported} rows. Created: {created}, updated: {updated}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-category", type=int, default=None, help="Limit imported rows from each CSV file.")
    parser.add_argument("--campaign-samples", action="store_true", help="Mark a small deterministic sample as campaigns.")
    parser.add_argument(
        "--csv-glob",
        default="migros_urunler_*.csv",
        help="CSV glob relative to project root. Defaults to category files only to avoid duplicate combined CSV rows.",
    )
    args = parser.parse_args()
    asyncio.run(import_products(args.per_category, args.campaign_samples, args.csv_glob))


if __name__ == "__main__":
    main()
