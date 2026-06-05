"""
Unified AI generation service.

Routes all AI modes through one orchestration layer:
- selects mode
- builds prompt
- calls mode engine
- returns structured response
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId

from app.ai.modes import AIMode
from app.ai.prompt_builder import (
    COOKWISE_JSON_SYSTEM_PROMPT,
    build_budget_json_prompt,
    build_diet_json_prompt,
    build_inventory_json_prompt,
    build_normal_json_prompt,
    build_prompt,
    build_weekly_plan_json_prompt,
    is_likely_greeting_or_smalltalk,
)
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.grok_provider import GrokProvider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.core.config import settings
from app.services.ai_budget_service import BudgetModeService
from app.services.ai_diet_service import DietModeService
from app.services.ai_inventory_service import InventoryModeService
from app.services.ai_weekly_planner_service import WeeklyPlannerService
from app.services.product_matching_service import ProductMatchingService
from app.services.recipe_service import RecipeService
from app.utils.recipe_utils import normalize_text


class AIGenerateService:
    """Production-ready orchestrator for single-endpoint AI generation."""

    def __init__(self) -> None:
        self.budget_service = BudgetModeService()
        self.diet_service = DietModeService()
        self.inventory_service = InventoryModeService()
        self.weekly_planner_service = WeeklyPlannerService()

        self.openai_provider = None
        self.gemini_provider = None
        self.grok_provider = None
        self.groq_provider = None
        self.ollama_provider = None
        
        provider = str(getattr(settings, "AI_PROVIDER", "local")).lower()
        if provider == "openai":
            if not getattr(settings, "OPENAI_API_KEY", None):
                self.openai_provider = None
            else:
                self.openai_provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
        elif provider == "gemini":
            if not getattr(settings, "GEMINI_API_KEY", None):
                self.gemini_provider = None
            else:
                self.gemini_provider = GeminiProvider(api_key=settings.GEMINI_API_KEY)
        elif provider == "grok":
            xai_api_key = getattr(settings, "XAI_API_KEY", None)
            xai_base_url = str(getattr(settings, "XAI_BASE_URL", "https://api.x.ai/v1")).strip()
            if xai_api_key:
                self.grok_provider = GrokProvider(api_key=xai_api_key, base_url=xai_base_url)
        elif provider == "groq":
            groq_api_key = getattr(settings, "GROQ_API_KEY", None)
            groq_base_url = str(getattr(settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1")).strip()
            if groq_api_key:
                self.groq_provider = GroqProvider(api_key=groq_api_key, base_url=groq_base_url)
        elif provider == "ollama":
            ollama_base_url = str(getattr(settings, "OLLAMA_BASE_URL", "http://host.docker.internal:11434")).strip()
            if ollama_base_url:
                self.ollama_provider = OllamaProvider(base_url=ollama_base_url)

    def _build_llm_prompt(self, mode: AIMode, user_input: str, preferences: dict | None) -> tuple[str, str]:
        prefs = preferences or {}
        user_norm = self._normalize_text(user_input)
        prompt: str
        suffix: str
        if mode == AIMode.BUDGET:
            prompt = build_budget_json_prompt(user_input=user_input, context=prefs.get("context"))
            suffix = "budget"
        elif mode == AIMode.DIET:
            goal = str(prefs.get("goal", "low_calorie"))
            prompt = build_diet_json_prompt(
                user_input=user_input,
                goal=goal,
                context=prefs.get("context"),
            )
            suffix = "diet"
        elif mode == AIMode.INVENTORY:
            ingredients = prefs.get("available_ingredients")
            if not isinstance(ingredients, list) or not ingredients:
                ingredients = [item.strip() for item in user_input.split(",") if item.strip()]
            prompt = build_inventory_json_prompt(
                available_ingredients=ingredients,
                context=prefs.get("context"),
            )
            suffix = "inventory"
        elif mode == AIMode.WEEKLY:
            prompt = build_weekly_plan_json_prompt(
                user_request=user_input,
                context=prefs.get("context"),
            )
            suffix = "weekly"
        else:
            prompt = build_normal_json_prompt(user_input=user_input, context=prefs.get("context"))
            suffix = "normal"

        if suffix == "normal" and is_likely_greeting_or_smalltalk(user_input):
            prompt += (
                "\n\n[NON_RECIPE_USER_MESSAGE]\n"
                "- Son [USER_REQUEST] yalnızca selamlaşma, teşekkür veya kısa sohbet; yemek talebi yok.\n"
                "- Uydurma tarif, malzeme veya detaylı pişirme anlatma.\n"
                "- title ve recipe kısa genel olsun (ör. recipe=\"Sohbet\" veya \"Karşılama\").\n"
                "- summary ve description: 1-3 cümle sıcak karşılık; ne pişirebileceğini nazikçe sor.\n"
                "- ingredients: [], preparation: [], optional_sides: [], optional_drinks: [].\n"
                "- steps: en fazla 1 kısa madde (davet veya yönlendirme).\n"
                "- calories, protein, carbs, fats: \"-\" veya \"Uygulanmıyor\".\n"
                "- shopping_recommendations: [].\n"
                "- [MARKET_CART_RULES] yoksa market_cart ekleme."
            )

        if suffix == "normal" and ("karniyarik" in user_norm or "karnıyarık" in user_input.lower()):
            prompt += (
                "\n\n[DISH_SPECIFIC_RULES]\n"
                "- Requested dish is karniyarik.\n"
                "- Core ingredients should be: patlican, kiyma, sogan, domates, biber, sarimsak.\n"
                "- Do NOT include egg/yumurta in ingredients unless user explicitly asks for it.\n"
                "- Keep response faithful to classic Turkish karniyarik."
            )
        if suffix == "normal" and ("makarna" in user_norm and ("sebze" in user_norm or "sebzeli" in user_norm)):
            prompt += (
                "\n\n[DISH_SPECIFIC_RULES]\n"
                "- Requested dish is sebzeli makarna.\n"
                "- Prefer pasta-compatible vegetables: domates, biber, kabak, mantar, sogan, sarimsak.\n"
                "- Do NOT include cucumber/salatalik or lettuce/marul unless user explicitly asks.\n"
                "- Keep response as a hot main dish, not salad."
            )

        if bool(prefs.get("include_market_cart")):
            prompt += (
                "\n\n[MARKET_CART_RULES]\n"
                "- market_cart yalnızca tarifle doğrudan ilişkili veya pişirmeyi tamamlayan ürünleri içersin.\n"
                "- Temizlik, kozmetik, ev gereci gibi gıda dışı ürünleri ekleme (kullanıcı özellikle istemedikçe).\n"
                "- product_id değerleri yalnızca [CONTEXT] içinde listelenen stoklu ürün id'lerinden seçilsin; uydurma id yasak.\n"
                "- Miktarları birim ve stokla uyumlu, gerçekçi seç (tam sayı veya mantıklı ondalık).\n"
                "- Aynı ürün ailesini gereksiz çoğaltma; sepet öz ama eksiksiz olsun.\n"
                "- shopping_recommendations: hangi ürün tipinin neden uygun olduğuna dair kısa cümleler (abartısız).\n"
                "- Yanıtta market_cart zorunlu: {\"items\": [{\"product_id\": \"...\", \"quantity\": number}, ...]}.\n"
                "- Önce ana protein/temel malzeme, sonra yardımcı malzemeler (yağ, baharat vb.) önceliği."
            )
        return (prompt, suffix)

    def _safe_json_parse(self, text: str) -> Dict[str, Any]:
        """
        Parse model output into JSON dict safely.
        Falls back to extracting the first JSON object substring.
        """
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
            raise ValueError("Parsed JSON is not an object")
        except Exception:
            pass

        # Extract first JSON object from the response
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in model output")

        candidate = match.group(0)
        data = json.loads(candidate)
        if not isinstance(data, dict):
            raise ValueError("Extracted JSON is not an object")
        return data

    def _validate_mode_keys(self, mode: AIMode, obj: Dict[str, Any]) -> bool:
        # Minimal validation to ensure structured response shape.
        if mode == AIMode.BUDGET:
            required = {"dish", "ingredients", "total_cost", "budget_tip"}
        elif mode == AIMode.DIET:
            required = {"dish", "goal", "ingredients", "calories", "macros"}
        elif mode == AIMode.INVENTORY:
            required = {"possible_dishes"}
        elif mode == AIMode.WEEKLY:
            required = {"request", "weekly_plan", "shopping_list", "optimization_note"}
        else:
            required = set()
        return required.issubset(set(obj.keys()))

    def _extract_servings(self, user_input: str) -> int:
        """
        Extract serving count from common Turkish/English patterns.
        Defaults to 2 servings when no explicit count exists.
        """
        text = user_input.lower()
        patterns = [
            r"(\d+)\s*kişilik",
            r"(\d+)\s*k\w*ilik",
            r"(\d+)\s*kişi",
            r"(\d+)\s*porsiyon",
            r"for\s+(\d+)\s*people",
            r"(\d+)\s*servings?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = int(match.group(1))
                    return max(1, min(value, 12))
                except Exception:
                    continue
        return 2

    async def _fetch_in_stock_products(self, db: Any, limit: int = 800) -> List[Dict[str, Any]]:
        if db is None:
            return []
        category_map: Dict[str, Dict[str, str]] = {}
        categories_cursor = db["categories"].find({}, {"name": 1, "slug": 1})
        async for category_doc in categories_cursor:
            category_map[str(category_doc.get("_id"))] = {
                "name": str(category_doc.get("name") or ""),
                "slug": str(category_doc.get("slug") or ""),
            }

        cursor = db["products"].find(
            {"is_active": True, "stock": {"$gt": 0}, "image_url": {"$nin": [None, ""]}},
            {
                "name": 1,
                "price": 1,
                "stock": 1,
                "brand": 1,
                "unit": 1,
                "category_id": 1,
                "image_url": 1,
            },
        ).limit(limit)
        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            items.append(
                {
                    "id": str(doc.get("_id")),
                    "name": str(doc.get("name") or ""),
                    "price": float(doc.get("price") or 0.0),
                    "stock": int(doc.get("stock") or 0),
                    "brand": str(doc.get("brand") or ""),
                    "unit": str(doc.get("unit") or ""),
                    "category_id": str(doc.get("category_id") or ""),
                    "category_name": category_map.get(str(doc.get("category_id") or ""), {}).get("name", ""),
                    "category_slug": category_map.get(str(doc.get("category_id") or ""), {}).get("slug", ""),
                }
            )
        return items

    def _build_market_context(
        self,
        products: List[Dict[str, Any]],
        max_items: int = 30,
        include_market_cart: bool = True,
        hint_text: str = "",
    ) -> str:
        hint_tokens = set(self._tokens(hint_text))

        def _product_match_score(product: Dict[str, Any]) -> int:
            if not hint_tokens:
                return 0
            haystack = self._normalize_text(
                f"{product.get('name') or ''} {product.get('brand') or ''} {product.get('category_name') or ''} {product.get('category_slug') or ''}"
            )
            return sum(1 for token in hint_tokens if token in haystack)

        ranked_products = sorted(products, key=_product_match_score, reverse=True) if hint_tokens else list(products)
        selected_for_context = ranked_products[:max_items]

        lines = []
        for p in selected_for_context:
            name_norm = self._normalize_text(str(p["name"]))
            if any(x in name_norm for x in ("havlu", "deterjan", "temizleyici", "camasir", "bulasik", "sabun", "sampuan")):
                continue
            lines.append(
                f"- id={p['id']}; name={p['name']}; price={p['price']:.2f}; stock={p['stock']}; brand={p.get('brand') or '-'}; unit={p.get('unit') or '-'}; category={p.get('category_name') or '-'}"
            )
        intro = (
            "Asagidaki markette stokta olan urunleri dikkate al.\n"
            "Asla stok disi urun kullanma.\n"
        )
        if include_market_cart:
            intro += "Sepet istenirse urun adlarini ve miktarlari gercekci sec. Mumkunse response icinde market_cart alani don.\n"
        return intro + "\n".join(lines)

    def _tokens(self, text: str) -> List[str]:
        return [t for t in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", self._normalize_text(text)) if len(t) >= 2]

    def _normalize_text(self, text: str) -> str:
        t = (text or "").lower()
        mapping = str.maketrans({
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        })
        return t.translate(mapping)

    def _extract_response_text(self, response_obj: Dict[str, Any]) -> str:
        parts: List[str] = []
        for key in ("dish", "title", "description", "recipe", "summary", "message", "request"):
            value = response_obj.get(key)
            if isinstance(value, str):
                parts.append(value)
        chef_notes = response_obj.get("chef_notes")
        if isinstance(chef_notes, str):
            parts.append(chef_notes)
        elif isinstance(chef_notes, list):
            parts.extend([str(x) for x in chef_notes if isinstance(x, str)])
        shopping = response_obj.get("shopping_recommendations")
        if isinstance(shopping, str):
            parts.append(shopping)
        elif isinstance(shopping, list):
            parts.extend([str(x) for x in shopping if isinstance(x, str)])
        ingredients = response_obj.get("ingredients")
        if isinstance(ingredients, list):
            for ing in ingredients:
                if isinstance(ing, str):
                    parts.append(ing)
                elif isinstance(ing, dict):
                    item_name = ing.get("item")
                    qty = ing.get("quantity")
                    if isinstance(item_name, str):
                        parts.append(item_name)
                    if isinstance(qty, str):
                        parts.append(qty)
        steps = response_obj.get("steps")
        if isinstance(steps, list):
            parts.extend([str(step) for step in steps if isinstance(step, str)])
        preparation = response_obj.get("preparation")
        if isinstance(preparation, list):
            parts.extend([str(step) for step in preparation if isinstance(step, str)])
        serving_suggestion = response_obj.get("serving_suggestion")
        if isinstance(serving_suggestion, str):
            parts.append(serving_suggestion)
        optional_sides = response_obj.get("optional_sides")
        if isinstance(optional_sides, str):
            parts.append(optional_sides)
        elif isinstance(optional_sides, list):
            parts.extend([str(item) for item in optional_sides if isinstance(item, str)])
        optional_drinks = response_obj.get("optional_drinks")
        if isinstance(optional_drinks, str):
            parts.append(optional_drinks)
        elif isinstance(optional_drinks, list):
            parts.extend([str(item) for item in optional_drinks if isinstance(item, str)])
        tips = response_obj.get("tips")
        if isinstance(tips, str):
            parts.append(tips)
        elif isinstance(tips, list):
            parts.extend([str(tip) for tip in tips if isinstance(tip, str)])
        plan = response_obj.get("plan")
        if isinstance(plan, dict):
            recipe = plan.get("recipe")
            if isinstance(recipe, str):
                parts.append(recipe)
            plan_ings = plan.get("ingredients")
            if isinstance(plan_ings, list):
                for ing in plan_ings:
                    if isinstance(ing, dict) and isinstance(ing.get("item"), str):
                        parts.append(ing["item"])
                    elif isinstance(ing, str):
                        parts.append(ing)
        return " ".join(parts)

    def _sanitize_response_for_common_dishes(self, user_input: str, response_obj: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(response_obj, dict):
            return response_obj
        normalized_input = self._normalize_text(user_input)
        ingredients = response_obj.get("ingredients")
        if not isinstance(ingredients, list):
            return response_obj

        banned_tokens: set[str] = set()
        if "karniyarik" in normalized_input:
            banned_tokens.update({"yumurta", "egg"})
        if "makarna" in normalized_input and ("sebze" in normalized_input or "sebzeli" in normalized_input):
            banned_tokens.update({"salatalik", "marul", "iceberg", "gobek"})
        if not banned_tokens:
            return response_obj

        filtered_ingredients: List[Any] = []
        for ing in ingredients:
            if isinstance(ing, str):
                if any(tok in self._normalize_text(ing) for tok in banned_tokens):
                    continue
                filtered_ingredients.append(ing)
                continue
            if isinstance(ing, dict):
                item_name = self._normalize_text(str(ing.get("item") or ""))
                if any(tok in item_name for tok in banned_tokens):
                    continue
                filtered_ingredients.append(ing)
                continue
            filtered_ingredients.append(ing)

        response_obj["ingredients"] = filtered_ingredients
        return response_obj

    def _normalize_normal_mode_response(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Eski istemciler için recipe/summary/cook_time alanlarını yeni şema ile hizalar."""
        if not isinstance(obj, dict):
            return obj

        title = obj.get("title")
        if isinstance(title, str) and title.strip():
            rec = obj.get("recipe")
            if not (isinstance(rec, str) and rec.strip()):
                obj["recipe"] = title.strip()

        desc = obj.get("description")
        if isinstance(desc, str) and desc.strip():
            summ = obj.get("summary")
            if not (isinstance(summ, str) and summ.strip()):
                obj["summary"] = desc.strip()

        ct = obj.get("cooking_time")
        if isinstance(ct, str) and ct.strip():
            ck = obj.get("cook_time")
            if not (isinstance(ck, str) and ck.strip()):
                obj["cook_time"] = ct.strip()
        ck2 = obj.get("cook_time")
        if isinstance(ck2, str) and ck2.strip():
            ct2 = obj.get("cooking_time")
            if not (isinstance(ct2, str) and ct2.strip()):
                obj["cooking_time"] = ck2.strip()

        macros = obj.get("macros")
        if isinstance(macros, dict):
            if not obj.get("protein") and macros.get("protein") is not None:
                obj["protein"] = str(macros.get("protein"))
            carb_val = macros.get("carbs") if macros.get("carbs") is not None else macros.get("carb")
            if not obj.get("carbs") and carb_val is not None:
                obj["carbs"] = str(carb_val)
            fat_val = macros.get("fats") if macros.get("fats") is not None else macros.get("fat")
            if not obj.get("fats") and fat_val is not None:
                obj["fats"] = str(fat_val)

        def _ensure_str_list(key: str) -> None:
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                obj[key] = [val.strip()]
            elif isinstance(val, list):
                obj[key] = [str(x).strip() for x in val if isinstance(x, str) and str(x).strip()]

        _ensure_str_list("tips")
        _ensure_str_list("chef_notes")
        _ensure_str_list("shopping_recommendations")
        _ensure_str_list("optional_sides")
        _ensure_str_list("optional_drinks")

        return obj

    def _normalize_llm_market_cart(
        self,
        market_cart: Dict[str, Any],
        products: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """LLM'in sepetini stoktaki urunlerle dogrula ve frontend icin zenginlestir."""
        if not isinstance(market_cart, dict):
            return {"items": [], "total_estimated": 0.0, "currency": "TRY", "notes": ["LLM sepeti gecersiz."]}

        product_by_id = {str(p.get("id")): p for p in products if p.get("id")}
        raw_items = market_cart.get("items")
        if not isinstance(raw_items, list):
            return {"items": [], "total_estimated": 0.0, "currency": "TRY", "notes": ["LLM sepetinde items yok."]}

        normalized_items: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            product_id = str(item.get("product_id") or "").strip()
            product = product_by_id.get(product_id)
            if product is None or product_id in seen_ids:
                continue

            raw_qty = item.get("quantity", 1)
            try:
                qty = int(float(str(raw_qty).strip().replace(",", ".")))
            except Exception:
                qty = 1
            qty = max(1, min(qty, int(product.get("stock") or 1)))
            price = float(product.get("price") or 0.0)
            normalized_items.append(
                {
                    "product_id": product_id,
                    "name": product.get("name") or "Urun",
                    "brand": product.get("brand") or None,
                    "unit": product.get("unit") or None,
                    "price": round(price, 2),
                    "stock": int(product.get("stock") or 0),
                    "quantity": qty,
                    "subtotal": round(price * qty, 2),
                }
            )
            seen_ids.add(product_id)

        total = round(sum(float(item["subtotal"]) for item in normalized_items), 2)
        return {
            "items": normalized_items,
            "total_estimated": total,
            "currency": "TRY",
            "notes": ["LLM sepeti stoktaki aktif urunlerle dogrulandi."],
        }

    def _merge_market_carts(
        self,
        primary_cart: Dict[str, Any],
        fallback_cart: Dict[str, Any],
        max_items: int = 8,
    ) -> Dict[str, Any]:
        """LLM sepeti eksik kalirsa deterministik eslestirmeyle tamamla."""
        primary_items = primary_cart.get("items") if isinstance(primary_cart, dict) else []
        fallback_items = fallback_cart.get("items") if isinstance(fallback_cart, dict) else []
        merged_items: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        for source in (primary_items, fallback_items):
            if not isinstance(source, list):
                continue
            for item in source:
                if not isinstance(item, dict):
                    continue
                product_id = str(item.get("product_id") or "").strip()
                if not product_id or product_id in seen_ids:
                    continue
                merged_items.append(item)
                seen_ids.add(product_id)
                if len(merged_items) >= max_items:
                    break
            if len(merged_items) >= max_items:
                break

        total = round(sum(float(item.get("subtotal") or 0.0) for item in merged_items), 2)
        notes: List[str] = []
        for cart in (primary_cart, fallback_cart):
            raw_notes = cart.get("notes") if isinstance(cart, dict) else None
            if isinstance(raw_notes, list):
                notes.extend(str(note) for note in raw_notes if note)
        return {
            "items": merged_items,
            "total_estimated": total,
            "currency": "TRY",
            "notes": notes or ["Sepet stoktaki aktif urunlerden olusturuldu."],
        }

    def _ingredient_cart_tokens(self, response_obj: Dict[str, Any]) -> set[str]:
        """Only use actual recipe ingredients as cart anchors, not serving suggestions or side notes."""
        ingredients = response_obj.get("ingredients")
        if not isinstance(ingredients, list):
            recipe = response_obj.get("recipe")
            if isinstance(recipe, dict):
                ingredients = recipe.get("ingredients")
        if not isinstance(ingredients, list):
            return set()

        stopwords = {
            "adet", "gr", "g", "kg", "ml", "lt", "litre", "bardak", "kasigi", "kasik",
            "yemek", "tatli", "cay", "su", "tutam", "paket", "kase", "dilim",
            "istege", "bagli", "taze", "ince", "iri", "dogranmis", "rendelenmis",
            "tarife", "gore", "olculerine", "malzeme", "temel", "tatmakligi",
        }
        tokens: set[str] = set()
        for ingredient in ingredients:
            if isinstance(ingredient, str):
                source = ingredient
            elif isinstance(ingredient, dict):
                source = str(
                    ingredient.get("item")
                    or ingredient.get("name")
                    or ingredient.get("ingredient")
                    or ingredient.get("raw")
                    or ""
                )
            else:
                continue
            source_norm = self._normalize_text(source)
            if "pul biber" in source_norm:
                tokens.update({"pul"})
                continue
            if "toz biber" in source_norm:
                tokens.update({"toz"})
                continue
            if "salca" in source_norm:
                tokens.update({"salca"})
                continue
            for token in self._tokens(source):
                if len(token) >= 3 and token not in stopwords:
                    tokens.add(token)
        return tokens

    def _filter_market_cart_by_ingredients(
        self,
        market_cart: Dict[str, Any],
        ingredient_tokens: set[str],
    ) -> Dict[str, Any]:
        if not ingredient_tokens or not isinstance(market_cart, dict):
            return market_cart
        raw_items = market_cart.get("items")
        if not isinstance(raw_items, list):
            return market_cart

        filtered_items: List[Dict[str, Any]] = []
        removed_names: List[str] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            name = self._normalize_text(str(item.get("name") or ""))
            if any(token in name for token in ingredient_tokens):
                filtered_items.append(item)
            else:
                item_name = str(item.get("name") or "").strip()
                if item_name:
                    removed_names.append(item_name)

        total = round(sum(float(item.get("subtotal") or 0.0) for item in filtered_items), 2)
        notes = list(market_cart.get("notes") or []) if isinstance(market_cart.get("notes"), list) else []
        if removed_names:
            notes.append("Tarifte olmayan urunler sepetten cikarildi: " + ", ".join(removed_names[:5]))
        return {
            **market_cart,
            "items": filtered_items,
            "total_estimated": total,
            "currency": market_cart.get("currency") or "TRY",
            "notes": notes or ["Sepet yalnizca tarif malzemelerine gore filtrelendi."],
        }

    def _build_market_cart(
        self,
        *,
        mode: AIMode,
        user_input: str,
        preferences: dict | None,
        response_obj: Dict[str, Any],
        products: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prefs = preferences or {}
        servings = self._extract_servings(user_input)
        tokens = set(self._tokens(user_input + " " + self._extract_response_text(response_obj)))
        meal_category = self._normalize_text(str(prefs.get("meal_category") or ""))
        nutrition_goal = self._normalize_text(str(prefs.get("nutrition_goal") or ""))
        text_for_intent = self._normalize_text(user_input + " " + self._extract_response_text(response_obj))
        cleaning_intent = any(
            k in text_for_intent for k in ("temizlik", "deterjan", "bulasik", "camasir", "hijyen", "yumusatici", "cif")
        )
        dairy_intent = any(
            k in text_for_intent for k in ("sut", "süt", "peynir", "yogurt", "yoğurt", "ayran", "kefir", "kasar", "kaşar")
        )
        dessert_intent = any(
            k in text_for_intent
            for k in (
                "tatli", "tatlı", "dessert", "pasta", "kek", "kurabiye", "biskuvi", "bisküvi",
                "cikolata", "çikolata", "gofret", "dondurma", "baklava", "sutlac", "sütlaç", "waffle", "wafer",
            )
        )
        karniyarik_intent = "karniyarik" in text_for_intent or "karnıyarık" in user_input.lower()
        sebzeli_makarna_intent = "makarna" in text_for_intent and ("sebze" in text_for_intent or "sebzeli" in text_for_intent)
        recipe_hint_tokens: set[str] = set()
        recipe_hints = {
            ("menemen",): "yumurta domates biber sogan tereyag ekmek",
            ("makarna",): "makarna domates sos biber sogan sarimsak peynir",
            ("sebzeli makarna", "sebze makarna"): "makarna kabak biber mantar domates sogan sarimsak",
            ("lazanya", "lasagna"): "lazanya makarna kiyma domates sos besamel sut peynir kasar",
            ("kofte",): "kiyma sogan ekmek yumurta baharat patates yogurt",
            ("tavuk",): "tavuk pilic yogurt pirinc bulgur salata domates biber",
            ("pilav",): "pirinc tereyag sehriye tavuk nohut yogurt",
            ("mercimek corbasi", "mercimek"): "mercimek sogan havuc patates limon ekmek",
            ("karniyarik",): "patlican kiyma sogan domates biber sarimsak pirinc yogurt",
            ("dolma", "sarma"): "biber yaprak pirinc kiyma sogan domates yogurt",
            ("salata",): "marul domates salatalik limon zeytinyagi peynir",
            ("kahvalti",): "yumurta peynir zeytin domates salatalik ekmek cay",
        }
        for keys, hint in recipe_hints.items():
            if any(key in text_for_intent for key in keys):
                recipe_hint_tokens.update(self._tokens(hint))
        available_ingredients = prefs.get("available_ingredients")
        if isinstance(available_ingredients, list):
            tokens.update(self._tokens(" ".join(str(x) for x in available_ingredients)))

        ingredient_focus_tokens: set[str] = set()
        response_ingredients = response_obj.get("ingredients")
        if isinstance(response_ingredients, list):
            for ing in response_ingredients:
                if isinstance(ing, str):
                    ingredient_focus_tokens.update(self._tokens(ing))
                elif isinstance(ing, dict):
                    item_name = ing.get("item")
                    if isinstance(item_name, str):
                        ingredient_focus_tokens.update(self._tokens(item_name))
        # LLM bazen ingredients alanını boş dönebiliyor; bu durumda cevabın metninden
        # temel odak token'larını türetip sepet eşleşmesini güçlendir.
        if not ingredient_focus_tokens:
            fallback_words = {
                "tarif", "yemek", "yemegi", "bir", "iki", "uc", "icin", "ve", "ile",
                "kg", "gr", "adet", "ml", "l", "kadar", "gibi", "oneri", "oner",
                "kolay", "pratik", "adim", "hazirla", "pisir", "servis", "sepet",
            }
            for tok in self._tokens(self._extract_response_text(response_obj)):
                if len(tok) >= 4 and tok not in fallback_words:
                    ingredient_focus_tokens.add(tok)

        if "kahvalt" in meal_category:
            tokens.update(self._tokens("yumurta sut peynir zeytin ekmek domates salatalik"))
        if "aksam" in meal_category:
            tokens.update(self._tokens("tavuk kiyma pirinc bulgur makarna yogurt salata"))
        if "protein" in nutrition_goal:
            tokens.update(self._tokens("tavuk hindi yumurta yogurt ton"))
        if "vejetaryen" in nutrition_goal:
            tokens.update(self._tokens("sebze bakliyat nohut mercimek"))
        if dessert_intent:
            tokens.update(self._tokens("tatli cikolata gofret biskuvi pasta kek kurabiye dondurma sutlac"))
        if "karniyarik" in text_for_intent or "karnıyarık" in text_for_intent:
            tokens.update(self._tokens("patlican kiyma sogan domates biber sarimsak yogurt pirinc"))

        if recipe_hint_tokens:
            tokens.update(recipe_hint_tokens)
            if not ingredient_focus_tokens:
                ingredient_focus_tokens.update(recipe_hint_tokens)

        def is_cleaning_name(name: str, category_name: str = "", category_slug: str = "") -> bool:
            lowered = self._normalize_text(f"{name} {category_name} {category_slug}")
            non_food_keywords = (
                "deterjan", "çamaşır", "camasir", "bulaşık", "bulasik", "temizleyici",
                "domestos", "cif", "sabun", "sampuan", "deodorant", "havlu", "islak",
                "pecete", "kopuk", "tras", "tuvalet kagidi", "yumusatici", "temizlik", "hijyen",
            )
            return any(k in lowered for k in non_food_keywords)

        def is_dairy_name(name: str, category_name: str = "", category_slug: str = "") -> bool:
            lowered = self._normalize_text(f"{name} {category_name} {category_slug}")
            dairy_keywords = (
                "sut", "süt", "peynir", "yogurt", "yoğurt", "ayran", "kefir",
                "labne", "kaymak", "kasar", "kaşar", "tereyag", "tereyağ",
            )
            return any(k in lowered for k in dairy_keywords)

        def is_dessert_name(name: str, category_name: str = "", category_slug: str = "") -> bool:
            lowered = self._normalize_text(f"{name} {category_name} {category_slug}")
            dessert_keywords = (
                "tatli", "tatlı", "dessert", "pasta", "kek", "kurabiye", "biskuvi", "bisküvi",
                "cikolata", "çikolata", "gofret", "dondurma", "baklava", "sutlac", "sütlaç", "wafer",
                "atistirmalik", "atıştırmalık", "firin pastane", "firin-pastane",
            )
            return any(k in lowered for k in dessert_keywords)

        def score(product: Dict[str, Any]) -> float:
            name = self._normalize_text(str(product.get("name") or ""))
            brand = self._normalize_text(str(product.get("brand") or ""))
            category_name = self._normalize_text(str(product.get("category_name") or ""))
            category_slug = self._normalize_text(str(product.get("category_slug") or ""))

            is_cleaning = is_cleaning_name(name, category_name, category_slug)
            is_dairy = is_dairy_name(name, category_name, category_slug)
            is_dessert = is_dessert_name(name, category_name, category_slug)

            if is_cleaning and not cleaning_intent:
                return -10.0
            value = 0.0
            match_score = 0.0
            for t in tokens:
                if t in name:
                    match_score += 2.0
                if t in brand:
                    match_score += 0.6
            value += match_score
            if cleaning_intent:
                if is_cleaning:
                    value += 3.0
                else:
                    value -= 2.0
            elif dairy_intent:
                if is_dairy:
                    value += 3.0
                if is_cleaning:
                    value -= 4.0
            elif dessert_intent:
                if is_dessert:
                    value += 3.2
                else:
                    value -= 1.8
            if mode == AIMode.BUDGET:
                # Fiyat bonusunu yalnizca urun metinsel olarak ilgiliyse uygula.
                if match_score > 0:
                    value += max(0.0, 2.0 - min(float(product.get("price") or 0.0), 300.0) / 150.0)
            if mode == AIMode.DIET:
                healthy_keywords = ("tavuk", "hindi", "yumurta", "yogurt", "yoğurt", "ton", "salata", "sebze")
                if any(k in name for k in healthy_keywords):
                    value += 1.8
            if mode == AIMode.INVENTORY:
                value += 0.8
            if karniyarik_intent:
                if any(k in name for k in ("yumurta", "egg")):
                    value -= 4.5
                if any(k in name for k in ("patlican", "kiyma", "sogan", "domates", "biber", "sarimsak")):
                    value += 2.4
            if sebzeli_makarna_intent:
                if any(k in name for k in ("salatalik", "marul", "iceberg", "gobek")):
                    value -= 4.2
                if any(k in name for k in ("makarna", "domates", "biber", "kabak", "mantar", "sogan", "sarimsak")):
                    value += 2.1
            return value

        ranked = sorted(products, key=lambda p: (score(p), -(p.get("stock") or 0)), reverse=True)
        relevant = [p for p in ranked if score(p) >= 1.2]
        if len(relevant) < 3:
            relevant = [p for p in ranked if score(p) > 0]
        if len(relevant) < 3:
            relevant = [
                p
                for p in ranked
                if score(p) > -5
                and (cleaning_intent or not is_cleaning_name(
                    str(p.get("name") or ""),
                    str(p.get("category_name") or ""),
                    str(p.get("category_slug") or ""),
                ))
            ]

        if cleaning_intent:
            cleaning_only = [
                p for p in relevant
                if is_cleaning_name(
                    str(p.get("name") or ""),
                    str(p.get("category_name") or ""),
                    str(p.get("category_slug") or ""),
                )
            ]
            if len(cleaning_only) >= 2:
                relevant = cleaning_only

        if dairy_intent and not cleaning_intent:
            dairy_only = [
                p for p in relevant
                if is_dairy_name(
                    str(p.get("name") or ""),
                    str(p.get("category_name") or ""),
                    str(p.get("category_slug") or ""),
                )
            ]
            if len(dairy_only) >= 2:
                relevant = dairy_only

        if dessert_intent and not cleaning_intent:
            dessert_only = [
                p for p in relevant
                if is_dessert_name(
                    str(p.get("name") or ""),
                    str(p.get("category_name") or ""),
                    str(p.get("category_slug") or ""),
                )
            ]
            if len(dessert_only) >= 2:
                relevant = dessert_only

        if karniyarik_intent:
            relevant = [
                p for p in relevant
                if "yumurta" not in self._normalize_text(str(p.get("name") or ""))
            ]
        if sebzeli_makarna_intent:
            relevant = [
                p
                for p in relevant
                if not any(
                    tok in self._normalize_text(str(p.get("name") or ""))
                    for tok in ("salatalik", "marul", "iceberg", "gobek")
                )
            ]

        if mode == AIMode.NORMAL and ingredient_focus_tokens:
            ingredient_matched = [
                p for p in relevant
                if any(
                    tok in self._normalize_text(str(p.get("name") or ""))
                    for tok in ingredient_focus_tokens
                    if len(tok) >= 3
                )
            ]
            if len(ingredient_matched) >= 2:
                relevant = ingredient_matched

        if "kahvalt" in meal_category:
            breakfast_keywords = ("yumurta", "sut", "peynir", "zeytin", "ekmek", "domates", "salatalik", "yogurt", "bal", "recel", "tereyag", "cay")
            breakfast_only = [
                p for p in relevant
                if any(k in self._normalize_text(str(p.get("name") or "")) for k in breakfast_keywords)
            ]
            if len(breakfast_only) >= 3:
                relevant = breakfast_only
        elif "aksam" in meal_category:
            dinner_keywords = ("tavuk", "kiyma", "pilic", "pirinc", "bulgur", "makarna", "domates", "biber", "sogan", "salata", "yogurt")
            dinner_only = [
                p for p in relevant
                if any(k in self._normalize_text(str(p.get("name") or "")) for k in dinner_keywords)
            ]
            if len(dinner_only) >= 3:
                relevant = dinner_only

        if mode == AIMode.BUDGET:
            relevant = sorted(relevant, key=lambda p: (float(p.get("price") or 0.0), -score(p)))
        else:
            relevant = sorted(relevant, key=lambda p: (score(p), -(p.get("stock") or 0)), reverse=True)

        if not relevant:
            return {"items": [], "total_estimated": 0.0, "currency": "TRY", "notes": ["Stokta uygun ürün bulunamadı."]}

        max_items = 6
        if mode == AIMode.WEEKLY:
            max_items = 10
        elif mode == AIMode.INVENTORY:
            max_items = 8

        selected = []
        used_families: set[str] = set()
        family_stopwords = {
            "kg", "gr", "adet", "paket", "yeni", "mahsul", "organik", "dogal",
            "naturel", "super", "mini", "buyuk", "orta", "kucuk", "pet", "cam",
        }
        for p in relevant:
            if len(selected) >= max_items:
                break
            p_score = score(p)
            if p_score <= 0 and len(selected) >= 3:
                continue
            family_key = None
            name_norm = self._normalize_text(str(p.get("name") or ""))
            for tok in ingredient_focus_tokens:
                if len(tok) >= 4 and tok in name_norm:
                    family_key = tok
                    break
            if family_key is None:
                for tok in self._tokens(name_norm):
                    if len(tok) >= 4 and tok not in family_stopwords:
                        family_key = tok
                        break
            if family_key and family_key in used_families and len(selected) >= 2:
                continue
            qty_base = 1 if mode == AIMode.BUDGET else max(1, min(3, servings // 2 + 1))
            qty = min(int(p.get("stock") or 1), qty_base)
            if qty <= 0:
                continue
            price = float(p.get("price") or 0.0)
            selected.append(
                {
                    "product_id": p["id"],
                    "name": p["name"],
                    "brand": p.get("brand") or None,
                    "unit": p.get("unit") or None,
                    "price": round(price, 2),
                    "stock": int(p.get("stock") or 0),
                    "quantity": qty,
                    "subtotal": round(price * qty, 2),
                }
            )
            if family_key:
                used_families.add(family_key)

        total = round(sum(float(i["subtotal"]) for i in selected), 2)
        return {
            "items": selected,
            "total_estimated": total,
            "currency": "TRY",
            "notes": [f"Mode: {mode.value}", "Sepet stokta olan aktif ürünlerden oluşturuldu."],
        }

    async def _apply_market_cart_to_user_cart(self, db: Any, user_id: str, market_cart: Dict[str, Any]) -> Dict[str, Any]:
        if db is None or not user_id:
            return {"applied": False, "reason": "db_or_user_missing"}
        items = market_cart.get("items") if isinstance(market_cart, dict) else None
        if not isinstance(items, list) or not items:
            return {"applied": False, "reason": "empty_market_cart"}

        normalized_user_id: Any = user_id
        try:
            normalized_user_id = ObjectId(user_id)
        except Exception:
            pass

        cart_items: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pid = item.get("product_id")
            raw_qty = item.get("quantity")
            qty = 0
            try:
                if isinstance(raw_qty, str):
                    normalized_qty = raw_qty.strip().replace(",", ".")
                    try:
                        qty = int(float(normalized_qty))
                    except Exception:
                        match = re.search(r"(\d+(?:\.\d+)?)", normalized_qty)
                        if match:
                            qty = int(float(match.group(1)))
                else:
                    qty = int(float(raw_qty or 0))
            except Exception:
                qty = 0
            if qty <= 0:
                try:
                    raw_float = float(str(raw_qty).strip().replace(",", "."))
                    if raw_float > 0:
                        qty = 1
                except Exception:
                    pass
            if not pid or qty <= 0:
                continue
            try:
                cart_items.append({"product_id": ObjectId(str(pid)), "quantity": qty})
            except Exception:
                continue

        if not cart_items:
            return {"applied": False, "reason": "no_valid_items"}

        carts = db["carts"]
        now = datetime.utcnow()
        await carts.update_one(
            {"user_id": normalized_user_id},
            {"$set": {"items": cart_items, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return {"applied": True, "item_count": len(cart_items)}

    def _build_normal_local_response(self, user_input: str, preferences: dict | None) -> dict:
        """
        Build a practical local response for normal mode.
        Çeşitlilik: kullanıcı metnindeki anahtar kelimelere göre şablon seçer; aksi halde öğün kategorisine döner.
        """
        prefs = preferences or {}
        ui = (user_input or "").strip()
        meal_category = str(prefs.get("meal_category") or "Akşam Yemeği")
        nutrition_goal = str(prefs.get("nutrition_goal") or "Dengeli Beslenme")
        allergies_raw = str(prefs.get("allergies") or "").strip()
        brands_raw = str(prefs.get("preferred_brands") or "").strip()
        inventory_notes = str(prefs.get("inventory_notes") or "").strip()
        budget_limit = prefs.get("budget_limit")
        servings = self._extract_servings(user_input=user_input)
        un = self._normalize_text(user_input)

        if is_likely_greeting_or_smalltalk(ui):
            return {
                "message": "Yerel hızlı karşılama.",
                "user_input": ui,
                "title": "Merhaba",
                "recipe": "Sohbet",
                "summary": "CookWise mutfak asistanıyım; bugün ne pişirmek veya markette ne aramak istediğini yazabilirsin.",
                "description": "Tarif, malzeme listesi, bütçe veya diyet için modunu seçip detay yazman yeterli.",
                "ingredients": [],
                "preparation": [],
                "steps": [
                    "Örnek: «Mercimek çorbası 4 kişilik» veya «elimde kabak ve peynir var ne yapayım?» şeklinde yazabilirsin."
                ],
                "tips": ["Normal, bütçe, diyet ve haftalık plan modlarını üst menüden deneyebilirsin."],
                "optional_sides": [],
                "optional_drinks": [],
                "allergen_warnings": [],
            }

        recipe_name: str
        ingredients: List[Dict[str, str]]
        steps: List[str]
        preparation: List[str]
        prep_minutes: int
        cook_minutes: int

        if "mercimek" in un and "corba" in un:
            recipe_name = "Mercimek Çorbası"
            preparation = [
                "Kırmızı mercimeği süzgeçte yıkayın; köpürmesini azaltmak için bir kez süzün.",
                "Soğanı küp küp doğrayın; havuç varsa rendeleyin.",
            ]
            ingredients = [
                {"item": "Kırmızı mercimek", "quantity": f"{max(1, servings)} su bardağı"},
                {"item": "Soğan", "quantity": f"{max(1, servings // 2 + 1)} adet"},
                {"item": "Havuç", "quantity": f"{max(1, servings // 2)} adet (isteğe bağlı)"},
                {"item": "Sıvı yağ", "quantity": "3 yemek kaşığı"},
                {"item": "Domates salçası", "quantity": "1 yemek kaşığı"},
                {"item": "Tuz, kimyon, nane, pul biber", "quantity": "tatmaklığı"},
            ]
            steps = [
                "Tencerede yağı ısıtıp soğanı (ve havucu) kavurun.",
                "Salçayı ekleyip 1 dk çevirin; mercimeği ekleyip üzerini geçecek kadar sıcak su verin.",
                "Kaynadıktan sonra kısık ateşte 20-25 dk pişirin; blender veya süzgeçle kıvamı düzeltin.",
                "Limon ve nane ile servis edin.",
            ]
            prep_minutes, cook_minutes = 15, 35
        elif "makarna" in un or "spagetti" in un or "fettuc" in un:
            recipe_name = "Domates Soslu Makarna"
            preparation = ["Makarnayı paket tavsiyesine göre haşlamak için su ve tuz hazırlayın.", "Soğanı ince doğrayın."]
            ingredients = [
                {"item": "Makarna", "quantity": f"{servings * 80} g"},
                {"item": "Domates konservesi veya rendelenmiş domates", "quantity": f"{max(1, servings)} su bardağı"},
                {"item": "Soğan", "quantity": "1 adet"},
                {"item": "Sarımsak", "quantity": "2 diş"},
                {"item": "Zeytinyağı", "quantity": "2 yemek kaşığı"},
                {"item": "Kaşar veya parmesan", "quantity": f"{servings * 20} g (isteğe bağlı)"},
            ]
            steps = [
                "Makarnayı tuzlu kaynar suda haşlayın; süzüp biraz sıvısını ayırın.",
                "Tavada zeytinyağı ile sarımsak ve soğanı soteleyin; domatesi ekleyip 8-10 dk pişirin.",
                "Makarnayı sosla karıştırın; gerekirse haşlama suyuyla inceltin; peynirle servis edin.",
            ]
            prep_minutes, cook_minutes = 10, 22
        elif "pilav" in un and "bulgur" not in un:
            recipe_name = "Tereyağlı Pirinç Pilavı"
            preparation = ["Pirinci yıkayıp süzün; 10-15 dk ılık tuzlu suda bekletebilirsiniz.", "Soğanı küp doğrayın."]
            ingredients = [
                {"item": "Baldo pirinç", "quantity": f"{servings * 60} g"},
                {"item": "Tereyağı veya yağ", "quantity": "2 yemek kaşığı"},
                {"item": "Soğan", "quantity": "1 küçük adet"},
                {"item": "Sıcak tavuk veya et suyu", "quantity": f"{servings * 1.2:.1f} su bardağı".replace(".", ",")},
            ]
            steps = [
                "Yağda soğanı pembeleştirin; süzülmüş pirinci kavurun.",
                "Sıcak suyu ekleyip kaynatın; kapağı kapatıp kısık ateşte sünger gibi olana kadar pişirin.",
                "Demlenmeye 8-10 dk bırakın; çatal ile karıştırarak servis edin.",
            ]
            prep_minutes, cook_minutes = 15, 25
        elif "kofte" in un or "köfte" in user_input.lower():
            recipe_name = "Ev Köftesi + Yanında Pilav veya Salata"
            preparation = ["Kıymayı oda sıcaklığında bekletin.", "Soğan ve maydanozu ince doğrayın."]
            ingredients = [
                {"item": "Kıyma (yağlı/orta)", "quantity": f"{servings * 120} g"},
                {"item": "Soğan", "quantity": "1 adet"},
                {"item": "Galeta unu veya bayat ekmek içi", "quantity": "2-3 yemek kaşığı"},
                {"item": "Yumurta", "quantity": "1 adet"},
                {"item": "Tuz, karabiber, kimyon", "quantity": "tatmaklığı"},
            ]
            steps = [
                "Tüm malzemeyi yoğurup buzdolabında 15 dk dinlendirin.",
                "Köfteleri şekillendirip tavada veya fırında pişirin (her yüzü altın rengi).",
                "Yanında pilav veya mevsim salata ile servis edin.",
            ]
            prep_minutes, cook_minutes = 20, 22
        elif "tatli" in un or "tatlı" in user_input.lower() or "sutlac" in un or "sütlaç" in user_input.lower():
            recipe_name = "Sütlaç"
            preparation = ["Pirinçleri yıkayıp süzün.", "Sütü ölçün."]
            ingredients = [
                {"item": "Pirinç", "quantity": "3 yemek kaşığı"},
                {"item": "Süt", "quantity": f"{servings * 250} ml"},
                {"item": "Şeker", "quantity": f"{servings * 1.5:.0f} yemek kaşığı".replace(".", ",")},
                {"item": "Nişasta (isteğe bağlı)", "quantity": "1 tatlı kaşığı"},
            ]
            steps = [
                "Pirinci az suda yumuşayıncaya kadar pişirin.",
                "Süt ve şekeri ekleyip karıştırarak kaynatın; kıvam için nişasta sulandırılarak eklenebilir.",
                "Kaselere paylaştırıp soğutun; tarçın serpin.",
            ]
            prep_minutes, cook_minutes = 10, 25
        elif meal_category == "Kahvaltı":
            recipe_name = "Sebzeli Menemen + Tam Buğday Tost"
            preparation = ["Domates ve biberi küçük doğrayın.", "Yumurtaları bir kasede çırpın."]
            ingredients = [
                {"item": "Yumurta", "quantity": f"{max(2, servings * 2)} adet"},
                {"item": "Domates", "quantity": f"{max(2, servings)} adet"},
                {"item": "Biber", "quantity": f"{max(1, servings // 2 + 1)} adet"},
                {"item": "Tam buğday ekmeği", "quantity": f"{servings * 2} dilim"},
                {"item": "Beyaz peynir", "quantity": f"{servings * 40} g"},
                {"item": "Zeytinyağı", "quantity": "2 yemek kaşığı"},
            ]
            steps = [
                "Domates ve biberi tavada zeytinyağı ile 4-5 dk soteleyin.",
                "Yumurtaları çırpıp tavaya ekleyin, kısık ateşte karıştırarak pişirin.",
                "Ekmeği tostlayın, peyniri yanında servis edin.",
            ]
            prep_minutes, cook_minutes = 12, 14
        elif meal_category == "Sağlıklı Atıştırmalıklar":
            recipe_name = "Yoğurtlu Yulaf Kasesi + Meyve"
            preparation = ["Meyveyi dilimleyin.", "Ölçü kaplarını hazırlayın."]
            ingredients = [
                {"item": "Süzme yoğurt", "quantity": f"{servings * 120} g"},
                {"item": "Yulaf ezmesi", "quantity": f"{servings * 40} g"},
                {"item": "Muz", "quantity": f"{max(1, servings // 2 + 1)} adet"},
                {"item": "Ceviz", "quantity": f"{servings * 10} g"},
                {"item": "Tarçın", "quantity": "1 çay kaşığı"},
            ]
            steps = [
                "Yoğurt ve yulafı karıştırıp 5-10 dk dinlendirin.",
                "Muzu dilimleyip kaseye ekleyin.",
                "Ceviz ve tarçın ile tamamlayın.",
            ]
            prep_minutes, cook_minutes = 8, 0
        else:
            recipe_name = "Tavuk Sote + Bulgur Pilavı + Mevsim Salata"
            preparation = ["Tavuğu jülyen doğrayın.", "Sebzeleri doğrayın; bulguru yıkayıp süzün."]
            ingredients = [
                {"item": "Tavuk göğsü", "quantity": f"{servings * 150} g"},
                {"item": "Bulgur", "quantity": f"{servings * 60} g"},
                {"item": "Soğan", "quantity": f"{max(1, servings // 2 + 1)} adet"},
                {"item": "Biber", "quantity": f"{max(1, servings // 2 + 1)} adet"},
                {"item": "Domates", "quantity": f"{max(2, servings)} adet"},
                {"item": "Marul", "quantity": "1 küçük adet"},
                {"item": "Zeytinyağı", "quantity": "4 yemek kaşığı"},
                {"item": "Yoğurt", "quantity": f"{servings * 75} g"},
            ]
            steps = [
                "Bulguru sıcak su ile pilav kıvamında 12-15 dk pişirin.",
                "Tavuğu soğan ve biberle tavada soteleyin.",
                "Domatesi ekleyip 6-7 dk daha pişirin; tuz-baharatla dengeleyin.",
                "Salatayı hazırlayıp yoğurt ile servis edin.",
            ]
            prep_minutes, cook_minutes = 18, 28

        allergen_warnings: List[str] = []
        if allergies_raw:
            lowered = allergies_raw.lower()
            if "gluten" in lowered and any("bulgur" in i["item"].lower() for i in ingredients):
                allergen_warnings.append("Gluten hassasiyeti için bulgur yerine karabuğday/pirinç kullanın.")
            if "fındık" in lowered or "kuruyemiş" in lowered:
                allergen_warnings.append("Kuruyemiş içeren ürünleri liste dışı bırakın.")
            if "laktoz" in lowered and any("yoğurt" in i["item"].lower() for i in ingredients):
                allergen_warnings.append("Laktozsuz yoğurt/peynir tercih edin.")

        tips = [f"Hedef: {nutrition_goal}"]
        if brands_raw:
            tips.append(f"Marka tercihi dikkate alındı: {brands_raw}.")
        if inventory_notes:
            tips.append("Envanter notlarınız doğrultusunda mevcut ürünleri önce kullanın.")
        if budget_limit not in (None, ""):
            tips.append(f"Bütçe limiti (TL): {budget_limit}. İndirimli market markalarına öncelik verin.")

        snippet = ui if len(ui) <= 160 else ui[:157] + "..."
        summary = f"«{snippet}» için {servings} kişilik öneri: {recipe_name}."
        description = (
            f"{recipe_name} — pratik adımlar ve ölçüler. "
            f"Öğün: {meal_category}. İstersen bir sonraki mesajda malzemelerini veya diyet tercihini netleştir."
        )

        plan = {
            "meal_category": meal_category,
            "recipe": recipe_name,
            "servings": servings,
            "nutrition_goal": nutrition_goal,
            "estimated_prep_time_minutes": prep_minutes,
            "estimated_cook_time_minutes": cook_minutes,
            "ingredients": ingredients,
            "steps": steps,
        }

        cook_label = f"{cook_minutes} dk" if cook_minutes > 0 else "—"
        return {
            "message": "Yerel akıllı öneri üretildi.",
            "user_input": ui,
            "title": recipe_name,
            "recipe": recipe_name,
            "summary": summary,
            "description": description,
            "servings": servings,
            "prep_time": f"{prep_minutes} dk",
            "cook_time": cook_label,
            "cooking_time": cook_label,
            "ingredients": ingredients,
            "preparation": preparation,
            "steps": steps,
            "plan": plan,
            "allergen_warnings": allergen_warnings,
            "tips": tips,
            "preferences": prefs,
        }

    def _generate_local(self, mode: AIMode, user_input: str, preferences: dict | None) -> dict:
        prefs = preferences or {}

        if mode == AIMode.BUDGET:
            prompt = build_budget_json_prompt(user_input=user_input, context=prefs.get("context"))
            result = self.budget_service.build_budget_plan(user_input)
            return {
                "mode": mode,
                "prompt": prompt,
                "response": result,
                "provider": "local-budget-engine",
            }

        if mode == AIMode.DIET:
            goal = str(prefs.get("goal", "low_calorie"))
            prompt = build_diet_json_prompt(
                user_input=user_input,
                goal=goal,
                context=prefs.get("context"),
            )
            result = self.diet_service.build_diet_plan(user_request=user_input, goal=goal)
            return {
                "mode": mode,
                "prompt": prompt,
                "response": result,
                "provider": "local-diet-engine",
            }

        if mode == AIMode.INVENTORY:
            ingredients = prefs.get("available_ingredients")
            if not isinstance(ingredients, list) or not ingredients:
                ingredients = [item.strip() for item in user_input.split(",") if item.strip()]
            prompt = build_inventory_json_prompt(
                available_ingredients=ingredients,
                context=prefs.get("context"),
            )
            result = self.inventory_service.build_inventory_plan(ingredients)
            return {
                "mode": mode,
                "prompt": prompt,
                "response": result,
                "provider": "local-inventory-engine",
            }

        if mode == AIMode.WEEKLY:
            prompt = build_weekly_plan_json_prompt(
                user_request=user_input,
                context=prefs.get("context"),
            )
            result = self.weekly_planner_service.build_weekly_plan(user_input)
            return {
                "mode": mode,
                "prompt": prompt,
                "response": result,
                "provider": "local-weekly-engine",
            }

        # NORMAL mode
        prompt = build_prompt(
            user_input=user_input,
            mode=AIMode.NORMAL,
            context=prefs.get("context"),
        )
        result = self._build_normal_local_response(user_input=user_input, preferences=prefs)
        return {
            "mode": mode,
            "prompt": prompt,
            "response": result,
            "provider": "local-normal-engine",
        }

    def _generate_openai(self, mode: AIMode, user_input: str, preferences: dict | None) -> dict:
        prefs = preferences or {}

        timeout_seconds = int(getattr(settings, "AI_OPENAI_TIMEOUT_SECONDS", 30))
        model = str(getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"))
        temperature = float(getattr(settings, "AI_TEMPERATURE", 0.7))

        # Use a rich system persona while keeping JSON-only output contract.
        system_prompt = COOKWISE_JSON_SYSTEM_PROMPT
        user_prompt, provider_suffix = self._build_llm_prompt(mode=mode, user_input=user_input, preferences=prefs)
        provider_name = f"openai-{provider_suffix}"

        raw = self.openai_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
            model=model,
            response_format={"type": "json_object"},
            temperature=temperature,
        )

        parsed = self._safe_json_parse(raw)
        if not self._validate_mode_keys(mode, parsed) and mode != AIMode.NORMAL:
            raise ValueError("OpenAI returned JSON but with unexpected keys")

        # For normal mode, we allow any JSON object.
        return {
            "mode": mode,
            "prompt": user_prompt,
            "response": parsed,
            "provider": provider_name,
        }

    def _generate_gemini(self, mode: AIMode, user_input: str, preferences: dict | None) -> dict:
        prefs = preferences or {}

        timeout_seconds = int(getattr(settings, "AI_OPENAI_TIMEOUT_SECONDS", 30))
        model = str(getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash"))
        temperature = float(getattr(settings, "AI_TEMPERATURE", 0.7))

        system_prompt = COOKWISE_JSON_SYSTEM_PROMPT
        user_prompt, provider_suffix = self._build_llm_prompt(mode=mode, user_input=user_input, preferences=prefs)
        provider_name = f"gemini-{provider_suffix}"

        raw = self.gemini_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
            model=model,
            response_format={"type": "json_object"},
            temperature=temperature,
        )

        parsed = self._safe_json_parse(raw)
        if not self._validate_mode_keys(mode, parsed) and mode != AIMode.NORMAL:
            raise ValueError("Gemini returned JSON but with unexpected keys")

        return {
            "mode": mode,
            "prompt": user_prompt,
            "response": parsed,
            "provider": provider_name,
        }

    def _generate_ollama(self, mode: AIMode, user_input: str, preferences: dict | None) -> dict:
        prefs = preferences or {}
        timeout_seconds = int(getattr(settings, "AI_OPENAI_TIMEOUT_SECONDS", 30))
        model = str(getattr(settings, "OLLAMA_MODEL", "llama3.1:8b"))
        temperature = float(getattr(settings, "AI_TEMPERATURE", 0.7))
        system_prompt = COOKWISE_JSON_SYSTEM_PROMPT
        user_prompt, provider_suffix = self._build_llm_prompt(mode=mode, user_input=user_input, preferences=prefs)
        provider_name = f"ollama-{provider_suffix}"

        raw = self.ollama_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
            model=model,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        parsed = self._safe_json_parse(raw)
        if not self._validate_mode_keys(mode, parsed) and mode != AIMode.NORMAL:
            raise ValueError("Ollama returned JSON but with unexpected keys")

        return {
            "mode": mode,
            "prompt": user_prompt,
            "response": parsed,
            "provider": provider_name,
        }

    def _generate_grok(self, mode: AIMode, user_input: str, preferences: dict | None) -> dict:
        prefs = preferences or {}
        timeout_seconds = int(getattr(settings, "AI_OPENAI_TIMEOUT_SECONDS", 30))
        model = str(getattr(settings, "GROK_MODEL", "grok-2-latest"))
        temperature = float(getattr(settings, "AI_TEMPERATURE", 0.7))
        system_prompt = COOKWISE_JSON_SYSTEM_PROMPT
        user_prompt, provider_suffix = self._build_llm_prompt(mode=mode, user_input=user_input, preferences=prefs)
        provider_name = f"grok-{provider_suffix}"

        raw = self.grok_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
            model=model,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        parsed = self._safe_json_parse(raw)
        if not self._validate_mode_keys(mode, parsed) and mode != AIMode.NORMAL:
            raise ValueError("Grok returned JSON but with unexpected keys")

        return {
            "mode": mode,
            "prompt": user_prompt,
            "response": parsed,
            "provider": provider_name,
        }

    def _generate_groq(self, mode: AIMode, user_input: str, preferences: dict | None) -> dict:
        prefs = preferences or {}
        timeout_seconds = int(getattr(settings, "AI_OPENAI_TIMEOUT_SECONDS", 30))
        model = str(getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"))
        temperature = float(getattr(settings, "GROQ_TEMPERATURE", getattr(settings, "AI_TEMPERATURE", 0.75)))
        max_tokens = int(getattr(settings, "GROQ_MAX_TOKENS", 1600))
        system_prompt = COOKWISE_JSON_SYSTEM_PROMPT
        user_prompt, provider_suffix = self._build_llm_prompt(mode=mode, user_input=user_input, preferences=prefs)
        provider_name = f"groq-{provider_suffix}"

        raw = self.groq_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
            model=model,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        parsed = self._safe_json_parse(raw)
        if not self._validate_mode_keys(mode, parsed) and mode != AIMode.NORMAL:
            raise ValueError("Groq returned JSON but with unexpected keys")

        return {
            "mode": mode,
            "prompt": user_prompt,
            "response": parsed,
            "provider": provider_name,
        }

    def _is_recipe_request(self, user_input: str) -> bool:
        normalized = normalize_text(user_input)
        if is_likely_greeting_or_smalltalk(user_input):
            return False
        request_tokens = (
            "tarif",
            "yapmak",
            "yapicam",
            "yapacagim",
            "pisirmek",
            "pisirecegim",
            "hazirlamak",
            "hazirla",
            "olustur",
            "oner",
            "malzeme",
            "sepetime",
            "sepet",
            "istiyorum",
            "var mi",
            "yok mu",
            "nasil yok",
            "veri taban",
            "veritabani",
            "veritabaninda",
        )
        known_meals = (
            "karniyarik",
            "karniyarin",
            "manti",
            "menemen",
            "pizza",
            "makarna",
            "kofte",
            "pilav",
            "corba",
            "lazanya",
        )
        return any(token in normalized for token in request_tokens) or any(meal in normalized for meal in known_meals)

    def _extract_meal_name(self, user_input: str) -> str:
        normalized = normalize_text(user_input)
        known_meals = (
            "karniyarik",
            "karniyarin",
            "kayseri mantisi",
            "manti",
            "menemen",
            "pizza",
            "makarna",
            "kofte",
            "pilav",
            "corba",
            "lazanya",
        )
        for meal in known_meals:
            if meal in normalized:
                if meal == "karniyarin":
                    return "karniyarik"
                return meal
        filler = {
            "bana", "bir", "bi", "icin", "lazim", "lazimdir", "lutfen", "tarif", "tarifi",
            "istiyorum", "isterim", "ver", "oner", "onerebilir", "yapmak", "yapicam",
            "yapacagim", "pisirmek", "pisirecegim", "hazirlamak", "hazirla", "olustur", "nasil",
            "olur", "malzemeleri", "malzeme", "sepetime", "sepet", "ekle", "koy",
            "yok", "mu", "var", "mi", "veri", "tabani", "veritabani", "veritabaninda",
            "database", "db", "bulunmadi", "bulunmuyor", "neden",
            "aksam", "sabah", "ogle", "oglen", "urun", "urunleri", "urunleri", "listele",
            "listeler", "misin", "midir", "miyim", "ile", "ve",
        }
        tokens = [token for token in normalized.split() if token not in filler and len(token) > 1]
        return " ".join(tokens).strip() or normalized

    def _recipe_prompt_contract(self, user_input: str, meal_name: str) -> str:
        return (
            "Recipe DB orchestration. AI tarif veya urun uyduramaz.\n"
            f"User request: {user_input}\n"
            f"Detected meal: {meal_name}\n"
            "Rules: recipe context MongoDB recipes collection'dan, product context MongoDB products collection'dan gelir."
        )

    def _recipe_market_cart(self, matched_products: list[dict[str, Any]]) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for product in matched_products:
            product_id = str(product.get("product_id") or "")
            if not product_id or product_id in seen:
                continue
            price = float(product.get("price") or 0.0)
            items.append(
                {
                    "product_id": product_id,
                    "name": product.get("product_name") or "Urun",
                    "price": round(price, 2),
                    "quantity": 1,
                    "subtotal": round(price, 2),
                }
            )
            seen.add(product_id)
        return {
            "items": items,
            "total_estimated": round(sum(float(item["subtotal"]) for item in items), 2),
            "currency": "TRY",
            "notes": ["Sepet tarif veritabani ve stoktaki urunlerle olusturuldu."],
        }

    def _score_recipe_product_match(
        self,
        meal_name: str,
        recipe: dict[str, Any],
        match_result: dict[str, Any],
    ) -> int:
        matched = match_result.get("matched_products") if isinstance(match_result, dict) else []
        missing = match_result.get("missing_products") if isinstance(match_result, dict) else []
        ingredient_text = " ".join(
            str(item.get("normalized_name") or "")
            for item in recipe.get("ingredients", [])
            if isinstance(item, dict)
        )
        normalized_meal = normalize_text(meal_name)
        score = len(matched or []) * 3 - len(missing or [])
        recipe_name = normalize_text(recipe.get("normalized_name") or recipe.get("name") or "")
        if recipe_name == normalized_meal:
            score += 100
        elif recipe_name.startswith(normalized_meal + " ") or recipe_name.endswith(" " + normalized_meal):
            score += 20
        if "manti" in normalized_meal:
            score += sum(
                2
                for token in ("kiyma", "yogurt", "sogan", "sarimsak", "un")
                if token in ingredient_text
            )
        if "menemen" in normalized_meal:
            score += sum(
                2
                for token in ("yumurta", "domates", "biber")
                if token in ingredient_text
            )
        return score

    async def _generate_recipe_from_database(
        self,
        *,
        mode: AIMode,
        user_input: str,
        preferences: dict | None,
        db: Any,
        current_user: Dict[str, Any] | None,
    ) -> dict | None:
        if mode != AIMode.NORMAL or db is None or not self._is_recipe_request(user_input):
            return None

        prefs = preferences or {}
        meal_name = self._extract_meal_name(user_input)
        recipe_service = RecipeService(db)
        recipes = await recipe_service.search_recipe_by_name(meal_name or user_input, limit=8)
        prompt = self._recipe_prompt_contract(user_input=user_input, meal_name=meal_name)

        if not recipes:
            response = {
                "intent": "recipe_request",
                "meal_name": meal_name,
                "recipe": {"name": "", "category": "", "ingredients": [], "steps": []},
                "matched_products": [],
                "missing_products": [],
                "total_estimated_price": 0,
                "message": "Bu yemek recipes veritabaninda bulunamadi. Tarif veya urun uydurmadim.",
                "market_cart": {"items": [], "total_estimated": 0.0, "currency": "TRY", "notes": ["Tarif bulunamadi."]},
            }
            return {"mode": mode, "prompt": prompt, "response": response, "provider": "recipe-db"}

        matcher = ProductMatchingService(db)
        best_recipe = recipes[0]
        best_match_result = await matcher.match_ingredients_to_products(best_recipe.get("ingredients", []))
        best_score = self._score_recipe_product_match(meal_name, best_recipe, best_match_result)
        for candidate in recipes[1:]:
            candidate_match = await matcher.match_ingredients_to_products(candidate.get("ingredients", []))
            candidate_score = self._score_recipe_product_match(meal_name, candidate, candidate_match)
            if candidate_score > best_score:
                best_recipe = candidate
                best_match_result = candidate_match
                best_score = candidate_score

        recipe = best_recipe
        match_result = best_match_result
        matched_products = match_result.get("matched_products", [])
        missing_products = match_result.get("missing_products", [])
        market_cart = self._recipe_market_cart(matched_products)

        recipe_payload = {
            "id": recipe.get("id"),
            "name": recipe.get("name") or "",
            "category": recipe.get("category") or "",
            "ingredients": recipe.get("ingredients") or [],
            "steps": recipe.get("steps") or [],
            "duration": recipe.get("duration") or "",
            "servings": recipe.get("servings") or "",
            "image": recipe.get("image") or "",
        }
        display_ingredients: list[dict[str, str]] = []
        for ingredient in recipe_payload["ingredients"]:
            if not isinstance(ingredient, dict):
                continue
            raw = str(ingredient.get("raw") or "").strip()
            name = str(ingredient.get("name") or "").strip()
            amount = str(ingredient.get("amount") or "").strip()
            unit = str(ingredient.get("unit") or "").strip()
            quantity = " ".join(part for part in (amount, unit) if part).strip()
            if not quantity and raw and name and raw != name:
                quantity = raw.replace(name, "").strip(" -,:;")
            display_ingredients.append(
                {
                    "item": name or raw or "Malzeme",
                    "quantity": quantity or raw or "Tarife gore",
                }
            )

        recipe_steps = [
            str(step).strip()
            for step in (recipe_payload.get("steps") or [])
            if isinstance(step, str) and str(step).strip()
        ]
        shopping_recommendations = [
            f"{product.get('ingredient') or 'Malzeme'} icin stoktaki {product.get('product_name') or 'urun'} uygun."
            for product in matched_products[:6]
        ]
        response = {
            "intent": "recipe_request",
            "meal_name": meal_name,
            "assistant_message": (
                f"{recipe_payload['name']} tarifini ekledigin tarif veritabanindan buldum; "
                "sepeti de stoktaki urun veritabanina gore hazirladim."
            ),
            "title": recipe_payload["name"] or meal_name.title(),
            "description": (
                f"{recipe_payload['name'] or meal_name.title()} icin malzemeleri, pisirme adimlarini "
                "ve sepete eklenebilen urunleri kendi veri setindeki kayitlara gore eslestirdim."
            ),
            "summary": (
                f"{len(display_ingredients)} malzeme ve {len(recipe_steps)} pisirme adimi bulundu; "
                f"{len(matched_products)} urun sepete eklenebilir durumda."
            ),
            "ingredients": display_ingredients,
            "preparation": [
                "Malzemeleri olculerine gore hazirlayin; sebzeleri yikayip dograyin.",
                "Tarifte gecen urunleri eksiklere gore kontrol edin ve pisirme sirasina alin.",
            ] if display_ingredients else [],
            "steps": recipe_steps,
            "serving_suggestion": "Sicak servis edin; yanina pilav, cacik veya mevsim salatasi yakisir.",
            "shopping_recommendations": shopping_recommendations,
            "recipe": recipe_payload,
            "matched_products": matched_products,
            "missing_products": missing_products,
            "total_estimated_price": market_cart["total_estimated"],
            "message": (
                f"{recipe_payload['name']} tarifi veritabanindan bulundu. "
                f"{len(matched_products)} malzeme market urunuyle eslesti; "
                f"{len(missing_products)} malzeme veritabaninda bulunamadi."
            ),
            "market_cart": market_cart,
        }

        apply_to_cart = bool(prefs.get("apply_to_cart", False))
        user_id = None
        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("user_id")
        if apply_to_cart and user_id:
            response["cart_sync"] = await self._apply_market_cart_to_user_cart(db, str(user_id), market_cart)

        return {"mode": mode, "prompt": prompt, "response": response, "provider": "recipe-db"}

    async def generate(
        self,
        mode: AIMode,
        user_input: str,
        preferences: dict | None = None,
        db: Any = None,
        current_user: Dict[str, Any] | None = None,
    ) -> dict:
        # Provider selection + fallback.
        provider = str(getattr(settings, "AI_PROVIDER", "local")).lower()
        prefs: Dict[str, Any] = dict(preferences or {})
        conv = str(prefs.get("conversation_history") or prefs.get("chat_context") or "").strip()
        if conv:
            conv_block = (
                "[SOHBET_DEVAMI]\n"
                f"{conv}\n"
                "Önceki turdaki tarif veya tercihlerle tutarlı ol; kullanıcı yeni bir yemek/konu istemedikçe "
                "aynı tarifi derinleştir veya soruya doğrudan yanıt ver."
            )
            prev_ctx = str(prefs.get("context") or "").strip()
            prefs["context"] = f"{conv_block}\n\n{prev_ctx}" if prev_ctx else conv_block

        recipe_db_result = await self._generate_recipe_from_database(
            mode=mode,
            user_input=user_input,
            preferences=prefs,
            db=db,
            current_user=current_user,
        )
        if recipe_db_result is not None:
            return recipe_db_result

        strict_llm = bool(getattr(settings, "AI_STRICT_LLM", False) or prefs.get("require_llm"))
        require_market_cart_from_llm = bool(prefs.get("require_market_cart_from_llm", False))

        include_market_cart = bool(prefs.get("include_market_cart", prefs.get("apply_to_cart", False)))
        in_stock_products = await self._fetch_in_stock_products(db)
        if in_stock_products:
            hint_text = user_input
            if conv:
                hint_text = f"{user_input}\n{conv[:1200]}"
            market_context = self._build_market_context(
                in_stock_products,
                include_market_cart=include_market_cart,
                hint_text=hint_text,
            )
            existing_context = str(prefs.get("context") or "").strip()
            prefs["context"] = f"{existing_context}\n\n{market_context}" if existing_context else market_context

        def _enrich_result(raw_result: Dict[str, Any]) -> Dict[str, Any]:
            response_obj = raw_result.get("response")
            if not isinstance(response_obj, dict):
                response_obj = {"raw": response_obj}
            response_obj = self._sanitize_response_for_common_dishes(user_input=user_input, response_obj=response_obj)
            if mode == AIMode.NORMAL:
                response_obj = self._normalize_normal_mode_response(response_obj)

            if include_market_cart:
                llm_market_cart = response_obj.get("market_cart")
                has_llm_market_cart = (
                    isinstance(llm_market_cart, dict)
                    and isinstance(llm_market_cart.get("items"), list)
                    and len(llm_market_cart.get("items") or []) > 0
                )
                if require_market_cart_from_llm and not has_llm_market_cart:
                    raise RuntimeError("LLM sepet oluşturamadı (market_cart dönmedi). Lütfen tekrar deneyin.")
                fallback_market_cart = self._build_market_cart(
                    mode=mode,
                    user_input=user_input,
                    preferences=prefs,
                    response_obj=response_obj,
                    products=in_stock_products,
                )
                if has_llm_market_cart:
                    normalized_llm_cart = self._normalize_llm_market_cart(llm_market_cart, in_stock_products)
                    market_cart = self._merge_market_carts(normalized_llm_cart, fallback_market_cart)
                else:
                    market_cart = fallback_market_cart
                ingredient_tokens = self._ingredient_cart_tokens(response_obj)
                market_cart = self._filter_market_cart_by_ingredients(market_cart, ingredient_tokens)
                response_obj["market_cart"] = market_cart
            raw_result["response"] = response_obj
            return raw_result

        if provider == "gemini" and self.gemini_provider is not None:
            try:
                result = self._generate_gemini(mode=mode, user_input=user_input, preferences=prefs)
            except Exception as e:
                import logging
                logging.error(f"Gemini fallback, error: {e}")
                if strict_llm:
                    raise RuntimeError(f"Gemini yanıtı alınamadı: {e}") from e
                local_result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
                local_result["provider"] = f"{local_result.get('provider')}-fallback"
                result = local_result
        elif provider == "gemini" and self.gemini_provider is None:
            if strict_llm:
                raise RuntimeError("AI_PROVIDER=gemini ama GEMINI_API_KEY bulunamadı.")
            result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
        elif provider == "openai" and self.openai_provider is not None:
            try:
                result = self._generate_openai(mode=mode, user_input=user_input, preferences=prefs)
            except Exception as e:
                # Safe fallback: return deterministic structured JSON from local engine.
                if strict_llm:
                    raise RuntimeError(f"OpenAI yanıtı alınamadı: {e}") from e
                local_result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
                local_result["provider"] = f"{local_result.get('provider')}-fallback"
                result = local_result
        elif provider == "openai" and self.openai_provider is None:
            if strict_llm:
                raise RuntimeError("AI_PROVIDER=openai ama OPENAI_API_KEY bulunamadı.")
            result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
        elif provider == "grok" and self.grok_provider is not None:
            try:
                result = self._generate_grok(mode=mode, user_input=user_input, preferences=prefs)
            except Exception as e:
                if strict_llm:
                    raise RuntimeError(f"Grok yanıtı alınamadı: {e}") from e
                local_result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
                local_result["provider"] = f"{local_result.get('provider')}-fallback"
                result = local_result
        elif provider == "grok" and self.grok_provider is None:
            if strict_llm:
                raise RuntimeError("AI_PROVIDER=grok ama XAI_API_KEY bulunamadı.")
            result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
        elif provider == "groq" and self.groq_provider is not None:
            try:
                result = self._generate_groq(mode=mode, user_input=user_input, preferences=prefs)
            except Exception as e:
                if strict_llm:
                    raise RuntimeError(f"Groq yanıtı alınamadı: {e}") from e
                local_result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
                local_result["provider"] = f"{local_result.get('provider')}-fallback"
                result = local_result
        elif provider == "groq" and self.groq_provider is None:
            if strict_llm:
                raise RuntimeError("AI_PROVIDER=groq ama GROQ_API_KEY bulunamadı.")
            result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
        elif provider == "ollama" and self.ollama_provider is not None:
            try:
                result = self._generate_ollama(mode=mode, user_input=user_input, preferences=prefs)
            except Exception as e:
                if strict_llm:
                    raise RuntimeError(f"Ollama yanıtı alınamadı: {e}") from e
                local_result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
                local_result["provider"] = f"{local_result.get('provider')}-fallback"
                result = local_result
        elif provider == "ollama" and self.ollama_provider is None:
            if strict_llm:
                raise RuntimeError("AI_PROVIDER=ollama ama OLLAMA_BASE_URL bulunamadı.")
            result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)
        else:
            if strict_llm:
                raise RuntimeError(f"AI_PROVIDER={provider} için geçerli bir LLM sağlayıcısı bulunamadı.")
            result = self._generate_local(mode=mode, user_input=user_input, preferences=prefs)

        result = _enrich_result(result)

        apply_to_cart = bool(prefs.get("apply_to_cart", False))
        user_id = None
        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("user_id")
        if include_market_cart and apply_to_cart and user_id and in_stock_products:
            cart_sync = await self._apply_market_cart_to_user_cart(db, str(user_id), result["response"].get("market_cart", {}))
            result["response"]["cart_sync"] = cart_sync

        return result

