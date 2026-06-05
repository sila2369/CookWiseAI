"""
Inventory mode planner for AI cooking assistant.

Goal:
- Suggest dishes based on available ingredients.
- Minimize missing ingredients.
"""

from __future__ import annotations

from typing import Dict, List


class InventoryModeService:
    """Find possible dishes from pantry and list missing ingredients."""

    DISH_LIBRARY: Dict[str, List[str]] = {
        "Menemen": ["domates", "biber", "yumurta", "sogan", "yag", "tuz"],
        "Mercimek Corbasi": ["mercimek", "sogan", "salca", "yag", "tuz"],
        "Makarna Soslu": ["makarna", "domates", "salca", "sogan", "yag", "tuz"],
        "Nohutlu Pilav": ["pirinc", "nohut", "sogan", "yag", "tuz"],
        "Sebzeli Omlet": ["yumurta", "kabak", "biber", "sogan", "yag", "tuz"],
    }

    def _normalize(self, items: List[str]) -> set[str]:
        return {item.strip().lower() for item in items if item and item.strip()}

    def build_inventory_plan(self, available_ingredients: List[str]) -> dict:
        available = self._normalize(available_ingredients)
        suggestions = []

        for dish, required in self.DISH_LIBRARY.items():
            req_set = self._normalize(required)
            missing = sorted(req_set - available)
            suggestions.append(
                {
                    "dish": dish,
                    "missing_ingredients": missing,
                    "missing_count": len(missing),
                }
            )

        # Minimize extra ingredients needed
        suggestions.sort(key=lambda x: (x["missing_count"], x["dish"]))

        return {
            "assistant_message": (
                "Evdeki malzemeleri once kullanacak sekilde tarifleri siraladim. "
                "En az eksigi olan yemekler listenin basinda."
            ),
            "available_ingredients": sorted(available),
            "possible_dishes": [
                {
                    "dish": item["dish"],
                    "why_it_fits": (
                        "Elinizdeki malzemelerle uyumlu; eksik sayisi dusuk."
                        if item["missing_count"] <= 2
                        else "Yapilabilir ama birkac tamamlayici malzeme gerekir."
                    ),
                    "missing_ingredients": item["missing_ingredients"],
                    "quick_steps": [
                        "Mevcut malzemeleri ayiklayip dograyin.",
                        "Ana malzemeyi pisirme sirasina gore tavaya veya tencereye alin.",
                        "Eksik malzemeleri varsa basit ikamelerle tamamlayin.",
                    ],
                }
                for item in suggestions
            ],
            "use_first": sorted(available)[:5],
            "shopping_minimum": sorted({missing for item in suggestions[:3] for missing in item["missing_ingredients"]})[:6],
        }

