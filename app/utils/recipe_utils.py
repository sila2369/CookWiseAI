"""Recipe normalization and ingredient parsing helpers."""

from __future__ import annotations

import html
import re
from typing import Any


TR_MAP = str.maketrans(
    {
        "\u00e7": "c",
        "\u011f": "g",
        "\u0131": "i",
        "\u00f6": "o",
        "\u015f": "s",
        "\u00fc": "u",
        "\u00c7": "c",
        "\u011e": "g",
        "\u0130": "i",
        "I": "i",
        "\u00d6": "o",
        "\u015e": "s",
        "\u00dc": "u",
    }
)

MOJIBAKE_MAP = {
    "Ã§": "\u00e7",
    "Ã‡": "\u00c7",
    "ÄŸ": "\u011f",
    "Äž": "\u011e",
    "Ä": "\u011e",
    "Ä±": "\u0131",
    "Ä°": "\u0130",
    "Ã¶": "\u00f6",
    "Ã–": "\u00d6",
    "ÅŸ": "\u015f",
    "Åž": "\u015e",
    "Å": "\u015e",
    "Ã¼": "\u00fc",
    "Ãœ": "\u00dc",
}

UNITS = [
    "su barda\u011f\u0131",
    "su bardagi",
    "\u00e7ay barda\u011f\u0131",
    "cay bardagi",
    "yemek ka\u015f\u0131\u011f\u0131",
    "yemek kasigi",
    "tatl\u0131 ka\u015f\u0131\u011f\u0131",
    "tatli kasigi",
    "\u00e7ay ka\u015f\u0131\u011f\u0131",
    "cay kasigi",
    "kahve fincan\u0131",
    "kahve fincani",
    "paket",
    "adet",
    "dilim",
    "demet",
    "tutam",
    "kase",
    "bardak",
    "kg",
    "kilogram",
    "gr",
    "gram",
    "g",
    "lt",
    "litre",
    "ml",
]


def strip_html(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def repair_mojibake(value: str) -> str:
    text = value or ""
    if not any(marker in text for marker in ("Ã", "Ä", "Å", "Â")):
        return text
    for bad, good in MOJIBAKE_MAP.items():
        text = text.replace(bad, good)
    if not any(marker in text for marker in ("Ã", "Ä", "Å", "Â")):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text
    return repaired if repaired else text


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = strip_html(repair_mojibake(str(value)))
    text = text.replace("\ufeff", " ").replace("\u200b", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(value: Any) -> str:
    text = clean_text(value).translate(TR_MAP).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_listish(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        rows: list[str] = []
        for item in value:
            if isinstance(item, dict):
                rows.append(clean_text(item.get("raw") or item.get("isim") or item.get("name") or ""))
            else:
                rows.append(clean_text(item))
        return [row for row in rows if row]
    text = clean_text(value)
    if not text:
        return []
    parts = re.split(r"\r?\n|;|\s+\|\s+|\u2022", text)
    if len(parts) == 1:
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\u00c7\u011e\u0130\u00d6\u015e\u00dc0-9])", text)
    return [clean_text(part).strip(" -\u2013\u2014,") for part in parts if clean_text(part).strip(" -\u2013\u2014,")]


def parse_ingredient(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        raw_name = clean_text(value.get("isim") or value.get("name") or value.get("ingredient") or value.get("raw") or "")
        amount = clean_text(value.get("miktar") or value.get("amount") or "")
        unit = clean_text(value.get("birim") or value.get("unit") or "")
        raw = clean_text(value.get("raw") or " ".join(part for part in [amount, unit, raw_name] if part))
        name = raw_name or raw
        return {
            "raw": raw,
            "name": clean_text(name),
            "normalized_name": normalize_text(name),
            "amount": amount,
            "unit": unit,
        }

    raw = clean_text(value)
    amount = ""
    unit = ""
    name = raw
    amount_match = re.match(r"^\s*(\d+(?:[.,]\d+)?|[\u00bc\u00bd\u00be\u2153\u2154])\s+", raw)
    rest = raw
    if amount_match:
        amount = amount_match.group(1).replace(",", ".")
        rest = raw[amount_match.end() :].strip()

    normalized_rest = normalize_text(rest)
    for candidate in sorted(UNITS, key=len, reverse=True):
        norm_unit = normalize_text(candidate)
        if normalized_rest == norm_unit or normalized_rest.startswith(norm_unit + " "):
            unit = candidate
            name = rest[len(candidate) :].strip(" -\u2013\u2014,")
            break

    if not name:
        name = rest or raw

    return {
        "raw": raw,
        "name": clean_text(name),
        "normalized_name": normalize_text(name),
        "amount": amount,
        "unit": unit,
    }


def recipe_document(
    *,
    name: Any,
    category: Any = "",
    ingredients: Any = None,
    steps: Any = None,
    duration: Any = "",
    servings: Any = "",
    image: Any = "",
    source: str = "kaggle",
) -> dict[str, Any]:
    cleaned_name = clean_text(name)
    parsed_ingredients = [parse_ingredient(item) for item in (ingredients or [])]
    parsed_ingredients = [item for item in parsed_ingredients if item["normalized_name"]]
    return {
        "name": cleaned_name,
        "normalized_name": normalize_text(cleaned_name),
        "category": clean_text(category),
        "ingredients": parsed_ingredients,
        "steps": [clean_text(step) for step in (steps or []) if clean_text(step)],
        "duration": clean_text(duration),
        "servings": clean_text(servings),
        "image": clean_text(image),
        "source": source,
        "is_active": True,
    }
