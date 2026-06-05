#!/usr/bin/env python3
"""
Fetch Migros category products into CSV files.

Usage:
    python scripts/migros_scrape.py
    python scripts/migros_scrape.py --max-pages 5
    python scripts/migros_scrape.py --categories temel-gida meyve-sebze

Session cookies are not stored in this file. If Migros requires a session,
pass it temporarily with the MIGROS_COOKIE environment variable.
"""

from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests


BASE_DOMAIN = "https://www.migros.com.tr"
OUTPUT_CSV = "migros_urunler.csv"
CSV_FIELDS = [
    "source_id",
    "name",
    "price",
    "regular_price",
    "isStock",
    "image_url",
    "brand",
    "unit",
    "subcategory",
    "promotion_label",
    "category",
    "source_url",
]

CATEGORY_TARGETS: List[Dict[str, str]] = [
    {
        "category": "meyve-sebze",
        "api_url": "https://www.migros.com.tr/rest/search/screens/meyve-sebze-c-2?reid=1778320782858000001",
    },
    {
        "category": "temel-gida",
        "api_url": "https://www.migros.com.tr/rest/search/screens/temel-gida-c-5?reid=1778839566511000001",
    },
    {
        "category": "et-tavuk-balik",
        "api_url": "https://www.migros.com.tr/rest/search/screens/et-tavuk-balik-c-3?reid=1778322072032000001",
    },
    {
        "category": "sut-kahvaltilik",
        "api_url": "https://www.migros.com.tr/rest/search/screens/sut-kahvaltilik-c-4?reid=1778322119438000001",
    },
    {
        "category": "icecek",
        "api_url": "https://www.migros.com.tr/rest/search/screens/icecek-c-6?reid=1778322163106000001",
    },
    {
        "category": "atistirmalik",
        "api_url": "https://www.migros.com.tr/rest/search/screens/atistirmalik-c-113fb?reid=1778322987254000001",
    },
    {
        "category": "firin-pastane",
        "api_url": "https://www.migros.com.tr/rest/search/screens/firin-pastane-c-7e?reid=1778323020796000001",
    },
    {
        "category": "meze-hazir-yemek-donuk",
        "api_url": "https://www.migros.com.tr/rest/search/screens/meze-hazir-yemek-donuk-c-7d?reid=1778323061038000001",
    },
    {
        "category": "deterjan-temizlik",
        "api_url": "https://www.migros.com.tr/rest/search/screens/deterjan-temizlik-c-7?reid=1778323095250000001",
    },
    {
        "category": "kagit-islak-mendil",
        "api_url": "https://www.migros.com.tr/rest/search/screens/kagit-islak-mendil-c-8d?reid=1778323128524000001",
    },
    {
        "category": "bebek",
        "api_url": "https://www.migros.com.tr/rest/search/screens/bebek-c-9?reid=1778323219522000001",
    },
    {
        "category": "kisisel-bakim-kozmetik-saglik",
        "api_url": "https://www.migros.com.tr/rest/search/screens/kisisel-bakim-kozmetik-saglik-c-8?reid=1778323287088000126",
    },
    {
        "category": "evcil-hayvan",
        "api_url": "https://www.migros.com.tr/rest/search/screens/evcil-hayvan-c-a0?reid=1778323320423000001",
    },
]


HEADERS: Dict[str, str] = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "tr",
    "priority": "u=1, i",
    "referer": "https://www.migros.com.tr",
    "sec-ch-ua": '"Google Chrome";v="148", "Not.A/Brand";v="99", "Chromium";v="148"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "x-device-pwa": "true",
    "x-forwarded-rest": "true",
    "x-pwa": "true",
}


def normalize_image_url(image_value: str) -> str:
    if not image_value:
        return ""
    if image_value.startswith(("http://", "https://")):
        return image_value
    return urljoin(BASE_DOMAIN, image_value)


def pick_image(images_field: Any) -> str:
    if isinstance(images_field, str):
        return normalize_image_url(images_field)

    if isinstance(images_field, list) and images_field:
        first = images_field[0]
        if isinstance(first, str):
            return normalize_image_url(first)
        if isinstance(first, dict):
            urls_obj = first.get("urls")
            if isinstance(urls_obj, dict):
                for key in ("PRODUCT_LIST", "PRODUCT_DETAIL", "PRODUCT_HD", "CART"):
                    value = urls_obj.get(key)
                    if value:
                        return normalize_image_url(str(value))
            for key in ("url", "imageUrl", "src", "path"):
                value = first.get(key)
                if value:
                    return normalize_image_url(str(value))

    if isinstance(images_field, dict):
        for key in ("url", "imageUrl", "src", "path"):
            value = images_field.get(key)
            if value:
                return normalize_image_url(str(value))

    return ""


def pick_price(item: Dict[str, Any]) -> Any:
    for key in ("shownPrice", "regularPrice"):
        value = item.get(key)
        if value is not None:
            try:
                return round(float(value) / 100, 2)
            except Exception:
                return value

    for key in ("price", "salePrice", "currentPrice", "amount"):
        if key in item and item[key] is not None:
            return item[key]

    price_obj = item.get("price")
    if isinstance(price_obj, dict):
        for key in ("value", "amount", "salePrice"):
            if key in price_obj and price_obj[key] is not None:
                return price_obj[key]
    return None


def pick_regular_price(item: Dict[str, Any]) -> Any:
    value = item.get("regularPrice")
    if value is None:
        return ""
    try:
        return round(float(value) / 100, 2)
    except Exception:
        return value


def pick_stock(item: Dict[str, Any]) -> Any:
    status_value = item.get("status")
    if isinstance(status_value, str):
        return status_value.upper() == "IN_SALE"

    for key in ("isStock", "inStock", "isInStock", "stockAvailable"):
        if key in item:
            return item[key]
    return None


def pick_brand(item: Dict[str, Any]) -> str:
    brand = item.get("brand")
    if isinstance(brand, dict):
        return str(brand.get("name") or "").strip()
    if isinstance(brand, str):
        return brand.strip()
    return ""


def pick_category_name(item: Dict[str, Any]) -> str:
    category = item.get("category")
    if isinstance(category, dict):
        return str(category.get("name") or "").strip()
    return ""


def pick_promotion_label(item: Dict[str, Any]) -> str:
    tags = item.get("crmDiscountTags")
    if isinstance(tags, list):
        labels = [
            str(tag.get("tag") or "").strip()
            for tag in tags
            if isinstance(tag, dict) and tag.get("tag")
        ]
        if labels:
            return " | ".join(labels)

    badges = item.get("badges")
    if isinstance(badges, list):
        labels = [
            str(badge.get("value") or badge.get("name") or "").strip()
            for badge in badges
            if isinstance(badge, dict) and (badge.get("value") or badge.get("name"))
        ]
        if labels:
            return " | ".join(labels)

    return ""


def collect_product_candidates(node: Any, collector: List[Dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("name"), str):
            collector.append(node)
        for value in node.values():
            collect_product_candidates(value, collector)
        return

    if isinstance(node, list):
        for item in node:
            collect_product_candidates(item, collector)


def product_row(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_id": item.get("id") or item.get("sku") or "",
        "name": item.get("name") or "",
        "price": pick_price(item),
        "regular_price": pick_regular_price(item),
        "isStock": pick_stock(item),
        "image_url": pick_image(item.get("images")),
        "brand": pick_brand(item),
        "unit": item.get("unit") or "",
        "subcategory": pick_category_name(item),
        "promotion_label": pick_promotion_label(item),
    }


def extract_products(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    direct_items = payload.get("data", {}).get("searchInfo", {}).get("storeProductInfos", [])
    if isinstance(direct_items, list) and direct_items:
        products = [product_row(item) for item in direct_items if isinstance(item, dict) and item.get("name")]
        if products:
            return products

    candidates: List[Dict[str, Any]] = []
    collect_product_candidates(payload, candidates)

    unique_rows = set()
    products: List[Dict[str, Any]] = []
    for item in candidates:
        row = product_row(item)
        if not row["name"] or (row["price"] is None and row["isStock"] is None and not row["image_url"]):
            continue

        unique_key = (str(row["name"]), str(row["price"]), str(row["isStock"]), str(row["image_url"]))
        if unique_key in unique_rows:
            continue

        unique_rows.add(unique_key)
        products.append(row)

    return products


def build_referer_from_api_url(api_url: str) -> str:
    marker = "/rest/search/screens/"
    if marker not in api_url:
        return BASE_DOMAIN
    category_path = api_url.split(marker, 1)[1].split("?", 1)[0]
    return f"{BASE_DOMAIN}/{category_path}"


def build_page_url(api_url: str, page: int) -> str:
    parts = urlsplit(api_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["sayfa"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def get_page_count(payload: Dict[str, Any]) -> int:
    value = payload.get("data", {}).get("searchInfo", {}).get("pageCount", 1)
    try:
        return max(1, int(value))
    except Exception:
        return 1


def fetch_category_products(
    category_name: str,
    api_url: str,
    max_pages: int | None = None,
    sleep_seconds: float = 0.3,
) -> List[Dict[str, Any]]:
    request_headers = dict(HEADERS)
    request_headers["referer"] = build_referer_from_api_url(api_url)
    cookie = os.getenv("MIGROS_COOKIE", "").strip()
    if cookie:
        request_headers["cookie"] = cookie

    all_products: List[Dict[str, Any]] = []
    seen_keys: set[str] = set()
    page = 1
    total_pages = 1

    while page <= total_pages:
        if max_pages is not None and page > max_pages:
            break

        page_url = build_page_url(api_url, page)
        response = requests.get(page_url, headers=request_headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        total_pages = get_page_count(payload)

        page_products = extract_products(payload)
        if not page_products:
            break

        for row in page_products:
            key = str(row.get("source_id") or row.get("name") or "").strip().lower()
            if key and key in seen_keys:
                continue
            if key:
                seen_keys.add(key)
            row["category"] = category_name
            row["source_url"] = page_url
            all_products.append(row)

        print(f"   sayfa {page}/{total_pages}: {len(page_products)} urun")
        page += 1
        if page <= total_pages and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return all_products


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migros kategori urunlerini CSV'ye aktarir.")
    parser.add_argument("--max-pages", type=int, default=None, help="Kategori basina en fazla kac sayfa cekilecek.")
    parser.add_argument(
        "--categories",
        nargs="*",
        default=None,
        help="Sadece belirtilen kategori slug'larini cek. Ornek: temel-gida meyve-sebze",
    )
    parser.add_argument("--sleep", type=float, default=0.3, help="Sayfalar arasi bekleme saniyesi.")
    return parser.parse_args()


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    targets = CATEGORY_TARGETS
    if args.categories:
        selected = set(args.categories)
        targets = [target for target in CATEGORY_TARGETS if target["category"] in selected]
        missing = selected.difference({target["category"] for target in targets})
        if missing:
            print(f"Uyari: kategori bulunamadi: {', '.join(sorted(missing))}")

    all_products: List[Dict[str, Any]] = []

    for target in targets:
        category_name = target["category"]
        api_url = target["api_url"]
        print(f"Kategori cekiliyor: {category_name}")

        try:
            category_products = fetch_category_products(
                category_name,
                api_url,
                max_pages=args.max_pages,
                sleep_seconds=args.sleep,
            )
            if not category_products:
                print(f" - Uyari: '{category_name}' icin urun bulunamadi.")
                continue

            all_products.extend(category_products)
            category_csv = f"migros_urunler_{category_name}.csv"
            write_csv(category_csv, category_products)
            print(f" - {len(category_products)} urun kaydedildi: {category_csv}")

        except requests.exceptions.RequestException as exc:
            print(f" - HTTP hatasi ({category_name}): {exc}")
        except ValueError as exc:
            print(f" - JSON parse hatasi ({category_name}): {exc}")
        except Exception as exc:
            print(f" - Beklenmeyen hata ({category_name}): {exc}")

    if not all_products:
        print("Hicbir kategoriden urun alinamadi.")
        return

    write_csv(OUTPUT_CSV, all_products)

    print(f"\nToplam urun: {len(all_products)}")
    print(f"Birlesik CSV kaydedildi: {OUTPUT_CSV}")
    for row in all_products[:10]:
        print(row)


if __name__ == "__main__":
    main()
