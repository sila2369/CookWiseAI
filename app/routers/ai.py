"""
AI router: example usage of mode-based prompt builder.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.prompt_builder import (
    build_budget_json_prompt,
    build_diet_json_prompt,
    build_inventory_json_prompt,
    build_weekly_plan_json_prompt,
    build_prompt,
)
from app.schemas.ai import (
    AIGenerateRequest,
    AIGenerateResponse,
    BudgetModeRequest,
    BudgetModeResponse,
    DietModeRequest,
    DietModeResponse,
    InventoryModeRequest,
    InventoryModeResponse,
    PromptPreviewRequest,
    PromptPreviewResponse,
    WeeklyMealPlannerRequest,
    WeeklyMealPlannerResponse,
)
from app.services.ai_budget_service import BudgetModeService
from app.services.ai_diet_service import DietModeService
from app.services.ai_generate_service import AIGenerateService
from app.services.ai_inventory_service import InventoryModeService
from app.services.ai_weekly_planner_service import WeeklyPlannerService
from app.dependencies.services import get_required_database
from app.dependencies.auth import get_optional_user

router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)
budget_service = BudgetModeService()
diet_service = DietModeService()
inventory_service = InventoryModeService()
weekly_planner_service = WeeklyPlannerService()
generate_service = AIGenerateService()


@router.post(
    "/prompt-preview",
    response_model=PromptPreviewResponse,
    summary="Build prompt preview by mode",
)
async def prompt_preview(payload: PromptPreviewRequest) -> PromptPreviewResponse:
    """
    Example endpoint that builds the final prompt text.
    This can later feed an LLM provider call.
    """
    prompt = build_prompt(
        user_input=payload.user_input,
        mode=payload.mode,
        context=payload.context,
    )
    return PromptPreviewResponse(mode=payload.mode, prompt=prompt)


@router.post(
    "/budget-plan",
    response_model=BudgetModeResponse,
    summary="Budget mode cooking suggestion (structured JSON)",
)
async def budget_plan(payload: BudgetModeRequest) -> BudgetModeResponse:
    """
    User sends a dish/general request.
    Service returns the cheapest practical ingredient basket,
    estimated cost, and one budget tip as structured JSON.

    Prompt engineering is applied through build_budget_json_prompt,
    ready for future LLM integration.
    """
    _prompt_for_llm = build_budget_json_prompt(
        user_input=payload.user_input,
        context=payload.context,
    )
    result = budget_service.build_budget_plan(payload.user_input)
    return BudgetModeResponse(**result)


@router.post(
    "/diet-plan",
    response_model=DietModeResponse,
    summary="Diet mode cooking suggestion (structured JSON)",
)
async def diet_plan(payload: DietModeRequest) -> DietModeResponse:
    """
    Supports low_calorie, high_protein, and vegetarian goals.
    Returns clean JSON with ingredients, calories, and macros.
    """
    _prompt_for_llm = build_diet_json_prompt(
        user_input=payload.user_input,
        goal=payload.goal.value,
        context=payload.context,
    )
    result = diet_service.build_diet_plan(
        user_request=payload.user_input,
        goal=payload.goal.value,
    )
    return DietModeResponse(**result)


@router.post(
    "/inventory-plan",
    response_model=InventoryModeResponse,
    summary="Inventory mode dish suggestion (structured JSON)",
)
async def inventory_plan(payload: InventoryModeRequest) -> InventoryModeResponse:
    """
    User provides available ingredients.
    Returns possible dishes sorted by minimum missing ingredients.
    """
    _prompt_for_llm = build_inventory_json_prompt(
        available_ingredients=payload.available_ingredients,
        context=payload.context,
    )
    result = inventory_service.build_inventory_plan(payload.available_ingredients)
    return InventoryModeResponse(**result)


@router.post(
    "/weekly-meal-plan",
    response_model=WeeklyMealPlannerResponse,
    summary="Generate 7-day meal plan + weekly shopping list (structured JSON)",
)
async def weekly_meal_plan(payload: WeeklyMealPlannerRequest) -> WeeklyMealPlannerResponse:
    """
    Generates:
    - 7-day meal plan (breakfast/lunch/dinner)
    - full-week shopping list
    - ingredient reuse optimization note
    """
    _prompt_for_llm = build_weekly_plan_json_prompt(
        user_request=payload.user_input,
        context=payload.context,
    )
    result = weekly_planner_service.build_weekly_plan(payload.user_input)
    return WeeklyMealPlannerResponse(**result)


@router.post(
    "/generate",
    response_model=AIGenerateResponse,
    summary="Unified AI generation endpoint",
)
async def generate(
    payload: AIGenerateRequest,
    db=Depends(get_required_database),
    current_user=Depends(get_optional_user),
) -> AIGenerateResponse:
    """
    Single entry point for AI modes:
    - mode selection
    - prompt build
    - AI engine call
    - structured response
    """
    try:
        result = await generate_service.generate(
            mode=payload.mode,
            user_input=payload.input,
            preferences=payload.preferences,
            db=db,
            current_user=current_user,
        )
        return AIGenerateResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

