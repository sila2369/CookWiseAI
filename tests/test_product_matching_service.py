from app.services.product_matching_service import ProductMatchingService


def test_best_match_prefers_fresh_eggplant_for_karniyarik():
    matcher = ProductMatchingService.__new__(ProductMatchingService)
    products = [
        {
            "id": "jar",
            "name": "Migros Kozlenmis Patlican 510 G",
            "normalized_name": "migros kozlenmis patlican 510 g",
            "normalized_category": "temel gida temel gida",
            "price": 55.95,
        },
        {
            "id": "fresh",
            "name": "Patlican Kemer Kg",
            "normalized_name": "patlican kemer kg",
            "normalized_category": "meyve sebze meyve sebze",
            "price": 39.95,
        },
    ]

    assert matcher._best_match("patlican", products)["id"] == "fresh"


def test_best_match_prefers_real_minced_meat_over_ready_meal():
    matcher = ProductMatchingService.__new__(ProductMatchingService)
    products = [
        {
            "id": "ready",
            "name": "Tazedo Pelmeni Manti Dana Kiymali 500 G",
            "normalized_name": "tazedo pelmeni manti dana kiymali 500 g",
            "normalized_category": "meze hazir yemek donuk meze hazir yemek donuk",
            "price": 299.95,
        },
        {
            "id": "mince",
            "name": "Uzman Kasap Dana Kiyma 400 G",
            "normalized_name": "uzman kasap dana kiyma 400 g",
            "normalized_category": "et tavuk balik et tavuk balik",
            "price": 300.0,
        },
    ]

    assert matcher._best_match("kiyma", products)["id"] == "mince"


def test_best_match_keeps_fresh_pepper_separate_from_spice():
    matcher = ProductMatchingService.__new__(ProductMatchingService)
    products = [
        {
            "id": "spice",
            "name": "Migros Pul Biber 85 G",
            "normalized_name": "migros pul biber 85 g",
            "normalized_category": "temel gida temel gida",
            "price": 37.5,
        },
        {
            "id": "fresh",
            "name": "Biber Sivri Kg",
            "normalized_name": "biber sivri kg",
            "normalized_category": "meyve sebze meyve sebze",
            "price": 49.95,
        },
    ]

    assert matcher._best_match("biber", products)["id"] == "fresh"
    assert matcher._best_match("kirmizi pul biber", products)["id"] == "spice"
