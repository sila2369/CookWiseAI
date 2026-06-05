"""
Schemas for AI prompt preview endpoints.
"""

from enum import Enum

from pydantic import BaseModel, Field

from app.ai.modes import AIMode


class PromptPreviewRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="User message")
    mode: AIMode = Field(default=AIMode.NORMAL, description="AI mode")
    context: str | None = Field(default=None, description="Optional runtime context")


class PromptPreviewResponse(BaseModel):
    mode: AIMode
    prompt: str


class BudgetModeRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="Dish name or general request")
    context: str | None = Field(default=None, description="Optional constraints")


class BudgetModeResponse(BaseModel):
    dish: str
    ingredients: list[str]
    total_cost: str
    budget_tip: str


class DietGoal(str, Enum):
    LOW_CALORIE = "low_calorie"
    HIGH_PROTEIN = "high_protein"
    VEGETARIAN = "vegetarian"


class DietModeRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="Dish name or diet request")
    goal: DietGoal = Field(default=DietGoal.LOW_CALORIE, description="Diet goal")
    context: str | None = Field(default=None, description="Optional constraints")


class MacrosResponse(BaseModel):
    protein: str
    carb: str
    fat: str


class DietModeResponse(BaseModel):
    dish: str
    goal: DietGoal
    ingredients: list[str]
    calories: str
    macros: MacrosResponse


class InventoryModeRequest(BaseModel):
    available_ingredients: list[str] = Field(
        ...,
        min_length=1,
        description="Ingredients currently available to user",
    )
    context: str | None = Field(default=None, description="Optional constraints")


class InventoryDishSuggestion(BaseModel):
    dish: str
    missing_ingredients: list[str]


class InventoryModeResponse(BaseModel):
    possible_dishes: list[InventoryDishSuggestion]


class WeeklyMealPlannerRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="Weekly meal planning request")
    context: str | None = Field(default=None, description="Optional constraints")


class DailyMealPlan(BaseModel):
    day: str
    breakfast: str
    lunch: str
    dinner: str


class ShoppingListItem(BaseModel):
    ingredient: str
    estimated_weekly_units: int


class WeeklyMealPlannerResponse(BaseModel):
    request: str
    weekly_plan: list[DailyMealPlan]
    shopping_list: list[ShoppingListItem]
    optimization_note: str


class AIGenerateRequest(BaseModel):
    mode: AIMode = Field(..., description="AI mode: normal|budget|diet|inventory")
    input: str = Field(..., min_length=1, description="User input text")
    preferences: dict = Field(
        default_factory=dict,
        description=(
            "İsteğe bağlı tercihler: context, include_market_cart, apply_to_cart, meal_category, "
            "conversation_history veya chat_context (sohbet özeti), goal (diet), available_ingredients (inventory) vb."
        ),
    )


class AIGenerateResponse(BaseModel):
    mode: AIMode
    prompt: str
    response: dict
    provider: str

