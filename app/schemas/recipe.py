"""Recipe API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class RecipeIngredientResponse(BaseModel):
    raw: str
    name: str
    normalized_name: str
    amount: str = ""
    unit: str = ""


class RecipeResponse(BaseModel):
    id: str
    name: str
    normalized_name: str
    category: str = ""
    ingredients: list[RecipeIngredientResponse]
    steps: list[str]
    duration: str = ""
    servings: str = ""
    image: str = ""
    source: str = "kaggle"
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class RecipeListResponse(BaseModel):
    items: list[RecipeResponse]
    total: int


class MatchedProduct(BaseModel):
    ingredient: str
    product_id: str
    product_name: str
    price: float
    image_url: str | None = None


class MissingProduct(BaseModel):
    ingredient: str
    reason: str


class IngredientProductMatchResponse(BaseModel):
    matched_products: list[MatchedProduct]
    missing_products: list[MissingProduct]


def recipe_doc_to_response(doc: dict[str, Any]) -> dict[str, Any]:
    data = dict(doc)
    if "_id" in data:
        data["id"] = str(data.pop("_id"))
    return data
