from app.utils.recipe_utils import normalize_text, parse_ingredient


def test_normalize_text_supports_turkish_characters():
    assert normalize_text("Kayseri Mantısı") == "kayseri mantisi"
    assert normalize_text("Dana Kıyma") == "dana kiyma"


def test_normalize_text_repairs_common_mojibake():
    assert normalize_text("mantÄ± piÅŸirmek istiyorum") == "manti pisirmek istiyorum"


def test_parse_ingredient_with_long_unit():
    ingredient = parse_ingredient("2 su bardağı un")

    assert ingredient["amount"] == "2"
    assert normalize_text(ingredient["unit"]) == "su bardagi"
    assert ingredient["name"] == "un"
    assert ingredient["normalized_name"] == "un"


def test_parse_ingredient_with_short_unit():
    ingredient = parse_ingredient("250 gr kıyma")

    assert ingredient["amount"] == "250"
    assert ingredient["unit"] == "gr"
    assert ingredient["name"] == "kıyma"
    assert ingredient["normalized_name"] == "kiyma"
