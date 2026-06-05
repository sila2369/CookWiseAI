"""Match recipe ingredients to real products from MongoDB."""

from __future__ import annotations

import re
from typing import Any

from app.utils.recipe_utils import normalize_text


class ProductMatchingService:
    FOOD_CATEGORY_HINTS = {
        "meyve sebze",
        "meyve-sebze",
        "et tavuk balik",
        "et-tavuk-balik",
        "temel gida",
        "temel-gida",
        "sut urunleri",
        "sut-urunleri",
        "sut kahvaltilik",
        "firin pastane",
        "firin-pastane",
        "meze hazir yemek donuk",
        "meze-hazir-yemek-donuk",
    }

    NON_FOOD_TOKENS = {
        "deterjan",
        "temizleyici",
        "camasir",
        "bulasik",
        "sabun",
        "sampuan",
        "pecete",
        "havlu",
        "mendil",
        "kozmetik",
        "kedi",
        "kopek",
    }

    PROCESSED_TOKENS = {
        "kozlenmis",
        "kurutulmus",
        "konserve",
        "tursu",
        "puresi",
        "salcasi",
        "sosu",
        "dolgulu",
        "hazir",
        "donuk",
    }

    INGREDIENT_SPECS = {
        "patlican": {
            "aliases": {"patlican", "patlicanlar"},
            "required_any": {"patlican"},
            "preferred_categories": {"meyve sebze", "meyve-sebze"},
            "preferred_tokens": {"kemer", "bostan", "kg"},
            "bad_tokens": PROCESSED_TOKENS.union({"dolmalik"}),
        },
        "kiyma": {
            "aliases": {"kiyma", "kiymalik", "kıyma"},
            "required_any": {"kiyma", "kiymalik"},
            "preferred_categories": {"et tavuk balik", "et-tavuk-balik"},
            "preferred_tokens": {"dana", "kuzu", "kasap"},
            "bad_tokens": {"manti", "pelmeni", "borek", "pide", "pizza", "kiymali"},
        },
        "sogan": {
            "aliases": {"sogan", "kuru sogan", "soganlar"},
            "required_any": {"sogan"},
            "preferred_categories": {"meyve sebze", "meyve-sebze"},
            "preferred_tokens": {"kuru", "kg", "yeni", "mahsul"},
            "bad_tokens": PROCESSED_TOKENS.union({"taze", "arpacik", "toz"}),
        },
        "domates": {
            "aliases": {"domates", "domatesler"},
            "required_any": {"domates"},
            "preferred_categories": {"meyve sebze", "meyve-sebze"},
            "preferred_tokens": {"kg", "yerli"},
            "bad_tokens": PROCESSED_TOKENS.union(
                {"salca", "rende", "rendesi", "kokteyl", "pembe", "salkim", "ceri", "mini", "atistirmalik", "siyah"}
            ),
        },
        "biber": {
            "aliases": {"biber", "biberler", "yesil biber", "sivri biber", "carliston biber"},
            "required_any": {"biber"},
            "preferred_categories": {"meyve sebze", "meyve-sebze"},
            "preferred_tokens": {"sivri", "carliston", "koy", "kg"},
            "bad_tokens": PROCESSED_TOKENS.union({"pul", "toz", "karabiber", "zeytin"}),
        },
        "sarimsak": {
            "aliases": {"sarimsak"},
            "required_any": {"sarimsak"},
            "preferred_categories": {"meyve sebze", "meyve-sebze"},
            "preferred_tokens": {"taze", "kg", "puresi"},
            "bad_tokens": {"soslu", "dolgulu"},
        },
        "tuz": {
            "aliases": {"tuz"},
            "required_any": {"tuz"},
            "preferred_categories": {"temel gida", "temel-gida"},
            "preferred_tokens": {"sofra", "deniz", "iyotlu"},
            "bad_tokens": {"tuzsuz", "ilave", "edilmemis", "ekmek", "kraker"},
        },
        "pul biber": {
            "aliases": {"pul biber", "kirmizi pul biber"},
            "required_all": {"pul", "biber"},
            "preferred_categories": {"temel gida", "temel-gida"},
            "preferred_tokens": {"baharat"},
            "bad_tokens": {"kozlenmis", "salca", "zeytin"},
        },
        "toz biber": {
            "aliases": {"toz biber", "kirmizi toz biber"},
            "required_all": {"toz", "biber"},
            "preferred_categories": {"temel gida", "temel-gida"},
            "preferred_tokens": {"baharat", "tatli"},
            "bad_tokens": {"kozlenmis", "salca", "zeytin"},
        },
        "domates salcasi": {
            "aliases": {"domates salcasi", "salca"},
            "required_all": {"domates", "salca"},
            "preferred_categories": {"temel gida", "temel-gida"},
            "preferred_tokens": {"cam", "migros", "tat"},
            "bad_tokens": {"kozlenmis", "tursu"},
        },
        "sivi yag": {
            "aliases": {"sivi yag", "aycicek yagi", "yag"},
            "required_any": {"yag", "yagi"},
            "preferred_categories": {"temel gida", "temel-gida"},
            "preferred_tokens": {"aycicek", "sivi"},
            "bad_tokens": {"zeytin", "tereyag", "sac", "bakim"},
        },
    }

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.products = db["products"]

    async def match_ingredients_to_products(self, ingredients: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        matched: list[dict[str, Any]] = []
        missing: list[dict[str, str]] = []
        seen_product_ids: set[str] = set()
        product_cache = await self._load_active_products()

        for ingredient in ingredients:
            ingredient_name = str(ingredient.get("name") or ingredient.get("raw") or "").strip()
            ingredient_norm = self._normalize_ingredient_for_match(
                str(ingredient.get("normalized_name") or ingredient_name)
            )
            if not ingredient_norm:
                continue
            product = self._best_match(ingredient_norm, product_cache)
            if product:
                if product["id"] in seen_product_ids:
                    continue
                seen_product_ids.add(product["id"])
                matched.append(
                    {
                        "ingredient": ingredient_name,
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "price": product["price"],
                        "image_url": product.get("image_url"),
                    }
                )
            else:
                missing.append(
                    {
                        "ingredient": ingredient_name,
                        "reason": "Urun veritabaninda bulunamadi",
                    }
                )

        return {"matched_products": matched, "missing_products": missing}

    def _normalize_ingredient_for_match(self, value: str) -> str:
        normalized = normalize_text(value)
        normalized = re.sub(r"\([^)]*\)", " ", normalized)
        normalized = re.sub(r"\b(sos icin|ici icin|ustu icin|hamuru icin|servis icin)\b", " ", normalized)

        removable_tokens = {
            "rendelenmis",
            "rendelenmiş",
            "dogranmis",
            "dogranmış",
            "ince",
            "iri",
            "kucuk",
            "buyuk",
            "taze",
            "istege",
            "bagli",
            "aldigi",
            "kadar",
            "biraz",
            "az",
            "cok",
        }
        tokens = [token for token in normalized.split() if token not in removable_tokens]
        return " ".join(tokens).strip()

    async def _load_active_products(self) -> list[dict[str, Any]]:
        category_map: dict[str, dict[str, str]] = {}
        categories_cursor = self.db["categories"].find({}, {"name": 1, "slug": 1})
        async for category_doc in categories_cursor:
            category_map[str(category_doc.get("_id"))] = {
                "name": str(category_doc.get("name") or ""),
                "slug": str(category_doc.get("slug") or ""),
            }

        cursor = self.products.find(
            {"is_active": True, "stock": {"$gt": 0}},
            {"name": 1, "price": 1, "image_url": 1, "brand": 1, "unit": 1, "category_id": 1},
        )
        products: list[dict[str, Any]] = []
        async for doc in cursor:
            name = str(doc.get("name") or "")
            category = category_map.get(str(doc.get("category_id") or ""), {})
            products.append(
                {
                    "id": str(doc.get("_id")),
                    "name": name,
                    "normalized_name": normalize_text(name),
                    "price": float(doc.get("price") or 0.0),
                    "image_url": doc.get("image_url"),
                    "category_name": category.get("name", ""),
                    "category_slug": category.get("slug", ""),
                    "normalized_category": normalize_text(
                        f"{category.get('name', '')} {category.get('slug', '')}"
                    ),
                }
            )
        return products

    def _best_match(self, ingredient_norm: str, products: list[dict[str, Any]]) -> dict[str, Any] | None:
        canonical = self._canonical_ingredient(ingredient_norm)
        spec = self.INGREDIENT_SPECS.get(canonical)
        tokens = [token for token in ingredient_norm.split() if len(token) >= 3]
        if not tokens:
            tokens = [ingredient_norm]

        best: tuple[float, dict[str, Any] | None] = (0.0, None)
        for product in products:
            product_norm = product["normalized_name"]
            product_tokens = set(re.findall(r"[a-z0-9]+", product_norm))
            category_norm = str(product.get("normalized_category") or "")
            category_tokens = set(re.findall(r"[a-z0-9]+", category_norm))
            if ingredient_norm == "tuz" and (
                "ilave edilmemis" in product_norm
                or "tuzsuz" in product_norm
                or "ekmek" in product_tokens
            ):
                continue
            if any(token in product_tokens for token in self.NON_FOOD_TOKENS):
                continue
            if spec and not self._product_allowed_by_spec(spec, product_tokens):
                continue

            score = 0.0

            if len(tokens) >= 2:
                if all(token in product_tokens for token in tokens):
                    score += 7.0
                elif ingredient_norm in product_norm:
                    score += 5.0
            else:
                token = tokens[0]
                if token in product_tokens:
                    score += 5.0
                elif len(token) >= 5 and any(product_token.startswith(token) for product_token in product_tokens):
                    score += 1.5
            if product_norm and product_norm in ingredient_norm:
                score += 1.5
            if spec:
                score += self._spec_score(spec, product_tokens, category_tokens, product_norm, category_norm)
            if score > best[0]:
                best = (score, product)

        threshold = 7.0 if spec else 5.0
        return best[1] if best[0] >= threshold else None

    def _canonical_ingredient(self, ingredient_norm: str) -> str:
        normalized = normalize_text(ingredient_norm)
        if "salca" in normalized and "domates" in normalized:
            return "domates salcasi"
        if "pul" in normalized and "biber" in normalized:
            return "pul biber"
        if "toz" in normalized and "biber" in normalized:
            return "toz biber"
        if "aycicek" in normalized or "sivi yag" in normalized:
            return "sivi yag"
        for canonical, spec in self.INGREDIENT_SPECS.items():
            aliases = spec.get("aliases", set())
            if any(alias in normalized for alias in aliases):
                return canonical
        return normalized

    def _product_allowed_by_spec(self, spec: dict[str, Any], product_tokens: set[str]) -> bool:
        required_all = set(spec.get("required_all") or set())
        if required_all and not required_all.issubset(product_tokens):
            return False
        required_any = set(spec.get("required_any") or set())
        if required_any and not required_any.intersection(product_tokens):
            return False
        return True

    def _spec_score(
        self,
        spec: dict[str, Any],
        product_tokens: set[str],
        category_tokens: set[str],
        product_norm: str,
        category_norm: str,
    ) -> float:
        score = 0.0
        preferred_categories = {normalize_text(item) for item in spec.get("preferred_categories", set())}
        if preferred_categories and any(category in category_norm for category in preferred_categories):
            score += 8.0
        elif category_tokens and not any(category in category_norm for category in self.FOOD_CATEGORY_HINTS):
            score -= 8.0

        preferred_tokens = set(spec.get("preferred_tokens") or set())
        score += 1.5 * len(preferred_tokens.intersection(product_tokens))

        bad_tokens = set(spec.get("bad_tokens") or set())
        score -= 5.0 * len(bad_tokens.intersection(product_tokens))

        if "kg" in product_tokens:
            score += 1.0
        if any(token in product_tokens for token in ("adet", "paket")):
            score += 0.2
        if any(token in product_norm for token in ("organik", "m life")):
            score -= 0.4
        return score
