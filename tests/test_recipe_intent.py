from app.ai.modes import AIMode
from app.services.ai_generate_service import AIGenerateService


def test_recipe_intent_detects_database_question():
    service = AIGenerateService()

    assert service._is_recipe_request("pizza nasıl yok veri tabanında")
    assert service._extract_meal_name("pizza nasıl yok veri tabanında") == "pizza"


def test_recipe_intent_detects_simple_meal_name():
    service = AIGenerateService()

    assert service._is_recipe_request("pizza")
    assert service._extract_meal_name("pizza") == "pizza"
    assert AIMode.NORMAL.value == "normal"


def test_recipe_intent_detects_short_create_request_for_dataset_recipe():
    service = AIGenerateService()

    assert service._is_recipe_request("karniyarik icin olustur")
    assert service._extract_meal_name("karniyarik icin olustur") == "karniyarik"
    assert service._is_recipe_request("karniyarin icin olustur")
    assert service._extract_meal_name("karniyarin icin olustur") == "karniyarik"


def test_recipe_intent_extracts_meal_from_long_market_request():
    service = AIGenerateService()

    text = "akşam pizza yapmak istiyorum tarifi verip ürünleri listeler misin"
    assert service._is_recipe_request(text)
    assert service._extract_meal_name(text) == "pizza"


def test_recipe_match_scoring_prefers_exact_recipe_name():
    service = AIGenerateService()
    exact = service._score_recipe_product_match(
        "pizza",
        {"name": "Pizza", "normalized_name": "pizza", "ingredients": []},
        {"matched_products": [], "missing_products": []},
    )
    variant = service._score_recipe_product_match(
        "pizza",
        {"name": "Pizza Poğaça", "normalized_name": "pizza pogaca", "ingredients": []},
        {"matched_products": [{"product_id": str(i)} for i in range(10)], "missing_products": []},
    )

    assert exact > variant


def test_market_cart_filter_removes_non_recipe_side_products():
    service = AIGenerateService()
    response = {
        "ingredients": [
            {"item": "Patlican", "quantity": "4 adet"},
            {"item": "Kiyma", "quantity": "300 g"},
            {"item": "Sogan", "quantity": "1 adet"},
        ]
    }
    cart = {
        "items": [
            {"product_id": "1", "name": "Patlican Kemer Kg", "subtotal": 40},
            {"product_id": "2", "name": "Uzman Kasap Dana Kiyma 400 G", "subtotal": 300},
            {"product_id": "3", "name": "Yogurt 1 Kg", "subtotal": 80},
            {"product_id": "4", "name": "Marul Adet", "subtotal": 50},
        ],
        "total_estimated": 470,
        "currency": "TRY",
    }

    filtered = service._filter_market_cart_by_ingredients(
        cart,
        service._ingredient_cart_tokens(response),
    )

    assert [item["product_id"] for item in filtered["items"]] == ["1", "2"]
    assert filtered["total_estimated"] == 340


def test_market_cart_filter_keeps_spice_separate_from_fresh_pepper():
    service = AIGenerateService()
    response = {"ingredients": [{"item": "Kirmizi pul biber", "quantity": "1 cay kasigi"}]}
    cart = {
        "items": [
            {"product_id": "1", "name": "Migros Pul Biber 85 G", "subtotal": 40},
            {"product_id": "2", "name": "Biber Sivri Kg", "subtotal": 50},
        ],
        "total_estimated": 90,
        "currency": "TRY",
    }

    filtered = service._filter_market_cart_by_ingredients(
        cart,
        service._ingredient_cart_tokens(response),
    )

    assert [item["product_id"] for item in filtered["items"]] == ["1"]
