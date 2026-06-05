export type AIResponse = {
  mode: string;
  response: Record<string, unknown>;
  provider?: string;
};

export type MarketCartItem = {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
  brand?: string | null;
  unit?: string | null;
};

type JsonObject = Record<string, unknown>;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** KÄ±sa selam / nezaket; tarif veya sepet baÄŸlamÄ± taÅŸÄ±maz. */
export function isLikelyNonRecipeMessage(text: string): boolean {
  const t = text.trim().toLowerCase().replace(/[!?.â€¦]+$/u, "").replace(/\s+/g, " ");
  if (!t || t.length > 80) return false;
  const phrases = new Set([
    "merhaba",
    "mrb",
    "selam",
    "slm",
    "hey",
    "hello",
    "sa",
    "as",
    "gÃ¼naydÄ±n",
    "gunaydin",
    "iyi gÃ¼nler",
    "iyi akÅŸamlar",
    "iyi aksamlar",
    "teÅŸekkÃ¼rler",
    "tesekkurler",
    "teÅŸekkÃ¼r",
    "tesekkur",
    "saÄŸol",
    "sagol",
    "eyvallah",
    "eyv",
    "tamam",
    "nasÄ±lsÄ±n",
    "nasilsin",
    "naber",
    "ne haber",
    "napÄ±yorsun",
    "napim",
    "gÃ¶rÃ¼ÅŸÃ¼rÃ¼z",
    "gorusuruz",
    "hoÅŸÃ§a kal",
    "hosca kal",
    "bb",
    "bye",
  ]);
  return phrases.has(t);
}

export function isCartRequest(text: string): boolean {
  const normalized = text.toLowerCase();
  const cartKeywords = [
    "sepet",
    "sepete ekle",
    "sepet oluÅŸtur",
    "sepet olustur",
    "sepet yap",
    "alÄ±ÅŸveriÅŸ listesi",
    "alisveris listesi",
    "market listesi",
    "Ã¼rÃ¼nlerini ver",
    "urunlerini ver",
    "Ã¼rÃ¼nleri ver",
    "urunleri ver",
    "malzeme ver",
    "malzemeleri ver",
    "liste Ã§Ä±kar",
    "liste cikar",
    "satÄ±n al",
    "satin al",
  ];
  return cartKeywords.some((keyword) => normalized.includes(keyword));
}

export function extractMarketCartItems(response: Record<string, unknown>): MarketCartItem[] {
  const cartObj = response.market_cart;
  if (!isJsonObject(cartObj) || !Array.isArray(cartObj.items)) return [];
  return cartObj.items
    .filter((item): item is Record<string, unknown> => isJsonObject(item))
    .map((item) => ({
      product_id: String(item.product_id ?? ""),
      name: String(item.name ?? "Urun"),
      price: Number(item.price ?? 0),
      quantity: Number(item.quantity ?? 1),
      subtotal: Number(item.subtotal ?? 0),
      brand: typeof item.brand === "string" ? item.brand : null,
      unit: typeof item.unit === "string" ? item.unit : null,
    }))
    .filter((item) => item.product_id.length > 0);
}

function toReadableGoal(goal: string): string {
  switch (goal) {
    case "low_calorie":
      return "dÃ¼ÅŸÃ¼k kalorili";
    case "high_protein":
      return "yÃ¼ksek proteinli";
    case "vegetarian":
      return "vejetaryen";
    default:
      return goal;
  }
}

function toTextList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") return item.trim();
      if (!isJsonObject(item)) return "";
      const name =
        (typeof item.item === "string" && item.item.trim()) ||
        (typeof item.ingredient === "string" && item.ingredient.trim()) ||
        (typeof item.dish === "string" && item.dish.trim()) ||
        (typeof item.name === "string" && item.name.trim()) ||
        "";
      const qty =
        (typeof item.quantity === "string" && item.quantity.trim()) ||
        (typeof item.amount === "string" && item.amount.trim()) ||
        "";
      return [name, qty].filter(Boolean).join(" - ");
    })
    .filter(Boolean);
}

export function buildAiNarrative(output: AIResponse): string {
  if (!isJsonObject(output.response)) return "Ã–nerinizi hazÄ±rladÄ±m. AÅŸaÄŸÄ±daki sepetten Ã¼rÃ¼nleri yÃ¶netebilirsiniz.";

  const response = output.response;
  const marketItems = extractMarketCartItems(response);
  const parts: string[] = [];
  const directAssistantMessage =
    typeof response.assistant_message === "string" ? response.assistant_message.trim() : "";

  if (output.mode === "budget") {
    const dish = typeof response.dish === "string" ? response.dish : "onerilen menu";
    const totalCost = typeof response.total_cost === "string" ? response.total_cost : "";
    const summary = typeof response.summary === "string" ? response.summary.trim() : "";
    const budgetTip = typeof response.budget_tip === "string" ? response.budget_tip : "";
    const ingredients = toTextList(response.ingredients);
    const steps = toTextList(response.steps);
    const costBreakdown = toTextList(response.cost_breakdown);
    const strategy = toTextList(response.shopping_strategy);
    const sectionLines = [`Ekonomik plan: ${dish}`];
    if (directAssistantMessage) sectionLines.push("", directAssistantMessage);
    if (summary) sectionLines.push("", summary);
    if (totalCost) sectionLines.push("", `Tahmini toplam: ${totalCost}`);
    if (ingredients.length > 0) sectionLines.push("", "Malzemeler:", ...ingredients.map((item) => `- ${item}`));
    if (costBreakdown.length > 0) sectionLines.push("", "Maliyet kirilimi:", ...costBreakdown.map((item) => `- ${item}`));
    if (steps.length > 0) sectionLines.push("", "Nasil hazirlanir:", ...steps.map((item, index) => `${index + 1}. ${item}`));
    if (budgetTip) sectionLines.push("", `Butce notu: ${budgetTip}`);
    if (strategy.length > 0) sectionLines.push("", "Alisveris stratejisi:", ...strategy.map((item) => `- ${item}`));
    parts.push(sectionLines.join("\n"));
  }

  if (output.mode === "diet") {
    const dish = typeof response.dish === "string" ? response.dish : "diyet menusu";
    const goal = typeof response.goal === "string" ? toReadableGoal(response.goal) : "hedefinize uygun";
    const calories = typeof response.calories === "string" ? response.calories : "";
    const summary = typeof response.summary === "string" ? response.summary.trim() : "";
    const ingredients = toTextList(response.ingredients);
    const steps = toTextList(response.steps);
    const nutritionNotes = toTextList(response.nutrition_notes);
    const timingTips = toTextList(response.timing_tips);
    const macros = isJsonObject(response.macros) ? response.macros : {};
    const macroText = [
      typeof macros.protein === "string" ? `Protein: ${macros.protein}` : "",
      typeof macros.carb === "string" ? `Karbonhidrat: ${macros.carb}` : "",
      typeof macros.fat === "string" ? `Yag: ${macros.fat}` : "",
    ].filter(Boolean);
    const sectionLines = [`${goal} plan: ${dish}`];
    if (directAssistantMessage) sectionLines.push("", directAssistantMessage);
    if (summary) sectionLines.push("", summary);
    if (calories || macroText.length > 0) sectionLines.push("", [calories ? `Kalori: ${calories}` : "", ...macroText].filter(Boolean).join(" • "));
    if (ingredients.length > 0) sectionLines.push("", "Malzemeler:", ...ingredients.map((item) => `- ${item}`));
    if (steps.length > 0) sectionLines.push("", "Hazirlik:", ...steps.map((item, index) => `${index + 1}. ${item}`));
    if (nutritionNotes.length > 0) sectionLines.push("", "Beslenme notlari:", ...nutritionNotes.map((item) => `- ${item}`));
    if (timingTips.length > 0) sectionLines.push("", "Zamanlama:", ...timingTips.map((item) => `- ${item}`));
    parts.push(sectionLines.join("\n"));
  }

  if (output.mode === "inventory") {
    const dishes = Array.isArray(response.possible_dishes)
      ? response.possible_dishes.filter((item): item is Record<string, unknown> => isJsonObject(item))
      : [];
    if (dishes.length > 0) {
      const sectionLines = ["Evdeki malzemelere gore en uygun fikirler:"];
      if (directAssistantMessage) sectionLines.push("", directAssistantMessage);
      dishes.slice(0, 3).forEach((item, index) => {
        const dish = typeof item.dish === "string" ? item.dish : "Tarif";
        const why = typeof item.why_it_fits === "string" ? item.why_it_fits : "";
        const missing = toTextList(item.missing_ingredients);
        const quickSteps = toTextList(item.quick_steps);
        sectionLines.push("", `${index + 1}. ${dish}`);
        if (why) sectionLines.push(why);
        sectionLines.push(missing.length > 0 ? `Eksikler: ${missing.join(", ")}` : "Eksik malzeme yok ya da cok az.");
        if (quickSteps.length > 0) sectionLines.push(...quickSteps.slice(0, 3).map((step) => `- ${step}`));
      });
      const shoppingMinimum = toTextList(response.shopping_minimum);
      if (shoppingMinimum.length > 0) sectionLines.push("", `Minimum alisveris: ${shoppingMinimum.join(", ")}`);
      parts.push(sectionLines.join("\n"));
    }
  }

  if (output.mode === "normal" && response.intent === "recipe_request" && isJsonObject(response.recipe)) {
    const recipe = response.recipe;
    const recipeName = typeof recipe.name === "string" && recipe.name.trim() ? recipe.name.trim() : "Tarif";
    const category = typeof recipe.category === "string" && recipe.category.trim() ? recipe.category.trim() : "";
    const duration = typeof recipe.duration === "string" && recipe.duration.trim() ? recipe.duration.trim() : "";
    const servings = typeof recipe.servings === "string" && recipe.servings.trim() ? recipe.servings.trim() : "";
    const recipeIngredients = Array.isArray(recipe.ingredients)
      ? recipe.ingredients.filter((item): item is Record<string, unknown> => isJsonObject(item))
      : [];
    const recipeSteps = Array.isArray(recipe.steps)
      ? recipe.steps.filter((step): step is string => typeof step === "string" && step.trim().length > 0)
      : [];
    const matchedProducts = Array.isArray(response.matched_products)
      ? response.matched_products.filter((item): item is Record<string, unknown> => isJsonObject(item))
      : [];
    const missingProducts = Array.isArray(response.missing_products)
      ? response.missing_products.filter((item): item is Record<string, unknown> => isJsonObject(item))
      : [];
    const message = typeof response.message === "string" ? response.message.trim() : "";

    const sectionLines: string[] = [];
    sectionLines.push(`ğŸ² ${recipeName}`);
    if (category || duration || servings) {
      const meta = [category, duration, servings ? `Porsiyon: ${servings}` : ""].filter(Boolean);
      sectionLines.push(meta.join(" â€¢ "));
    }
    if (message) {
      sectionLines.push("");
      sectionLines.push(message);
    }
    sectionLines.push("");
    sectionLines.push("Malzemeler:");
    if (recipeIngredients.length > 0) {
      sectionLines.push(
        ...recipeIngredients.map((ingredient) => {
          const raw = typeof ingredient.raw === "string" ? ingredient.raw.trim() : "";
          const name = typeof ingredient.name === "string" ? ingredient.name.trim() : "";
          const amount = typeof ingredient.amount === "string" ? ingredient.amount.trim() : "";
          const unit = typeof ingredient.unit === "string" ? ingredient.unit.trim() : "";
          const composed = [amount, unit, name].filter(Boolean).join(" ");
          return `- ${raw || composed || "Malzeme"}`;
        }),
      );
    } else {
      sectionLines.push("- Bu tarif icin malzeme listesi bulunamadi.");
    }
    sectionLines.push("");
    sectionLines.push("PiÅŸirme AdÄ±mlarÄ±:");
    if (recipeSteps.length > 0) {
      sectionLines.push(...recipeSteps.slice(0, 12).map((step, index) => `${index + 1}. ${step}`));
      if (recipeSteps.length > 12) {
        sectionLines.push(`... ${recipeSteps.length - 12} adim daha var.`);
      }
    } else {
      sectionLines.push("1. Bu tarif icin yapilis adimlari bulunamadi.");
    }

    if (matchedProducts.length > 0) {
      sectionLines.push("");
      sectionLines.push("Sepete Eklenebilen Urunler:");
      sectionLines.push(
        ...matchedProducts.map((product) => {
          const ingredient = typeof product.ingredient === "string" ? product.ingredient : "malzeme";
          const productName = typeof product.product_name === "string" ? product.product_name : "urun";
          const price = Number(product.price ?? 0);
          return `- ${ingredient}: ${productName}${price > 0 ? ` (${price.toFixed(2)} TL)` : ""}`;
        }),
      );
    }

    if (missingProducts.length > 0) {
      sectionLines.push("");
      sectionLines.push("Market Veritabaninda Bulunamayanlar:");
      sectionLines.push(
        ...missingProducts.map((item) => {
          const ingredient = typeof item.ingredient === "string" ? item.ingredient : "malzeme";
          return `- ${ingredient}`;
        }),
      );
    }

    parts.push(sectionLines.join("\n"));
  }

  if (output.mode === "normal" && directAssistantMessage && response.intent !== "recipe_request") {
    parts.push(directAssistantMessage);
  }

  if (output.mode === "normal" && !directAssistantMessage && response.intent !== "recipe_request") {
    const displayTitle =
      (typeof response.title === "string" && response.title.trim()) ||
      (typeof response.recipe === "string" && response.recipe.trim()) ||
      (typeof response.dish === "string" && response.dish.trim()) ||
      "Tarif Ã–nerisi";
    const summary =
      (typeof response.summary === "string" && response.summary.trim()) ||
      "Sana mutfakta kolay takip edebileceÄŸin detaylÄ± bir tarif hazÄ±rladÄ±m.";
    const description =
      typeof response.description === "string" ? response.description.trim() : "";
    const servings = typeof response.servings === "number" ? response.servings : null;
    const prepTime = typeof response.prep_time === "string" ? response.prep_time.trim() : "";
    const cookTime =
      (typeof response.cook_time === "string" && response.cook_time.trim()) ||
      (typeof response.cooking_time === "string" && response.cooking_time.trim()) ||
      "";
    const difficulty = typeof response.difficulty === "string" ? response.difficulty.trim() : "";
    const calories = typeof response.calories === "string" ? response.calories.trim() : "";
    const protein = typeof response.protein === "string" ? response.protein.trim() : "";
    const carbs = typeof response.carbs === "string" ? response.carbs.trim() : "";
    const fats = typeof response.fats === "string" ? response.fats.trim() : "";

    const rawIngredients = Array.isArray(response.ingredients) ? response.ingredients : [];
    const ingredients = rawIngredients
      .map((ingredient) => {
        if (typeof ingredient === "string") return ingredient.trim();
        if (isJsonObject(ingredient) && typeof ingredient.item === "string") {
          const qty = typeof ingredient.quantity === "string" ? ingredient.quantity.trim() : "";
          return qty ? `${ingredient.item.trim()} - ${qty}` : ingredient.item.trim();
        }
        return "";
      })
      .filter(Boolean);

    const rawPreparation = Array.isArray(response.preparation) ? response.preparation : [];
    const preparation = rawPreparation.filter((step): step is string => typeof step === "string" && step.trim().length > 0);
    const rawSteps = Array.isArray(response.steps)
      ? response.steps
      : Array.isArray(response.yapilis_asamalari)
        ? response.yapilis_asamalari
        : [];
    const cookingSteps = rawSteps.filter((step): step is string => typeof step === "string" && step.trim().length > 0);
    const isNonRecipeStyle =
      ingredients.length === 0 && preparation.length === 0 && cookingSteps.length <= 1;
    const servingSuggestion = typeof response.serving_suggestion === "string" ? response.serving_suggestion.trim() : "";
    const optionalSides = Array.isArray(response.optional_sides)
      ? response.optional_sides.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [];
    const optionalDrinks = Array.isArray(response.optional_drinks)
      ? response.optional_drinks.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [];
    const tips = Array.isArray(response.tips)
      ? response.tips.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [];

    const chefNotes = Array.isArray(response.chef_notes)
      ? response.chef_notes.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [];
    const shoppingRecs = Array.isArray(response.shopping_recommendations)
      ? response.shopping_recommendations.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [];

    const sectionLines: string[] = [];
    sectionLines.push(`ğŸ² ${displayTitle}`);
    sectionLines.push("");
    sectionLines.push(summary);
    if (description && description !== summary) {
      sectionLines.push("");
      sectionLines.push(description);
    }
    sectionLines.push("");
    const metaBits: string[] = [];
    if (servings != null) metaBits.push(`Porsiyon: ${servings}`);
    if (prepTime) metaBits.push(`HazÄ±rlÄ±k: ${prepTime}`);
    if (cookTime) metaBits.push(`PiÅŸirme: ${cookTime}`);
    if (difficulty) metaBits.push(`Zorluk: ${difficulty}`);
    if (metaBits.length > 0) {
      sectionLines.push(metaBits.join(" â€¢ "));
      sectionLines.push("");
    }
    const nutritionBits: string[] = [];
    const nutLabel = (v: string) => {
      const x = v.trim().toLowerCase();
      if (!x || x === "-" || x.includes("uygulan")) return null;
      return v;
    };
    if (nutLabel(calories)) nutritionBits.push(`Kalori: ${calories}`);
    if (nutLabel(protein)) nutritionBits.push(`Protein: ${protein}`);
    if (nutLabel(carbs)) nutritionBits.push(`Karbonhidrat: ${carbs}`);
    if (nutLabel(fats)) nutritionBits.push(`YaÄŸ: ${fats}`);
    if (nutritionBits.length > 0) {
      sectionLines.push(nutritionBits.join(" â€¢ "));
      sectionLines.push("");
    }

    sectionLines.push("Malzemeler:");
    if (ingredients.length > 0) {
      sectionLines.push(...ingredients.map((item) => `- ${item}`));
    } else if (isNonRecipeStyle) {
      sectionLines.push("- HenÃ¼z tarif seÃ§ilmedi; bir yemek adÄ± veya elindeki malzemeleri yazabilirsin.");
    } else {
      sectionLines.push("- Malzeme listesi oluÅŸturulamadÄ±.");
    }
    sectionLines.push("");

    sectionLines.push("HazÄ±rlÄ±k:");
    if (preparation.length > 0) {
      sectionLines.push(...preparation.map((item, idx) => `${idx + 1}. ${item}`));
    } else if (isNonRecipeStyle) {
      sectionLines.push("1. Tarif hazÄ±rlÄ±ÄŸÄ± burada listelenmedi; yemek isteÄŸini netleÅŸtirdiÄŸinde adÄ±m adÄ±m yazarÄ±m.");
    } else {
      sectionLines.push("1. Malzemeleri yÄ±kayÄ±p Ã¶lÃ§Ã¼lerine gÃ¶re hazÄ±rlayÄ±n.");
      sectionLines.push("2. DoÄŸrama ve Ã¶n hazÄ±rlÄ±k iÅŸlemlerini tamamlayÄ±n.");
    }
    sectionLines.push("");

    sectionLines.push("PiÅŸirme AdÄ±mlarÄ±:");
    if (cookingSteps.length > 0) {
      sectionLines.push(...cookingSteps.map((item, idx) => `${idx + 1}. ${item}`));
    } else if (isNonRecipeStyle) {
      sectionLines.push("1. BugÃ¼n ne piÅŸirmek istediÄŸini yaz; sana Ã¶zel adÄ±mlar Ã§Ä±karayÄ±m.");
    } else {
      sectionLines.push("1. Tarife uygun ÅŸekilde orta ateÅŸte piÅŸirmeye baÅŸlayÄ±n.");
      sectionLines.push("2. KÄ±vam ve lezzeti kontrol ederek aÅŸamalarÄ± tamamlayÄ±n.");
    }
    sectionLines.push("");

    sectionLines.push("Servis Ã–nerisi:");
    if (servingSuggestion) {
      sectionLines.push(servingSuggestion);
    } else {
      sectionLines.push("SÄ±cak servis edin, yanÄ±nda mevsim salatasÄ± ile sunabilirsiniz.");
    }
    if (optionalSides.length > 0) {
      sectionLines.push(`Opsiyonel Yan Lezzetler: ${optionalSides.join(", ")}`);
    }
    if (optionalDrinks.length > 0) {
      sectionLines.push(`Ä°Ã§ecek Ã–nerileri: ${optionalDrinks.join(", ")}`);
    }
    if (tips.length > 0) {
      sectionLines.push("");
      sectionLines.push("PÃ¼f NoktalarÄ±:");
      sectionLines.push(...tips.map((tip) => `- ${tip}`));
    }
    if (chefNotes.length > 0) {
      sectionLines.push("");
      sectionLines.push("Åef NotlarÄ±:");
      sectionLines.push(...chefNotes.map((note) => `- ${note}`));
    }
    if (shoppingRecs.length > 0) {
      sectionLines.push("");
      sectionLines.push("Market Ä°puÃ§larÄ±:");
      sectionLines.push(...shoppingRecs.map((line) => `- ${line}`));
    }
    parts.push(sectionLines.join("\n"));
  }

  if (output.mode === "weekly") {
    const weeklyPlan = Array.isArray(response.weekly_plan)
      ? response.weekly_plan.filter((item): item is Record<string, unknown> => isJsonObject(item))
      : [];
    const optimizationNote = typeof response.optimization_note === "string" ? response.optimization_note : "";
    if (weeklyPlan.length > 0) {
      parts.push(`HaftalÄ±k planÄ±nÄ±z oluÅŸturuldu; ${weeklyPlan.length} gÃ¼n iÃ§in Ã¶ÄŸÃ¼n daÄŸÄ±lÄ±mÄ± hazÄ±r.`);
    }
    if (optimizationNote) parts.push(`Plan notu: ${optimizationNote}`);
  }

  if (marketItems.length > 0) {
    const total = marketItems.reduce((sum, item) => sum + item.subtotal, 0).toFixed(2);
    parts.push(`Stoktaki Ã¼rÃ¼nlere gÃ¶re ${marketItems.length} Ã¼rÃ¼nlÃ¼k bir sepet Ã¶nerdim. Tahmini sepet tutarÄ± ${total} TL.`);
  }

  const merged = parts.filter(Boolean).join(" ");
  return merged || "Ã–nerinizi hazÄ±rladÄ±m. AÅŸaÄŸÄ±daki sepetten Ã¼rÃ¼nleri yÃ¶netebilirsiniz.";
}
