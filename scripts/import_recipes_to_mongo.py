"""Import cleaned recipes JSON into MongoDB.

Usage:
  python scripts/import_recipes_to_mongo.py --input cleaned_recipes.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


async def import_recipes(input_path: Path) -> None:
    recipes = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(recipes, list):
        raise ValueError("Input JSON must contain a list")

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    collection = db["recipes"]
    now = datetime.utcnow()

    await collection.create_index("normalized_name", unique=True)
    await collection.create_index("category")
    await collection.create_index("ingredients.normalized_name")
    await collection.create_index("is_active")

    inserted = 0
    skipped = 0
    for recipe in recipes:
        normalized_name = recipe.get("normalized_name")
        if not normalized_name:
            skipped += 1
            continue
        recipe.setdefault("created_at", now)
        recipe["updated_at"] = now
        result = await collection.update_one(
            {"normalized_name": normalized_name},
            {"$setOnInsert": recipe},
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
        else:
            skipped += 1

    client.close()
    print(f"Recipes import complete. inserted={inserted}, skipped={skipped}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="cleaned_recipes.json", help="Cleaned recipes JSON path")
    args = parser.parse_args()
    asyncio.run(import_recipes(Path(args.input)))


if __name__ == "__main__":
    main()
