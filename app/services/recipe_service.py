"""Recipe search service backed by MongoDB."""

from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.schemas.recipe import recipe_doc_to_response
from app.utils.recipe_utils import normalize_text


class RecipeService:
    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.recipes = db["recipes"]

    def normalize_recipe_query(self, query: str) -> str:
        return normalize_text(query)

    async def search_recipe_by_name(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        normalized = normalize_text(query)
        normalized = self._normalize_alias(normalized)
        if not normalized:
            return []

        scan_limit = max(limit * 5, 25)
        exact_cursor = self.recipes.find(
            {
                "is_active": True,
                "$or": [
                    {"normalized_name": normalized},
                    {"normalized_name": {"$regex": f"(^| ){normalized}( |$)", "$options": "i"}},
                    {"normalized_name": {"$regex": normalized, "$options": "i"}},
                ],
            }
        ).limit(scan_limit)
        exact_results = [recipe_doc_to_response(doc) async for doc in exact_cursor]
        if exact_results:
            return self._rank_results(exact_results, normalized)[:limit]

        tokens = [token for token in normalized.split() if len(token) >= 3]
        if not tokens:
            return []

        token_cursor = self.recipes.find(
            {
                "is_active": True,
                "$and": [{"normalized_name": {"$regex": token, "$options": "i"}} for token in tokens],
            }
        ).limit(scan_limit)
        token_results = [recipe_doc_to_response(doc) async for doc in token_cursor]
        return self._rank_results(token_results, normalized)[:limit]

    async def get_recipe_by_id(self, recipe_id: str) -> dict[str, Any] | None:
        try:
            oid = ObjectId(recipe_id)
        except Exception:
            return None
        doc = await self.recipes.find_one({"_id": oid, "is_active": True})
        return recipe_doc_to_response(doc) if doc else None

    async def find_recipes_by_ingredients(self, ingredients: list[str], limit: int = 10) -> list[dict[str, Any]]:
        normalized = [normalize_text(item) for item in ingredients if normalize_text(item)]
        if not normalized:
            return []

        cursor = self.recipes.find(
            {
                "is_active": True,
                "$or": [
                    {"ingredients.normalized_name": {"$regex": ingredient, "$options": "i"}}
                    for ingredient in normalized
                ],
            }
        ).limit(limit)
        docs = [recipe_doc_to_response(doc) async for doc in cursor]
        return sorted(
            docs,
            key=lambda recipe: self._ingredient_score(recipe, normalized),
            reverse=True,
        )

    def _normalize_alias(self, normalized_query: str) -> str:
        aliases = {
            "karniyarik": ("karniyarik", "karniyarin"),
            "manti": ("manti", "manta", "mant"),
            "menemen": ("menemen",),
            "pizza": ("pizza", "piza"),
            "kayseri mantisi": ("kayseri manti", "kayseri mantisi"),
        }
        for canonical, variants in aliases.items():
            if any(variant in normalized_query for variant in variants):
                return canonical
        return normalized_query

    def _rank_results(self, recipes: list[dict[str, Any]], normalized_query: str) -> list[dict[str, Any]]:
        query_tokens = set(normalized_query.split())

        def score(recipe: dict[str, Any]) -> tuple[int, int]:
            name = str(recipe.get("normalized_name") or "")
            name_tokens = set(name.split())
            exact = 20 if name == normalized_query else 0
            contains = 10 if normalized_query in name else 0
            overlap = len(query_tokens.intersection(name_tokens))
            ingredient_text = " ".join(
                str(item.get("normalized_name") or "")
                for item in recipe.get("ingredients", [])
                if isinstance(item, dict)
            )
            profile_bonus = 0
            if "manti" in normalized_query:
                profile_bonus += sum(
                    2
                    for token in ("kiyma", "yogurt", "sogan", "sarimsak")
                    if token in ingredient_text
                )
            if "menemen" in normalized_query:
                profile_bonus += sum(
                    2
                    for token in ("yumurta", "domates", "biber")
                    if token in ingredient_text
                )
            return (exact + contains + overlap + profile_bonus, -len(name))

        return sorted(recipes, key=score, reverse=True)

    def _ingredient_score(self, recipe: dict[str, Any], normalized_ingredients: list[str]) -> int:
        recipe_ingredients = " ".join(
            str(item.get("normalized_name") or "")
            for item in recipe.get("ingredients", [])
            if isinstance(item, dict)
        )
        return sum(1 for ingredient in normalized_ingredients if ingredient in recipe_ingredients)
