"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isAxiosError } from "axios";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  Bot,
  ChefHat,
  ClipboardList,
  Heart,
  LogOut,
  Menu,
  Mic,
  Paperclip,
  RotateCcw,
  Search,
  Send,
  ShoppingCart,
  Sparkles,
  Trash2,
  UserCircle2,
  X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

type Product = {
  id: string;
  name: string;
  price: number;
  stock: number;
  category_id: string;
  unit?: string | null;
  image_url?: string | null;
  is_promoted?: boolean;
  promotion_type?: string | null;
  promotion_label?: string | null;
  discounted_price?: number | null;
  promotion_buy_quantity?: number | null;
  promotion_pay_quantity?: number | null;
};

type Category = {
  id: string;
  name: string;
  slug: string;
};

type CartItem = {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
};

type CartResponse = {
  id: string;
  user_id: string;
  items: CartItem[];
  total_price: number;
};

type OrderItem = {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
};

type Order = {
  id: string;
  status: string;
  items: OrderItem[];
  total_price: number;
  delivery_address: string;
  payment_method: string;
  created_at: string;
};

type OrdersResponse = {
  items?: Order[];
  total: number;
};

type FavoritesResponse = {
  items?: { id: string }[];
  total_count: number;
};

type OverviewSection = "cart" | "orders" | "favorites" | "profile";

type ProductListResponse = {
  items: Product[];
};

type CategoryListResponse = {
  items: Category[];
};

type NotificationItem = {
  id: string;
  title: string;
  body: string;
  type: string;
  product_id?: string | null;
  product_name?: string | null;
  promotion_label?: string | null;
  is_read: boolean;
  created_at: string;
};

type NotificationListResponse = {
  items: NotificationItem[];
  unread_count: number;
  total: number;
};

type AIResponse = {
  mode: string;
  response: Record<string, unknown>;
  provider?: string;
};

type MarketCartItem = {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
  brand?: string | null;
  unit?: string | null;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

const DEFAULT_ADDRESS = "Örnek Mah. 100 Sok. No:10 Kadıköy/İstanbul";
const MEAL_CATEGORIES = [
  "Akşam Yemeği",
  "Kahvaltı",
  "Sağlıklı Atıştırmalıklar",
  "Haftalık Plan",
] as const;
const AI_MODE_OPTIONS = [
  { value: "normal", label: "Normal" },
  { value: "budget", label: "Bütçe" },
  { value: "diet", label: "Diyet" },
  { value: "inventory", label: "Stok" },
  { value: "weekly", label: "Haftalık" },
] as const;
const CAMPAIGN_CATEGORY_ID = "campaigns";
const CATEGORY_IMAGE_BY_SLUG: Record<string, string> = {
  atistirmalik: "/categories/atistirmalik.png",
  bebek: "/categories/bebekurunleri.png",
  "et-tavuk-balik": "/categories/etbaliktavuk.png",
  "evcil-hayvan": "/categories/evcilhayvan.png",
  "firin-pastane": "/categories/firin.png",
  icecek: "/categories/icecek.png",
  "kisisel-bakim-kozmetik-saglik": "/categories/kisiselbakim.png",
  "kisisel-bakim": "/categories/kisiselbakim.png",
  "sut-kahvaltilik": "/categories/kahvaltilik.png",
  "sut-urunleri": "/categories/kahvaltilik.png",
  "meyve-sebze": "/categories/meyvesebze.png",
  "kagit-islak-mendil": "/categories/pecete.png",
  "temel-gida": "/categories/temelgida.png",
  temizlik: "/categories/temizlik.png",
  "deterjan-temizlik": "/categories/temizlik.png",
  "donuk": "/categories/donuk.png",
  "meze-hazir-yemek-donuk": "/categories/donuk.png",
};
const marbleTextureStyle = {
  backgroundColor: "#F4FFF8",
  backgroundImage:
    "radial-gradient(circle at 8% 4%, rgba(34,211,238,0.22) 0%, rgba(22,196,127,0.16) 22%, rgba(244,255,248,0.9) 44%, rgba(244,255,248,1) 100%), radial-gradient(circle at 92% 8%, rgba(245,158,11,0.16) 0%, rgba(34,211,238,0.1) 34%, rgba(244,255,248,0.95) 58%, rgba(244,255,248,1) 100%)",
};

function getCategoryEmoji(slug: string): string {
  const normalized = slug.toLowerCase();
  if (normalized.includes("sebze") || normalized.includes("meyve")) return "🥦";
  if (normalized.includes("sut") || normalized.includes("kahvalti")) return "🥛";
  if (normalized.includes("icecek")) return "🥤";
  if (normalized.includes("atistirmalik")) return "??";
  if (normalized.includes("temizlik")) return "🧼";
  return "🛒";
}

function getCategoryImagePath(slug: string): string | null {
  return CATEGORY_IMAGE_BY_SLUG[slug.toLowerCase()] ?? null;
}

function toHighResMigrosImage(imageUrl: string): string {
  if (!imageUrl) return imageUrl;
  // Migros thumbnail URL'leri genelde ...-105x105.jpg formatında geliyor.
  // Boyut suffix'ini kaldırınca daha yüksek çözünürlükte ana görsel dönebiliyor.
  return imageUrl.replace(/-\d+x\d+(?=\.(jpg|jpeg|png|webp)$)/i, "");
}

function getProductPhoto(name: string, imageUrl?: string | null): string {
  if (imageUrl) return toHighResMigrosImage(imageUrl);
  const n = name.toLowerCase();
  if (n.includes("süt")) return "https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=900&q=80";
  if (n.includes("fındık")) return "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=900&q=80";
  if (n.includes("temizleyici")) return "https://images.unsplash.com/photo-1583947215259-38e31be8751f?auto=format&fit=crop&w=900&q=80";
  if (n.includes("zeytin")) return "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=900&q=80";
  if (n.includes("domates")) return "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=900&q=80";
  return "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=80";
}

function getEffectiveProductPrice(product: Product): number {
  if (product.is_promoted && product.promotion_type === "discount_price" && product.discounted_price != null) {
    return product.discounted_price;
  }
  return product.price;
}

function getPromotionLabel(product: Product): string {
  if (!product.is_promoted) return "";
  if (product.promotion_label) return product.promotion_label;
  if (product.promotion_type === "buy_x_pay_y" && product.promotion_buy_quantity && product.promotion_pay_quantity) {
    return `${product.promotion_buy_quantity} al ${product.promotion_pay_quantity} ode`;
  }
  if (product.promotion_type === "discount_price") return "Indirimli urun";
  return "Kampanya";
}

type JsonObject = Record<string, unknown>;

type IngredientSuggestion = {
  item: string;
  quantity: string;
};

type NormalModePlanView = {
  summary: string;
  recipe: string;
  servings: number;
  prepMinutes?: number;
  cookMinutes?: number;
  ingredients: IngredientSuggestion[];
  steps: string[];
  allergenWarnings: string[];
  tips: string[];
};

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isIngredientSuggestion(value: unknown): value is IngredientSuggestion {
  return (
    isJsonObject(value) &&
    typeof value.item === "string" &&
    typeof value.quantity === "string"
  );
}

async function withRetry<T>(fn: () => Promise<T>, retries = 2, delayMs = 800): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }
  throw lastError;
}

function toReadableGoal(goal: string): string {
  switch (goal) {
    case "low_calorie":
      return "düşük kalorili";
    case "high_protein":
      return "yüksek proteinli";
    case "vegetarian":
      return "vejetaryen";
    default:
      return goal;
  }
}

function isCartRequest(text: string): boolean {
  const normalized = text.toLowerCase();
  const cartKeywords = [
    "sepet",
    "sepete ekle",
    "sepet oluştur",
    "sepet olustur",
    "sepet yap",
    "alışveriş listesi",
    "alisveris listesi",
    "market listesi",
    "ürünlerini ver",
    "urunlerini ver",
    "ürünleri ver",
    "urunleri ver",
    "malzeme ver",
    "malzemeleri ver",
    "liste çıkar",
    "liste cikar",
    "satın al",
    "satin al",
  ];
  return cartKeywords.some((keyword) => normalized.includes(keyword));
}

function extractMarketCartItems(response: Record<string, unknown>): MarketCartItem[] {
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

function buildAiNarrative(output: AIResponse): string {
  if (!isJsonObject(output.response)) return "Önerinizi hazırladım. Aşağıdaki sepetten ürünleri yönetebilirsiniz.";

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
    if (calories || macroText.length > 0) sectionLines.push("", [calories ? `Kalori: ${calories}` : "", ...macroText].filter(Boolean).join("  "));
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

  if (output.mode === "normal" && directAssistantMessage) {
    parts.push(directAssistantMessage);
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
    sectionLines.push(`?? ${recipeName}`);
    if (category || duration || servings) {
      const meta = [category, duration, servings ? `Porsiyon: ${servings}` : ""].filter(Boolean);
      sectionLines.push(meta.join(" • "));
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
      sectionLines.push("- Bu tarif için malzeme listesi bulunamadı.");
    }
    sectionLines.push("");
    sectionLines.push("Pişirme Adımları:");
    if (recipeSteps.length > 0) {
      sectionLines.push(...recipeSteps.slice(0, 12).map((step, index) => `${index + 1}. ${step}`));
      if (recipeSteps.length > 12) {
        sectionLines.push(`... ${recipeSteps.length - 12} adım daha var.`);
      }
    } else {
      sectionLines.push("1. Bu tarif için yapılış adımları bulunamadı.");
    }

    if (matchedProducts.length > 0) {
      sectionLines.push("");
      sectionLines.push("Sepete Eklenebilen Ürünler:");
      sectionLines.push(
        ...matchedProducts.map((product) => {
          const ingredient = typeof product.ingredient === "string" ? product.ingredient : "malzeme";
          const productName = typeof product.product_name === "string" ? product.product_name : "ürün";
          const price = Number(product.price ?? 0);
          return `- ${ingredient}: ${productName}${price > 0 ? ` (${price.toFixed(2)} TL)` : ""}`;
        }),
      );
    }

    if (missingProducts.length > 0) {
      sectionLines.push("");
      sectionLines.push("Market Veritabanında Bulunamayanlar:");
      sectionLines.push(
        ...missingProducts.map((item) => {
          const ingredient = typeof item.ingredient === "string" ? item.ingredient : "malzeme";
          return `- ${ingredient}`;
        }),
      );
    }

    parts.push(sectionLines.join("\n"));
  }

  if (output.mode === "normal" && !directAssistantMessage && response.intent !== "recipe_request") {
    const displayTitle =
      (typeof response.title === "string" && response.title.trim()) ||
      (typeof response.recipe === "string" && response.recipe.trim()) ||
      (typeof response.dish === "string" && response.dish.trim()) ||
      "Tarif Önerisi";
    const summary =
      (typeof response.summary === "string" && response.summary.trim()) ||
      "Sana mutfakta kolay takip edebileceğin detaylı bir tarif hazırladım.";
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
    sectionLines.push(` ${displayTitle}`);
    sectionLines.push("");
    sectionLines.push(summary);
    if (description && description !== summary) {
      sectionLines.push("");
      sectionLines.push(description);
    }
    sectionLines.push("");
    const metaBits: string[] = [];
    if (servings != null) metaBits.push(`Porsiyon: ${servings}`);
    if (prepTime) metaBits.push(`Hazırlık: ${prepTime}`);
    if (cookTime) metaBits.push(`Pişirme: ${cookTime}`);
    if (difficulty) metaBits.push(`Zorluk: ${difficulty}`);
    if (metaBits.length > 0) {
      sectionLines.push(metaBits.join(" • "));
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
    if (nutLabel(fats)) nutritionBits.push(`Yağ: ${fats}`);
    if (nutritionBits.length > 0) {
      sectionLines.push(nutritionBits.join(" • "));
      sectionLines.push("");
    }

    sectionLines.push("Malzemeler:");
    if (ingredients.length > 0) {
      sectionLines.push(...ingredients.map((item) => `- ${item}`));
    } else if (isNonRecipeStyle) {
      sectionLines.push("- Henüz tarif seçilmedi; bir yemek adı veya elindeki malzemeleri yazabilirsin.");
    } else {
      sectionLines.push("- Malzeme listesi oluşturulamadı.");
    }
    sectionLines.push("");

    sectionLines.push("Hazırlık:");
    if (preparation.length > 0) {
      sectionLines.push(...preparation.map((item, idx) => `${idx + 1}. ${item}`));
    } else if (isNonRecipeStyle) {
      sectionLines.push("1. Tarif hazırlığı burada listelenmedi; yemek isteğini netleştirdiğinde adım adım yazarım.");
    } else {
      sectionLines.push("1. Malzemeleri yıkayıp ölçülerine göre hazırlayın.");
      sectionLines.push("2. Doğrama ve ön hazırlık işlemlerini tamamlayın.");
    }
    sectionLines.push("");

    sectionLines.push("Pişirme Adımları:");
    if (cookingSteps.length > 0) {
      sectionLines.push(...cookingSteps.map((item, idx) => `${idx + 1}. ${item}`));
    } else if (isNonRecipeStyle) {
      sectionLines.push("1. Bugün ne pişirmek istediğini yaz; sana özel adımlar çıkarayım.");
    } else {
      sectionLines.push("1. Tarife uygun şekilde orta ateşte pişirmeye başlayın.");
      sectionLines.push("2. Kıvam ve lezzeti kontrol ederek aşamaları tamamlayın.");
    }
    sectionLines.push("");

    sectionLines.push("Servis Önerisi:");
    if (servingSuggestion) {
      sectionLines.push(servingSuggestion);
    } else {
      sectionLines.push("Sıcak servis edin, yanında mevsim salatası ile sunabilirsiniz.");
    }
    if (optionalSides.length > 0) {
      sectionLines.push(`Opsiyonel Yan Lezzetler: ${optionalSides.join(", ")}`);
    }
    if (optionalDrinks.length > 0) {
      sectionLines.push(`İçecek Önerileri: ${optionalDrinks.join(", ")}`);
    }
    if (tips.length > 0) {
      sectionLines.push("");
      sectionLines.push("Püf Noktaları:");
      sectionLines.push(...tips.map((tip) => `- ${tip}`));
    }
    if (chefNotes.length > 0) {
      sectionLines.push("");
      sectionLines.push("ef Notları:");
      sectionLines.push(...chefNotes.map((note) => `- ${note}`));
    }
    if (shoppingRecs.length > 0) {
      sectionLines.push("");
      sectionLines.push("Market İpuçları:");
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
      parts.push(`Haftalık planınız oluşturuldu; ${weeklyPlan.length} gün için öğün dağılımı hazır.`);
    }
    if (optimizationNote) parts.push(`Plan notu: ${optimizationNote}`);
  }

  if (marketItems.length > 0) {
    const total = marketItems.reduce((sum, item) => sum + item.subtotal, 0).toFixed(2);
    parts.push(`Stoktaki ürünlere göre ${marketItems.length} ürünlük bir sepet önerdim. Tahmini sepet tutarı ${total} TL.`);
  }

  const merged = parts.filter(Boolean).join(" ");
  return merged || "Önerinizi hazırladım. Aşağıdaki sepetten ürünleri yönetebilirsiniz.";
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, token, isReady, logout } = useAuth();

  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState("all");
  const [categoryProducts, setCategoryProducts] = useState<Product[]>([]);
  const [categoryProductsLoading, setCategoryProductsLoading] = useState(false);
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [ordersTotal, setOrdersTotal] = useState(0);
  const [favoritesTotal, setFavoritesTotal] = useState(0);
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [activeOverviewSection, setActiveOverviewSection] = useState<OverviewSection>("cart");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [aiInput, setAiInput] = useState("");
  const [aiMode, setAiMode] = useState("normal");
  const [isModeMenuOpen, setIsModeMenuOpen] = useState(false);
  const [mealCategory, setMealCategory] = useState<(typeof MEAL_CATEGORIES)[number]>("Akşam Yemeği");
  const [budgetLimit, setBudgetLimit] = useState("");
  const [nutritionGoal, setNutritionGoal] = useState("Dengeli Beslenme");
  const [allergies, setAllergies] = useState("");
  const [preferredBrands, setPreferredBrands] = useState("");
  const [inventoryInput, setInventoryInput] = useState("");
  const [aiOutput, setAiOutput] = useState<AIResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiFeedback, setAiFeedback] = useState("");
  const [aiChatMessages, setAiChatMessages] = useState<ChatMessage[]>([]);
  const [attachedFileName, setAttachedFileName] = useState("");
  const [busyProductId, setBusyProductId] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isMobileAssistantOpen, setIsMobileAssistantOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const modeMenuRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const quickActions = [
    "Ekonomik akşam yemeği öner",
    "Sporcu menüsü hazırla",
    "Evdeki malzemelerle ne yapabilirim?",
  ].map((label) => {
    if (label.startsWith("Ekonomik")) {
      return { label, mode: "budget", preferences: { meal_category: "Akşam Yemeği" } };
    }
    if (label.startsWith("Sporcu")) {
      return { label, mode: "diet", preferences: { goal: "high_protein", nutrition_goal: "high_protein" } };
    }
    return { label, mode: "inventory", preferences: {} };
  });

  function parseIngredientList(value: string): string[] {
    return value
      .split(/[,;\n]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function normalizeDietGoal(value: string): string {
    const normalized = value.toLocaleLowerCase("tr-TR");
    if (normalized.includes("protein") || normalized.includes("spor")) return "high_protein";
    if (normalized.includes("vejet") || normalized.includes("sebze")) return "vegetarian";
    return "low_calorie";
  }

  async function fetchAllProducts(limit = 100): Promise<Product[]> {
    let skip = 0;
    let total = 0;
    const items: Product[] = [];

    do {
      const response = await api.get<{ items: Product[]; total: number }>("/api/v1/products", {
        params: { limit, skip },
      });
      const pageItems = response.data.items ?? [];
      total = response.data.total ?? pageItems.length;
      items.push(...pageItems);
      skip += limit;
    } while (skip < total);

    return items;
  }

  async function fetchCategoryProducts(categoryId: string, limit = 100): Promise<Product[]> {
    let skip = 0;
    let total = 0;
    const items: Product[] = [];

    do {
      const response = await api.get<{ items: Product[]; total: number }>("/api/v1/products", {
        params: { category_id: categoryId, limit, skip },
      });
      const pageItems = response.data.items ?? [];
      total = response.data.total ?? pageItems.length;
      items.push(...pageItems);
      skip += limit;
    } while (skip < total);

    return items;
  }

  async function fetchAllCategories(limit = 100): Promise<Category[]> {
    let skip = 0;
    let total = 0;
    const items: Category[] = [];

    do {
      const response = await api.get<{ items: Category[]; total: number }>("/api/v1/categories", {
        params: { limit, skip },
      });
      const pageItems = response.data.items ?? [];
      total = response.data.total ?? pageItems.length;
      items.push(...pageItems);
      skip += limit;
    } while (skip < total);

    return items;
  }

  const fetchDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError("");

      const [productsRes, categoriesRes, cartRes, ordersRes, favoritesRes, notificationsRes] = await Promise.allSettled([
        withRetry(() => fetchAllProducts(500), 2, 1000),
        withRetry(() => fetchAllCategories(500), 2, 1000),
        api.get<CartResponse>("/api/v1/cart"),
        api.get<OrdersResponse>("/api/v1/orders"),
        api.get<FavoritesResponse>("/api/v1/favorites"),
        api.get<NotificationListResponse>("/api/v1/notifications"),
      ]);
      const settledResults = [productsRes, categoriesRes, cartRes, ordersRes, favoritesRes, notificationsRes];
      const unauthorizedResult = settledResults.find(
        (result) =>
          result.status === "rejected" &&
          isAxiosError(result.reason) &&
          result.reason.response?.status === 401
      );
      if (unauthorizedResult?.status === "rejected") {
        setError("Oturum süreniz dolmuş olabilir. Lütfen tekrar giriş yapın.");
        logout();
        return;
      }

      if (productsRes.status === "fulfilled") {
        setProducts(productsRes.value ?? []);
      }

      if (categoriesRes.status === "fulfilled") {
        setCategories(categoriesRes.value ?? []);
      }

      if (cartRes.status === "fulfilled") {
        setCart(cartRes.value.data ?? null);
      } else {
        setCart(null);
      }

      if (ordersRes.status === "fulfilled") {
        setOrders(ordersRes.value.data.items ?? []);
        setOrdersTotal(ordersRes.value.data.total ?? 0);
      } else {
        setOrders([]);
        setOrdersTotal(0);
      }

      if (favoritesRes.status === "fulfilled") {
        setFavoritesTotal(favoritesRes.value.data.total_count ?? 0);
        const ids = (favoritesRes.value.data.items ?? []).map((item) => item.id);
        setFavoriteIds(new Set(ids));
      } else {
        setFavoritesTotal(0);
        setFavoriteIds(new Set());
      }

      if (notificationsRes.status === "fulfilled") {
        setNotifications(notificationsRes.value.data.items ?? []);
        setUnreadNotifications(notificationsRes.value.data.unread_count ?? 0);
      } else {
        setNotifications([]);
        setUnreadNotifications(0);
      }

      const failedRequest = settledResults.find((result) => result.status === "rejected");
      if (failedRequest?.status === "rejected") {
        const reason = failedRequest.reason;
        if (isAxiosError(reason) && !reason.response) {
          setError("Backend'e bağlanılamadı. API sunucusunun açık olduğundan emin olun.");
        } else {
          setError("Bazı dashboard verileri yüklenemedi.");
        }
      }
    } catch (err) {
      setError("Dashboard verileri yüklenemedi. Lütfen sayfayı yenileyin.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    if (selectedCategoryId === "all" || selectedCategoryId === CAMPAIGN_CATEGORY_ID) return;
    const categoryExists = categories.some((category) => category.id === selectedCategoryId);
    if (!categoryExists) {
      setSelectedCategoryId("all");
    }
  }, [categories, selectedCategoryId]);

  useEffect(() => {
    let cancelled = false;

    async function loadCategoryProducts() {
      if (selectedCategoryId === "all" || selectedCategoryId === CAMPAIGN_CATEGORY_ID) {
        setCategoryProducts([]);
        return;
      }

      try {
        setCategoryProductsLoading(true);
        const items = await fetchCategoryProducts(selectedCategoryId, 500);

        if (!cancelled) {
          setCategoryProducts(items);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.status === 401) {
            setError("Oturum süresi doldu. Lütfen tekrar giriş yapın.");
            logout();
            return;
          }
          setCategoryProducts([]);
          setError("Kategori ürünleri yüklenemedi.");
        }
      } finally {
        if (!cancelled) {
          setCategoryProductsLoading(false);
        }
      }
    }

    void loadCategoryProducts();

    return () => {
      cancelled = true;
    };
  }, [selectedCategoryId, logout]);

  useEffect(() => {
    if (!isReady) return;
    if (!user && !token) {
      router.push("/login");
      return;
    }
    if (user?.is_admin) {
      router.push("/admin");
      return;
    }
    void fetchDashboardData();
  }, [isReady, user, token, router, fetchDashboardData]);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      if (modeMenuRef.current && !modeMenuRef.current.contains(event.target as Node)) {
        setIsModeMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const cartCount = useMemo(
    () => (cart?.items ?? []).reduce((acc, item) => acc + item.quantity, 0),
    [cart]
  );
  const categoryNameMap = useMemo(
    () => new Map(categories.map((category) => [category.id, category.name])),
    [categories]
  );
  const productCountByCategory = useMemo(() => {
    const counts = new Map<string, number>();
    for (const product of products) {
      counts.set(product.category_id, (counts.get(product.category_id) ?? 0) + 1);
    }
    return counts;
  }, [products]);
  const promotedProducts = useMemo(() => products.filter((product) => product.is_promoted), [products]);
  const selectedCategoryName = useMemo(() => {
    if (selectedCategoryId === "all") return "Kategoriler";
    if (selectedCategoryId === CAMPAIGN_CATEGORY_ID) return "Kampanyalar";
    return categoryNameMap.get(selectedCategoryId) ?? "Kategori";
  }, [selectedCategoryId, categoryNameMap]);
  const displayedProducts = useMemo(() => {
    const source =
      selectedCategoryId === "all"
        ? []
        : selectedCategoryId === CAMPAIGN_CATEGORY_ID
          ? promotedProducts
          : categoryProducts;
    const normalized = searchQuery.trim().toLowerCase();
    if (!normalized) return source;
    return source.filter((product) => product.name.toLowerCase().includes(normalized));
  }, [selectedCategoryId, promotedProducts, categoryProducts, searchQuery]);
  const statCards = useMemo(
    () => [
      { section: "cart" as const, label: "Sepetim", value: String(cartCount), icon: ShoppingCart, tone: "from-[#16C47F] to-[#22D3EE]" },
      { section: "orders" as const, label: "Siparişlerim", value: String(ordersTotal), icon: ClipboardList, tone: "from-[#22D3EE] to-[#16C47F]" },
      { section: "favorites" as const, label: "Favorilerim", value: String(favoritesTotal), icon: Heart, tone: "from-[#F59E0B] to-[#16C47F]" },
      { section: "profile" as const, label: "Profilim", value: user?.full_name || "-", icon: UserCircle2, tone: "from-[#1f2937] to-[#16C47F]" },
    ],
    [cartCount, ordersTotal, favoritesTotal, user?.full_name]
  );

  const actionButtonLabel = useMemo(() => {
    if (budgetLimit.trim()) return "Alışveriş Listemi Hazırla";
    return "Bana Öner";
  }, [budgetLimit]);

  const recommendationCriteria = useMemo(() => {
    const criteria: string[] = [
      `Kategori: ${mealCategory}`,
      `Hedef: ${nutritionGoal}`,
    ];
    if (budgetLimit.trim()) criteria.push(`Bütçe limiti: ${budgetLimit} TL`);
    if (allergies.trim()) criteria.push(`Alerjiler: ${allergies}`);
    if (preferredBrands.trim()) criteria.push(`Tercih edilen markalar: ${preferredBrands}`);
    return criteria;
  }, [mealCategory, nutritionGoal, budgetLimit, allergies, preferredBrands]);

  const estimatedSuggestionTotal = useMemo(() => {
    const topProducts = products.slice(0, 3);
    if (!topProducts.length) return 0;
    return topProducts.reduce((sum, p) => sum + p.price, 0);
  }, [products]);

  const budgetStatus = useMemo(() => {
    const budget = Number(budgetLimit);
    if (!budgetLimit.trim() || Number.isNaN(budget) || budget <= 0) return "";
    return estimatedSuggestionTotal > budget
      ? `Tahmini öneri tutarı (${estimatedSuggestionTotal.toFixed(2)} TL), belirlediğiniz bütçeyi aşıyor.`
      : `Tahmini öneri tutarı (${estimatedSuggestionTotal.toFixed(2)} TL), bütçenize uygun görünüyor.`;
  }, [budgetLimit, estimatedSuggestionTotal]);

  const inventoryWarnings = useMemo(() => {
    const rows = inventoryInput
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    return rows.flatMap((row) => {
      const [name, qtyRaw] = row.split(":").map((v) => v?.trim() ?? "");
      const qty = Number(qtyRaw);
      if (!name || Number.isNaN(qty)) return [];
      if (qty <= 2) return [`${name} stoğu azaldı (${qty}).`];
      return [];
    });
  }, [inventoryInput]);

  const selectedModeLabel = useMemo(
    () => AI_MODE_OPTIONS.find((option) => option.value === aiMode)?.label ?? "Normal",
    [aiMode]
  );

  const normalModePlan = useMemo<NormalModePlanView | null>(() => {
    if (!aiOutput || !isJsonObject(aiOutput.response)) return null;

    const response = aiOutput.response;
    const plan = isJsonObject(response.plan) ? response.plan : null;
    if (!plan) return null;

    const recipe = typeof plan.recipe === "string" ? plan.recipe : "";
    const servings = typeof plan.servings === "number" ? plan.servings : 0;
    if (!recipe || servings <= 0) return null;

    const summary =
      typeof response.summary === "string"
        ? response.summary
        : "Kişiselleştirilmiş öneri planı hazırlandı.";
    const prepMinutes =
      typeof plan.estimated_prep_time_minutes === "number" ? plan.estimated_prep_time_minutes : undefined;
    const cookMinutes =
      typeof plan.estimated_cook_time_minutes === "number" ? plan.estimated_cook_time_minutes : undefined;

    const ingredients = Array.isArray(plan.ingredients)
      ? plan.ingredients.filter(isIngredientSuggestion)
      : [];
    const steps = isStringArray(plan.steps) ? plan.steps : [];
    const allergenWarnings = isStringArray(response.allergen_warnings) ? response.allergen_warnings : [];
    const tips = isStringArray(response.tips) ? response.tips : [];

    return {
      summary,
      recipe,
      servings,
      prepMinutes,
      cookMinutes,
      ingredients,
      steps,
      allergenWarnings,
      tips,
    };
  }, [aiOutput]);

  const aiMarketCartItems = useMemo<MarketCartItem[]>(
    () => (aiOutput && isJsonObject(aiOutput.response) ? extractMarketCartItems(aiOutput.response) : []),
    [aiOutput]
  );

  const aiNarrative = useMemo(() => (aiOutput ? buildAiNarrative(aiOutput) : ""), [aiOutput]);

  const cartItemMap = useMemo(() => {
    const map = new Map<string, CartItem>();
    for (const item of cart?.items ?? []) {
      map.set(item.product_id, item);
    }
    return map;
  }, [cart]);

  const favoriteProducts = useMemo(
    () => products.filter((product) => favoriteIds.has(product.id)),
    [favoriteIds, products]
  );

  const orderStatusLabel = useCallback((status: string) => {
    const labels: Record<string, string> = {
      PENDING: "Bekliyor",
      PREPARING: "Hazirlaniyor",
      ON_THE_WAY: "Yolda",
      DELIVERED: "Teslim edildi",
      CANCELLED: "Iptal edildi",
    };
    return labels[status] ?? status;
  }, []);

  async function addToCart(productId: string, quantity = 1) {
    try {
      setBusyProductId(productId);
      const { data } = await api.post<CartResponse>("/api/v1/cart/items", {
        product_id: productId,
        quantity,
      });
      setCart(data);
    } catch (err) {
      setError("Ürün sepete eklenemedi.");
      console.error(err);
    } finally {
      setBusyProductId("");
    }
  }

  async function updateCartItem(productId: string, quantity: number) {
    try {
      setBusyProductId(productId);
      const { data } = await api.put<CartResponse>(`/api/v1/cart/items/${productId}`, {
        quantity,
      });
      setCart(data);
    } catch (err) {
      setError("Sepet güncellenemedi.");
      console.error(err);
    } finally {
      setBusyProductId("");
    }
  }

  async function removeCartItem(productId: string) {
    try {
      setBusyProductId(productId);
      const { data } = await api.delete<CartResponse>(`/api/v1/cart/items/${productId}`);
      setCart(data);
    } catch (err) {
      setError("Ürün sepetten çıkarılamadı.");
      console.error(err);
    } finally {
      setBusyProductId("");
    }
  }

  async function toggleFavorite(productId: string) {
    try {
      setBusyProductId(productId);
      if (favoriteIds.has(productId)) {
        const { data } = await api.delete<FavoritesResponse>(`/api/v1/favorites/${productId}`);
        setFavoritesTotal(data.total_count ?? 0);
        const ids = (data.items ?? []).map((item) => item.id);
        setFavoriteIds(new Set(ids));
      } else {
        const { data } = await api.post<FavoritesResponse>(`/api/v1/favorites/${productId}`);
        setFavoritesTotal(data.total_count ?? 0);
        const ids = (data.items ?? []).map((item) => item.id);
        setFavoriteIds(new Set(ids));
      }
    } catch (err) {
      setError("Favori işlemi başarısız.");
      console.error(err);
    } finally {
      setBusyProductId("");
    }
  }

  async function createOrderFromCart() {
    if (!cart?.items.length) return;
    try {
      setCheckoutLoading(true);
      await api.post("/api/v1/orders", {
        delivery_address: DEFAULT_ADDRESS,
        payment_method: "CASH_ON_DELIVERY",
      });
      await fetchDashboardData();
    } catch (err) {
      setError("Sipariş oluşturulamadı.");
      console.error(err);
    } finally {
      setCheckoutLoading(false);
    }
  }

  async function runAIRequest(
    prompt: string,
    options?: {
      replaceLastAssistant?: boolean;
      modeOverride?: string;
      preferenceOverrides?: Record<string, unknown>;
    }
  ) {
    const userPrompt = prompt.trim();
    if (!userPrompt) return;
    const requestMode = options?.modeOverride || aiMode;
    const wantsCart = isCartRequest(userPrompt);
    const shouldSuggestCart = requestMode !== "weekly";
    const availableIngredients = parseIngredientList(inventoryInput);
    const dietGoal = normalizeDietGoal(nutritionGoal);

    const contextMessages =
      options?.replaceLastAssistant && aiChatMessages.at(-1)?.role === "assistant"
        ? aiChatMessages.slice(0, -1)
        : aiChatMessages;
    const userMessage: ChatMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content: userPrompt,
    };
    const chatContext = [...contextMessages.slice(-7), userMessage]
      .map((item) => `${item.role === "user" ? "Kullanıcı" : "Asistan"}: ${item.content}`)
      .join("\n");

    try {
      setAiLoading(true);
      setAiFeedback("");
      setAiInput("");
      setAiChatMessages((prev) => {
        const base = options?.replaceLastAssistant && prev.at(-1)?.role === "assistant" ? prev.slice(0, -1) : prev;
        return [...base, userMessage];
      });

      const { data } = await api.post<AIResponse>("/api/v1/ai/generate", {
        mode: requestMode,
        input: userPrompt,
        preferences: {
          require_llm: true,
          include_market_cart: shouldSuggestCart,
          require_market_cart_from_llm: false,
          apply_to_cart: shouldSuggestCart,
          meal_category: mealCategory,
          budget_limit: budgetLimit ? Number(budgetLimit) : undefined,
          goal: requestMode === "diet" ? dietGoal : undefined,
          nutrition_goal: nutritionGoal,
          available_ingredients: availableIngredients.length > 0 ? availableIngredients : undefined,
          allergies,
          preferred_brands: preferredBrands,
          inventory_notes: inventoryInput,
          context: chatContext || undefined,
          ...options?.preferenceOverrides,
        },
      });

      setAiOutput(data);
      const assistantMessage: ChatMessage = {
        id: `${Date.now()}-assistant`,
        role: "assistant",
        content: buildAiNarrative(data),
      };
      setAiChatMessages((prev) => [...prev, assistantMessage]);
      await fetchDashboardData();
      setAiFeedback(
        shouldSuggestCart
          ? data.provider?.includes("local")
            ? `Yanıt hazırlandı. Sepet önerisi üretildi (yerel fallback: ${data.provider}).`
            : `Yanıt hazırlandı. Gerçek LLM yanıtı kullanıldı (${data.provider}). Sepet önerisi üretildi.`
          : data.provider?.includes("local")
            ? `Yanıt hazırlandı (yerel fallback: ${data.provider}).`
            : `Yanıt hazırlandı. Gerçek LLM yanıtı kullanıldı (${data.provider}).`
      );
      setError("");
    } catch (err) {
      if (isAxiosError(err)) {
        if (err.response?.status === 401) {
          setError("Oturum süresi doldu. Lütfen tekrar giriş yapın.");
          logout();
          return;
        }
        const backendDetail = typeof err.response?.data?.detail === "string" ? err.response?.data?.detail : "";
        setError(
          backendDetail
            ? `AI yanıtı alınamadı: ${backendDetail}`
            : "AI yanıtı alınamadı. Lütfen birkaç saniye sonra tekrar deneyin."
        );
      } else {
        setError("AI yanıtı alınamadı. Lütfen birkaç saniye sonra tekrar deneyin.");
      }
      console.error(err);
    } finally {
      setAiLoading(false);
    }
  }

  async function handleAI(event: FormEvent) {
    event.preventDefault();
    await runAIRequest(aiInput);
  }

  function clearAIChat() {
    setAiChatMessages([]);
    setAiOutput(null);
    setAiFeedback("");
    setAiInput("");
    setAttachedFileName("");
  }

  async function refreshLastAIResponse() {
    if (aiLoading) return;
    const lastUserMessage = [...aiChatMessages].reverse().find((message) => message.role === "user");
    const prompt = lastUserMessage?.content || aiInput.trim();
    if (!prompt) return;
    await runAIRequest(prompt, { replaceLastAssistant: true });
  }

  if (!isReady) return null;
  if (!user && !token) return null;

  return (
    <main
      className="min-h-screen overflow-x-hidden overflow-y-auto text-[#1F2937] flex flex-col font-[Inter,Poppins,ui-sans-serif,system-ui,sans-serif] antialiased dark:bg-slate-950 dark:text-slate-100"
      style={marbleTextureStyle}
    >
      <div className="min-h-screen px-3 pb-6 pt-3 md:px-6 md:pt-5">
        <div className="rounded-[2rem] border border-white/60 bg-white/40 shadow-[0_40px_80px_-32px_rgba(31,41,55,0.35)] backdrop-blur-2xl dark:border-slate-800/70 dark:bg-slate-900/65">
          <header className="sticky top-0 z-30 border-b border-white/60 bg-white/65 px-4 py-4 backdrop-blur-2xl md:px-6 dark:border-slate-800/80 dark:bg-slate-900/80">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <p className="bg-gradient-to-r from-[#16C47F] via-[#22D3EE] to-[#F59E0B] bg-clip-text text-xs font-semibold uppercase tracking-[0.24em] text-transparent">
                  CookWise Dashboard
                </p>
                <h1 className="text-xl font-semibold text-[#1F2937] dark:text-slate-100">
                  Hoş geldin, {user?.full_name || "CookWise kullanıcısı"}
                </h1>
              </div>
              <div className="ml-auto flex w-full items-center gap-2 sm:w-auto">
                <div className="relative hidden sm:block">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Ürün ara..."
                    className="w-56 rounded-2xl border border-white/70 bg-white/80 py-2 pl-9 pr-3 text-sm outline-none transition focus:border-[#22D3EE] focus:ring-2 focus:ring-[#22D3EE]/30 dark:border-slate-700 dark:bg-slate-900/70"
                  />
                </div>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setIsNotificationsOpen((prev) => !prev)}
                    className="relative inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/70 bg-white/80 text-slate-600 transition hover:-translate-y-0.5 hover:text-[#16C47F] dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300"
                  >
                    <Bell className="h-4 w-4" />
                    {unreadNotifications > 0 ? (
                      <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-[#F59E0B] px-1 text-[10px] font-bold text-white">
                        {unreadNotifications}
                      </span>
                    ) : null}
                  </button>
                  <AnimatePresence>
                    {isNotificationsOpen ? (
                      <motion.div
                        initial={{ opacity: 0, y: -8, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -8, scale: 0.98 }}
                        className="absolute right-0 z-40 mt-3 w-[min(22rem,calc(100vw-2rem))] rounded-3xl border border-white/80 bg-white/95 p-3 shadow-2xl backdrop-blur-2xl"
                      >
                        <div className="mb-2 flex items-center justify-between">
                          <p className="text-sm font-semibold text-[#1F2937]">Bildirimler</p>
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                            {unreadNotifications} yeni
                          </span>
                        </div>
                        <div className="max-h-80 space-y-2 overflow-auto">
                          {notifications.length === 0 ? (
                            <p className="rounded-2xl border border-slate-100 bg-slate-50 px-3 py-4 text-xs text-slate-500">
                              Su an bildirimin yok.
                            </p>
                          ) : (
                            notifications.map((notification) => (
                              <button
                                key={notification.id}
                                type="button"
                                onClick={async () => {
                                  await api.post(`/api/v1/notifications/${notification.id}/read`);
                                  setNotifications((prev) =>
                                    prev.map((item) => (item.id === notification.id ? { ...item, is_read: true } : item))
                                  );
                                  setUnreadNotifications((prev) => Math.max(0, prev - (notification.is_read ? 0 : 1)));
                                }}
                                className={`w-full rounded-2xl border px-3 py-2 text-left transition ${
                                  notification.is_read
                                    ? "border-slate-100 bg-white text-slate-600"
                                    : "border-[#16C47F]/25 bg-emerald-50/80 text-[#1F2937]"
                                }`}
                              >
                                <p className="text-xs font-semibold">{notification.title}</p>
                                <p className="mt-1 text-xs leading-5 text-slate-600">{notification.body}</p>
                              </button>
                            ))
                          )}
                        </div>
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </div>
                <button
                  type="button"
                  onClick={() => setIsMobileAssistantOpen(true)}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/70 bg-white/80 text-slate-600 transition hover:-translate-y-0.5 lg:hidden"
                >
                  <Menu className="h-4 w-4" />
                </button>
                {user?.is_admin ? (
                  <Link
                    href="/admin"
                    className="hidden rounded-2xl border border-[#16C47F]/30 bg-white/90 px-3 py-2 text-sm font-semibold text-[#138a5b] transition hover:-translate-y-0.5 sm:inline-flex"
                  >
                    Admin
                  </Link>
                ) : null}
                <button
                  onClick={logout}
                  className="inline-flex items-center gap-1.5 rounded-2xl bg-gradient-to-r from-[#16C47F] via-[#22D3EE] to-[#16C47F] px-3 py-2 text-sm font-semibold text-white shadow-[0_14px_30px_-16px_rgba(34,211,238,0.9)] transition hover:-translate-y-0.5"
                >
                  <LogOut className="h-4 w-4" />
                  Çıkış
                </button>
              </div>
            </div>
          </header>

          <section className="grid grid-cols-1 gap-6 p-4 md:p-6 lg:grid-cols-12">
            <div className="space-y-5 lg:col-span-8">
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                className="grid grid-cols-2 gap-3 md:grid-cols-4"
              >
                {statCards.map((stat) => (
                  <motion.button
                    type="button"
                    key={stat.label}
                    onClick={() => {
                      if (stat.section === "cart") {
                        router.push("/cart");
                        return;
                      }
                      setActiveOverviewSection(stat.section);
                    }}
                    whileHover={{ y: -4, scale: 1.01 }}
                    className={`rounded-[24px] border p-3 text-left backdrop-blur-xl shadow-[0_20px_40px_-30px_rgba(31,41,55,0.55)] transition dark:border-slate-700 dark:bg-slate-900/70 ${
                      activeOverviewSection === stat.section
                        ? "border-[#16C47F]/55 bg-white/90 ring-2 ring-[#22D3EE]/25"
                        : "border-white/70 bg-white/70"
                    }`}
                  >
                    <div className={`mb-2 inline-flex rounded-xl bg-gradient-to-r p-2 text-white ${stat.tone}`}>
                      <stat.icon className="h-4 w-4" />
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{stat.label}</p>
                    <p className="line-clamp-1 text-sm font-semibold text-[#1F2937] dark:text-slate-100">{stat.value}</p>
                  </motion.button>
                ))}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-[28px] border border-white/75 bg-white/70 p-4 shadow-[0_25px_55px_-36px_rgba(31,41,55,0.45)] backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/70"
              >
                {activeOverviewSection === "cart" ? (
                  <div>
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <h2 className="text-lg font-semibold text-[#1F2937] dark:text-slate-100">Sepetim</h2>
                      <span className="rounded-2xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] px-3 py-1.5 text-sm font-bold text-white">
                        {(cart?.total_price || 0).toFixed(2)} TL
                      </span>
                    </div>
                    {!cart?.items?.length ? (
                      <p className="rounded-2xl border border-dashed border-[#16C47F]/35 bg-white/75 p-4 text-sm text-slate-500">
                        Sepetin bos. Kategorilerden urun secerek ekleyebilirsin.
                      </p>
                    ) : (
                      <div className="grid gap-2 md:grid-cols-2">
                        {cart.items.map((item) => (
                          <div key={item.product_id} className="rounded-2xl border border-white/80 bg-white/86 p-3">
                            <p className="text-sm font-semibold text-[#1F2937]">{item.name}</p>
                            <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                              <span>{item.quantity} x {item.price.toFixed(2)} TL</span>
                              <span className="font-bold text-[#16C47F]">{item.subtotal.toFixed(2)} TL</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <Link
                      href="/cart"
                      className="mt-3 inline-flex rounded-2xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] px-4 py-2 text-sm font-semibold text-white shadow-sm"
                    >
                      Sepet Sayfasina Git
                    </Link>
                  </div>
                ) : null}

                {activeOverviewSection === "orders" ? (
                  <div>
                    <h2 className="text-lg font-semibold text-[#1F2937] dark:text-slate-100">Siparişlerim</h2>
                    <div className="mt-3 space-y-2">
                      {orders.length === 0 ? (
                        <p className="rounded-2xl border border-dashed border-[#16C47F]/35 bg-white/75 p-4 text-sm text-slate-500">
                          Henüz siparişin yok.
                        </p>
                      ) : (
                        orders.slice(0, 5).map((order) => (
                          <div key={order.id} className="rounded-2xl border border-white/80 bg-white/86 p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-sm font-semibold text-[#1F2937]">#{order.id.slice(-6).toUpperCase()}</p>
                                <p className="mt-1 text-xs text-slate-500">{order.items.length} ürün • {order.payment_method}</p>
                              </div>
                              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                                {orderStatusLabel(order.status)}
                              </span>
                            </div>
                            <p className="mt-2 text-sm font-bold text-[#16C47F]">{order.total_price.toFixed(2)} TL</p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ) : null}

                {activeOverviewSection === "favorites" ? (
                  <div>
                    <h2 className="text-lg font-semibold text-[#1F2937] dark:text-slate-100">Favorilerim</h2>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      {favoriteProducts.length === 0 ? (
                        <p className="rounded-2xl border border-dashed border-[#16C47F]/35 bg-white/75 p-4 text-sm text-slate-500 md:col-span-2">
                          Henüz favori ürün eklemedin.
                        </p>
                      ) : (
                        favoriteProducts.slice(0, 8).map((product) => (
                          <div key={product.id} className="rounded-2xl border border-white/80 bg-white/86 p-3">
                            <p className="line-clamp-1 text-sm font-semibold text-[#1F2937]">{product.name}</p>
                            <div className="mt-2 flex items-center justify-between">
                              <span className="text-sm font-bold text-[#16C47F]">{getEffectiveProductPrice(product).toFixed(2)} TL</span>
                              <button
                                type="button"
                                onClick={() => addToCart(product.id)}
                                className="rounded-full bg-[#16C47F] px-3 py-1 text-xs font-semibold text-white"
                              >
                                Sepete Ekle
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ) : null}

                {activeOverviewSection === "profile" ? (
                  <div>
                    <h2 className="text-lg font-semibold text-[#1F2937] dark:text-slate-100">Profilim</h2>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl border border-white/80 bg-white/86 p-3">
                        <p className="text-xs text-slate-500">Ad Soyad</p>
                        <p className="mt-1 text-sm font-semibold text-[#1F2937]">{user?.full_name || "-"}</p>
                      </div>
                      <div className="rounded-2xl border border-white/80 bg-white/86 p-3">
                        <p className="text-xs text-slate-500">E-posta</p>
                        <p className="mt-1 break-all text-sm font-semibold text-[#1F2937]">{user?.email || "-"}</p>
                      </div>
                      <div className="rounded-2xl border border-white/80 bg-white/86 p-3">
                        <p className="text-xs text-slate-500">Rol</p>
                        <p className="mt-1 text-sm font-semibold text-[#1F2937]">{user?.is_admin ? "Admin" : "Kullanıcı"}</p>
                      </div>
                      <div className="rounded-2xl border border-white/80 bg-white/86 p-3">
                        <p className="text-xs text-slate-500">Durum</p>
                        <p className="mt-1 text-sm font-semibold text-[#1F2937]">{user?.is_active ? "Aktif" : "Pasif"}</p>
                      </div>
                    </div>
                  </div>
                ) : null}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05, duration: 0.35 }}
                className="rounded-[28px] border border-white/75 bg-white/68 p-4 backdrop-blur-xl shadow-[0_25px_55px_-32px_rgba(31,41,55,0.48)] dark:border-slate-700 dark:bg-slate-900/70"
              >
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-semibold text-[#1F2937] dark:text-slate-100">
                      {selectedCategoryId === "all" ? "Kategoriler" : selectedCategoryName}
                    </h2>
                    <p className="text-xs text-slate-500">
                      {selectedCategoryId === "all"
                        ? "Alisverise baslamak icin bir kategori sec"
                        : `${selectedCategoryName} • ${displayedProducts.length} ürün`}
                    </p>
                  </div>
                  {selectedCategoryId !== "all" ? (
                  <div className="relative w-full sm:hidden">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Ürün ara..."
                      className="w-full rounded-2xl border border-white/70 bg-white/85 py-2 pl-9 pr-3 text-sm outline-none"
                    />
                  </div>
                  ) : null}
                </div>

                {selectedCategoryId !== "all" ? (
                  <div className="mb-4">
                    <motion.button
                      type="button"
                      onClick={() => {
                        setSelectedCategoryId("all");
                        setSearchQuery("");
                      }}
                      whileTap={{ scale: 0.97 }}
                      className="rounded-2xl border border-emerald-200/80 bg-white/85 px-4 py-2 text-sm font-semibold text-[#0f766e] shadow-sm transition hover:bg-emerald-50"
                    >
                      Kategorilere Don
                    </motion.button>
                  </div>
                ) : null}

                {isLoading ? (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, idx) => (
                      <div key={`skeleton-${idx}`} className="animate-pulse rounded-3xl border border-white/70 bg-white/80 p-3">
                        <div className="h-36 rounded-2xl bg-slate-200/80" />
                        <div className="mt-3 h-4 w-3/4 rounded bg-slate-200/80" />
                        <div className="mt-2 h-4 w-1/2 rounded bg-slate-200/80" />
                      </div>
                    ))}
                  </div>
                ) : selectedCategoryId === "all" ? (
                  <motion.div
                    initial="hidden"
                    animate="visible"
                    variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.045 } } }}
                    className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4"
                  >
                    <motion.button
                      type="button"
                      onClick={() => setSelectedCategoryId(CAMPAIGN_CATEGORY_ID)}
                      variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } }}
                      whileHover={{ y: -5, scale: 1.01 }}
                      whileTap={{ scale: 0.98 }}
                      className="relative min-h-[170px] overflow-hidden rounded-[24px] border border-amber-100 bg-amber-50/90 p-0 text-left shadow-[0_16px_30px_-24px_rgba(245,158,11,0.55)] transition"
                    >
                      <img src="/categories/kampanya.png" alt="" className="absolute inset-0 h-full w-full object-cover" />
                      <span className="absolute inset-0 bg-gradient-to-t from-black/25 via-transparent to-white/10" />
                      <span className="absolute bottom-3 left-3 max-w-[76%] rounded-xl border border-white/70 bg-white/90 px-2.5 py-1.5 text-[0px] shadow-sm backdrop-blur [&>span:nth-child(2)]:hidden">
                        <span className="block text-[13px] font-extrabold leading-tight text-[#1F2937]">Kampanyalar <span className="mt-0.5 block text-[11px] font-bold leading-tight text-amber-700">{promotedProducts.length} indirimli urun</span></span>
                        <span className="mt-1 block text-xs font-semibold text-white/85">{promotedProducts.length} indirimli ürün</span>
                        ✨
                      </span>
                    </motion.button>
                    {categories.map((category) => {
                      const categoryImage = getCategoryImagePath(category.slug);
                      return (
                      <motion.button
                        key={category.id}
                        type="button"
                        onClick={() => setSelectedCategoryId(category.id)}
                        variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } }}
                        whileHover={{ y: -5, scale: 1.01 }}
                        whileTap={{ scale: 0.98 }}
                        className={
                          categoryImage
                            ? "relative min-h-[170px] overflow-hidden rounded-[24px] border border-white/80 bg-white/85 p-0 text-left shadow-[0_16px_30px_-24px_rgba(31,41,55,0.45)] transition hover:border-[#16C47F]/35"
                            : "min-h-[150px] rounded-[24px] border border-white/80 bg-white/85 p-4 text-left shadow-[0_16px_30px_-24px_rgba(31,41,55,0.45)] transition hover:border-[#16C47F]/35"
                        }
                      >
                        {categoryImage ? (
                          <>
                            <img src={categoryImage} alt="" className="absolute inset-0 h-full w-full object-cover contrast-[1.04] saturate-[1.08]" />
                            <span className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-white/10" />
                            <span className="absolute bottom-3 left-3 max-w-[78%] rounded-xl border border-white/70 bg-white/90 px-2.5 py-1.5 shadow-sm backdrop-blur">
                              <span className="block text-[13px] font-extrabold leading-tight text-[#1F2937]">{category.name}</span>
                              <span className="mt-0.5 block text-[11px] font-bold leading-tight text-[#0f766e]">{productCountByCategory.get(category.id) ?? 0} urun</span>
                            </span>
                          </>
                        ) : (
                          <>
                        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-[#16C47F]/18 to-[#22D3EE]/22 text-2xl">
                          {getCategoryEmoji(category.slug)}
                        </span>
                        <span className="mt-4 block text-sm font-bold text-[#1F2937] dark:text-slate-100">{category.name}</span>
                        <span className="mt-1 block text-xs text-slate-500">{productCountByCategory.get(category.id) ?? 0} urun</span>
                          </>
                        )}
                      </motion.button>
                      );
                    })}
                  </motion.div>
                ) : categoryProductsLoading ? (
                  <p className="rounded-2xl border border-white/70 bg-white/70 px-4 py-6 text-sm text-slate-500">Ürünler yükleniyor...</p>
                ) : displayedProducts.length === 0 ? (
                  <div className="rounded-3xl border border-dashed border-[#16C47F]/35 bg-white/65 px-5 py-10 text-center">
                    <p className="text-sm text-slate-500">Aradığın kriterde ürün bulunamadı.</p>
                  </div>
                ) : (
                  <motion.div
                    initial="hidden"
                    animate="visible"
                    variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.045 } } }}
                    className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3"
                  >
                    {displayedProducts.map((product) => (
                      <motion.article
                        key={product.id}
                        variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } }}
                        whileHover={{ y: -6, scale: 1.01 }}
                        className="group rounded-[24px] border border-white/80 bg-white/88 p-3 shadow-[0_16px_30px_-20px_rgba(31,41,55,0.5)] transition dark:border-slate-700 dark:bg-slate-900/75"
                      >
                        <div className="relative h-36 overflow-hidden rounded-2xl bg-gradient-to-br from-[#16C47F]/10 to-[#22D3EE]/15">
                          <img
                            src={getProductPhoto(product.name, product.image_url)}
                            alt={product.name}
                            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                            loading="lazy"
                          />
                          <span className="absolute left-2 top-2 inline-flex items-center gap-1 rounded-full bg-[#1F2937]/75 px-2 py-0.5 text-[11px] text-white">
                            <Sparkles className="h-3 w-3 text-[#F59E0B]" />
                            AI öneriyor
                          </span>
                          <button
                            type="button"
                            onClick={() => toggleFavorite(product.id)}
                            className="absolute right-2 top-2 rounded-full bg-white/85 p-1.5 text-[#F59E0B] shadow"
                          >
                            <Heart className={`h-3.5 w-3.5 ${favoriteIds.has(product.id) ? "fill-[#F59E0B]" : ""}`} />
                          </button>
                        </div>
                        <p className="mt-3 min-h-[2.8rem] text-sm font-semibold text-[#1F2937] dark:text-slate-100">{product.name}</p>
                        <div className="mt-3 flex items-center justify-between">
                          <span className="flex flex-col">
                            {getEffectiveProductPrice(product) < product.price ? (
                              <span className="text-xs text-slate-400 line-through">{product.price.toFixed(2)} TL</span>
                            ) : null}
                            <span className="text-base font-bold text-[#16C47F]">{getEffectiveProductPrice(product).toFixed(2)} TL</span>
                          </span>
                          <motion.button
                            type="button"
                            whileTap={{ scale: 0.96 }}
                            onClick={() => addToCart(product.id)}
                            disabled={busyProductId === product.id}
                            className="rounded-xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] px-3 py-1.5 text-xs font-semibold text-white shadow-[0_10px_22px_-12px_rgba(34,211,238,0.95)] disabled:opacity-70"
                          >
                            {busyProductId === product.id ? "Ekleniyor..." : "Sepete Ekle"}
                          </motion.button>
                        </div>
                      </motion.article>
                    ))}
                  </motion.div>
                )}
              </motion.div>
            </div>

            <aside className="hidden space-y-4 lg:col-span-4 lg:block lg:sticky lg:top-28 lg:h-fit">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35 }}
                className="rounded-[30px] border border-[#22D3EE]/35 bg-gradient-to-br from-[#ffffffc9] via-[#ecfffae0] to-[#e9f7ffcf] p-4 shadow-[0_30px_65px_-36px_rgba(34,211,238,0.95)] backdrop-blur-2xl dark:border-[#22D3EE]/30 dark:from-slate-900/80 dark:to-slate-800/80"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded-xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] p-2 text-white shadow-lg">
                      <Bot className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-[#1F2937] dark:text-slate-100">CookWise AI</p>
                      <p className="text-[11px] text-slate-500">Premium asistan</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={refreshLastAIResponse}
                      disabled={aiLoading || (!aiInput.trim() && !aiChatMessages.some((message) => message.role === "user"))}
                      title="Son AI yanitini yenile"
                      className="rounded-xl border border-[#22D3EE]/35 bg-white/80 p-1.5 text-slate-500 transition hover:border-[#16C47F]/45 hover:text-[#138a5b] disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={clearAIChat}
                      disabled={aiLoading || (aiChatMessages.length === 0 && !aiOutput && !aiInput && !attachedFileName)}
                      title="AI sohbetini temizle"
                      className="rounded-xl border border-rose-100 bg-white/80 p-1.5 text-slate-500 transition hover:border-rose-200 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  <span className="rounded-full border border-[#22D3EE]/45 bg-white/80 px-2 py-0.5 text-[11px] text-[#138a5b]">
                    {aiOutput?.provider ?? "hazır"}
                  </span>
                  </div>
                </div>

                <div ref={modeMenuRef} className="mb-3 relative">
                  <button
                    type="button"
                    onClick={() => setIsModeMenuOpen((prev) => !prev)}
                    className="w-full rounded-2xl border border-white/80 bg-white/80 px-3 py-2 text-left text-xs font-medium text-slate-600"
                  >
                    Mod: <span className="font-semibold text-[#16C47F]">{selectedModeLabel}</span>
                  </button>
                  <AnimatePresence>
                    {isModeMenuOpen ? (
                      <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        className="absolute z-20 mt-2 w-full rounded-2xl border border-white/80 bg-white/95 p-1 shadow-xl"
                      >
                        {AI_MODE_OPTIONS.map((option) => (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => {
                              setAiMode(option.value);
                              setIsModeMenuOpen(false);
                            }}
                            className={`w-full rounded-xl px-3 py-2 text-left text-xs transition ${
                              aiMode === option.value ? "bg-[#16C47F]/15 text-[#128156]" : "hover:bg-slate-100/90"
                            }`}
                          >
                            {option.label}
                          </button>
                        ))}
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </div>

                <div className="custom-scrollbar max-h-72 space-y-2 overflow-auto rounded-2xl border border-white/75 bg-white/78 p-2.5 dark:border-slate-700 dark:bg-slate-900/70">
                  {aiChatMessages.length === 0 ? (
                    <p className="text-xs text-slate-500">Bütçeni ve hedefini yaz, sepetini yapay zeka oluştursun.</p>
                  ) : (
                    aiChatMessages.slice(-10).map((message) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`whitespace-pre-line rounded-2xl px-3 py-2 text-xs leading-relaxed ${
                          message.role === "user"
                            ? "ml-8 bg-gradient-to-r from-[#16C47F] to-[#22D3EE] text-white"
                            : "mr-8 border border-[#22D3EE]/25 bg-[#f8fffc] text-slate-700 dark:bg-slate-800 dark:text-slate-100"
                        }`}
                      >
                        {message.content}
                      </motion.div>
                    ))
                  )}
                  <AnimatePresence>
                    {aiLoading ? (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="mr-10 inline-flex items-center gap-2 rounded-xl border border-[#22D3EE]/35 bg-white px-3 py-2 text-xs text-slate-500"
                      >
                        <span className="h-2 w-2 animate-pulse rounded-full bg-[#16C47F]" />
                        <span className="h-2 w-2 animate-pulse rounded-full bg-[#22D3EE] [animation-delay:120ms]" />
                        <span className="h-2 w-2 animate-pulse rounded-full bg-[#F59E0B] [animation-delay:240ms]" />
                        AI yazıyor...
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </div>

                <div className="mt-2 grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={refreshLastAIResponse}
                    disabled={aiLoading || (!aiInput.trim() && !aiChatMessages.some((message) => message.role === "user"))}
                    className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-[#22D3EE]/35 bg-white/85 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-[#16C47F]/45 hover:text-[#138a5b] disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Yenile
                  </button>
                  <button
                    type="button"
                    onClick={clearAIChat}
                    disabled={aiLoading || (aiChatMessages.length === 0 && !aiOutput && !aiInput && !attachedFileName)}
                    className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-rose-100 bg-white/85 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-rose-200 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Sohbeti temizle
                  </button>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {quickActions.map((action) => (
                    <button
                      key={action.label}
                      type="button"
                      onClick={() => {
                        setAiInput(action.label);
                        setAiMode(action.mode);
                        void runAIRequest(action.label, {
                          modeOverride: action.mode,
                          preferenceOverrides: action.preferences,
                        });
                      }}
                      className="rounded-full border border-[#22D3EE]/35 bg-white/85 px-2.5 py-1 text-[11px] text-slate-600 transition hover:-translate-y-0.5 hover:border-[#16C47F]/45 hover:text-[#138a5b]"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>

                <form onSubmit={handleAI} className="mt-3 rounded-2xl border border-white/80 bg-white/88 p-1.5">
                  <div className="flex items-center gap-1.5">
                    <button type="button" onClick={() => fileInputRef.current?.click()} className="rounded-xl p-2 text-slate-600 transition hover:bg-slate-100">
                      <Paperclip className="h-4 w-4" />
                    </button>
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.08 }}
                      whileTap={{ scale: 0.95 }}
                      className="rounded-xl p-2 text-[#16C47F] transition hover:bg-[#16C47F]/10"
                    >
                      <Mic className="h-4 w-4" />
                    </motion.button>
                    <input
                      value={aiInput}
                      onChange={(e) => setAiInput(e.target.value)}
                      placeholder="AI asistanına yaz..."
                      className="flex-1 bg-transparent px-1 py-2 text-sm outline-none"
                    />
                    <motion.button
                      type="submit"
                      disabled={aiLoading}
                      whileTap={{ scale: 0.97 }}
                      className="inline-flex items-center gap-1 rounded-xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] px-3 py-2 text-xs font-semibold text-white shadow-[0_12px_24px_-14px_rgba(34,211,238,0.9)] disabled:opacity-70"
                    >
                      <Send className="h-3.5 w-3.5" />
                      Gönder
                    </motion.button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (!f) return;
                        setAttachedFileName(f.name);
                      }}
                    />
                  </div>
                </form>
                {attachedFileName ? <p className="mt-1 text-[11px] text-slate-500">Dosya: {attachedFileName}</p> : null}
                {aiFeedback ? <p className="mt-2 rounded-xl bg-emerald-50/80 px-2 py-1 text-xs text-emerald-700">{aiFeedback}</p> : null}
              </motion.div>

              {aiMarketCartItems.length > 0 ? (
                <motion.div
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.06, duration: 0.35 }}
                  className="rounded-[28px] border border-[#16C47F]/25 bg-white/80 p-4 backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/70"
                >
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold">AI Sepet Onerisi</h3>
                    <span className="rounded-xl bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                      {aiMarketCartItems.length} urun
                    </span>
                  </div>
                  <div className="custom-scrollbar max-h-44 space-y-2 overflow-auto">
                    {aiMarketCartItems.map((item) => (
                      <div key={item.product_id} className="rounded-2xl border border-white/80 bg-white/90 p-2">
                        <p className="line-clamp-1 text-xs font-semibold">{item.name}</p>
                        <div className="mt-1 flex items-center justify-between gap-2">
                          <span className="text-xs text-slate-500">
                            {item.quantity} adet - {item.subtotal.toFixed(2)} TL
                          </span>
                          <button
                            type="button"
                            onClick={() => addToCart(item.product_id, item.quantity)}
                            disabled={busyProductId === item.product_id}
                            className="rounded-full bg-[#16C47F] px-3 py-1 text-[11px] font-semibold text-white disabled:opacity-60"
                          >
                            {busyProductId === item.product_id ? "Ekleniyor" : "Ekle"}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              ) : null}

              <motion.div
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.08, duration: 0.35 }}
                className="rounded-[28px] border border-white/70 bg-white/76 p-4 backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/70"
              >
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Sepetim</h3>
                  <span className="rounded-xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] px-2 py-1 text-sm font-semibold text-white">
                    {(cart?.total_price || 0).toFixed(2)} TL
                  </span>
                </div>
                {!cart?.items?.length ? (
                  <div className="rounded-2xl border border-dashed border-[#16C47F]/35 bg-white/75 p-4 text-xs text-slate-500">
                    Sepetiniz boş. Ürün kartlarından hızlıca ekleme yapabilirsiniz.
                  </div>
                ) : (
                  <div className="custom-scrollbar max-h-44 space-y-2 overflow-auto">
                    {cart.items.map((item) => (
                      <div key={item.product_id} className="rounded-2xl border border-white/80 bg-white/90 p-2 transition hover:-translate-y-0.5 hover:shadow-md">
                        <p className="line-clamp-1 text-xs font-semibold">{item.name}</p>
                        <div className="mt-1 flex items-center justify-between gap-2">
                          <span className="text-xs text-slate-500">{item.price.toFixed(2)} TL</span>
                          <div className="flex items-center gap-1 rounded-full border border-slate-200 bg-white px-1">
                            <button
                              type="button"
                              onClick={() => (item.quantity <= 1 ? removeCartItem(item.product_id) : updateCartItem(item.product_id, item.quantity - 1))}
                              className="rounded-full px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100"
                            >
                              -
                            </button>
                            <span className="min-w-5 text-center text-xs font-semibold">{item.quantity}</span>
                            <button
                              type="button"
                              onClick={() => updateCartItem(item.product_id, item.quantity + 1)}
                              className="rounded-full px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100"
                            >
                              +
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <motion.button
                  type="button"
                  whileTap={{ scale: 0.98 }}
                  onClick={createOrderFromCart}
                  disabled={!cart?.items?.length || checkoutLoading}
                  className="mt-3 w-full rounded-2xl bg-gradient-to-r from-[#16C47F] via-[#22D3EE] to-[#16C47F] py-2.5 text-sm font-semibold text-white shadow-[0_16px_30px_-16px_rgba(34,211,238,0.95)] disabled:opacity-70"
                >
                  {checkoutLoading ? "Sipariş oluşturuluyor..." : "Checkout ile Siparişi Tamamla"}
                </motion.button>
              </motion.div>
            </aside>
          </section>
        </div>
      </div>

      <AnimatePresence>
        {isMobileAssistantOpen ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[#0f172a]/45 p-3 backdrop-blur-sm lg:hidden"
          >
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 18, opacity: 0 }}
              className="ml-auto h-full w-full max-w-md rounded-[28px] border border-white/65 bg-white/92 p-4 shadow-2xl"
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ChefHat className="h-5 w-5 text-[#16C47F]" />
                  <p className="text-sm font-semibold">CookWise AI Panel</p>
                </div>
                <button type="button" onClick={() => setIsMobileAssistantOpen(false)} className="rounded-xl border border-slate-200 p-1.5">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <p className="text-xs text-slate-500">Masaüstündeki AI panelinin mobil görünümü.</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={refreshLastAIResponse}
                  disabled={aiLoading || (!aiInput.trim() && !aiChatMessages.some((message) => message.role === "user"))}
                  className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-[#22D3EE]/35 bg-white px-3 py-2 text-xs font-semibold text-slate-600 disabled:opacity-45"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Yenile
                </button>
                <button
                  type="button"
                  onClick={clearAIChat}
                  disabled={aiLoading || (aiChatMessages.length === 0 && !aiOutput && !aiInput && !attachedFileName)}
                  className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-rose-100 bg-white px-3 py-2 text-xs font-semibold text-rose-600 disabled:opacity-45"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Temizle
                </button>
              </div>

              <div className="custom-scrollbar mt-3 max-h-[58vh] space-y-2 overflow-auto rounded-2xl border border-slate-100 bg-white/80 p-2">
                {aiChatMessages.length === 0 ? (
                  <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
                    AI sohbeti bos. Bir tarif veya malzeme istegi yazabilirsin.
                  </p>
                ) : (
                  aiChatMessages.slice(-10).map((message) => (
                    <div
                      key={message.id}
                      className={`whitespace-pre-line rounded-2xl px-3 py-2 text-xs leading-relaxed ${
                        message.role === "user"
                          ? "ml-8 bg-gradient-to-r from-[#16C47F] to-[#22D3EE] text-white"
                          : "mr-8 border border-[#22D3EE]/25 bg-[#f8fffc] text-slate-700"
                      }`}
                    >
                      {message.content}
                    </div>
                  ))
                )}
                {aiLoading ? <p className="text-xs text-slate-500">AI yaziyor...</p> : null}
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {error ? (
        <div className="fixed bottom-4 left-1/2 z-40 w-[min(92vw,860px)] -translate-x-1/2 rounded-2xl border border-red-200 bg-red-50/95 px-4 py-3 text-sm text-red-700 shadow-lg">
          {error}
        </div>
      ) : null}

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(226, 232, 240, 0.45);
          border-radius: 9999px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, #16c47f, #22d3ee);
          border-radius: 9999px;
        }
      `}</style>
    </main>
  );
}
