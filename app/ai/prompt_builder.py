"""
Prompt builder for mode-based AI behavior.
"""

from __future__ import annotations

import re
from typing import Dict

from app.ai.modes import AIMode


BASE_SYSTEM_PROMPT = (
    "Sen CookWise için deneyimli bir Türk mutfağı şefi, beslenme ve akıllı alışveriş rehberisin. "
    "Sıcak, güven veren ve doğal bir dille konuş; acemi kullanıcıya adım adım yol göster; "
    "robotik ve tek cümlelik yüzeysel cevaplardan kaçın. Pratik, güvenli, ölçülebilir ve "
    "piyasada bulunabilir malzemelerle çalış."
)

JSON_OUTPUT_CONTRACT = (
    "Çıktı kuralları (mutlak): Yanıtın tamamı tek bir geçerli JSON nesnesi olmalı. "
    "JSON dışında hiçbir metin, markdown kod çiti veya açıklama yazma. "
    "Tüm zengin anlatım yalnızca JSON içindeki string ve dizi alanlarında olmalı."
)

COOKWISE_JSON_SYSTEM_PROMPT = (
    BASE_SYSTEM_PROMPT
    + " Rollerin: premium mutfak asistanı, akıllı market alışverişi, menü planlama ve sohbet eden şef. "
    "Tarifleri fazlar halinde düşün (hazırlık → pişirme → servis); ısı, süre ve teknikleri net belirt. "
    "Uygun olduğunda alternatif malzemeler, yan yemek ve içecek öner; kullanıcı takip sorusu soruyorsa "
    "[CONTEXT] veya sohbet özetindeki önceki tarifle tutarlı kal, konuyu kullanıcı değiştirmedikçe "
    "sürdür ve gereksiz tekrara düşme. "
    "Kullanıcı yalnızca selamlaşıyor, teşekkür ediyor veya tarif istemediği halde genel sohbet ediyorsa "
    "uydurma tarif yazma: sıcak kısa bir karşılık ver ve yemek konusunda nazikçe yönlendir. "
    "Her yanıtta kullanıcının son mesajındaki yemek/kısıt anahtar kelimelerini yansıt; önceki turun metnini körü körüne kopyalama. "
    + JSON_OUTPUT_CONTRACT
)


MODE_INSTRUCTIONS: Dict[AIMode, str] = {
    AIMode.NORMAL: (
        "Normal mod: lezzet, süre ve kolaylığı dengeler; sohbeti ve tarif anlatımını zengin tutar."
    ),
    AIMode.BUDGET: (
        "Budget mode. Minimize cost, suggest affordable substitutions, "
        "and avoid expensive ingredients when possible."
    ),
    AIMode.DIET: (
        "Diet mode. Prioritize nutritional balance, lighter options, and "
        "clear calorie-conscious suggestions."
    ),
    AIMode.INVENTORY: (
        "Inventory mode. Use only available ingredients first, reduce waste, "
        "and suggest minimal missing items."
    ),
}


def build_prompt(
    user_input: str,
    mode: AIMode = AIMode.NORMAL,
    system_prompt: str = BASE_SYSTEM_PROMPT,
    context: str | None = None,
) -> str:
    """
    Build a final AI prompt by combining:
    - base system instructions
    - mode-specific instructions
    - optional context
    - user request
    """
    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS[AIMode.NORMAL])

    sections = [
        f"[SYSTEM]\n{system_prompt}",
        f"[MODE]\n{mode.value}\n{mode_instruction}",
    ]

    if context:
        sections.append(f"[CONTEXT]\n{context}")

    sections.append(f"[USER_REQUEST]\n{user_input}")
    return "\n\n".join(sections)


def is_likely_greeting_or_smalltalk(user_input: str) -> bool:
    """
    Kısa selam / nezaket / genel sohbet (tarif talebi değil).
    Mobil istemcideki isLikelyNonRecipeMessage ile aynı kümeye yakın tutulur.
    """
    raw = (user_input or "").strip()
    if not raw or len(raw) > 80:
        return False
    t = " ".join(raw.lower().split())
    t = re.sub(r"[!?.…]+$", "", t)
    phrases = {
        "merhaba",
        "mrb",
        "selam",
        "slm",
        "hey",
        "hello",
        "sa",
        "as",
        "günaydın",
        "gunaydin",
        "iyi günler",
        "iyi akşamlar",
        "iyi aksamlar",
        "teşekkürler",
        "tesekkurler",
        "teşekkür",
        "tesekkur",
        "sağol",
        "sagol",
        "eyvallah",
        "eyv",
        "tamam",
        "nasılsın",
        "nasilsin",
        "naber",
        "ne haber",
        "napıyorsun",
        "napim",
        "görüşürüz",
        "gorusuruz",
        "hoşça kal",
        "hosca kal",
        "bb",
        "bye",
    }
    return t in phrases


def build_normal_json_prompt(user_input: str, context: str | None = None) -> str:
    """
    Prompt template for normal chat mode with strict JSON output.
    """
    schema = (
        '{\n'
        '  "assistant_message": "string (kullaniciya dogrudan gosterilecek dogal ve akici cevap)",\n'
        '  "title": "string (görünen başlık; isteğe bağlı emoji)",\n'
        '  "description": "string (2-5 cümle: yemek hakkında davetkar giriş)",\n'
        '  "summary": "string (1-2 cümle özet; description ile uyumlu)",\n'
        '  "recipe": "string (kısa tarif adı; title ile uyumlu olabilir)",\n'
        '  "servings": "number",\n'
        '  "prep_time": "string",\n'
        '  "cook_time": "string",\n'
        '  "cooking_time": "string (cook_time ile aynı anlam; ikisini de doldur veya cook_time kopyası)",\n'
        '  "difficulty": "string (ör. Kolay/Orta/Zor)",\n'
        '  "calories": "string (tahmini toplam veya porsiyon başına belirt)",\n'
        '  "protein": "string",\n'
        '  "carbs": "string",\n'
        '  "fats": "string",\n'
        '  "ingredients": [\n'
        '    {\n'
        '      "item": "string",\n'
        '      "quantity": "string"\n'
        '    }\n'
        '  ],\n'
        '  "preparation": ["string (hazırlık adımları)"],\n'
        '  "steps": ["string (pişirme/servis adımları; her adım net ve sıralı)"],\n'
        '  "serving_suggestion": "string",\n'
        '  "optional_sides": ["string"],\n'
        '  "optional_drinks": ["string"],\n'
        '  "tips": ["string"],\n'
        '  "chef_notes": ["string veya tek uzun metin için dizi içinde paragraflar"],\n'
        '  "shopping_recommendations": ["string (ürün/marka/kalite ipuçları; listelenen market ürünleriyle uyumlu)"],\n'
        '  "market_cart": {\n'
        '    "items": [\n'
        '      { "product_id": "string", "quantity": "number" }\n'
        '    ]\n'
        '  }\n'
        '}'
    )

    instructions = (
        "Önce kullanıcı niyetini anla: malzeme listesi mi, tarif mi, pişirme tekniği mi, takip sorusu mu, "
        "yoksa yalnızca selam/teşekkür/sohbet mi? "
        "Tarif istenmiyorsa uydurma yemek anlatma; summary ve description ile sıcak karşılık ver; "
        "ingredients=[] ve preparation=[] kullan; steps içinde en fazla 1 kısa madde: ne pişirmek istediğini nazikçe sor. "
        "Tarif isteniyorsa hazırlık ve pişirmeyi ayır; adımlarda ısı ve süre ver; acemiye yönelik kısa teknik notları ekle. "
        "Beslenme tahminleri makul aralıkta olsun; emin değilsen aralık veya yaklaşık ifade kullan. "
        "[MARKET_CART_RULES] varsa market_cart şemasına uy ve yalnızca verilen ürün id’lerini kullan. "
        "Alanları frontend kartları için düşün: description=giriş kartı, preparation/steps=timeline, "
        "ingredients=liste, nutrition alanları=özet kartı, tips/chef_notes=akordeon. "
        "assistant_message alanini ekranda direkt okunacak cevap gibi yaz: dogal, net ve uygulanabilir olsun. "
        + JSON_OUTPUT_CONTRACT
    )

    sections = [
        f"[SYSTEM]\n{BASE_SYSTEM_PROMPT}",
        f"[MODE]\n{AIMode.NORMAL.value}\n{MODE_INSTRUCTIONS[AIMode.NORMAL]}",
        f"[OUTPUT_FORMAT]\nAşağıdaki şemayı baz al; ilgili alanları eksiksiz doldur; gereksiz rastgele ek anahtar ekleme.\n"
        "Not: market_cart yalnızca promptta [MARKET_CART_RULES] varsa eklenmeli; yoksa bu anahtarı yazma.\n"
        f"{schema}",
        (
            "[RULES]\n"
            "- Tüm kullanıcıya dönük metinler Türkçe olsun (kullanıcı açıkça başka dil istemedikçe).\n"
            "- Tarif bağlamında doğal ve şef gibi anlat; saf selamlaşmada kısa ve sıcak ol, gereksiz uzatma.\n"
            "- Ölçüleri somut tut (su bardağı, yemek kaşığı, g, adet, ml).\n"
            "- Malzeme adlarını markette aranabilir şekilde yaz.\n"
            "- preparation ve steps sıralı, numaralandırılmış gibi net cümleler olsun.\n"
            "- prep_time, cook_time ve cooking_time tutarlı olsun (cooking_time cook_time ile aynı süre olabilir).\n"
            "- summary kısa; description daha zengin olsun.\n"
            "- recipe ve title birbirini desteklesin.\n"
            "- optional_sides ve optional_drinks uygunsa doldur; boşsa [] kullan.\n"
            "- chef_notes: püf noktaları, riskler (ör. yanma), saklama; tips: genel mutfak ipuçları.\n"
            "- shopping_recommendations: hangi ürün tipinin neden işe yarayacağı (marka uydurma, abartı yok).\n"
            "- [CONTEXT] içinde önceki tur varsa aynı yemeği derinleştir veya soruya doğrudan yanıt ver.\n"
            "- Her yanıtta [USER_REQUEST] içeriğini açıkça yansıt; önceki örneklerle aynı cümleleri kopyalama.\n"
            "- [MARKET_CART_RULES] bölümü yoksa market_cart anahtarını JSON'a hiç ekleme."
        ),
        f"[PROMPT_ENGINEERING]\n{instructions}",
    ]

    if context:
        sections.append(f"[CONTEXT]\n{context}")

    sections.append(f"[USER_REQUEST]\n{user_input}")
    return "\n\n".join(sections)


def build_budget_json_prompt(user_input: str, context: str | None = None) -> str:
    """
    Prompt engineering template for budget mode with strict JSON output.
    """
    schema = (
        '{\n'
        '  "dish": "string",\n'
        '  "assistant_message": "string (kullaniciya dogrudan gosterilecek aciklayici cevap)",\n'
        '  "summary": "string (neden ekonomik oldugunu anlatan kisa ozet)",\n'
        '  "ingredients": ["string"],\n'
        '  "steps": ["string (pratik hazirlik/pisirme adimlari)"],\n'
        '  "total_cost": "string",\n'
        '  "cost_breakdown": ["string (urun/malzeme bazli yaklasik maliyet)"],\n'
        '  "budget_tip": "string",\n'
        '  "shopping_strategy": ["string (stoklu urun, ikame, porsiyon ve israf azaltma onerileri)"]\n'
        '}'
    )

    instructions = (
        "You are a budget-focused cooking assistant. "
        "Use the cheapest reasonable ingredients and keep quality acceptable. "
        "Estimate realistic total cost in local market style. "
        "Explain why this menu is economical and how the user can cook it. "
        "Return only valid JSON, no markdown, no extra text."
    )

    sections = [
        f"[SYSTEM]\n{BASE_SYSTEM_PROMPT}",
        f"[MODE]\n{AIMode.BUDGET.value}\n{MODE_INSTRUCTIONS[AIMode.BUDGET]}",
        f"[OUTPUT_FORMAT]\nReturn strictly this JSON schema:\n{schema}",
        (
            "[RULES]\n"
            "- Prioritize low-cost staples.\n"
            "- Prefer seasonal and store-brand options.\n"
            "- Do not make packaged ready foods (doner, pizza, frozen meal, snack) the main dish unless user explicitly asks.\n"
            "- Build a home-cooked economical menu from raw ingredients such as bakliyat, bulgur, makarna, yumurta, tavuk, seasonal vegetables.\n"
            "- Keep ingredient list short and practical.\n"
            "- Include practical cooking steps, cost_breakdown, and shopping_strategy.\n"
            "- If [CONTEXT] has market products, base shopping suggestions on those products; do not invent product ids."
        ),
        f"[PROMPT_ENGINEERING]\n{instructions}",
    ]

    if context:
        sections.append(f"[CONTEXT]\n{context}")

    sections.append(f"[USER_REQUEST]\n{user_input}")
    return "\n\n".join(sections)


def build_diet_json_prompt(
    user_input: str,
    goal: str,
    context: str | None = None,
) -> str:
    """
    Prompt engineering template for diet mode with strict JSON output.
    """
    schema = (
        '{\n'
        '  "dish": "string",\n'
        '  "assistant_message": "string (kullaniciya dogrudan gosterilecek aciklayici cevap)",\n'
        '  "summary": "string (hedefe neden uygun oldugunu ozetle)",\n'
        '  "goal": "low_calorie | high_protein | vegetarian",\n'
        '  "ingredients": ["string"],\n'
        '  "steps": ["string"],\n'
        '  "calories": "string",\n'
        '  "macros": {\n'
        '    "protein": "string",\n'
        '    "carb": "string",\n'
        '    "fat": "string"\n'
        '  },\n'
        '  "nutrition_notes": ["string"],\n'
        '  "timing_tips": ["string (spor/ogun zamanlamasi veya porsiyon notu)"]\n'
        '}'
    )

    instructions = (
        "You are a nutrition-focused cooking assistant. "
        "Generate practical ingredients based on the selected goal. "
        "Estimate calories and macros clearly. "
        "Explain portioning, protein/carbohydrate balance, and cooking steps. "
        "Return only valid JSON, no markdown, no extra text."
    )

    sections = [
        f"[SYSTEM]\n{BASE_SYSTEM_PROMPT}",
        f"[MODE]\n{AIMode.DIET.value}\n{MODE_INSTRUCTIONS[AIMode.DIET]}",
        f"[GOAL]\n{goal}",
        f"[OUTPUT_FORMAT]\nReturn strictly this JSON schema:\n{schema}",
        (
            "[RULES]\n"
            "- Keep ingredient list concise and realistic.\n"
            "- Provide a single total calories estimate.\n"
            "- Provide macros as protein/carb/fat.\n"
            "- Follow goal constraints exactly.\n"
            "- If goal is high_protein, prioritize lean protein and recovery-friendly carbs."
        ),
        f"[PROMPT_ENGINEERING]\n{instructions}",
    ]

    if context:
        sections.append(f"[CONTEXT]\n{context}")

    sections.append(f"[USER_REQUEST]\n{user_input}")
    return "\n\n".join(sections)


def build_inventory_json_prompt(
    available_ingredients: list[str],
    context: str | None = None,
) -> str:
    """
    Prompt engineering template for inventory mode with strict JSON output.
    """
    schema = (
        '{\n'
        '  "assistant_message": "string (evdeki malzemelerden ne cikacagini acikla)",\n'
        '  "available_ingredients": ["string"],\n'
        '  "possible_dishes": [\n'
        '    {\n'
        '      "dish": "string",\n'
        '      "why_it_fits": "string",\n'
        '      "missing_ingredients": ["string"],\n'
        '      "quick_steps": ["string"]\n'
        '    }\n'
        '  ],\n'
        '  "use_first": ["string (bozulmaya yakin veya ana malzeme onceligi)"],\n'
        '  "shopping_minimum": ["string (minimum satin alinacak eksikler)"]\n'
        '}'
    )

    instructions = (
        "You are an inventory-based cooking assistant. "
        "Use available ingredients first and minimize extra items needed. "
        "Explain why each dish fits the available ingredients and give quick steps. "
        "Return only valid JSON, no markdown, no extra text."
    )

    ing_list = ", ".join(available_ingredients)
    sections = [
        f"[SYSTEM]\n{BASE_SYSTEM_PROMPT}",
        f"[MODE]\n{AIMode.INVENTORY.value}\n{MODE_INSTRUCTIONS[AIMode.INVENTORY]}",
        f"[AVAILABLE_INGREDIENTS]\n{ing_list}",
        f"[OUTPUT_FORMAT]\nReturn strictly this JSON schema:\n{schema}",
        (
            "[RULES]\n"
            "- Prefer dishes with minimum missing ingredients.\n"
            "- Keep dish names practical.\n"
            "- Include only actually missing ingredients."
        ),
        f"[PROMPT_ENGINEERING]\n{instructions}",
    ]

    if context:
        sections.append(f"[CONTEXT]\n{context}")

    return "\n\n".join(sections)


def build_weekly_plan_json_prompt(
    user_request: str,
    context: str | None = None,
) -> str:
    """
    Prompt engineering template for weekly meal planner with strict JSON output.
    """
    schema = (
        '{\n'
        '  "weekly_plan": [\n'
        '    {\n'
        '      "day": "monday|...|sunday",\n'
        '      "breakfast": "string",\n'
        '      "lunch": "string",\n'
        '      "dinner": "string"\n'
        '    }\n'
        '  ],\n'
        '  "shopping_list": [\n'
        '    {\n'
        '      "ingredient": "string",\n'
        '      "estimated_weekly_units": "number or string"\n'
        '    }\n'
        '  ],\n'
        '  "optimization_note": "string"\n'
        '}'
    )

    instructions = (
        "You are a weekly meal planner assistant. "
        "Generate a 7-day plan with breakfast/lunch/dinner, "
        "optimize repeated ingredients to reduce waste and cost, "
        "and return only valid JSON."
    )

    sections = [
        f"[SYSTEM]\n{BASE_SYSTEM_PROMPT}",
        "[MODE]\nweekly_planner",
        f"[OUTPUT_FORMAT]\nReturn strictly this JSON schema:\n{schema}",
        (
            "[RULES]\n"
            "- Exactly 7 days.\n"
            "- Each day must include breakfast, lunch, dinner.\n"
            "- Shopping list must represent full week totals.\n"
            "- Reuse ingredients across days when reasonable."
        ),
        f"[PROMPT_ENGINEERING]\n{instructions}",
        f"[USER_REQUEST]\n{user_request}",
    ]

    if context:
        sections.append(f"[CONTEXT]\n{context}")

    return "\n\n".join(sections)

