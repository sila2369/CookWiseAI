"""
Weekly meal planner service.

Generates:
- 7-day meal plan (breakfast, lunch, dinner)
- shopping list for entire week
- ingredient reuse optimization
"""

from __future__ import annotations

from collections import Counter


class WeeklyPlannerService:
    """Build deterministic weekly meal plan and aggregated shopping list."""

    WEEK_DAYS = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    # Repeated-core ingredients for optimization
    BREAKFAST = [
        {"dish": "Yogurt Oat Bowl", "ingredients": ["yogurt", "oats", "banana"]},
        {"dish": "Veg Omelette", "ingredients": ["eggs", "onion", "tomato", "pepper"]},
        {"dish": "Cheese Toast", "ingredients": ["bread", "cheese", "tomato"]},
    ]
    LUNCH = [
        {"dish": "Chicken Rice Bowl", "ingredients": ["chicken", "rice", "onion", "pepper"]},
        {"dish": "Lentil Soup", "ingredients": ["lentils", "onion", "tomato paste"]},
        {"dish": "Pasta with Tomato Sauce", "ingredients": ["pasta", "tomato", "onion"]},
    ]
    DINNER = [
        {"dish": "Bulgur Pilaf + Yogurt", "ingredients": ["bulgur", "onion", "yogurt"]},
        {"dish": "Chickpea Stew", "ingredients": ["chickpeas", "onion", "tomato paste"]},
        {"dish": "Baked Chicken & Potatoes", "ingredients": ["chicken", "potato", "onion"]},
    ]

    def build_weekly_plan(self, request_text: str) -> dict:
        weekly_plan = []
        ingredient_counter = Counter()

        for i, day in enumerate(self.WEEK_DAYS):
            b = self.BREAKFAST[i % len(self.BREAKFAST)]
            l = self.LUNCH[i % len(self.LUNCH)]
            d = self.DINNER[i % len(self.DINNER)]

            day_plan = {
                "day": day,
                "breakfast": b["dish"],
                "lunch": l["dish"],
                "dinner": d["dish"],
            }
            weekly_plan.append(day_plan)

            ingredient_counter.update(b["ingredients"])
            ingredient_counter.update(l["ingredients"])
            ingredient_counter.update(d["ingredients"])

        shopping_list = [
            {"ingredient": ingredient, "estimated_weekly_units": count}
            for ingredient, count in sorted(
                ingredient_counter.items(),
                key=lambda x: (-x[1], x[0]),
            )
        ]

        return {
            "request": request_text.strip() or "weekly meal plan",
            "weekly_plan": weekly_plan,
            "shopping_list": shopping_list,
            "optimization_note": (
                "Meals are rotated to reuse core ingredients "
                "(onion, tomato, yogurt, chicken) across multiple days."
            ),
        }

