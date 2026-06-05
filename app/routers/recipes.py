"""Recipe endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.services import get_required_database
from app.schemas.recipe import RecipeListResponse, RecipeResponse
from app.services.recipe_service import RecipeService


router = APIRouter(prefix="/recipes", tags=["Recipes"])


@router.get("/search", response_model=RecipeListResponse)
async def search_recipes(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    db=Depends(get_required_database),
) -> RecipeListResponse:
    service = RecipeService(db)
    items = await service.search_recipe_by_name(q, limit=limit)
    return RecipeListResponse(items=items, total=len(items))


@router.get("/by-ingredients", response_model=RecipeListResponse)
async def recipes_by_ingredients(
    ingredients: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    db=Depends(get_required_database),
) -> RecipeListResponse:
    parsed = [item.strip() for item in ingredients.split(",") if item.strip()]
    service = RecipeService(db)
    items = await service.find_recipes_by_ingredients(parsed, limit=limit)
    return RecipeListResponse(items=items, total=len(items))


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: str, db=Depends(get_required_database)) -> RecipeResponse:
    service = RecipeService(db)
    recipe = await service.get_recipe_by_id(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarif bulunamadi",
        )
    return RecipeResponse(**recipe)
