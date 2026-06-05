"""
Budget mode planner for cooking assistant.

Note:
- This is a deterministic, low-cost estimator.
- Can later be replaced with an LLM call using the prompt from prompt_builder.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


class BudgetModeService:
    """Generate cheapest ingredient suggestions with rough total cost."""

    # Estimated low-end market prices (TRY-like simple estimates)
    PRICE_CATALOG: Dict[str, float] = {
        "pirinc 500g": 28.0,
        "makarna 500g": 20.0,
        "bulgur 500g": 22.0,
        "kuru sogan 1kg": 18.0,
        "domates 1kg": 30.0,
        "patates 1kg": 25.0,
        "yesil biber 250g": 20.0,
        "yumurta 6'li": 32.0,
        "mercimek 500g": 30.0,
        "nohut 500g": 35.0,
        "tavuk but 500g": 65.0,
        "yogurt 1kg": 45.0,
        "salca 165g": 18.0,
        "sivi yag 500ml": 42.0,
        "tuz baharat temel": 12.0,
        "sarimsak 100g": 10.0,
    }

    DISH_KEYWORDS: Dict[str, List[str]] = {
        "pilav": ["pirinc 500g", "kuru sogan 1kg", "sivi yag 500ml", "tuz baharat temel"],
        "makarna": ["makarna 500g", "domates 1kg", "salca 165g", "sivi yag 500ml", "tuz baharat temel"],
        "corba": ["mercimek 500g", "kuru sogan 1kg", "salca 165g", "sivi yag 500ml", "tuz baharat temel"],
        "tavuk": ["tavuk but 500g", "patates 1kg", "kuru sogan 1kg", "sivi yag 500ml", "tuz baharat temel"],
        "vegan": ["nohut 500g", "bulgur 500g", "domates 1kg", "kuru sogan 1kg", "tuz baharat temel"],
    }

    DEFAULT_BASKET: List[str] = [
        "bulgur 500g",
        "kuru sogan 1kg",
        "domates 1kg",
        "yumurta 6'li",
        "sivi yag 500ml",
        "tuz baharat temel",
    ]

    def _pick_ingredients(self, user_request: str) -> Tuple[str, List[str]]:
        req = user_request.lower().strip()
        for keyword, ingredients in self.DISH_KEYWORDS.items():
            if keyword in req:
                return user_request.strip(), ingredients
        return user_request.strip() or "Ekonomik yemek", self.DEFAULT_BASKET

    def build_budget_plan(self, user_request: str) -> dict:
        dish, ingredients = self._pick_ingredients(user_request)
        total = sum(self.PRICE_CATALOG.get(item, 0.0) for item in ingredients)
        rounded_total = f"{total:.2f} TL"

        tip = (
            "Market markali urun secin ve mevsimlik sebze kullanin. "
            "Ayni malzemelerle 2-3 ogun planlayarak birim maliyeti dusurun."
        )

        return {
            "dish": dish,
            "assistant_message": (
                f"{dish} icin ekonomik bir plan hazirladim. Ana fikir pahali proteinleri azaltip "
                "doyuruculugu bulgur, makarna, yumurta, bakliyat ve mevsim sebzeleriyle tamamlamak."
            ),
            "summary": "Butce modu; dusuk maliyet, az fire ve birden fazla ogune yayilabilecek malzemeleri one alir.",
            "ingredients": ingredients,
            "steps": [
                "Once en uzun pisen bakliyat, bulgur veya makarnayi hazirlayin.",
                "Sogan, salca ve mevsim sebzesini az yagla kavurup ana malzemeye lezzet tabani yapin.",
                "Porsiyonu yogurt, salata veya yumurta gibi uygun tamamlayicilarla doyurucu hale getirin.",
            ],
            "total_cost": rounded_total,
            "cost_breakdown": [
                f"{item}: yaklasik {self.PRICE_CATALOG.get(item, 0.0):.2f} TL"
                for item in ingredients
            ],
            "budget_tip": tip,
            "shopping_strategy": [
                "Market markali ve kampanyali temel urunleri secin.",
                "Ayni sogan, salca ve yag tabanini iki farkli yemekte kullanarak fireyi azaltin.",
                "Et yerine yumurta, bakliyat veya tavuk gibi daha ekonomik proteinleri degerlendirin.",
            ],
        }

