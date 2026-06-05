"""
Diet mode planner for AI cooking assistant.

Supports:
- low calorie
- high protein
- vegetarian
"""

from __future__ import annotations

from typing import Dict, List


class DietModeService:
    """Create deterministic diet-oriented ingredient and macro plans."""

    PLANS: Dict[str, dict] = {
        "low_calorie": {
            "ingredients": [
                "tavuk gogus 200g",
                "brokoli 200g",
                "kabak 150g",
                "zeytinyagi 1 tatli kasigi",
                "limon suyu",
            ],
            "calories": "430 kcal",
            "macros": {"protein": "48g", "carb": "22g", "fat": "14g"},
        },
        "high_protein": {
            "ingredients": [
                "yumurta 3 adet",
                "lor peyniri 100g",
                "yulaf 40g",
                "yogurt 200g",
                "ispanak 100g",
            ],
            "calories": "620 kcal",
            "macros": {"protein": "58g", "carb": "42g", "fat": "24g"},
        },
        "vegetarian": {
            "ingredients": [
                "nohut 150g",
                "kinoa 80g",
                "mantar 150g",
                "kabak 150g",
                "zeytinyagi 1 yemek kasigi",
            ],
            "calories": "560 kcal",
            "macros": {"protein": "24g", "carb": "68g", "fat": "20g"},
        },
    }

    def _normalize_goal(self, goal: str) -> str:
        key = goal.strip().lower()
        if key not in self.PLANS:
            return "low_calorie"
        return key

    def build_diet_plan(self, user_request: str, goal: str) -> dict:
        normalized_goal = self._normalize_goal(goal)
        plan = self.PLANS[normalized_goal]

        dish = user_request.strip() or "Diet meal"
        ingredients: List[str] = plan["ingredients"]

        return {
            "dish": dish,
            "assistant_message": (
                f"{dish} icin {normalized_goal} hedefine uygun bir plan hazirladim. "
                "Porsiyon, protein ve karbonhidrat dengesini birlikte tuttum."
            ),
            "summary": "Diyet modu; hedefe gore kalori, makro ve pisirme yontemini dengeler.",
            "goal": normalized_goal,
            "ingredients": ingredients,
            "steps": [
                "Proteini izgara, haslama veya az yagli tavada pisirin.",
                "Sebzeleri hacim ve lif icin tabaga ekleyin; sosu yagi olculu kullanarak hazirlayin.",
                "Karbonhidrati hedefe gore porsiyonlayin ve tabagi sicak servis edin.",
            ],
            "calories": plan["calories"],
            "macros": plan["macros"],
            "nutrition_notes": [
                "Protein ana tokluk kaynagi olarak planlandi.",
                "Sebze ve lif destegi kan sekerini daha dengeli tutmaya yardimci olur.",
                "Yag miktarini kasikla olcmek kaloriyi kontrol etmeyi kolaylastirir.",
            ],
            "timing_tips": [
                "Antrenman sonrasi tuketilecekse karbonhidrati tamamen cikarmayin.",
                "Gece gec saatte yiyecekseniz porsiyonu kucultup sebze oranini artirin.",
            ],
        }

