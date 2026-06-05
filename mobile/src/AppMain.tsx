import { StatusBar } from "expo-status-bar";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImagePicker from "expo-image-picker";
import * as SecureStore from "expo-secure-store";
import axios, { isAxiosError } from "axios";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  FlatList,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { api, getApiBaseUrl, SESSION_TOKEN_KEY } from "./lib/api";
import { getProductImage, withRetry } from "./lib/utils";
import { AI_MODE_OPTIONS, QUICK_ACTION_PROMPTS } from "./features/assistant/constants";
import { buildAiNarrative, extractMarketCartItems, isCartRequest, type AIResponse, type MarketCartItem } from "./features/assistant/parser";
import type {
  AuthUser,
  CartResponse,
  Category,
  ChatMessage,
  FavoritesResponse,
  LoginResponse,
  Order,
  OrdersResponse,
  Product,
} from "./types/app";
import GlassCard from "./components/ui/GlassCard";
import SegmentedControl from "./components/ui/SegmentedControl";
import FloatingComposer from "./components/ui/FloatingComposer";
import ChatBubble from "./components/ui/ChatBubble";
import { palette, shadows } from "./theme/palette";
import AuthScreen, { type AuthMode as AuthScreenMode } from "./screens/AuthScreen";

/** Kullanıcı profili: AsyncStorage (SecureStore ~2048 bayt sınırını aşabiliyor). */
const USER_KEY = "cookwise_mobile_user";
const CATEGORY_IMAGE_SOURCES: Record<string, ReturnType<typeof require>> = {
  atistirmalik: require("../assets/categories/atistirmalik.png"),
  bebek: require("../assets/categories/bebekurunleri.png"),
  "et-tavuk-balik": require("../assets/categories/etbaliktavuk.png"),
  "evcil-hayvan": require("../assets/categories/evcilhayvan.png"),
  "firin-pastane": require("../assets/categories/firin.png"),
  icecek: require("../assets/categories/icecek.png"),
  "kisisel-bakim-kozmetik-saglik": require("../assets/categories/kisiselbakim.png"),
  "kisisel-bakim": require("../assets/categories/kisiselbakim.png"),
  "sut-kahvaltilik": require("../assets/categories/kahvaltilik.png"),
  "sut-urunleri": require("../assets/categories/kahvaltilik.png"),
  "meyve-sebze": require("../assets/categories/meyvesebze.png"),
  "kagit-islak-mendil": require("../assets/categories/pecete.png"),
  "temel-gida": require("../assets/categories/temelgida.png"),
  temizlik: require("../assets/categories/temizlik.png"),
  "deterjan-temizlik": require("../assets/categories/temizlik.png"),
  "donuk": require("../assets/categories/temelgida.png"),
  "meze-hazir-yemek-donuk": require("../assets/categories/temelgida.png"),
};
const CHAT_KEY_PREFIX = "cookwise_mobile_chat_";
const DISCOUNT_CATEGORY_ID = "__discounts";
const DEFAULT_ADDRESS = "Örnek Mah. 100 Sok. No:10 Kadıköy/İstanbul";
const MEAL_CATEGORIES = ["Akşam Yemeği", "Kahvaltı", "Sağlıklı Atıştırmalıklar", "Haftalık Plan"] as const;

type MainTab = "assistant" | "market" | "cart" | "admin" | "profile";
type OrderStatus = "PENDING" | "PREPARING" | "ON_THE_WAY" | "DELIVERED" | "CANCELLED";
type AdminModule = "home" | "analytics" | "users" | "notifications" | "product-add" | "products" | "campaigns" | "orders" | "stock";
type AdminUser = {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  is_active: boolean;
  is_admin: boolean;
  is_verified: boolean;
  created_at: string;
};
type AdminUserListResponse = {
  items: AdminUser[];
  total: number;
  skip: number;
  limit: number;
};
type AdminAnalytics = {
  users_total: number;
  active_users: number;
  products_total: number;
  low_stock_products: number;
  active_campaigns: number;
  orders_total: number;
  pending_orders: number;
  revenue_total: number;
  top_products: Array<{ name: string; quantity: number; revenue: number }>;
  orders_by_status: Array<{ status: OrderStatus; count: number }>;
};

const TAB_ITEMS: { value: MainTab; label: string; icon: string }[] = [
  { value: "assistant", label: "Asistan", icon: "✨" },
  { value: "market", label: "Market", icon: "🛒" },
  { value: "cart", label: "Sepet", icon: "🧺" },
  { value: "profile", label: "Profil", icon: "👤" },
];

function chatStorageKey(userId: string): string {
  return `${CHAT_KEY_PREFIX}${userId}`;
}

const ADMIN_TAB_ITEM: { value: MainTab; label: string; icon: string } = { value: "admin", label: "Admin", icon: "ADM" };
const ADMIN_TAB_ITEMS: { value: MainTab; label: string; icon: string }[] = [
  ADMIN_TAB_ITEM,
  { value: "market", label: "Urunler", icon: "PRD" },
  { value: "profile", label: "Profil", icon: "PRF" },
];
const ORDER_STATUS_OPTIONS: OrderStatus[] = ["PENDING", "PREPARING", "ON_THE_WAY", "DELIVERED", "CANCELLED"];

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
  return "Indirimli urun";
}

export default function AppMain() {
  const sendScale = useRef(new Animated.Value(1)).current;
  const chatScrollRef = useRef<ScrollView | null>(null);

  const [sessionLoading, setSessionLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  const [authMode, setAuthMode] = useState<AuthScreenMode>("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [apiReachable, setApiReachable] = useState<boolean | null>(null);

  const [activeTab, setActiveTab] = useState<MainTab>("assistant");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastSyncAt, setLastSyncAt] = useState<string>("");

  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [ordersTotal, setOrdersTotal] = useState(0);
  const [adminOrders, setAdminOrders] = useState<Order[]>([]);
  const [adminOrdersTotal, setAdminOrdersTotal] = useState(0);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [adminAnalytics, setAdminAnalytics] = useState<AdminAnalytics | null>(null);
  const [busyOrderId, setBusyOrderId] = useState("");
  const [busyUserId, setBusyUserId] = useState("");
  const [favoritesTotal, setFavoritesTotal] = useState(0);
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [busyProductId, setBusyProductId] = useState("");
  const [productSaving, setProductSaving] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [adminProductName, setAdminProductName] = useState("");
  const [adminProductPrice, setAdminProductPrice] = useState("");
  const [adminProductStock, setAdminProductStock] = useState("");
  const [adminProductCategoryId, setAdminProductCategoryId] = useState("");
  const [adminProductImageUrl, setAdminProductImageUrl] = useState("");
  const [adminProductCampaign, setAdminProductCampaign] = useState(false);
  const [adminImageUploading, setAdminImageUploading] = useState(false);
  const [adminProductSearch, setAdminProductSearch] = useState("");
  const [adminProductDrafts, setAdminProductDrafts] = useState<Record<string, { name: string; price: string; stock: string }>>({});
  const [activeAdminModule, setActiveAdminModule] = useState<AdminModule>("home");
  const [adminNotificationTitle, setAdminNotificationTitle] = useState("");
  const [adminNotificationBody, setAdminNotificationBody] = useState("");
  const [notificationSaving, setNotificationSaving] = useState(false);

  const [aiInput, setAiInput] = useState("");
  const [aiMode, setAiMode] = useState<string>("normal");
  const [mealCategory, setMealCategory] = useState<(typeof MEAL_CATEGORIES)[number]>("Akşam Yemeği");
  const [budgetLimit, setBudgetLimit] = useState("");
  const [nutritionGoal, setNutritionGoal] = useState("Dengeli Beslenme");
  const [allergies, setAllergies] = useState("");
  const [preferredBrands, setPreferredBrands] = useState("");
  const [inventoryInput, setInventoryInput] = useState("");
  const [aiChatMessages, setAiChatMessages] = useState<ChatMessage[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiOutput, setAiOutput] = useState<AIResponse | null>(null);
  const [aiFeedback, setAiFeedback] = useState("");
  const [expandedFilters, setExpandedFilters] = useState(false);

  const cartCount = useMemo(
    () => (cart?.items ?? []).reduce((acc, item) => acc + item.quantity, 0),
    [cart]
  );

  const promotedProducts = useMemo(() => products.filter((product) => product.is_promoted), [products]);
  const lowStockProducts = useMemo(() => products.filter((product) => product.stock <= 5), [products]);
  const visibleTabItems = useMemo(() => {
    if (!user?.is_admin) return TAB_ITEMS;
    return ADMIN_TAB_ITEMS;
  }, [user?.is_admin]);
  const adminModuleCards = useMemo(
    () => [
      { id: "notifications" as const, title: "Bildirim Merkezi", subtitle: "Duyuru gonder", stat: "Manuel", icon: "DUY" },
      { id: "analytics" as const, title: "Analitik", subtitle: "Ciro ve performans", stat: `${adminAnalytics?.revenue_total?.toFixed(0) ?? 0} TL`, icon: "ANL" },
      { id: "users" as const, title: "Kullanici", subtitle: "Uyeleri yonet", stat: `${adminUsers.length} uye`, icon: "USR" },
      { id: "product-add" as const, title: "Urun Ekle", subtitle: "Yeni stok karti", stat: `${categories.length} kategori`, icon: "EKL" },
      { id: "products" as const, title: "Urun Yonetimi", subtitle: "Stok ve fiyat", stat: `${products.length} urun`, icon: "URN" },
      { id: "campaigns" as const, title: "Kampanya", subtitle: "3 Al 2 Ode", stat: `${promotedProducts.length} aktif`, icon: "KMP" },
      { id: "orders" as const, title: "Siparis Merkezi", subtitle: "Durum takip", stat: `${adminOrdersTotal} kayit`, icon: "SIP" },
      { id: "stock" as const, title: "Stok Uyarilari", subtitle: "Kritik urunler", stat: `${lowStockProducts.length} kritik`, icon: "STK" },
    ],
    [adminAnalytics?.revenue_total, adminOrdersTotal, adminUsers.length, categories.length, lowStockProducts.length, products.length, promotedProducts.length]
  );

  const displayedProducts = useMemo(() => {
    const byCategory =
      selectedCategoryId === "all"
        ? products
        : selectedCategoryId === DISCOUNT_CATEGORY_ID
        ? promotedProducts
        : products.filter((product) => product.category_id === selectedCategoryId);
    const q = searchQuery.trim().toLowerCase();
    if (!q) return byCategory;
    return byCategory.filter((product) => product.name.toLowerCase().includes(q));
  }, [products, promotedProducts, searchQuery, selectedCategoryId]);
  const adminManagedProducts = useMemo(() => {
    const q = adminProductSearch.trim().toLowerCase();
    if (!q) return products;
    return products.filter((product) => {
      const categoryName = categories.find((category) => category.id === product.category_id)?.name ?? "";
      return `${product.name} ${categoryName}`.toLowerCase().includes(q);
    });
  }, [adminProductSearch, categories, products]);

  const selectedModeLabel = useMemo(
    () => AI_MODE_OPTIONS.find((option) => option.value === aiMode)?.label ?? "Normal",
    [aiMode]
  );

  const aiProvider = aiOutput?.provider ?? "hazır";

  const aiMarketCartItems = useMemo<MarketCartItem[]>(
    () => (aiOutput ? extractMarketCartItems(aiOutput.response) : []),
    [aiOutput]
  );

  const composerDisabled = aiLoading || !aiInput.trim();

  function animateSendPressIn() {
    Animated.spring(sendScale, { toValue: 0.94, useNativeDriver: true }).start();
  }

  function animateSendPressOut() {
    Animated.spring(sendScale, { toValue: 1, useNativeDriver: true }).start();
  }

  async function restoreSession() {
    try {
      const storedToken = await SecureStore.getItemAsync(SESSION_TOKEN_KEY);
      let storedUser = await AsyncStorage.getItem(USER_KEY);
      if (!storedUser) {
        const legacyUser = await SecureStore.getItemAsync(USER_KEY);
        if (legacyUser) {
          await AsyncStorage.setItem(USER_KEY, legacyUser);
          await SecureStore.deleteItemAsync(USER_KEY);
          storedUser = legacyUser;
        }
      }
      if (storedToken && storedUser) {
        const parsedUser = JSON.parse(storedUser) as AuthUser;
        setToken(storedToken);
        setUser(parsedUser);
      }
    } finally {
      setSessionLoading(false);
    }
  }

  async function persistSession(accessToken: string, authUser: AuthUser) {
    await Promise.all([
      SecureStore.setItemAsync(SESSION_TOKEN_KEY, accessToken),
      AsyncStorage.setItem(USER_KEY, JSON.stringify(authUser)),
    ]);
    setToken(accessToken);
    setUser(authUser);
  }

  async function clearSession() {
    const userId = user?.id;
    const chatKey = userId ? chatStorageKey(userId) : null;
    await Promise.all([
      SecureStore.deleteItemAsync(SESSION_TOKEN_KEY),
      AsyncStorage.removeItem(USER_KEY),
      SecureStore.deleteItemAsync(USER_KEY).catch(() => undefined),
      chatKey ? AsyncStorage.removeItem(chatKey) : Promise.resolve(),
      chatKey ? SecureStore.deleteItemAsync(chatKey).catch(() => undefined) : Promise.resolve(),
    ]);
    setToken(null);
    setUser(null);
    setAiChatMessages([]);
    setAiOutput(null);
    setOrders([]);
    setAdminOrders([]);
    setAdminOrdersTotal(0);
    setCategories([]);
    setProducts([]);
    setCart(null);
    setFavoriteIds(new Set());
  }

  async function loadChatHistory(userId: string) {
    const key = chatStorageKey(userId);
    let raw = await AsyncStorage.getItem(key);
    if (!raw) {
      const legacy = await SecureStore.getItemAsync(key);
      if (legacy) {
        await AsyncStorage.setItem(key, legacy);
        await SecureStore.deleteItemAsync(key);
        raw = legacy;
      }
    }
    if (!raw) {
      setAiChatMessages([]);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as ChatMessage[];
      setAiChatMessages(Array.isArray(parsed) ? parsed.slice(-50) : []);
    } catch {
      setAiChatMessages([]);
    }
  }

  async function saveChatHistory(userId: string, messages: ChatMessage[]) {
    await AsyncStorage.setItem(chatStorageKey(userId), JSON.stringify(messages.slice(-50)));
  }

  async function checkApiReachability() {
    try {
      await api.get("/api/v1/health/");
      setApiReachable(true);
    } catch {
      setApiReachable(false);
    }
  }

  async function handleLogin() {
    try {
      setAuthLoading(true);
      setAuthError("");
      const { data } = await api.post<LoginResponse>("/api/v1/auth/login", {
        email: email.trim().toLowerCase(),
        password: password.trim(),
      });
      await persistSession(data.access_token, data.user);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        if (!err.response) {
          setAuthError(`Sunucuya bağlanılamadı. API: ${getApiBaseUrl()}`);
        } else if (err.response.status === 403 && err.response.data?.detail === "Email adresi henüz doğrulanmadı") {
          setAuthModeWithReset("verify");
          setAuthError("Giriş için e-posta doğrulaması gerekli.");
        } else {
          const detail = typeof err.response.data?.detail === "string" ? err.response.data.detail : "";
          setAuthError(detail || `Giriş başarısız (HTTP ${err.response.status}).`);
        }
      } else {
        setAuthError("Giriş sırasında beklenmeyen bir hata oluştu.");
      }
    } finally {
      setAuthLoading(false);
    }
  }

  function setAuthModeWithReset(next: AuthScreenMode) {
    setAuthMode(next);
    setAuthError("");
    if (next !== "register") {
      setConfirmPassword("");
    }
    if (next !== "verify") {
      setVerificationCode("");
    }
  }

  async function handleRegister() {
    const name = fullName.trim();
    const cleanEmail = email.trim().toLowerCase();
    const cleanPassword = password.trim();
    if (!name || !cleanEmail || !cleanPassword || !confirmPassword) {
      setAuthError("Lütfen tüm alanları doldurun.");
      return;
    }
    if (name.length < 2) {
      setAuthError("Ad en az 2 karakter olmalı.");
      return;
    }
    if (cleanPassword !== confirmPassword.trim()) {
      setAuthError("Şifreler eşleşmiyor.");
      return;
    }
    if (cleanPassword.length < 8) {
      setAuthError("Şifre en az 8 karakter olmalı.");
      return;
    }
    if (!/[A-Z]/.test(cleanPassword)) {
      setAuthError("Şifre en az bir büyük harf içermeli.");
      return;
    }
    if (!/[0-9]/.test(cleanPassword)) {
      setAuthError("Şifre en az bir rakam içermeli.");
      return;
    }
    try {
      setAuthLoading(true);
      setAuthError("");
      await api.post("/api/v1/auth/register", {
        full_name: name,
        email: cleanEmail,
        password: cleanPassword,
      });
      setAuthModeWithReset("verify");
      setVerificationCode("");
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        const detail = typeof err.response.data?.detail === "string" ? err.response.data.detail : "";
        setAuthError(detail || `Kayıt başarısız (HTTP ${err.response.status}).`);
      } else {
        setAuthError("Kayıt sırasında beklenmeyen bir hata oluştu.");
      }
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleVerifyEmail() {
    if (!verificationCode) {
      setAuthError("Lütfen kodu girin.");
      return;
    }
    try {
      setAuthLoading(true);
      setAuthError("");
      const { data } = await api.post<LoginResponse>("/api/v1/auth/verify-email", {
        email: email.trim().toLowerCase(),
        code: verificationCode,
      });
      await persistSession(data.access_token, data.user);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        const detail = typeof err.response.data?.detail === "string" ? err.response.data.detail : "";
        setAuthError(detail || "Doğrulama başarısız.");
      } else {
        setAuthError("Doğrulama sırasında hata oluştu.");
      }
    } finally {
      setAuthLoading(false);
    }
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
      const [productsRes, categoriesRes, cartRes, ordersRes, favoritesRes, adminOrdersRes, adminUsersRes, adminAnalyticsRes] = await Promise.allSettled([
        withRetry(() => fetchAllProducts(100), 2, 1000),
        withRetry(() => fetchAllCategories(100), 2, 1000),
        api.get<CartResponse>("/api/v1/cart"),
        api.get<OrdersResponse>("/api/v1/orders"),
        api.get<FavoritesResponse>("/api/v1/favorites"),
        user?.is_admin ? api.get<OrdersResponse>("/api/v1/orders/admin/all", { params: { limit: 100 } }) : Promise.resolve(null),
        user?.is_admin ? api.get<AdminUserListResponse>("/api/v1/admin/users", { params: { limit: 100 } }) : Promise.resolve(null),
        user?.is_admin ? api.get<AdminAnalytics>("/api/v1/admin/analytics") : Promise.resolve(null),
      ]);

      const settled = [productsRes, categoriesRes, cartRes, ordersRes, favoritesRes, adminOrdersRes, adminUsersRes, adminAnalyticsRes];
      const unauthorized = settled.find(
        (result) => result.status === "rejected" && isAxiosError(result.reason) && result.reason.response?.status === 401
      );
      if (unauthorized) {
        await clearSession();
        setError("Oturum süresi doldu. Tekrar giriş yapın.");
        return;
      }

      if (productsRes.status === "fulfilled") setProducts(productsRes.value);
      if (categoriesRes.status === "fulfilled") setCategories(categoriesRes.value);
      if (cartRes.status === "fulfilled") setCart(cartRes.value.data);
      if (ordersRes.status === "fulfilled") {
        setOrders(ordersRes.value.data.items ?? []);
        setOrdersTotal(ordersRes.value.data.total ?? 0);
      }
      if (favoritesRes.status === "fulfilled") {
        setFavoritesTotal(favoritesRes.value.data.total_count ?? 0);
        setFavoriteIds(new Set((favoritesRes.value.data.items ?? []).map((item) => item.id)));
      }
      if (adminOrdersRes.status === "fulfilled" && adminOrdersRes.value) {
        setAdminOrders(adminOrdersRes.value.data.items ?? []);
        setAdminOrdersTotal(adminOrdersRes.value.data.total ?? 0);
      }
      if (adminUsersRes.status === "fulfilled" && adminUsersRes.value) {
        setAdminUsers(adminUsersRes.value.data.items ?? []);
      }
      if (adminAnalyticsRes.status === "fulfilled" && adminAnalyticsRes.value) {
        setAdminAnalytics(adminAnalyticsRes.value.data);
      }
      setLastSyncAt(new Date().toLocaleTimeString("tr-TR"));
    } catch {
      setError("Dashboard verileri yüklenemedi.");
    } finally {
      setIsLoading(false);
    }
  }, [user?.is_admin]);

  async function addToCart(productId: string, quantity = 1) {
    try {
      setBusyProductId(productId);
      const { data } = await api.post<CartResponse>("/api/v1/cart/items", { product_id: productId, quantity });
      setCart(data);
    } catch {
      setError("Ürün sepete eklenemedi.");
    } finally {
      setBusyProductId("");
    }
  }

  async function updateCartItem(productId: string, quantity: number) {
    try {
      setBusyProductId(productId);
      const { data } = await api.put<CartResponse>(`/api/v1/cart/items/${productId}`, { quantity });
      setCart(data);
    } catch {
      setError("Sepet güncellenemedi.");
    } finally {
      setBusyProductId("");
    }
  }

  async function removeCartItem(productId: string) {
    try {
      setBusyProductId(productId);
      const { data } = await api.delete<CartResponse>(`/api/v1/cart/items/${productId}`);
      setCart(data);
    } catch {
      setError("Ürün sepetten çıkarılamadı.");
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
        setFavoriteIds(new Set((data.items ?? []).map((item) => item.id)));
      } else {
        const { data } = await api.post<FavoritesResponse>(`/api/v1/favorites/${productId}`);
        setFavoritesTotal(data.total_count ?? 0);
        setFavoriteIds(new Set((data.items ?? []).map((item) => item.id)));
      }
    } catch {
      setError("Favori işlemi başarısız.");
    } finally {
      setBusyProductId("");
    }
  }

  async function createOrderFromCart() {
    if (!cart?.items?.length) return;
    try {
      setCheckoutLoading(true);
      await api.post("/api/v1/orders", {
        delivery_address: DEFAULT_ADDRESS,
        payment_method: "CASH_ON_DELIVERY",
      });
      await fetchDashboardData();
      setActiveTab("cart");
    } catch {
      setError("Sipariş oluşturulamadı.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  async function updateAdminOrderStatus(orderId: string, status: OrderStatus) {
    try {
      setBusyOrderId(orderId);
      await api.put(`/api/v1/orders/${orderId}/status`, { status });
      await fetchDashboardData();
    } catch {
      setError("Siparis durumu guncellenemedi.");
    } finally {
      setBusyOrderId("");
    }
  }

  async function applyQuickCampaign(product: Product) {
    try {
      setBusyProductId(product.id);
      await api.put(`/api/v1/products/${product.id}`, {
        is_promoted: true,
        promotion_type: "buy_x_pay_y",
        promotion_label: "3 Al 2 Ode",
        promotion_buy_quantity: 3,
        promotion_pay_quantity: 2,
      });
      await fetchDashboardData();
    } catch {
      setError("Kampanya uygulanamadi.");
    } finally {
      setBusyProductId("");
    }
  }

  function getAdminProductDraft(product: Product) {
    return adminProductDrafts[product.id] ?? {
      name: product.name,
      price: String(product.price),
      stock: String(product.stock),
    };
  }

  function updateAdminProductDraft(product: Product, field: "name" | "price" | "stock", value: string) {
    setAdminProductDrafts((prev) => ({
      ...prev,
      [product.id]: {
        ...(prev[product.id] ?? {
          name: product.name,
          price: String(product.price),
          stock: String(product.stock),
        }),
        [field]: value,
      },
    }));
  }

  async function saveAdminProduct(product: Product) {
    const draft = getAdminProductDraft(product);
    const name = draft.name.trim();
    const price = Number(draft.price.replace(",", "."));
    const stock = Number(draft.stock);
    if (!name || Number.isNaN(price) || Number.isNaN(stock) || stock < 0 || price < 0) {
      setError("Urun adi, fiyat ve stok degerlerini kontrol et.");
      return;
    }
    try {
      setBusyProductId(product.id);
      await api.put(`/api/v1/products/${product.id}`, {
        name,
        price,
        stock,
      });
      setAdminProductDrafts((prev) => {
        const next = { ...prev };
        delete next[product.id];
        return next;
      });
      await fetchDashboardData();
    } catch {
      setError("Urun guncellenemedi.");
    } finally {
      setBusyProductId("");
    }
  }

  async function toggleAdminProductCampaign(product: Product) {
    try {
      setBusyProductId(product.id);
      if (product.is_promoted) {
        await api.put(`/api/v1/products/${product.id}`, {
          is_promoted: false,
          promotion_type: null,
          promotion_label: null,
          discounted_price: null,
          promotion_buy_quantity: null,
          promotion_pay_quantity: null,
        });
      } else {
        await api.put(`/api/v1/products/${product.id}`, {
          is_promoted: true,
          promotion_type: "buy_x_pay_y",
          promotion_label: "3 Al 2 Ode",
          promotion_buy_quantity: 3,
          promotion_pay_quantity: 2,
        });
      }
      await fetchDashboardData();
    } catch {
      setError("Kampanya durumu guncellenemedi.");
    } finally {
      setBusyProductId("");
    }
  }

  async function deactivateAdminProduct(product: Product) {
    try {
      setBusyProductId(product.id);
      await api.delete(`/api/v1/products/${product.id}`);
      await fetchDashboardData();
    } catch {
      setError("Urun pasife alinamadi.");
    } finally {
      setBusyProductId("");
    }
  }

  async function sendAdminNotification() {
    if (!adminNotificationTitle.trim() || !adminNotificationBody.trim()) {
      setError("Bildirim basligi ve mesaji gerekli.");
      return;
    }
    try {
      setNotificationSaving(true);
      await api.post("/api/v1/notifications/admin/broadcast", {
        title: adminNotificationTitle.trim(),
        body: adminNotificationBody.trim(),
        type: "announcement",
      });
      setAdminNotificationTitle("");
      setAdminNotificationBody("");
    } catch {
      setError("Bildirim gonderilemedi.");
    } finally {
      setNotificationSaving(false);
    }
  }

  async function updateAdminUserStatus(targetUser: AdminUser) {
    try {
      setBusyUserId(targetUser.id);
      await api.patch(`/api/v1/admin/users/${targetUser.id}/status`, {
        is_active: !targetUser.is_active,
      });
      await fetchDashboardData();
    } catch {
      setError("Kullanici durumu guncellenemedi.");
    } finally {
      setBusyUserId("");
    }
  }

  async function createAdminProduct() {
    const name = adminProductName.trim();
    const categoryId = adminProductCategoryId || categories[0]?.id || "";
    const price = Number(adminProductPrice.replace(",", "."));
    const stock = Number(adminProductStock);
    if (!name || !categoryId || Number.isNaN(price) || Number.isNaN(stock)) {
      setError("Urun adi, kategori, fiyat ve stok gerekli.");
      return;
    }
    try {
      setProductSaving(true);
      await api.post("/api/v1/products", {
        name,
        description: `${name} urunu`,
        price,
        stock,
        category_id: categoryId,
        image_url: adminProductImageUrl.trim() || undefined,
        unit: "adet",
        is_active: true,
        is_promoted: adminProductCampaign,
        promotion_type: adminProductCampaign ? "buy_x_pay_y" : undefined,
        promotion_label: adminProductCampaign ? "3 Al 2 Ode" : undefined,
        promotion_buy_quantity: adminProductCampaign ? 3 : undefined,
        promotion_pay_quantity: adminProductCampaign ? 2 : undefined,
      });
      setAdminProductName("");
      setAdminProductPrice("");
      setAdminProductStock("");
      setAdminProductImageUrl("");
      setAdminProductCampaign(false);
      await fetchDashboardData();
    } catch {
      setError("Urun eklenemedi.");
    } finally {
      setProductSaving(false);
    }
  }

  async function uploadAdminProductImage(source: "camera" | "library") {
    try {
      setError("");
      const permission =
        source === "camera"
          ? await ImagePicker.requestCameraPermissionsAsync()
          : await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permission.granted) {
        setError(source === "camera" ? "Kamera izni gerekli." : "Galeri izni gerekli.");
        return;
      }

      const result =
        source === "camera"
          ? await ImagePicker.launchCameraAsync({
              allowsEditing: true,
              aspect: [4, 3],
              quality: 0.82,
              mediaTypes: ["images"],
            })
          : await ImagePicker.launchImageLibraryAsync({
              allowsEditing: true,
              aspect: [4, 3],
              quality: 0.82,
              mediaTypes: ["images"],
            });

      if (result.canceled || !result.assets[0]) {
        return;
      }

      const asset = result.assets[0];
      const uriLower = asset.uri.toLowerCase();
      const mimeType =
        asset.mimeType ||
        (uriLower.endsWith(".png")
          ? "image/png"
          : uriLower.endsWith(".webp")
            ? "image/webp"
            : uriLower.endsWith(".heic")
              ? "image/heic"
              : uriLower.endsWith(".heif")
                ? "image/heif"
                : "image/jpeg");
      const extension = mimeType.split("/")[1] || "jpg";
      const rawFileName = asset.fileName || `product-${Date.now()}.${extension}`;
      const fileName = /\.[a-z0-9]+$/i.test(rawFileName) ? rawFileName : `${rawFileName}.${extension}`;
      const formData = new FormData();
      formData.append("file", {
        uri: asset.uri,
        name: fileName,
        type: mimeType,
      } as unknown as Blob);

      setAdminImageUploading(true);
      const uploadResponse = await fetch(`${getApiBaseUrl().replace(/\/$/, "")}/api/v1/uploads/image`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: formData,
      });
      const uploadData = await uploadResponse.json().catch(() => ({}));
      if (!uploadResponse.ok) {
        const detail = typeof uploadData.detail === "string" ? uploadData.detail : "";
        setError(detail ? `Gorsel yuklenemedi: ${detail}` : `Gorsel yuklenemedi (HTTP ${uploadResponse.status}).`);
        return;
      }
      if (typeof uploadData.image_url !== "string") {
        setError("Gorsel yuklendi ama sunucu URL dondurmedi.");
        return;
      }
      setAdminProductImageUrl(uploadData.image_url);
    } catch (err: unknown) {
      if (isAxiosError(err) && err.response) {
        const detail = typeof err.response.data?.detail === "string" ? err.response.data.detail : "";
        setError(detail ? `Gorsel yuklenemedi: ${detail}` : `Gorsel yuklenemedi (HTTP ${err.response.status}).`);
      } else {
        setError(`Gorsel yuklenemedi. API: ${getApiBaseUrl()}`);
      }
    } finally {
      setAdminImageUploading(false);
    }
  }

  /** Sepet yalnızca kullanıcı açıkça isterse; her normal mesajda zorunlu sepet LLM'i tarife zorluyordu. */
  function shouldAutoCreateCart(prompt: string): boolean {
    return aiMode !== "weekly" || isCartRequest(prompt);
  }

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

  function quickActionConfig(prompt: string) {
    if (prompt.startsWith("Ekonomik")) {
      return { mode: "budget", preferences: { meal_category: "Akşam Yemeği" } };
    }
    if (prompt.startsWith("Sporcu")) {
      return { mode: "diet", preferences: { goal: "high_protein", nutrition_goal: "high_protein" } };
    }
    return { mode: "inventory", preferences: {} };
  }

  async function runAIRequest(
    prompt: string,
    options?: {
      replaceLastAssistant?: boolean;
      modeOverride?: string;
      preferenceOverrides?: Record<string, unknown>;
    },
  ) {
    const userPrompt = prompt.trim();
    if (!userPrompt) return;
    const requestMode = options?.modeOverride || aiMode;
    const wantsCart = requestMode !== "weekly" && (requestMode !== "normal" || shouldAutoCreateCart(userPrompt));
    const availableIngredients = parseIngredientList(inventoryInput);
    const dietGoal = normalizeDietGoal(nutritionGoal);
    const lastMessage = aiChatMessages.length > 0 ? aiChatMessages[aiChatMessages.length - 1] : null;
    const contextMessages =
      options?.replaceLastAssistant && lastMessage?.role === "assistant"
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
        const prevLast = prev.length > 0 ? prev[prev.length - 1] : null;
        const base = options?.replaceLastAssistant && prevLast?.role === "assistant" ? prev.slice(0, -1) : prev;
        return [...base, userMessage];
      });

      const { data } = await api.post<AIResponse>("/api/v1/ai/generate", {
        mode: requestMode,
        input: userPrompt,
        preferences: {
          require_llm: true,
          include_market_cart: wantsCart,
          require_market_cart_from_llm: false,
          apply_to_cart: wantsCart,
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

      const assistantMessage: ChatMessage = {
        id: `${Date.now()}-assistant`,
        role: "assistant",
        content: buildAiNarrative(data),
      };
      setAiOutput(data);
      setAiChatMessages((prev) => [...prev, assistantMessage]);
      await fetchDashboardData();
      setAiFeedback(
        wantsCart
          ? `Yanıt hazırlandı (${data.provider ?? "LLM"}). Tarif malzemeleri sepete işlendi.`
          : `Yanıt hazırlandı (${data.provider ?? "LLM"}).`
      );
      setActiveTab("assistant");
      setError("");
    } catch (err) {
      if (isAxiosError(err)) {
        const detail = typeof err.response?.data?.detail === "string" ? err.response?.data?.detail : "";
        setError(detail ? `AI yanıtı alınamadı: ${detail}` : "AI yanıtı alınamadı.");
      } else {
        setError("AI yanıtı alınamadı.");
      }
    } finally {
      setAiLoading(false);
    }
  }

  async function clearAIChat() {
    setAiChatMessages([]);
    setAiOutput(null);
    setAiFeedback("");
    setAiInput("");
    if (user?.id) {
      await AsyncStorage.removeItem(chatStorageKey(user.id));
    }
  }

  async function refreshLastAIResponse() {
    if (aiLoading) return;
    const lastUserMessage = [...aiChatMessages].reverse().find((message) => message.role === "user");
    const prompt = lastUserMessage?.content || aiInput.trim();
    if (!prompt) return;
    await runAIRequest(prompt, { replaceLastAssistant: true });
  }

  useEffect(() => {
    void restoreSession();
    void checkApiReachability();
  }, []);

  useEffect(() => {
    if (!token) return;
    void fetchDashboardData();
  }, [token, fetchDashboardData]);

  useEffect(() => {
    if (!token) return;
    const timer = setInterval(() => {
      void fetchDashboardData();
    }, 20000);
    return () => clearInterval(timer);
  }, [token, fetchDashboardData]);

  useEffect(() => {
    if (!user?.id) return;
    void loadChatHistory(user.id);
  }, [user?.id]);

  useEffect(() => {
    if (user?.is_admin && (activeTab === "assistant" || activeTab === "cart")) {
      setActiveTab("admin");
      return;
    }
    if (!user?.is_admin && activeTab === "admin") {
      setActiveTab("assistant");
    }
  }, [activeTab, user?.is_admin]);

  useEffect(() => {
    if (!user?.id) return;
    void saveChatHistory(user.id, aiChatMessages);
    chatScrollRef.current?.scrollToEnd({ animated: true });
  }, [aiChatMessages, user?.id]);

  if (sessionLoading) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={palette.mint} />
      </SafeAreaView>
    );
  }

  if (!token || !user) {
    return (
      <>
        <StatusBar style="dark" />
        <AuthScreen
          authMode={authMode}
          setAuthMode={setAuthModeWithReset}
          fullName={fullName}
          setFullName={setFullName}
          email={email}
          setEmail={setEmail}
          password={password}
          setPassword={setPassword}
          confirmPassword={confirmPassword}
          setConfirmPassword={setConfirmPassword}
          verificationCode={verificationCode}
          setVerificationCode={setVerificationCode}
          authLoading={authLoading}
          authError={authError}
          apiReachable={apiReachable}
          onLogin={handleLogin}
          onRegister={handleRegister}
          onVerify={handleVerifyEmail}
          onClearError={() => setAuthError("")}
        />
      </>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <LinearGradient
        colors={["#F8FCFA", "#F4FAF7", "#F7FBF9"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFillObject}
      />

      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>{user.is_admin ? "CookWise Admin" : "CookWise AI"}</Text>
          <Text style={styles.subtitle}>{user.is_admin ? "Operasyon paneli" : `Hos geldin, ${user.full_name}`}</Text>
        </View>
        <View style={styles.headerRight}>
          <Pressable onPress={() => setActiveTab("profile")} style={styles.profileShortcut}>
            <Text style={styles.profileShortcutText}>{user.full_name?.charAt(0)?.toUpperCase() || "C"}</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.tabRow}>
        {visibleTabItems.map((tab) => (
          <Pressable
            key={tab.value}
            style={[styles.tabButton, activeTab === tab.value && styles.tabButtonActive]}
            onPress={() => setActiveTab(tab.value)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text style={[styles.tabText, activeTab === tab.value && styles.tabTextActive]}>{tab.label}</Text>
            {tab.value === "cart" && cartCount > 0 ? (
              <View style={styles.tabBadge}>
                <Text style={styles.tabBadgeText}>{cartCount}</Text>
              </View>
            ) : null}
          </Pressable>
        ))}
      </View>

      <View style={styles.contentWrap}>
        {activeTab === "assistant" ? (
          <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 160 }}>
            <LinearGradient
              colors={["#0B8D5C", "#17B67A", "#86E2CC"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.assistantHero}
            >
              <View style={styles.heroTextBlock}>
                <Text style={styles.heroEyebrow}>AI mutfak akisi</Text>
                <Text style={styles.heroTitle}>Tarif iste, sepet hazir olsun.</Text>
                <Text style={styles.heroBody}>
                  Mod, hedef ve ev envanterini kullanarak yanit ve alisveris listesini birlikte uretir.
                </Text>
              </View>
              <View style={styles.heroMetricRow}>
                <View style={styles.heroMetric}>
                  <Text style={styles.heroMetricValue}>{cartCount}</Text>
                  <Text style={styles.heroMetricLabel}>sepette</Text>
                </View>
                <View style={styles.heroMetric}>
                  <Text style={styles.heroMetricValue}>{aiMarketCartItems.length}</Text>
                  <Text style={styles.heroMetricLabel}>AI urunu</Text>
                </View>
                <View style={styles.heroMetric}>
                  <Text style={styles.heroMetricValue}>{selectedModeLabel}</Text>
                  <Text style={styles.heroMetricLabel}>mod</Text>
                </View>
              </View>
            </LinearGradient>

            <GlassCard>
              <View style={styles.aiHeaderRow}>
                <View>
                  <Text style={styles.sectionTitle}>AI Modu</Text>
                  <Text style={styles.sectionSubtitle}>Mod: {selectedModeLabel} • Sağlayıcı: {aiProvider}</Text>
                </View>
                <Pressable
                  style={styles.filterToggle}
                  onPress={() => setExpandedFilters((prev) => !prev)}
                >
                  <Text style={styles.filterToggleText}>{expandedFilters ? "Gizle" : "Ayarlar"}</Text>
                </Pressable>
              </View>
              <SegmentedControl options={AI_MODE_OPTIONS} value={aiMode} onChange={setAiMode} />
            </GlassCard>

            <GlassCard>
              <Text style={styles.sectionTitle}>Yemek Kategorisi</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
                {MEAL_CATEGORIES.map((category) => (
                  <Pressable
                    key={category}
                    style={[styles.cleanChip, mealCategory === category && styles.cleanChipActive]}
                    onPress={() => setMealCategory(category)}
                  >
                    <Text style={[styles.cleanChipText, mealCategory === category && styles.cleanChipTextActive]}>
                      {category}
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>
            </GlassCard>

            {expandedFilters ? (
              <GlassCard>
                <Text style={styles.sectionTitle}>Akıllı Kişiselleştirme</Text>
                <View style={styles.fieldGrid}>
                  <FormField
                    label="Bütçe"
                    placeholder="Örn. 300"
                    keyboardType="numeric"
                    value={budgetLimit}
                    onChangeText={setBudgetLimit}
                  />
                  <FormField
                    label="Beslenme Hedefi"
                    placeholder="Dengeli"
                    value={nutritionGoal}
                    onChangeText={setNutritionGoal}
                  />
                  <FormField
                    label="Alerjiler"
                    placeholder="Yok / Fındık"
                    value={allergies}
                    onChangeText={setAllergies}
                  />
                  <FormField
                    label="Marka Tercihleri"
                    placeholder="Örn. Torku"
                    value={preferredBrands}
                    onChangeText={setPreferredBrands}
                  />
                  <FormField
                    label="Ev Envanteri"
                    placeholder="Örn. 2 domates, 1 paket makarna"
                    value={inventoryInput}
                    onChangeText={setInventoryInput}
                  />
                </View>
              </GlassCard>
            ) : null}

            <GlassCard>
              <View style={styles.chatCardHeader}>
                <Text style={styles.chatCardIcon}>✨</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.sectionTitle}>CookWise Assistant</Text>
                  <Text style={styles.sectionSubtitle}>Tarif, öneri ve otomatik sepet yönetimi</Text>
                </View>
                <View style={styles.chatActions}>
                  <Pressable
                    onPress={() => void refreshLastAIResponse()}
                    disabled={aiLoading || (!aiInput.trim() && !aiChatMessages.some((message) => message.role === "user"))}
                    style={({ pressed }) => [
                      styles.chatActionButton,
                      pressed && styles.pressed,
                      (aiLoading || (!aiInput.trim() && !aiChatMessages.some((message) => message.role === "user"))) &&
                        styles.disabledButton,
                    ]}
                  >
                    <Text style={styles.chatActionText}>Yenile</Text>
                  </Pressable>
                  <Pressable
                    onPress={() => void clearAIChat()}
                    disabled={aiLoading || (aiChatMessages.length === 0 && !aiOutput && !aiInput)}
                    style={({ pressed }) => [
                      styles.chatActionButton,
                      styles.chatActionDanger,
                      pressed && styles.pressed,
                      (aiLoading || (aiChatMessages.length === 0 && !aiOutput && !aiInput)) && styles.disabledButton,
                    ]}
                  >
                    <Text style={[styles.chatActionText, styles.chatActionDangerText]}>Temizle</Text>
                  </Pressable>
                </View>
              </View>

              <LinearGradient
                colors={["#FAFDFC", "#F3FBF7"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.chatSurface}
              >
                <ScrollView
                  ref={chatScrollRef}
                  contentContainerStyle={styles.chatContent}
                  showsVerticalScrollIndicator={false}
                >
                  {aiChatMessages.length === 0 ? (
                    <View style={styles.emptyState}>
                      <Text style={styles.emptyStateTitle}>Bugün ne pişirelim?</Text>
                      <Text style={styles.emptyStateText}>
                        Bütçeni, hedefini veya evdeki malzemeleri yaz. Detaylı tarif ve market sepetini hazırlayalım.
                      </Text>
                    </View>
                  ) : (
                    aiChatMessages.map((message) => <ChatBubble key={message.id} message={message} />)
                  )}

                  {aiLoading ? (
                    <View style={styles.typingWrap}>
                      <View style={styles.typingDot} />
                      <View style={[styles.typingDot, { opacity: 0.65 }]} />
                      <View style={[styles.typingDot, { opacity: 0.4 }]} />
                      <Text style={styles.typingText}>AI düşünüyor...</Text>
                    </View>
                  ) : null}
                </ScrollView>
              </LinearGradient>

              {!!aiFeedback ? <Text style={styles.feedbackText}>{aiFeedback}</Text> : null}
            </GlassCard>

            <GlassCard>
              <Text style={styles.sectionTitle}>Hızlı Başlat</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
                {QUICK_ACTION_PROMPTS.map((prompt) => (
                  <Pressable
                    key={prompt}
                    style={styles.quickChip}
                    onPress={() => {
                      const action = quickActionConfig(prompt);
                      setAiMode(action.mode);
                      void runAIRequest(prompt, {
                        modeOverride: action.mode,
                        preferenceOverrides: action.preferences,
                      });
                    }}
                  >
                    <Text style={styles.quickChipText}>{prompt}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            </GlassCard>

            {aiMarketCartItems.length > 0 ? (
              <GlassCard>
                <View style={styles.suggestedHeader}>
                  <View>
                    <Text style={styles.sectionTitle}>AI Sepet Onerisi</Text>
                    <Text style={styles.sectionSubtitle}>Tarife gore eslesen stoktaki urunler</Text>
                  </View>
                  <Text style={styles.suggestedTotal}>
                    {aiMarketCartItems.reduce((sum, item) => sum + item.subtotal, 0).toFixed(2)} TL
                  </Text>
                </View>
                <View style={styles.suggestedList}>
                  {aiMarketCartItems.slice(0, 5).map((item) => (
                    <View key={item.product_id} style={styles.suggestedItem}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.suggestedName} numberOfLines={1}>{item.name}</Text>
                        <Text style={styles.suggestedMeta}>
                          {item.quantity} adet - {item.subtotal.toFixed(2)} TL
                        </Text>
                      </View>
                      <Pressable
                        style={[styles.suggestedAddButton, busyProductId === item.product_id && styles.disabledButton]}
                        onPress={() => void addToCart(item.product_id, item.quantity)}
                        disabled={busyProductId === item.product_id}
                      >
                        <Text style={styles.suggestedAddText}>Ekle</Text>
                      </Pressable>
                    </View>
                  ))}
                </View>
              </GlassCard>
            ) : null}
          </ScrollView>
        ) : null}

        {activeTab === "market" ? (
          <View style={{ flex: 1 }}>
            {selectedCategoryId === "all" ? (
              <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.marketCategoryScroll}>
                <GlassCard>
                  <View style={styles.marketHeader}>
                    <View>
                      <Text style={styles.sectionTitle}>Kategoriler</Text>
                      <Text style={styles.sectionSubtitle}>Alisverise baslamak icin bir kategori sec</Text>
                    </View>
                    <Text style={styles.marketCount}>{categories.length + 1} kategori</Text>
                  </View>
                </GlassCard>

                {isLoading ? (
                  <ActivityIndicator size="large" color={palette.mint} style={{ marginTop: 24 }} />
                ) : (
                  <View style={styles.categoryGrid}>
                    <Pressable
                      style={({ pressed }) => [styles.categoryTile, styles.discountCategoryTile, pressed && styles.pressed]}
                      onPress={() => {
                        setSelectedCategoryId(DISCOUNT_CATEGORY_ID);
                        setSearchQuery("");
                      }}
                    >
                      <View style={styles.categoryImageCard}>
                        <Image source={require("../assets/categories/kampanya.png")} style={styles.categoryCardImage} />
                        <View style={styles.categoryImageShade} />
                        <View style={styles.categoryImageTextWrap}>
                          <Text style={styles.categoryImageTitle} numberOfLines={2}>Indirimler</Text>
                          <Text style={styles.categoryImageMeta}>{promotedProducts.length} kampanyali urun</Text>
                        </View>
                      </View>
                    </Pressable>
                    {categories.map((category) => {
                      const count = products.filter((product) => product.category_id === category.id).length;
                      const categoryImage = getCategoryImageSource(category.slug || category.name);
                      return (
                        <Pressable
                          key={category.id}
                          style={({ pressed }) => [styles.categoryTile, categoryImage && styles.imageCategoryTile, pressed && styles.pressed]}
                          onPress={() => {
                            setSelectedCategoryId(category.id);
                            setSearchQuery("");
                          }}
                        >
                          {categoryImage ? (
                            <View style={styles.categoryImageCard}>
                              <Image source={categoryImage} style={styles.categoryCardImage} />
                              <View style={styles.categoryImageShade} />
                              <View style={styles.categoryImageTextWrap}>
                                <Text style={styles.categoryImageTitle} numberOfLines={2}>{category.name}</Text>
                                <Text style={styles.categoryImageMeta}>{count} urun</Text>
                              </View>
                            </View>
                          ) : (
                            <>
                              <View style={styles.categoryIconWrap}>
                                <Text style={styles.categoryIcon}>{getCategoryIcon(category.slug || category.name)}</Text>
                              </View>
                              <Text style={styles.categoryTitle} numberOfLines={2}>{category.name}</Text>
                              <Text style={styles.categoryMeta}>{count} urun</Text>
                            </>
                          )}
                        </Pressable>
                      );
                    })}
                  </View>
                )}
              </ScrollView>
            ) : (
              <>
            <GlassCard>
              <TextInput
                style={styles.searchInput}
                placeholder="Ürün ara..."
                placeholderTextColor="#98A2B3"
                value={searchQuery}
                onChangeText={setSearchQuery}
              />
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
                <Pressable
                  style={[styles.cleanChip, selectedCategoryId === "all" && styles.cleanChipActive]}
                  onPress={() => setSelectedCategoryId("all")}
                >
                  <Text style={[styles.cleanChipText, selectedCategoryId === "all" && styles.cleanChipTextActive]}>Tümü</Text>
                </Pressable>
                <Pressable
                  style={[styles.cleanChip, selectedCategoryId === DISCOUNT_CATEGORY_ID && styles.cleanChipActive]}
                  onPress={() => setSelectedCategoryId(DISCOUNT_CATEGORY_ID)}
                >
                  <Text style={[styles.cleanChipText, selectedCategoryId === DISCOUNT_CATEGORY_ID && styles.cleanChipTextActive]}>
                    Indirimler
                  </Text>
                </Pressable>
                {categories.map((category) => (
                  <Pressable
                    key={category.id}
                    style={[styles.cleanChip, selectedCategoryId === category.id && styles.cleanChipActive]}
                    onPress={() => setSelectedCategoryId(category.id)}
                  >
                    <Text style={[styles.cleanChipText, selectedCategoryId === category.id && styles.cleanChipTextActive]}>
                      {category.name}
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>
            </GlassCard>

            {isLoading ? (
              <ActivityIndicator size="large" color={palette.mint} style={{ marginTop: 24 }} />
            ) : (
              <FlatList
                data={displayedProducts}
                numColumns={user.is_admin ? 1 : 2}
                key={user.is_admin ? "admin-products" : "customer-products"}
                keyExtractor={(item) => item.id}
                contentContainerStyle={[styles.productList, user.is_admin && styles.adminProductList]}
                columnWrapperStyle={user.is_admin ? undefined : styles.productRow}
                ListEmptyComponent={
                  <View style={styles.emptyProducts}>
                    <Text style={styles.emptyCart}>Bu kategoride urun bulunamadi.</Text>
                  </View>
                }
                renderItem={({ item }) => (
                  <View style={styles.productCard}>
                    <Image source={{ uri: getProductImage(item.image_url) }} style={styles.productImage} resizeMode="cover" />
                    <Text style={styles.productName} numberOfLines={2}>
                      {item.name}
                    </Text>
                    {getPromotionLabel(item) ? (
                      <Text style={styles.promotionBadge} numberOfLines={1}>{getPromotionLabel(item)}</Text>
                    ) : null}
                    <View style={styles.productPriceRow}>
                      {getEffectiveProductPrice(item) < item.price ? (
                        <Text style={styles.productOriginalPrice}>{item.price.toFixed(2)} TL</Text>
                      ) : null}
                      <Text style={styles.productPrice}>{getEffectiveProductPrice(item).toFixed(2)} TL</Text>
                    </View>
                    <View style={styles.productActions}>
                      <Pressable
                        style={styles.favoriteButton}
                        onPress={() => void toggleFavorite(item.id)}
                        disabled={busyProductId === item.id}
                      >
                        <Text style={styles.favoriteButtonText}>{favoriteIds.has(item.id) ? "♥" : "♡"}</Text>
                      </Pressable>
                      <Pressable
                        style={styles.cartButton}
                        onPress={() => void addToCart(item.id)}
                        disabled={busyProductId === item.id}
                      >
                        <Text style={styles.cartButtonText}>{busyProductId === item.id ? "..." : "Sepete Ekle"}</Text>
                      </Pressable>
                    </View>
                  </View>
                )}
              />
            )}
              </>
            )}
          </View>
        ) : null}

        {activeTab === "cart" ? (
          <View style={{ flex: 1 }}>
            <GlassCard>
              <Text style={styles.cartTitle}>Sepet Toplamı</Text>
              <Text style={styles.cartAmount}>{(cart?.total_price ?? 0).toFixed(2)} TL</Text>
              <Text style={styles.syncText}>Son senkron: {lastSyncAt || "-"}</Text>
            </GlassCard>

            {!cart?.items?.length ? (
              <GlassCard>
                <Text style={styles.emptyCart}>Sepetin boş. AI ile tarif iste, malzemeler otomatik eklensin.</Text>
              </GlassCard>
            ) : (
              <ScrollView style={styles.cartList} showsVerticalScrollIndicator={false}>
                {cart.items.map((item) => (
                  <View key={item.product_id} style={styles.cartItemCard}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cartItemName} numberOfLines={1}>
                        {item.name}
                      </Text>
                      {item.promotion_label ? <Text style={styles.cartPromotionText}>{item.promotion_label}</Text> : null}
                      <Text style={styles.cartItemMeta}>{item.price.toFixed(2)} TL x {item.quantity}</Text>
                    </View>
                    <View style={styles.qtyRow}>
                      <Pressable
                        style={styles.qtyButton}
                        onPress={() =>
                          void (item.quantity <= 1 ? removeCartItem(item.product_id) : updateCartItem(item.product_id, item.quantity - 1))
                        }
                      >
                        <Text style={styles.qtyText}>-</Text>
                      </Pressable>
                      <Text style={styles.qtyValue}>{item.quantity}</Text>
                      <Pressable style={styles.qtyButton} onPress={() => void updateCartItem(item.product_id, item.quantity + 1)}>
                        <Text style={styles.qtyText}>+</Text>
                      </Pressable>
                    </View>
                  </View>
                ))}
              </ScrollView>
            )}

            <Pressable
              style={[styles.checkoutButton, (!cart?.items?.length || checkoutLoading) && { opacity: 0.65 }]}
              onPress={() => void createOrderFromCart()}
              disabled={!cart?.items?.length || checkoutLoading}
            >
              <Text style={styles.checkoutText}>{checkoutLoading ? "Sipariş hazırlanıyor..." : "Siparişi Tamamla"}</Text>
            </Pressable>
          </View>
        ) : null}

        {activeTab === "admin" && user.is_admin ? (
          <KeyboardAvoidingView
            behavior={Platform.OS === "ios" ? "padding" : "height"}
            keyboardVerticalOffset={Platform.OS === "ios" ? 88 : 0}
            style={styles.adminKeyboardWrap}
          >
          <ScrollView
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"}
            contentContainerStyle={styles.adminScrollContent}
          >
            <LinearGradient
              colors={["#14213D", "#0B8D5C"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.adminHero}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.adminEyebrow}>Yonetim Paneli</Text>
                <Text style={styles.adminTitle}>Modul sec, islemi rahat yonet.</Text>
                <Text style={styles.adminSubtitle}>Bildirim, urun, kampanya, stok ve siparis alanlari ayri acilir.</Text>
              </View>
              <Pressable style={styles.adminRefreshButton} onPress={() => void fetchDashboardData()}>
                <Text style={styles.adminRefreshText}>Yenile</Text>
              </Pressable>
            </LinearGradient>

            <View style={styles.adminStatsGrid}>
              <View style={styles.adminStatCard}>
                <Text style={styles.adminStatValue}>{adminOrdersTotal}</Text>
                <Text style={styles.adminStatLabel}>Toplam siparis</Text>
              </View>
              <View style={styles.adminStatCard}>
                <Text style={styles.adminStatValue}>{products.length}</Text>
                <Text style={styles.adminStatLabel}>Aktif urun</Text>
              </View>
              <View style={styles.adminStatCard}>
                <Text style={styles.adminStatValue}>{lowStockProducts.length}</Text>
                <Text style={styles.adminStatLabel}>Dusuk stok</Text>
              </View>
              <View style={styles.adminStatCard}>
                <Text style={styles.adminStatValue}>{promotedProducts.length}</Text>
                <Text style={styles.adminStatLabel}>Kampanya</Text>
              </View>
            </View>

            <GlassCard>
              <View style={styles.adminModuleHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.sectionTitle}>
                    {activeAdminModule === "home"
                      ? "Admin Ana Sayfa"
                      : adminModuleCards.find((item) => item.id === activeAdminModule)?.title}
                  </Text>
                  <Text style={styles.sectionSubtitle}>
                    {activeAdminModule === "home" ? "Islem kutularindan birini sec." : "Bu modul acik, islem bitince ana menuye donebilirsin."}
                  </Text>
                </View>
                {activeAdminModule !== "home" ? (
                  <Pressable style={styles.adminBackButton} onPress={() => setActiveAdminModule("home")}>
                    <Text style={styles.adminBackText}>Ana Menu</Text>
                  </Pressable>
                ) : null}
              </View>
              <View style={styles.adminModuleGrid}>
                {adminModuleCards.map((item) => (
                  <Pressable
                    key={item.id}
                    style={[styles.adminModuleCard, activeAdminModule === item.id && styles.adminModuleCardActive]}
                    onPress={() => setActiveAdminModule(item.id)}
                  >
                    <LinearGradient
                      colors={item.id === "campaigns" ? ["#F59E0B", "#F97316"] : item.id === "orders" ? ["#38BDF8", "#2563EB"] : item.id === "stock" ? ["#FB7185", "#EC4899"] : ["#16C47F", "#22D3EE"]}
                      start={{ x: 0, y: 0 }}
                      end={{ x: 1, y: 1 }}
                      style={styles.adminModuleIcon}
                    >
                      <Text style={styles.adminModuleIconText}>{item.icon}</Text>
                    </LinearGradient>
                    <Text style={styles.adminModuleTitle}>{item.title}</Text>
                    <Text style={styles.adminModuleSubtitle}>{item.subtitle}</Text>
                    <Text style={styles.adminModuleStat}>{item.stat}</Text>
                  </Pressable>
                ))}
              </View>
            </GlassCard>

            {activeAdminModule === "analytics" ? (
              <GlassCard>
                <Text style={styles.sectionTitle}>Analitik Dashboard</Text>
                <Text style={styles.sectionSubtitle}>Ciro, siparis ve performans ozeti.</Text>
                <View style={styles.adminStatsGrid}>
                  {[
                    ["Ciro", `${(adminAnalytics?.revenue_total ?? 0).toFixed(0)} TL`],
                    ["Siparis", String(adminAnalytics?.orders_total ?? adminOrdersTotal)],
                    ["Bekleyen", String(adminAnalytics?.pending_orders ?? 0)],
                    ["Kullanici", `${adminAnalytics?.active_users ?? 0}/${adminAnalytics?.users_total ?? adminUsers.length}`],
                    ["Urun", String(adminAnalytics?.products_total ?? products.length)],
                    ["Dusuk stok", String(adminAnalytics?.low_stock_products ?? lowStockProducts.length)],
                  ].map(([label, value]) => (
                    <View key={label} style={styles.adminStatCard}>
                      <Text style={styles.adminStatValue}>{value}</Text>
                      <Text style={styles.adminStatLabel}>{label}</Text>
                    </View>
                  ))}
                </View>
                <Text style={[styles.sectionSubtitle, { marginTop: 6 }]}>En cok satilanlar</Text>
                <View style={styles.adminList}>
                  {(adminAnalytics?.top_products ?? []).length === 0 ? (
                    <Text style={styles.emptyCart}>Henuz satis verisi yok.</Text>
                  ) : (
                    adminAnalytics?.top_products.map((item) => (
                      <View key={item.name} style={styles.adminProductRow}>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.adminProductName} numberOfLines={1}>{item.name}</Text>
                          <Text style={styles.adminProductMeta}>{item.quantity} adet</Text>
                        </View>
                        <Text style={styles.adminPriceText}>{item.revenue.toFixed(0)} TL</Text>
                      </View>
                    ))
                  )}
                </View>
              </GlassCard>
            ) : null}

            {activeAdminModule === "users" ? (
              <GlassCard>
                <Text style={styles.sectionTitle}>Kullanici Yonetimi</Text>
                <Text style={styles.sectionSubtitle}>{adminUsers.length} kullanici listeleniyor.</Text>
                <View style={styles.adminList}>
                  {adminUsers.map((item) => (
                    <View key={item.id} style={styles.adminProductRow}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.adminProductName} numberOfLines={1}>{item.full_name}</Text>
                        <Text style={styles.adminProductMeta} numberOfLines={1}>{item.email}</Text>
                        <Text style={styles.adminCampaignText}>{item.is_admin ? "Admin" : item.is_active ? "Aktif" : "Pasif"}</Text>
                      </View>
                      <Pressable
                        style={[styles.adminSmallButton, busyUserId === item.id && styles.disabledButton]}
                        disabled={busyUserId === item.id || item.id === user.id}
                        onPress={() => void updateAdminUserStatus(item)}
                      >
                        <Text style={styles.adminSmallButtonText}>{item.is_active ? "Pasife Al" : "Aktif Et"}</Text>
                      </Pressable>
                    </View>
                  ))}
                </View>
              </GlassCard>
            ) : null}

            {activeAdminModule === "notifications" ? (
              <GlassCard>
                <Text style={styles.sectionTitle}>Bildirim Merkezi</Text>
                <Text style={styles.sectionSubtitle}>Tum kullanicilarin bildirim kutusuna duyuru gonder.</Text>
                <View style={styles.adminForm}>
                  <TextInput
                    style={styles.adminInput}
                    placeholder="Baslik"
                    placeholderTextColor="#98A2B3"
                    value={adminNotificationTitle}
                    onChangeText={setAdminNotificationTitle}
                  />
                  <TextInput
                    style={[styles.adminInput, styles.adminTextArea]}
                    placeholder="Mesaj"
                    placeholderTextColor="#98A2B3"
                    value={adminNotificationBody}
                    onChangeText={setAdminNotificationBody}
                    multiline
                  />
                  <Pressable
                    style={[styles.adminCreateButton, notificationSaving && styles.disabledButton]}
                    disabled={notificationSaving}
                    onPress={() => void sendAdminNotification()}
                  >
                    <Text style={styles.adminCreateButtonText}>{notificationSaving ? "Gonderiliyor..." : "Bildirimi Gonder"}</Text>
                  </Pressable>
                </View>
              </GlassCard>
            ) : null}

            {activeAdminModule === "product-add" ? (
            <GlassCard>
              <Text style={styles.sectionTitle}>Urun Ekle</Text>
              <View style={styles.adminForm}>
                <TextInput
                  style={styles.adminInput}
                  placeholder="Urun adi"
                  placeholderTextColor="#98A2B3"
                  value={adminProductName}
                  onChangeText={setAdminProductName}
                />
                <View style={styles.adminFormRow}>
                  <TextInput
                    style={[styles.adminInput, { flex: 1 }]}
                    placeholder="Fiyat"
                    placeholderTextColor="#98A2B3"
                    value={adminProductPrice}
                    onChangeText={setAdminProductPrice}
                    keyboardType="numeric"
                  />
                  <TextInput
                    style={[styles.adminInput, { flex: 1 }]}
                    placeholder="Stok"
                    placeholderTextColor="#98A2B3"
                    value={adminProductStock}
                    onChangeText={setAdminProductStock}
                    keyboardType="numeric"
                  />
                </View>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.statusChipRow}>
                  {categories.map((category) => (
                    <Pressable
                      key={category.id}
                      style={[styles.statusChip, (adminProductCategoryId || categories[0]?.id) === category.id && styles.statusChipActive]}
                      onPress={() => setAdminProductCategoryId(category.id)}
                    >
                      <Text style={[styles.statusChipText, (adminProductCategoryId || categories[0]?.id) === category.id && styles.statusChipTextActive]}>
                        {category.name}
                      </Text>
                    </Pressable>
                  ))}
                </ScrollView>
                <TextInput
                  style={styles.adminInput}
                  placeholder="Gorsel URL opsiyonel"
                  placeholderTextColor="#98A2B3"
                  value={adminProductImageUrl}
                  onChangeText={setAdminProductImageUrl}
                />
                <View style={styles.adminImageActions}>
                  <Pressable
                    style={[styles.adminImageButton, adminImageUploading && styles.disabledButton]}
                    disabled={adminImageUploading}
                    onPress={() => void uploadAdminProductImage("camera")}
                  >
                    <Text style={styles.adminImageButtonText}>{adminImageUploading ? "Yukleniyor..." : "Kamera"}</Text>
                  </Pressable>
                  <Pressable
                    style={[styles.adminImageButton, adminImageUploading && styles.disabledButton]}
                    disabled={adminImageUploading}
                    onPress={() => void uploadAdminProductImage("library")}
                  >
                    <Text style={styles.adminImageButtonText}>Galeriden Sec</Text>
                  </Pressable>
                </View>
                {adminProductImageUrl ? (
                  <Image source={{ uri: adminProductImageUrl }} style={styles.adminImagePreview} resizeMode="cover" />
                ) : null}
                <View style={styles.adminFormRow}>
                  <Pressable
                    style={[styles.adminToggle, adminProductCampaign && styles.adminToggleActive]}
                    onPress={() => setAdminProductCampaign((prev) => !prev)}
                  >
                    <Text style={[styles.adminToggleText, adminProductCampaign && styles.adminToggleTextActive]}>
                      3 Al 2 Ode kampanyasi
                    </Text>
                  </Pressable>
                  <Pressable
                    style={[styles.adminCreateButton, productSaving && styles.disabledButton]}
                    disabled={productSaving}
                    onPress={() => void createAdminProduct()}
                  >
                    <Text style={styles.adminCreateButtonText}>{productSaving ? "Ekleniyor..." : "Urun Ekle"}</Text>
                  </Pressable>
                </View>
              </View>
            </GlassCard>
            ) : null}

            {activeAdminModule === "campaigns" ? (
            <GlassCard>
              <Text style={styles.sectionTitle}>Kampanya Yap</Text>
              <Text style={styles.sectionSubtitle}>Urunlere hizlica 3 Al 2 Ode kampanyasi uygula.</Text>
              <View style={styles.adminList}>
                {products.slice(0, 8).map((product) => (
                  <View key={product.id} style={styles.adminProductRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.adminProductName} numberOfLines={1}>{product.name}</Text>
                      <Text style={styles.adminProductMeta}>
                        {product.stock} stok - {product.price.toFixed(2)} TL
                      </Text>
                    </View>
                    <Pressable
                      style={[styles.adminSmallButton, busyProductId === product.id && styles.disabledButton]}
                      disabled={busyProductId === product.id}
                      onPress={() => void applyQuickCampaign(product)}
                    >
                      <Text style={styles.adminSmallButtonText}>{product.is_promoted ? "Guncelle" : "Kampanya"}</Text>
                    </Pressable>
                  </View>
                ))}
              </View>
            </GlassCard>
            ) : null}

            {activeAdminModule === "orders" ? (
            <GlassCard>
              <View style={styles.orderHeader}>
                <Text style={styles.sectionTitle}>Siparis Yonetimi</Text>
                <Text style={styles.sectionSubtitle}>{adminOrders.length} kayit</Text>
              </View>
              {adminOrders.length === 0 ? (
                <Text style={styles.emptyCart}>Henuz yonetilecek siparis yok.</Text>
              ) : (
                <View style={styles.adminList}>
                  {adminOrders.slice(0, 8).map((order) => (
                    <View key={order.id} style={styles.adminOrderCard}>
                      <View style={styles.adminOrderTop}>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.orderCode}>#{order.id.slice(-6).toUpperCase()}</Text>
                          <Text style={styles.orderMeta}>
                            {order.items.length} urun - {order.total_price.toFixed(2)} TL
                          </Text>
                        </View>
                        <Text style={styles.adminStatusPill}>{order.status}</Text>
                      </View>
                      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.statusChipRow}>
                        {ORDER_STATUS_OPTIONS.map((statusOption) => (
                          <Pressable
                            key={statusOption}
                            style={[
                              styles.statusChip,
                              order.status === statusOption && styles.statusChipActive,
                              busyOrderId === order.id && styles.disabledButton,
                            ]}
                            disabled={busyOrderId === order.id || order.status === statusOption}
                            onPress={() => void updateAdminOrderStatus(order.id, statusOption)}
                          >
                            <Text style={[styles.statusChipText, order.status === statusOption && styles.statusChipTextActive]}>
                              {statusOption}
                            </Text>
                          </Pressable>
                        ))}
                      </ScrollView>
                    </View>
                  ))}
                </View>
              )}
            </GlassCard>
            ) : null}

            {activeAdminModule === "stock" ? (
            <GlassCard>
              <Text style={styles.sectionTitle}>Stok Uyarilari</Text>
              {lowStockProducts.length === 0 ? (
                <Text style={[styles.emptyCart, { marginTop: 8 }]}>Dusuk stoklu urun yok.</Text>
              ) : (
                <View style={styles.adminList}>
                  {lowStockProducts.slice(0, 6).map((product) => (
                    <View key={product.id} style={styles.adminProductRow}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.adminProductName} numberOfLines={1}>{product.name}</Text>
                        <Text style={styles.adminProductMeta}>{product.stock} stok - {product.price.toFixed(2)} TL</Text>
                      </View>
                      <Pressable
                        style={[styles.adminSmallButton, busyProductId === product.id && styles.disabledButton]}
                        disabled={busyProductId === product.id}
                        onPress={() => void applyQuickCampaign(product)}
                      >
                        <Text style={styles.adminSmallButtonText}>3 Al 2 Ode</Text>
                      </Pressable>
                    </View>
                  ))}
                </View>
              )}
            </GlassCard>
            ) : null}

            {activeAdminModule === "products" ? (
              <GlassCard>
                <Text style={styles.sectionTitle}>Urun Yonetimi</Text>
                <Text style={styles.sectionSubtitle}>Fiyat, stok, kampanya ve aktiflik islemlerini buradan yonet.</Text>
                <TextInput
                  style={[styles.adminInput, styles.adminProductSearchInput]}
                  placeholder="Urun ara"
                  placeholderTextColor="#98A2B3"
                  value={adminProductSearch}
                  onChangeText={setAdminProductSearch}
                />
                <View style={styles.adminList}>
                  {adminManagedProducts.length === 0 ? (
                    <Text style={[styles.emptyCart, { marginTop: 8 }]}>Aramaya uygun urun bulunamadi.</Text>
                  ) : (
                    adminManagedProducts.slice(0, 30).map((product) => {
                      const draft = getAdminProductDraft(product);
                      const categoryName = categories.find((category) => category.id === product.category_id)?.name ?? "Kategori yok";
                      return (
                        <View key={product.id} style={styles.adminProductManageCard}>
                          <View style={styles.adminProductManageTop}>
                            <Image source={{ uri: getProductImage(product.image_url) }} style={styles.adminProductThumb} resizeMode="cover" />
                            <View style={{ flex: 1 }}>
                              <TextInput
                                style={styles.adminProductNameInput}
                                value={draft.name}
                                onChangeText={(value) => updateAdminProductDraft(product, "name", value)}
                                placeholder="Urun adi"
                                placeholderTextColor="#98A2B3"
                              />
                              <Text style={styles.adminProductMeta} numberOfLines={1}>{categoryName}</Text>
                              {product.is_promoted ? <Text style={styles.adminCampaignText}>{getPromotionLabel(product)}</Text> : null}
                            </View>
                          </View>
                          <View style={styles.adminProductEditRow}>
                            <View style={styles.adminProductEditField}>
                              <Text style={styles.adminProductFieldLabel}>Fiyat</Text>
                              <TextInput
                                style={styles.adminProductEditInput}
                                value={draft.price}
                                onChangeText={(value) => updateAdminProductDraft(product, "price", value)}
                                keyboardType="decimal-pad"
                              />
                            </View>
                            <View style={styles.adminProductEditField}>
                              <Text style={styles.adminProductFieldLabel}>Stok</Text>
                              <TextInput
                                style={styles.adminProductEditInput}
                                value={draft.stock}
                                onChangeText={(value) => updateAdminProductDraft(product, "stock", value.replace(/[^0-9]/g, ""))}
                                keyboardType="number-pad"
                              />
                            </View>
                            <View style={styles.adminProductEffectiveBox}>
                              <Text style={styles.adminProductFieldLabel}>Satis</Text>
                              <Text style={styles.adminPriceText}>{getEffectiveProductPrice(product).toFixed(2)} TL</Text>
                            </View>
                          </View>
                          <View style={styles.adminProductActionRow}>
                            <Pressable
                              style={[styles.adminSmallButton, busyProductId === product.id && styles.disabledButton]}
                              disabled={busyProductId === product.id}
                              onPress={() => void saveAdminProduct(product)}
                            >
                              <Text style={styles.adminSmallButtonText}>{busyProductId === product.id ? "..." : "Kaydet"}</Text>
                            </Pressable>
                            <Pressable
                              style={[styles.adminSmallButton, product.is_promoted && styles.adminDangerSoftButton, busyProductId === product.id && styles.disabledButton]}
                              disabled={busyProductId === product.id}
                              onPress={() => void toggleAdminProductCampaign(product)}
                            >
                              <Text style={[styles.adminSmallButtonText, product.is_promoted && styles.adminDangerSoftButtonText]}>
                                {product.is_promoted ? "Kampanyayi Kapat" : "3 Al 2 Ode"}
                              </Text>
                            </Pressable>
                            <Pressable
                              style={[styles.adminSmallButton, styles.adminDangerButton, busyProductId === product.id && styles.disabledButton]}
                              disabled={busyProductId === product.id}
                              onPress={() => void deactivateAdminProduct(product)}
                            >
                              <Text style={styles.adminDangerButtonText}>Pasife Al</Text>
                            </Pressable>
                          </View>
                        </View>
                      );
                    })
                  )}
                </View>
              </GlassCard>
            ) : null}

            {activeAdminModule === "campaigns" ? (
            <GlassCard>
              <Text style={styles.sectionTitle}>Kampanyalar</Text>
              {promotedProducts.length === 0 ? (
                <Text style={[styles.emptyCart, { marginTop: 8 }]}>Aktif kampanya yok.</Text>
              ) : (
                <View style={styles.adminList}>
                  {promotedProducts.slice(0, 6).map((product) => (
                    <View key={product.id} style={styles.adminProductRow}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.adminProductName} numberOfLines={1}>{product.name}</Text>
                        <Text style={styles.adminCampaignText}>{getPromotionLabel(product)}</Text>
                      </View>
                      <Text style={styles.adminPriceText}>{getEffectiveProductPrice(product).toFixed(2)} TL</Text>
                    </View>
                  ))}
                </View>
              )}
            </GlassCard>
            ) : null}
          </ScrollView>
          </KeyboardAvoidingView>
        ) : null}

        {activeTab === "profile" ? (
          <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 32 }}>
            <LinearGradient
              colors={["#102A43", "#0B8D5C"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.profileHero}
            >
              <View style={styles.avatarCircle}>
                <Text style={styles.avatarText}>{user.full_name?.charAt(0)?.toUpperCase() || "C"}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.profileName}>{user.full_name}</Text>
                <Text style={styles.profileEmail}>{user.email}</Text>
                <Text style={styles.profileBadge}>{user.is_admin ? "Admin hesap" : "CookWise kullanicisi"}</Text>
              </View>
            </LinearGradient>

            <View style={styles.profileGrid}>
              <View style={styles.profileMiniCard}>
                <Text style={styles.profileMiniValue}>{ordersTotal}</Text>
                <Text style={styles.profileMiniLabel}>Siparis</Text>
              </View>
              <View style={styles.profileMiniCard}>
                <Text style={styles.profileMiniValue}>{favoritesTotal}</Text>
                <Text style={styles.profileMiniLabel}>Favori</Text>
              </View>
              <View style={styles.profileMiniCard}>
                <Text style={styles.profileMiniValue}>{cartCount}</Text>
                <Text style={styles.profileMiniLabel}>Sepet</Text>
              </View>
            </View>

            <GlassCard>
              <Text style={styles.sectionTitle}>Teslimat ve Odeme</Text>
              <View style={styles.infoRow}>
                <Text style={styles.infoIcon}>📍</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.infoTitle}>Varsayilan adres</Text>
                  <Text style={styles.infoText}>{DEFAULT_ADDRESS}</Text>
                </View>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoIcon}>💳</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.infoTitle}>Odeme yontemi</Text>
                  <Text style={styles.infoText}>Kapida odeme</Text>
                </View>
              </View>
            </GlassCard>

            <GlassCard>
              <View style={styles.orderHeader}>
                <Text style={styles.sectionTitle}>Siparislerim</Text>
                <Pressable style={styles.orderRefresh} onPress={() => void fetchDashboardData()}>
                  <Text style={styles.orderRefreshText}>Yenile</Text>
                </Pressable>
              </View>
              {orders.length === 0 ? (
                <Text style={styles.emptyCart}>Henuz siparis yok. Sepetini tamamlayip ilk siparisini verebilirsin.</Text>
              ) : (
                <View style={styles.orderList}>
                  {orders.slice(0, 5).map((order) => (
                    <View key={order.id} style={styles.orderCard}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.orderCode}>#{order.id.slice(-6).toUpperCase()}</Text>
                        <Text style={styles.orderMeta}>
                          {order.items.length} urun - {new Date(order.created_at).toLocaleDateString("tr-TR")}
                        </Text>
                      </View>
                      <View style={{ alignItems: "flex-end" }}>
                        <Text style={styles.orderStatus}>{order.status}</Text>
                        <Text style={styles.orderTotal}>{order.total_price.toFixed(2)} TL</Text>
                      </View>
                    </View>
                  ))}
                </View>
              )}
            </GlassCard>

            <Pressable style={styles.profileLogoutButton} onPress={() => void clearSession()}>
              <Text style={styles.profileLogoutText}>Cikis Yap</Text>
            </Pressable>
          </ScrollView>
        ) : null}
      </View>

      {activeTab === "assistant" && !user.is_admin ? (
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
          style={styles.composerWrap}
        >
          <FloatingComposer
            value={aiInput}
            onChange={setAiInput}
            onSend={() => void runAIRequest(aiInput)}
            disabled={composerDisabled}
            scale={sendScale}
            onPressIn={animateSendPressIn}
            onPressOut={animateSendPressOut}
          />
        </KeyboardAvoidingView>
      ) : null}

      {!!error ? (
        <View style={styles.errorToast}>
          <Text style={styles.errorToastText}>{error}</Text>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

function FormField({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  keyboardType?: "default" | "numeric";
}) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        style={styles.fieldInput}
        placeholder={placeholder}
        placeholderTextColor="#98A2B3"
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
      />
    </View>
  );
}

function getCategoryIcon(value: string): string {
  const normalized = value
    .toLowerCase()
    .replaceAll("ı", "i")
    .replaceAll("ğ", "g")
    .replaceAll("ü", "u")
    .replaceAll("ş", "s")
    .replaceAll("ö", "o")
    .replaceAll("ç", "c");

  if (normalized.includes("meyve") || normalized.includes("sebze")) return "🥕";
  if (normalized.includes("sut") || normalized.includes("kahval")) return "🧀";
  if (normalized.includes("icecek")) return "🥤";
  if (normalized.includes("firin") || normalized.includes("pastane")) return "🥐";
  if (normalized.includes("meze") || normalized.includes("hazir") || normalized.includes("donuk")) return "❄️";
  if (normalized.includes("atistirmalik")) return "🍿";
  if (normalized.includes("bebek")) return "🍼";
  if (normalized.includes("temizlik") || normalized.includes("deterjan")) return "🧼";
  if (normalized.includes("kagit") || normalized.includes("mendil")) return "🧻";
  if (normalized.includes("kisisel") || normalized.includes("bakim") || normalized.includes("kozmetik")) return "🪥";
  if (normalized.includes("saglik")) return "💊";
  if (normalized.includes("evcil") || normalized.includes("hayvan")) return "🐾";
  if (normalized.includes("et-tavuk") || normalized.includes("tavuk") || normalized.includes("balik")) return "🍗";
  if (normalized === "et" || normalized.startsWith("et-") || normalized.includes("-et-")) return "🥩";
  return "🛒";
}

function getCategoryImageSource(value: string): ReturnType<typeof require> | null {
  const normalized = value.toLowerCase();
  return CATEGORY_IMAGE_SOURCES[normalized] ?? null;
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: palette.bg,
    paddingHorizontal: 12,
    paddingTop: 2,
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: palette.bg,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.82)",
    paddingHorizontal: 12,
    paddingVertical: 9,
    ...shadows.soft,
  },
  brand: {
    color: palette.mintDark,
    fontWeight: "800",
    fontSize: 14,
    letterSpacing: 0.5,
  },
  subtitle: {
    color: palette.textSecondary,
    marginTop: 2,
    fontSize: 12,
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  profileShortcut: {
    width: 34,
    height: 34,
    borderRadius: 999,
    backgroundColor: palette.mint,
    alignItems: "center",
    justifyContent: "center",
  },
  profileShortcutText: {
    color: "#fff",
    fontWeight: "900",
    fontSize: 14,
  },
  logoutChip: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: "#EAF7F1",
  },
  logout: {
    color: palette.mintDark,
    fontWeight: "700",
    fontSize: 12,
  },
  tabRow: {
    flexDirection: "row",
    gap: 6,
    marginBottom: 9,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.74)",
    padding: 5,
    ...shadows.soft,
  },
  tabButton: {
    flex: 1,
    borderRadius: 14,
    minHeight: 45,
    paddingVertical: 5,
    backgroundColor: "transparent",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  tabButtonActive: {
    backgroundColor: palette.mint,
    ...shadows.soft,
  },
  tabIcon: {
    fontSize: 14,
    marginBottom: 1,
  },
  tabText: {
    color: palette.mintDark,
    fontWeight: "700",
    fontSize: 10,
  },
  tabTextActive: {
    color: "#fff",
  },
  tabBadge: {
    position: "absolute",
    top: 5,
    right: 8,
    minWidth: 18,
    height: 18,
    borderRadius: 999,
    backgroundColor: "#F59E0B",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
  },
  tabBadgeText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "900",
  },
  contentWrap: {
    flex: 1,
    gap: 10,
  },
  adminKeyboardWrap: {
    flex: 1,
  },
  adminScrollContent: {
    paddingBottom: 220,
  },
  assistantHero: {
    borderRadius: 22,
    padding: 14,
    marginBottom: 10,
    ...shadows.card,
  },
  heroTextBlock: {
    maxWidth: "92%",
  },
  heroEyebrow: {
    color: "rgba(255,255,255,0.82)",
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  heroTitle: {
    marginTop: 4,
    color: "#fff",
    fontSize: 21,
    lineHeight: 25,
    fontWeight: "900",
  },
  heroBody: {
    marginTop: 6,
    color: "rgba(255,255,255,0.88)",
    fontSize: 13,
    lineHeight: 18,
  },
  heroMetricRow: {
    marginTop: 12,
    flexDirection: "row",
    gap: 8,
  },
  heroMetric: {
    flex: 1,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.18)",
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  heroMetricValue: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "900",
  },
  heroMetricLabel: {
    marginTop: 2,
    color: "rgba(255,255,255,0.78)",
    fontSize: 11,
    fontWeight: "700",
  },
  aiHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  sectionTitle: {
    color: palette.textPrimary,
    fontSize: 16,
    fontWeight: "700",
  },
  sectionSubtitle: {
    marginTop: 2,
    color: palette.textSecondary,
    fontSize: 12,
  },
  filterToggle: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: "#ECF8F1",
  },
  filterToggleText: {
    color: palette.mintDark,
    fontWeight: "700",
    fontSize: 12,
  },
  chipRow: {
    gap: 8,
    paddingTop: 8,
  },
  cleanChip: {
    borderRadius: 999,
    backgroundColor: palette.chipBg,
    paddingHorizontal: 13,
    paddingVertical: 8,
  },
  cleanChipActive: {
    backgroundColor: palette.mint,
    ...shadows.soft,
  },
  cleanChipText: {
    color: palette.mintDark,
    fontSize: 12,
    fontWeight: "600",
  },
  cleanChipTextActive: {
    color: "#fff",
  },
  fieldGrid: {
    gap: 10,
    marginTop: 8,
  },
  fieldWrap: {
    gap: 6,
  },
  fieldLabel: {
    color: palette.textSecondary,
    fontSize: 12,
    fontWeight: "600",
    paddingHorizontal: 2,
  },
  fieldInput: {
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.9)",
    minHeight: 44,
    paddingHorizontal: 12,
    color: palette.textPrimary,
    fontSize: 14,
  },
  chatCardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 10,
  },
  chatCardIcon: {
    fontSize: 18,
  },
  chatActions: {
    flexDirection: "row",
    gap: 6,
  },
  chatActionButton: {
    borderRadius: 999,
    backgroundColor: "#F0F8F3",
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: "rgba(34, 211, 238, 0.28)",
  },
  chatActionDanger: {
    backgroundColor: "#FFF5F5",
    borderColor: "rgba(251, 113, 133, 0.22)",
  },
  chatActionText: {
    color: palette.mintDark,
    fontSize: 11,
    fontWeight: "700",
  },
  chatActionDangerText: {
    color: "#be123c",
  },
  pressed: {
    opacity: 0.72,
  },
  disabledButton: {
    opacity: 0.45,
  },
  chatSurface: {
    borderRadius: 18,
    minHeight: 280,
    maxHeight: 380,
    overflow: "hidden",
  },
  chatContent: {
    padding: 12,
    gap: 8,
  },
  emptyState: {
    backgroundColor: "rgba(255,255,255,0.78)",
    borderRadius: 16,
    padding: 14,
  },
  emptyStateTitle: {
    color: palette.textPrimary,
    fontWeight: "700",
    fontSize: 15,
  },
  emptyStateText: {
    marginTop: 4,
    color: palette.textSecondary,
    fontSize: 13,
    lineHeight: 20,
  },
  typingWrap: {
    alignSelf: "flex-start",
    marginTop: 2,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.9)",
    paddingHorizontal: 10,
    paddingVertical: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  typingDot: {
    width: 7,
    height: 7,
    borderRadius: 999,
    backgroundColor: palette.mint,
  },
  typingText: {
    marginLeft: 4,
    color: palette.textSecondary,
    fontSize: 12,
  },
  feedbackText: {
    marginTop: 10,
    color: palette.mintDark,
    fontWeight: "600",
    fontSize: 12,
  },
  quickChip: {
    borderRadius: 999,
    backgroundColor: "#F0F8F3",
    paddingHorizontal: 13,
    paddingVertical: 8,
  },
  quickChipText: {
    color: "#2E4B3F",
    fontWeight: "600",
    fontSize: 12,
  },
  suggestedHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 10,
    marginBottom: 10,
  },
  suggestedTotal: {
    color: palette.mintDark,
    fontSize: 14,
    fontWeight: "900",
  },
  suggestedList: {
    gap: 8,
  },
  suggestedItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.88)",
    padding: 10,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
  },
  suggestedName: {
    color: palette.textPrimary,
    fontSize: 12.5,
    fontWeight: "800",
  },
  suggestedMeta: {
    marginTop: 3,
    color: palette.textSecondary,
    fontSize: 11.5,
    fontWeight: "600",
  },
  suggestedAddButton: {
    borderRadius: 999,
    backgroundColor: palette.mint,
    paddingHorizontal: 13,
    paddingVertical: 8,
  },
  suggestedAddText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 12,
  },
  composerWrap: {
    position: "absolute",
    left: 14,
    right: 14,
    bottom: 12,
  },
  marketCategoryScroll: {
    paddingBottom: 24,
  },
  marketHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  marketCount: {
    color: palette.mintDark,
    fontSize: 12,
    fontWeight: "900",
  },
  categoryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    paddingTop: 12,
    paddingBottom: 12,
  },
  categoryTile: {
    width: "47%",
    minHeight: 132,
    borderRadius: 22,
    backgroundColor: "rgba(255,255,255,0.96)",
    padding: 14,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
    ...shadows.soft,
  },
  discountCategoryTile: {
    backgroundColor: "#FFF7ED",
    borderColor: "rgba(245,158,11,0.22)",
    padding: 0,
    overflow: "hidden",
  },
  imageCategoryTile: {
    padding: 0,
    overflow: "hidden",
  },
  categoryIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 16,
    backgroundColor: "#ECF8F1",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
    position: "relative",
    overflow: "hidden",
  },
  discountIconWrap: {
    backgroundColor: "#FFEDD5",
  },
  categoryIcon: {
    fontSize: 23,
  },
  categoryImageOverlay: {
    position: "absolute",
    width: 34,
    height: 34,
    resizeMode: "contain",
    zIndex: 2,
  },
  categoryImageCard: {
    flex: 1,
    minHeight: 150,
    overflow: "hidden",
    borderRadius: 22,
  },
  categoryCardImage: {
    ...StyleSheet.absoluteFillObject,
    width: "100%",
    height: "100%",
    resizeMode: "cover",
  },
  categoryImageShade: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.12)",
  },
  categoryImageTextWrap: {
    position: "absolute",
    left: 10,
    bottom: 10,
    maxWidth: "76%",
    borderRadius: 13,
    backgroundColor: "rgba(255,255,255,0.90)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.72)",
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  categoryImageTitle: {
    color: palette.textPrimary,
    fontSize: 13.5,
    lineHeight: 17,
    fontWeight: "900",
  },
  categoryImageMeta: {
    marginTop: 4,
    color: "#B45309",
    fontSize: 10.5,
    fontWeight: "800",
  },
  categoryTitle: {
    color: palette.textPrimary,
    fontSize: 14,
    lineHeight: 18,
    fontWeight: "900",
    minHeight: 36,
  },
  categoryMeta: {
    marginTop: 8,
    color: palette.textSecondary,
    fontSize: 11.5,
    fontWeight: "700",
  },
  searchInput: {
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.88)",
    paddingHorizontal: 12,
    paddingVertical: 11,
    marginBottom: 8,
    fontSize: 14,
    color: palette.textPrimary,
  },
  productList: {
    paddingBottom: 20,
    gap: 10,
    paddingTop: 8,
  },
  adminProductList: {
    gap: 8,
  },
  productRow: {
    gap: 10,
  },
  emptyProducts: {
    padding: 16,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.86)",
  },
  productCard: {
    flex: 1,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.95)",
    padding: 10,
    ...shadows.soft,
  },
  productImage: {
    width: "100%",
    height: 108,
    borderRadius: 14,
    backgroundColor: "#F1F5F9",
  },
  productName: {
    marginTop: 8,
    minHeight: 36,
    color: palette.textPrimary,
    fontWeight: "700",
    fontSize: 12.5,
  },
  productPrice: {
    color: palette.mintDark,
    fontWeight: "800",
    fontSize: 14.5,
  },
  productPriceRow: {
    marginTop: 4,
    minHeight: 19,
    flexDirection: "row",
    alignItems: "baseline",
    gap: 6,
  },
  productOriginalPrice: {
    color: palette.textSecondary,
    fontSize: 11.5,
    fontWeight: "700",
    textDecorationLine: "line-through",
  },
  promotionBadge: {
    alignSelf: "flex-start",
    marginTop: 5,
    borderRadius: 999,
    backgroundColor: "#FEF3C7",
    color: "#92400E",
    overflow: "hidden",
    paddingHorizontal: 8,
    paddingVertical: 3,
    fontSize: 10.5,
    fontWeight: "900",
  },
  productActions: {
    marginTop: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 6,
  },
  favoriteButton: {
    width: 34,
    height: 32,
    borderRadius: 10,
    backgroundColor: "#FFF7ED",
    alignItems: "center",
    justifyContent: "center",
  },
  favoriteButtonText: {
    color: "#F59E0B",
    fontSize: 16,
  },
  cartButton: {
    flex: 1,
    borderRadius: 12,
    backgroundColor: palette.mint,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 9,
  },
  cartButtonText: {
    color: "#fff",
    fontSize: 11.5,
    fontWeight: "700",
  },
  cartTitle: {
    fontSize: 14,
    color: palette.textSecondary,
    fontWeight: "600",
  },
  cartAmount: {
    marginTop: 2,
    fontSize: 24,
    color: palette.textPrimary,
    fontWeight: "800",
  },
  syncText: {
    marginTop: 4,
    fontSize: 12,
    color: palette.textSecondary,
  },
  emptyCart: {
    fontSize: 13,
    color: palette.textSecondary,
    lineHeight: 20,
  },
  cartList: {
    marginTop: 10,
  },
  cartItemCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.95)",
    padding: 12,
    marginBottom: 8,
    ...shadows.soft,
  },
  cartItemName: {
    fontSize: 13.5,
    fontWeight: "700",
    color: palette.textPrimary,
  },
  cartItemMeta: {
    marginTop: 2,
    fontSize: 11.5,
    color: palette.textSecondary,
  },
  cartPromotionText: {
    alignSelf: "flex-start",
    marginTop: 4,
    borderRadius: 999,
    backgroundColor: "#FEF3C7",
    color: "#92400E",
    overflow: "hidden",
    paddingHorizontal: 7,
    paddingVertical: 2,
    fontSize: 10.5,
    fontWeight: "900",
  },
  qtyRow: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 999,
    backgroundColor: "#F2F6F4",
    paddingHorizontal: 4,
    paddingVertical: 2,
  },
  qtyButton: {
    width: 24,
    height: 24,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
  },
  qtyText: {
    fontWeight: "700",
    color: palette.textPrimary,
  },
  qtyValue: {
    minWidth: 20,
    textAlign: "center",
    fontWeight: "700",
    color: palette.textPrimary,
  },
  checkoutButton: {
    marginTop: 12,
    borderRadius: 18,
    backgroundColor: palette.mint,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    ...shadows.soft,
  },
  checkoutText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 14,
  },
  adminHero: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    borderRadius: 24,
    padding: 16,
    marginBottom: 12,
    ...shadows.card,
  },
  adminEyebrow: {
    color: "rgba(255,255,255,0.78)",
    fontSize: 11,
    fontWeight: "900",
    textTransform: "uppercase",
  },
  adminTitle: {
    marginTop: 5,
    color: "#fff",
    fontSize: 20,
    lineHeight: 24,
    fontWeight: "900",
  },
  adminSubtitle: {
    marginTop: 5,
    color: "rgba(255,255,255,0.82)",
    fontSize: 12,
    lineHeight: 17,
  },
  adminRefreshButton: {
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.18)",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  adminRefreshText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "900",
  },
  adminStatsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginBottom: 12,
  },
  adminModuleHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  adminBackButton: {
    borderRadius: 999,
    backgroundColor: "#ECFDF3",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  adminBackText: {
    color: palette.mintDark,
    fontSize: 11.5,
    fontWeight: "900",
  },
  adminModuleGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 14,
  },
  adminModuleCard: {
    width: "48%",
    minHeight: 154,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.9)",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.12)",
    padding: 12,
  },
  adminModuleCardActive: {
    borderColor: "rgba(34,211,238,0.65)",
    backgroundColor: "#F0FDFA",
  },
  adminModuleIcon: {
    width: 44,
    height: 44,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    ...shadows.soft,
  },
  adminModuleIconText: {
    color: "#fff",
    fontSize: 11,
    fontWeight: "900",
  },
  adminModuleTitle: {
    marginTop: 11,
    color: palette.textPrimary,
    fontSize: 13,
    fontWeight: "900",
  },
  adminModuleSubtitle: {
    marginTop: 4,
    color: palette.textSecondary,
    fontSize: 11,
    lineHeight: 15,
    fontWeight: "700",
  },
  adminModuleStat: {
    alignSelf: "flex-start",
    marginTop: 9,
    overflow: "hidden",
    borderRadius: 999,
    backgroundColor: "#ECFDF3",
    color: palette.mintDark,
    paddingHorizontal: 8,
    paddingVertical: 3,
    fontSize: 10.5,
    fontWeight: "900",
  },
  adminForm: {
    gap: 9,
    marginTop: 10,
  },
  adminFormRow: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
  },
  adminInput: {
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.9)",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.12)",
    paddingHorizontal: 12,
    paddingVertical: 11,
    color: palette.textPrimary,
    fontSize: 13,
    fontWeight: "700",
  },
  adminTextArea: {
    minHeight: 96,
    textAlignVertical: "top",
  },
  adminImageActions: {
    flexDirection: "row",
    gap: 8,
  },
  adminImageButton: {
    flex: 1,
    borderRadius: 14,
    backgroundColor: "#E0F7F1",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.18)",
    paddingHorizontal: 12,
    paddingVertical: 10,
    alignItems: "center",
  },
  adminImageButtonText: {
    color: palette.mintDark,
    fontSize: 12,
    fontWeight: "900",
  },
  adminImagePreview: {
    width: "100%",
    height: 150,
    borderRadius: 14,
    backgroundColor: "#F1F5F9",
  },
  adminToggle: {
    flex: 1,
    borderRadius: 999,
    backgroundColor: "#F2F6F4",
    paddingHorizontal: 12,
    paddingVertical: 10,
    alignItems: "center",
  },
  adminToggleActive: {
    backgroundColor: "#FEF3C7",
  },
  adminToggleText: {
    color: palette.textSecondary,
    fontSize: 11.5,
    fontWeight: "900",
  },
  adminToggleTextActive: {
    color: "#92400E",
  },
  adminCreateButton: {
    flex: 1,
    borderRadius: 999,
    backgroundColor: palette.mint,
    paddingHorizontal: 12,
    paddingVertical: 10,
    alignItems: "center",
  },
  adminCreateButtonText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "900",
  },
  adminStatCard: {
    width: "48%",
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.95)",
    padding: 12,
    ...shadows.soft,
  },
  adminStatValue: {
    color: palette.textPrimary,
    fontSize: 21,
    fontWeight: "900",
  },
  adminStatLabel: {
    marginTop: 3,
    color: palette.textSecondary,
    fontSize: 11.5,
    fontWeight: "800",
  },
  adminList: {
    gap: 8,
    marginTop: 10,
  },
  adminOrderCard: {
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.88)",
    padding: 11,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
  },
  adminOrderTop: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  adminStatusPill: {
    overflow: "hidden",
    borderRadius: 999,
    backgroundColor: "#ECF8F1",
    color: palette.mintDark,
    paddingHorizontal: 8,
    paddingVertical: 4,
    fontSize: 10.5,
    fontWeight: "900",
  },
  statusChipRow: {
    gap: 6,
    paddingTop: 10,
  },
  statusChip: {
    borderRadius: 999,
    backgroundColor: "#F2F6F4",
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  statusChipActive: {
    backgroundColor: palette.mint,
  },
  statusChipText: {
    color: palette.textSecondary,
    fontSize: 10.5,
    fontWeight: "900",
  },
  statusChipTextActive: {
    color: "#fff",
  },
  adminProductRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.88)",
    padding: 11,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
  },
  adminProductSearchInput: {
    marginTop: 10,
  },
  adminProductManageCard: {
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.9)",
    padding: 11,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
    gap: 10,
  },
  adminProductManageTop: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  adminProductThumb: {
    width: 54,
    height: 54,
    borderRadius: 12,
    backgroundColor: "#F1F5F9",
  },
  adminProductNameInput: {
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
    paddingHorizontal: 10,
    paddingVertical: 8,
    color: palette.textPrimary,
    fontSize: 12.5,
    fontWeight: "900",
  },
  adminProductEditRow: {
    flexDirection: "row",
    alignItems: "stretch",
    gap: 8,
  },
  adminProductEditField: {
    flex: 1,
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
    paddingHorizontal: 9,
    paddingVertical: 7,
  },
  adminProductEffectiveBox: {
    flex: 1,
    borderRadius: 12,
    backgroundColor: "#ECFDF3",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.12)",
    paddingHorizontal: 9,
    paddingVertical: 7,
    justifyContent: "center",
  },
  adminProductFieldLabel: {
    color: palette.textSecondary,
    fontSize: 10.5,
    fontWeight: "800",
  },
  adminProductEditInput: {
    marginTop: 3,
    color: palette.textPrimary,
    fontSize: 13,
    fontWeight: "900",
    padding: 0,
  },
  adminProductActionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  adminProductName: {
    color: palette.textPrimary,
    fontSize: 12.5,
    fontWeight: "900",
  },
  adminProductMeta: {
    marginTop: 3,
    color: palette.textSecondary,
    fontSize: 11,
    fontWeight: "700",
  },
  adminCampaignText: {
    alignSelf: "flex-start",
    marginTop: 4,
    borderRadius: 999,
    backgroundColor: "#FEF3C7",
    color: "#92400E",
    overflow: "hidden",
    paddingHorizontal: 7,
    paddingVertical: 2,
    fontSize: 10.5,
    fontWeight: "900",
  },
  adminSmallButton: {
    borderRadius: 999,
    backgroundColor: "#FEF3C7",
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  adminDangerSoftButton: {
    backgroundColor: "#FEE2E2",
  },
  adminDangerSoftButtonText: {
    color: "#B42318",
  },
  adminDangerButton: {
    backgroundColor: "#FFF1F3",
    borderWidth: 1,
    borderColor: "#FECDD3",
  },
  adminDangerButtonText: {
    color: "#BE123C",
    fontSize: 11,
    fontWeight: "900",
  },
  adminSmallButtonText: {
    color: "#92400E",
    fontSize: 11,
    fontWeight: "900",
  },
  adminPriceText: {
    color: palette.mintDark,
    fontSize: 12.5,
    fontWeight: "900",
  },
  profileHero: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    borderRadius: 26,
    padding: 16,
    marginBottom: 12,
    ...shadows.card,
  },
  avatarCircle: {
    width: 58,
    height: 58,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.22)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.32)",
  },
  avatarText: {
    color: "#fff",
    fontSize: 24,
    fontWeight: "900",
  },
  profileName: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "900",
  },
  profileEmail: {
    marginTop: 3,
    color: "rgba(255,255,255,0.82)",
    fontSize: 12,
    fontWeight: "600",
  },
  profileBadge: {
    alignSelf: "flex-start",
    marginTop: 8,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.20)",
    color: "#fff",
    overflow: "hidden",
    paddingHorizontal: 10,
    paddingVertical: 4,
    fontSize: 11,
    fontWeight: "800",
  },
  profileGrid: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 12,
  },
  profileMiniCard: {
    flex: 1,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.95)",
    padding: 12,
    ...shadows.soft,
  },
  profileMiniValue: {
    color: palette.textPrimary,
    fontSize: 19,
    fontWeight: "900",
  },
  profileMiniLabel: {
    marginTop: 3,
    color: palette.textSecondary,
    fontSize: 11,
    fontWeight: "700",
  },
  infoRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 12,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.78)",
    padding: 12,
  },
  infoIcon: {
    fontSize: 20,
  },
  infoTitle: {
    color: palette.textPrimary,
    fontWeight: "800",
    fontSize: 13,
  },
  infoText: {
    marginTop: 3,
    color: palette.textSecondary,
    fontSize: 12,
    lineHeight: 17,
  },
  orderHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  orderRefresh: {
    borderRadius: 999,
    backgroundColor: "#ECF8F1",
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  orderRefreshText: {
    color: palette.mintDark,
    fontWeight: "800",
    fontSize: 12,
  },
  orderList: {
    gap: 8,
  },
  orderCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 10,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.88)",
    padding: 12,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
  },
  orderCode: {
    color: palette.textPrimary,
    fontWeight: "900",
    fontSize: 13,
  },
  orderMeta: {
    marginTop: 3,
    color: palette.textSecondary,
    fontSize: 11.5,
    fontWeight: "600",
  },
  orderStatus: {
    color: palette.mintDark,
    fontWeight: "900",
    fontSize: 11,
  },
  orderTotal: {
    marginTop: 4,
    color: palette.textPrimary,
    fontWeight: "900",
    fontSize: 13,
  },
  profileLogoutButton: {
    marginTop: 12,
    borderRadius: 18,
    backgroundColor: palette.dangerBg,
    alignItems: "center",
    paddingVertical: 13,
  },
  profileLogoutText: {
    color: palette.dangerText,
    fontWeight: "900",
    fontSize: 14,
  },
  errorToast: {
    position: "absolute",
    left: 14,
    right: 14,
    bottom: 92,
    borderRadius: 16,
    backgroundColor: palette.dangerBg,
    paddingHorizontal: 12,
    paddingVertical: 10,
    ...shadows.soft,
  },
  errorToastText: {
    color: palette.dangerText,
    fontSize: 12,
    fontWeight: "600",
  },
});
