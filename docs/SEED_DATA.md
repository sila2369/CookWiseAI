# Seed Data - Örnek Veri Ekleme

Test için örnek kategoriler ve ürünler ekler.

## Nasıl Çalıştırılır

```bash
# Proje kökünden
python scripts/seed_data.py
```

veya

```bash
cd CookWise
python scripts/seed_data.py
```

## Ön Koşullar

- MongoDB çalışıyor olmalı
- `.env` dosyasında `MONGODB_URL` ve `MONGODB_DB` tanımlı olmalı

## Ne Eklener?

**5 Kategori:**
- Meyve & Sebze
- İçecek
- Atıştırmalık
- Temizlik
- Süt Ürünleri

**19 Ürün** (her kategori için birkaç adet, price, stock, slug, category_id dolu)

## Tekrar Çalıştırma

Script birden fazla kez çalıştırılabilir. `slug` zaten varsa ekleme atlanır; duplicate oluşmaz.
