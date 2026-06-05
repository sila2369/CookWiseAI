"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { getApiErrorDetail } from "@/lib/errors";

type AdminTestResponse = {
  message: string;
  user_email: string;
};

type Category = {
  id: string;
  name: string;
  slug: string;
};

type CategoryListResponse = {
  items: Category[];
  total: number;
  skip: number;
  limit: number;
};

type Product = {
  id: string;
  name: string;
  slug: string;
  description: string;
  price: number;
  stock: number;
  category_id: string;
  brand?: string | null;
  unit?: string | null;
  image_url?: string | null;
  is_active: boolean;
  is_promoted?: boolean;
  promotion_type?: string | null;
  promotion_label?: string | null;
  discounted_price?: number | null;
  promotion_buy_quantity?: number | null;
  promotion_pay_quantity?: number | null;
};

type ProductListResponse = {
  items: Product[];
  total: number;
  skip: number;
  limit: number;
};

type OrderStatus = "PENDING" | "PREPARING" | "ON_THE_WAY" | "DELIVERED" | "CANCELLED";

type OrderItem = {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
};

type Order = {
  id: string;
  user_id: string;
  status: OrderStatus;
  items: OrderItem[];
  total_price: number;
  delivery_address: string;
  payment_method: string;
  created_at: string;
  updated_at: string;
};

type OrderListResponse = {
  items: Order[];
  total: number;
};

type AdminUser = {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  is_active: boolean;
  is_admin: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at?: string | null;
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

type ProductCreateForm = {
  name: string;
  slug: string;
  description: string;
  price: string;
  stock: string;
  category_id: string;
  brand: string;
  unit: string;
  image_url: string;
  is_promoted: boolean;
  promotion_type: string;
  promotion_label: string;
  discounted_price: string;
  promotion_buy_quantity: string;
  promotion_pay_quantity: string;
};

type CampaignForm = {
  product_id: string;
  promotion_type: "buy_x_pay_y" | "discount_price";
  promotion_label: string;
  discounted_price: string;
  promotion_buy_quantity: string;
  promotion_pay_quantity: string;
};

type ManualNotificationForm = {
  title: string;
  body: string;
  type: "announcement" | "campaign" | "stock" | "order";
};

type AdminModule = "home" | "analytics" | "users" | "notifications" | "product-add" | "products" | "campaigns" | "orders" | "stock";

const ORDER_STATUS_OPTIONS: OrderStatus[] = ["PENDING", "PREPARING", "ON_THE_WAY", "DELIVERED", "CANCELLED"];
const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  PENDING: "Bekliyor",
  PREPARING: "Hazirlaniyor",
  ON_THE_WAY: "Yolda",
  DELIVERED: "Teslim edildi",
  CANCELLED: "Iptal edildi",
};
const ORDER_STATUS_CLASSES: Record<OrderStatus, string> = {
  PENDING: "bg-amber-100 text-amber-800 border-amber-200",
  PREPARING: "bg-cyan-100 text-cyan-800 border-cyan-200",
  ON_THE_WAY: "bg-blue-100 text-blue-800 border-blue-200",
  DELIVERED: "bg-emerald-100 text-emerald-800 border-emerald-200",
  CANCELLED: "bg-rose-100 text-rose-800 border-rose-200",
};

const INITIAL_PRODUCT_FORM: ProductCreateForm = {
  name: "",
  slug: "",
  description: "",
  price: "",
  stock: "",
  category_id: "",
  brand: "",
  unit: "",
  image_url: "",
  is_promoted: false,
  promotion_type: "",
  promotion_label: "",
  discounted_price: "",
  promotion_buy_quantity: "",
  promotion_pay_quantity: "",
};

const INITIAL_CAMPAIGN_FORM: CampaignForm = {
  product_id: "",
  promotion_type: "buy_x_pay_y",
  promotion_label: "3 Al 2 Ode",
  discounted_price: "",
  promotion_buy_quantity: "3",
  promotion_pay_quantity: "2",
};

const INITIAL_NOTIFICATION_FORM: ManualNotificationForm = {
  title: "",
  body: "",
  type: "announcement",
};

const PANEL_CLASS =
  "rounded-[28px] border border-emerald-200/70 bg-white/78 p-5 shadow-[0_35px_80px_-55px_rgba(22,196,127,0.45)] backdrop-blur-2xl";
const FIELD_CLASS =
  "w-full rounded-2xl border border-emerald-200/70 bg-white/85 px-3 py-2.5 text-sm text-[#1F2937] outline-none transition placeholder:text-slate-400 focus:border-[#22D3EE]/70 focus:ring-2 focus:ring-[#22D3EE]/30";
const COMPACT_FIELD_CLASS =
  "rounded-xl border border-emerald-200/70 bg-white/85 px-2 py-1 text-sm text-[#1F2937] outline-none transition focus:border-[#22D3EE]/70 focus:ring-2 focus:ring-[#22D3EE]/30";
const PRIMARY_BUTTON_CLASS =
  "rounded-2xl bg-gradient-to-r from-[#16C47F] via-[#22D3EE] to-[#16C47F] px-4 py-2.5 text-sm font-semibold text-white shadow-[0_20px_40px_-24px_rgba(34,211,238,0.85)] transition hover:-translate-y-0.5 disabled:opacity-70";

function formatDateTime(value: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function AdminPage() {
  const router = useRouter();
  const { user, token, isReady, logout } = useAuth();
  const [adminCheck, setAdminCheck] = useState<AdminTestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [adminAnalytics, setAdminAnalytics] = useState<AdminAnalytics | null>(null);
  const [productForm, setProductForm] = useState<ProductCreateForm>(INITIAL_PRODUCT_FORM);
  const [campaignForm, setCampaignForm] = useState<CampaignForm>(INITIAL_CAMPAIGN_FORM);
  const [notificationForm, setNotificationForm] = useState<ManualNotificationForm>(INITIAL_NOTIFICATION_FORM);
  const [productSaving, setProductSaving] = useState(false);
  const [campaignSaving, setCampaignSaving] = useState(false);
  const [notificationSaving, setNotificationSaving] = useState(false);
  const [busyProductId, setBusyProductId] = useState("");
  const [busyOrderId, setBusyOrderId] = useState("");
  const [busyUserId, setBusyUserId] = useState("");
  const [userSearchQuery, setUserSearchQuery] = useState("");
  const [selectedProductCategoryId, setSelectedProductCategoryId] = useState("");
  const [selectedOrderFilter, setSelectedOrderFilter] = useState<OrderStatus | "ALL">("ALL");
  const [orderSearchQuery, setOrderSearchQuery] = useState("");
  const [selectedOrderStatus, setSelectedOrderStatus] = useState<Record<string, OrderStatus>>({});
  const [activeAdminModule, setActiveAdminModule] = useState<AdminModule>("home");

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
  const selectedCategoryProducts = useMemo(
    () =>
      products
        .filter((product) => product.category_id === selectedProductCategoryId)
        .sort((a, b) => a.name.localeCompare(b.name, "tr")),
    [products, selectedProductCategoryId]
  );
  const selectedProductCategoryName = categoryNameMap.get(selectedProductCategoryId) || "Kategori secin";
  const sortedProducts = useMemo(
    () => products.slice().sort((a, b) => a.name.localeCompare(b.name, "tr")),
    [products]
  );
  const activeCampaignProducts = useMemo(
    () => sortedProducts.filter((product) => product.is_promoted),
    [sortedProducts]
  );
  const lowStockProducts = useMemo(
    () => sortedProducts.filter((product) => product.stock <= 5),
    [sortedProducts]
  );
  const adminModuleCards = useMemo(
    () => [
      {
        id: "analytics" as const,
        title: "Analitik Dashboard",
        description: "Ciro, siparis, stok ve urun performansi",
        icon: "ANL",
        stat: `${adminAnalytics?.revenue_total?.toFixed(0) ?? 0} TL`,
        tone: "from-indigo-400 to-cyan-400",
      },
      {
        id: "users" as const,
        title: "Kullanici Yonetimi",
        description: "Uyeleri gor, aktif/pasif durumunu yonet",
        icon: "USR",
        stat: `${adminUsers.length} kullanici`,
        tone: "from-violet-400 to-fuchsia-400",
      },
      {
        id: "notifications" as const,
        title: "Bildirim Merkezi",
        description: "Duyuru ve kampanya bildirimi gonder",
        icon: "DUY",
        stat: "Manuel",
        tone: "from-cyan-400 to-emerald-400",
      },
      {
        id: "product-add" as const,
        title: "Urun Ekle",
        description: "Yeni stok karti olustur",
        icon: "EKL",
        stat: `${categories.length} kategori`,
        tone: "from-emerald-400 to-lime-400",
      },
      {
        id: "products" as const,
        title: "Urun Yonetimi",
        description: "Kategoriye gore fiyat, stok ve durum yonet",
        icon: "URN",
        stat: `${products.length} urun`,
        tone: "from-teal-400 to-cyan-400",
      },
      {
        id: "campaigns" as const,
        title: "Kampanya Merkezi",
        description: "Indirim ve 3 al 2 ode kurgula",
        icon: "KMP",
        stat: `${activeCampaignProducts.length} aktif`,
        tone: "from-amber-400 to-orange-400",
      },
      {
        id: "orders" as const,
        title: "Siparis Merkezi",
        description: "Siparis durumlarini takip et",
        icon: "SIP",
        stat: `${orders.length} siparis`,
        tone: "from-sky-400 to-blue-500",
      },
      {
        id: "stock" as const,
        title: "Stok Uyarilari",
        description: "Dusuk stoklu urunleri hizli gor",
        icon: "STK",
        stat: `${lowStockProducts.length} kritik`,
        tone: "from-rose-400 to-pink-400",
      },
    ],
    [activeCampaignProducts.length, adminAnalytics?.revenue_total, adminUsers.length, categories.length, lowStockProducts.length, orders.length, products.length]
  );
  const visibleAdminUsers = useMemo(() => {
    const q = userSearchQuery.trim().toLowerCase();
    if (!q) return adminUsers;
    return adminUsers.filter((item) =>
      item.full_name.toLowerCase().includes(q) ||
      item.email.toLowerCase().includes(q) ||
      (item.phone || "").toLowerCase().includes(q)
    );
  }, [adminUsers, userSearchQuery]);
  const selectedCampaignProduct = useMemo(
    () => products.find((product) => product.id === campaignForm.product_id) ?? null,
    [products, campaignForm.product_id]
  );
  const orderCountsByStatus = useMemo(() => {
    const counts = new Map<OrderStatus, number>();
    for (const status of ORDER_STATUS_OPTIONS) counts.set(status, 0);
    for (const order of orders) counts.set(order.status, (counts.get(order.status) ?? 0) + 1);
    return counts;
  }, [orders]);
  const visibleOrders = useMemo(() => {
    const normalized = orderSearchQuery.trim().toLowerCase();
    return orders.filter((order) => {
      const matchesStatus = selectedOrderFilter === "ALL" || order.status === selectedOrderFilter;
      const matchesSearch =
        !normalized ||
        order.id.toLowerCase().includes(normalized) ||
        order.user_id.toLowerCase().includes(normalized) ||
        order.delivery_address.toLowerCase().includes(normalized) ||
        order.items.some((item) => item.name.toLowerCase().includes(normalized));
      return matchesStatus && matchesSearch;
    });
  }, [orders, orderSearchQuery, selectedOrderFilter]);
  async function fetchAllCategories(limit = 100): Promise<Category[]> {
    let skip = 0;
    let total = 0;
    const items: Category[] = [];

    do {
      const response = await api.get<CategoryListResponse>("/api/v1/categories", { params: { limit, skip } });
      const pageItems = response.data.items ?? [];
      total = response.data.total ?? pageItems.length;
      items.push(...pageItems);
      skip += limit;
    } while (skip < total);

    return items;
  }

  async function fetchAllProducts(limit = 100): Promise<Product[]> {
    let skip = 0;
    let total = 0;
    const items: Product[] = [];

    do {
      const response = await api.get<ProductListResponse>("/api/v1/products", { params: { limit, skip } });
      const pageItems = response.data.items ?? [];
      total = response.data.total ?? pageItems.length;
      items.push(...pageItems);
      skip += limit;
    } while (skip < total);

    return items;
  }

  async function loadAdminPanelData() {
    const [adminRes, categoriesItems, productItems, ordersRes, usersRes, analyticsRes] = await Promise.all([
      api.get<AdminTestResponse>("/api/v1/admin/test"),
      fetchAllCategories(500),
      fetchAllProducts(500),
      api.get<OrderListResponse>("/api/v1/orders/admin/all", { params: { limit: 200 } }),
      api.get<AdminUserListResponse>("/api/v1/admin/users", { params: { limit: 200 } }),
      api.get<AdminAnalytics>("/api/v1/admin/analytics"),
    ]);

    setAdminCheck(adminRes.data);
    setCategories(categoriesItems);
    setProducts(productItems);
    setAdminUsers(usersRes.data.items ?? []);
    setAdminAnalytics(analyticsRes.data);
    const incomingOrders = ordersRes.data.items ?? [];
    setOrders(incomingOrders);
    setSelectedOrderStatus(
      incomingOrders.reduce<Record<string, OrderStatus>>((acc, order) => {
        acc[order.id] = order.status;
        return acc;
      }, {})
    );
  }

  useEffect(() => {
    if (!isReady) return;

    if (!token || !user) {
      router.push("/admin/login");
      return;
    }

    if (!user.is_admin) {
      router.push("/dashboard");
      return;
    }

    async function fetchAdminData() {
      try {
        setLoading(true);
        await loadAdminPanelData();
        setError("");
      } catch (err: unknown) {
        if (isAxiosError(err) && err.response?.status === 401) {
          setError("Oturum geçersiz. Lütfen tekrar giriş yapın.");
          logout();
          return;
        }
        if (isAxiosError(err) && err.response?.status === 403) {
          setError("Bu hesapta admin yetkisi bulunmuyor.");
          return;
        }
        setError(getApiErrorDetail(err, "Admin verileri alınamadı."));
      } finally {
        setLoading(false);
      }
    }

    void fetchAdminData();
  }, [isReady, logout, router, token, user]);

  useEffect(() => {
    if (!categories.length) {
      setSelectedProductCategoryId("");
      return;
    }
    const selectedExists = categories.some((category) => category.id === selectedProductCategoryId);
    if (!selectedProductCategoryId || !selectedExists) {
      setSelectedProductCategoryId(categories[0].id);
    }
  }, [categories, selectedProductCategoryId]);

  useEffect(() => {
    if (!sortedProducts.length) {
      setCampaignForm((prev) => ({ ...prev, product_id: "" }));
      return;
    }
    const selectedExists = sortedProducts.some((product) => product.id === campaignForm.product_id);
    if (!campaignForm.product_id || !selectedExists) {
      setCampaignForm((prev) => ({ ...prev, product_id: sortedProducts[0].id }));
    }
  }, [campaignForm.product_id, sortedProducts]);

  if (!isReady) return null;
  if (!token || !user || !user.is_admin) return null;

  async function handleCreateProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setProductSaving(true);
      setActionMessage("");
      await api.post("/api/v1/products", {
        name: productForm.name,
        slug: productForm.slug || undefined,
        description: productForm.description,
        price: Number(productForm.price),
        stock: Number(productForm.stock),
        category_id: productForm.category_id,
        brand: productForm.brand || undefined,
        unit: productForm.unit || undefined,
        image_url: productForm.image_url || undefined,
        is_promoted: productForm.is_promoted,
        promotion_type: productForm.is_promoted ? productForm.promotion_type || undefined : undefined,
        promotion_label:
          productForm.is_promoted
            ? productForm.promotion_label || (productForm.promotion_type === "discount_price" ? "Indirimli Urun" : "3 Al 2 Ode")
            : undefined,
        discounted_price:
          productForm.is_promoted && productForm.promotion_type === "discount_price" && productForm.discounted_price
            ? Number(productForm.discounted_price)
            : undefined,
        promotion_buy_quantity:
          productForm.is_promoted && productForm.promotion_type === "buy_x_pay_y"
            ? Number(productForm.promotion_buy_quantity || 3)
            : undefined,
        promotion_pay_quantity:
          productForm.is_promoted && productForm.promotion_type === "buy_x_pay_y"
            ? Number(productForm.promotion_pay_quantity || 2)
            : undefined,
        is_active: true,
      });
      await loadAdminPanelData();
      setProductForm(INITIAL_PRODUCT_FORM);
      setActionMessage("Ürün başarıyla eklendi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Ürün eklenemedi."));
    } finally {
      setProductSaving(false);
    }
  }

  async function handleUpdateProduct(productId: string, payload: Partial<Product>) {
    try {
      setBusyProductId(productId);
      setActionMessage("");
      await api.put(`/api/v1/products/${productId}`, payload);
      await loadAdminPanelData();
      setActionMessage("Ürün güncellendi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Ürün güncellenemedi."));
    } finally {
      setBusyProductId("");
    }
  }

  async function handleDeleteProduct(productId: string) {
    try {
      setBusyProductId(productId);
      setActionMessage("");
      await api.delete(`/api/v1/products/${productId}`);
      await loadAdminPanelData();
      setActionMessage("Ürün pasife alındı (soft delete).");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Ürün silinemedi."));
    } finally {
      setBusyProductId("");
    }
  }

  async function handleUpdateUserStatus(targetUser: AdminUser) {
    try {
      setBusyUserId(targetUser.id);
      setActionMessage("");
      await api.patch(`/api/v1/admin/users/${targetUser.id}/status`, {
        is_active: !targetUser.is_active,
      });
      await loadAdminPanelData();
      setActionMessage(targetUser.is_active ? "Kullanici pasife alindi." : "Kullanici aktif edildi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Kullanici durumu guncellenemedi."));
    } finally {
      setBusyUserId("");
    }
  }

  async function handleCreateCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!campaignForm.product_id) return;
    try {
      setCampaignSaving(true);
      setActionMessage("");
      const payload: Partial<Product> = {
        is_promoted: true,
        promotion_type: campaignForm.promotion_type,
        promotion_label:
          campaignForm.promotion_label ||
          (campaignForm.promotion_type === "discount_price" ? "Indirimli Urun" : "3 Al 2 Ode"),
      };
      if (campaignForm.promotion_type === "discount_price") {
        payload.discounted_price = campaignForm.discounted_price
          ? Number(campaignForm.discounted_price)
          : selectedCampaignProduct
            ? Number((selectedCampaignProduct.price * 0.85).toFixed(2))
            : 0;
        payload.promotion_buy_quantity = undefined;
        payload.promotion_pay_quantity = undefined;
      } else {
        payload.discounted_price = undefined;
        payload.promotion_buy_quantity = Number(campaignForm.promotion_buy_quantity || 3);
        payload.promotion_pay_quantity = Number(campaignForm.promotion_pay_quantity || 2);
      }
      await api.put(`/api/v1/products/${campaignForm.product_id}`, payload);
      await loadAdminPanelData();
      setActionMessage("Kampanya uygulandi ve kullanici bildirim kutusuna eklendi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Kampanya olusturulamadi."));
    } finally {
      setCampaignSaving(false);
    }
  }

  async function handleCreateCampaignForProduct(product: Product) {
    try {
      setBusyProductId(product.id);
      setActionMessage("");
      await api.put(`/api/v1/products/${product.id}`, {
        is_promoted: true,
        promotion_type: "buy_x_pay_y",
        promotion_label: "3 Al 2 Ode",
        discounted_price: undefined,
        promotion_buy_quantity: 3,
        promotion_pay_quantity: 2,
      });
      await loadAdminPanelData();
      setActionMessage("Kampanya uygulandi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Kampanya uygulanamadi."));
    } finally {
      setBusyProductId("");
    }
  }

  async function handleRemoveCampaign(productId: string) {
    try {
      setBusyProductId(productId);
      setActionMessage("");
      await api.put(`/api/v1/products/${productId}`, {
        is_promoted: false,
        promotion_type: "",
        promotion_label: "",
      });
      await loadAdminPanelData();
      setActionMessage("Kampanya kaldirildi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Kampanya kaldirilamadi."));
    } finally {
      setBusyProductId("");
    }
  }

  async function handleSendManualNotification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setNotificationSaving(true);
      setActionMessage("");
      await api.post("/api/v1/notifications/admin/broadcast", {
        title: notificationForm.title,
        body: notificationForm.body,
        type: notificationForm.type,
      });
      setNotificationForm(INITIAL_NOTIFICATION_FORM);
      setActionMessage("Bildirim tum kullanicilarin bildirim kutusuna gonderildi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Bildirim gonderilemedi."));
    } finally {
      setNotificationSaving(false);
    }
  }

  async function handleUpdateOrderStatus(orderId: string) {
    const status = selectedOrderStatus[orderId];
    if (!status) return;
    try {
      setBusyOrderId(orderId);
      setActionMessage("");
      await api.put(`/api/v1/orders/${orderId}/status`, { status });
      await loadAdminPanelData();
      setActionMessage("Sipariş durumu güncellendi.");
    } catch (err: unknown) {
      setError(getApiErrorDetail(err, "Sipariş durumu güncellenemedi."));
    } finally {
      setBusyOrderId("");
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#F4FFF8] p-4 pb-16 text-[#1F2937] md:p-8">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-emerald-300/30 blur-3xl" />
        <div className="absolute right-0 top-10 h-[28rem] w-[28rem] rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="absolute bottom-[-8rem] left-[30%] h-80 w-80 rounded-full bg-amber-200/25 blur-3xl" />
      </div>
      <div className="relative z-10 mx-auto max-w-7xl">
        <header className="overflow-hidden rounded-[34px] border border-emerald-200/70 bg-white/72 p-6 shadow-[0_45px_120px_-56px_rgba(22,196,127,0.35)] backdrop-blur-2xl md:p-7 flex flex-col md:flex-row md:items-center md:justify-between gap-5">
          <div>
            <div className="mb-4 inline-flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-[#16C47F] to-[#22D3EE] text-xs font-black text-white shadow-[0_18px_34px_-20px_rgba(34,211,238,0.8)]">
                CW
              </span>
              <span className="rounded-full border border-emerald-200/70 bg-emerald-50/80 px-3 py-1 text-[11px] font-medium text-emerald-700">
                Admin Console
              </span>
            </div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#0ea5b7]">CookWise Yonetim</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[#1F2937] md:text-4xl">Operasyon modullerini secerek yonet.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Bildirim, urun, kampanya, stok ve siparis islemlerini ayri alanlarda daha rahat takip et.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/dashboard"
              className="rounded-2xl border border-emerald-200/80 bg-white/80 px-4 py-2.5 text-sm font-semibold text-[#0f766e] shadow-sm transition hover:bg-emerald-50"
            >
              Kullanıcı Paneli
            </Link>
            <button
              onClick={logout}
              className={PRIMARY_BUTTON_CLASS}
            >
              Çıkış Yap
            </button>
          </div>
        </header>

        <section className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-4">
          <article className="rounded-3xl border border-emerald-200/70 bg-white/75 p-5 shadow-sm backdrop-blur-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Rol</p>
            <p className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-[#1F2937]">Admin</p>
          </article>
          <article className="rounded-3xl border border-emerald-200/70 bg-white/75 p-5 shadow-sm backdrop-blur-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">E-posta</p>
            <p className="mt-2 break-all text-lg font-semibold tracking-[-0.02em] text-[#1F2937]">{user.email}</p>
          </article>
          <article className="rounded-3xl border border-emerald-200/70 bg-white/75 p-5 shadow-sm backdrop-blur-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Durum</p>
            <p className="mt-2 text-lg font-semibold tracking-[-0.02em] text-[#1F2937]">
              {loading ? "Kontrol ediliyor..." : adminCheck ? "Yetki Doğrulandı" : "Bekleniyor"}
            </p>
          </article>
          <article className="rounded-3xl border border-emerald-200/70 bg-white/75 p-5 shadow-sm backdrop-blur-xl">
            <p className="text-xs text-[#436d58]">Operasyon Özeti</p>
            <p className="text-sm mt-1">Ürün: {products.length}</p>
            <p className="text-sm">Sipariş: {orders.length}</p>
          </article>
        </section>

        {actionMessage && (
          <div className="mt-5 rounded-2xl border border-emerald-200/70 bg-emerald-50/90 px-4 py-3 text-sm font-medium text-emerald-800 shadow-sm backdrop-blur-xl">
            {actionMessage}
          </div>
        )}

        <section className={`mt-5 ${PANEL_CLASS}`}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0ea5b7]">Admin Ana Sayfa</p>
              <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-[#1F2937]">
                {activeAdminModule === "home"
                  ? "Yapmak istedigin islemi sec"
                  : adminModuleCards.find((card) => card.id === activeAdminModule)?.title}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {activeAdminModule === "home"
                  ? "Her modulu ayri acarak ekran kalabaligini azalt."
                  : "Bu modulde isini bitirince ana menuden baska bir alana gecebilirsin."}
              </p>
            </div>
            {activeAdminModule !== "home" ? (
              <button
                type="button"
                onClick={() => setActiveAdminModule("home")}
                className="w-fit rounded-2xl border border-emerald-200/80 bg-white/85 px-4 py-2.5 text-sm font-semibold text-[#0f766e] shadow-sm transition hover:bg-emerald-50"
              >
                Ana Menu
              </button>
            ) : null}
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
            {adminModuleCards.map((card) => (
              <button
                key={card.id}
                type="button"
                onClick={() => setActiveAdminModule(card.id)}
                className={`group min-h-[150px] rounded-[26px] border p-4 text-left shadow-sm backdrop-blur-xl transition hover:-translate-y-1 ${
                  activeAdminModule === card.id
                    ? "border-emerald-300 bg-white shadow-[0_26px_55px_-36px_rgba(22,196,127,0.95)]"
                    : "border-emerald-200/70 bg-white/72 hover:border-cyan-200"
                }`}
              >
                <span className={`grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br ${card.tone} text-xs font-black text-white shadow-lg`}>
                  {card.icon}
                </span>
                <span className="mt-4 block text-sm font-bold text-[#1F2937]">{card.title}</span>
                <span className="mt-1 block text-xs leading-5 text-slate-500">{card.description}</span>
                <span className="mt-3 inline-flex rounded-full border border-emerald-100 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-800">
                  {card.stat}
                </span>
              </button>
            ))}
          </div>
        </section>

        {activeAdminModule === "analytics" && (
          <section className={`mt-5 ${PANEL_CLASS}`}>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0ea5b7]">Analitik Dashboard</p>
                <h2 className="mt-1 text-lg font-semibold">Operasyon ozeti</h2>
                <p className="mt-1 text-xs text-[#3f6d56]">Ciro, siparis, kullanici ve urun performansini tek bakista gor.</p>
              </div>
              <button type="button" onClick={() => void loadAdminPanelData()} className="w-fit rounded-2xl border border-emerald-200/80 bg-white/85 px-4 py-2 text-sm font-semibold text-[#0f766e]">
                Yenile
              </button>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-4">
              {[
                ["Toplam Ciro", `${(adminAnalytics?.revenue_total ?? 0).toFixed(2)} TL`],
                ["Toplam Siparis", String(adminAnalytics?.orders_total ?? orders.length)],
                ["Bekleyen Siparis", String(adminAnalytics?.pending_orders ?? 0)],
                ["Aktif Kullanici", `${adminAnalytics?.active_users ?? 0}/${adminAnalytics?.users_total ?? adminUsers.length}`],
                ["Aktif Urun", String(adminAnalytics?.products_total ?? products.length)],
                ["Dusuk Stok", String(adminAnalytics?.low_stock_products ?? lowStockProducts.length)],
                ["Kampanya", String(adminAnalytics?.active_campaigns ?? activeCampaignProducts.length)],
                ["Sepet Ortalama", `${adminAnalytics?.orders_total ? ((adminAnalytics.revenue_total ?? 0) / adminAnalytics.orders_total).toFixed(2) : "0.00"} TL`],
              ].map(([label, value]) => (
                <article key={label} className="rounded-3xl border border-emerald-200/70 bg-white/70 p-4 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p>
                  <p className="mt-2 text-2xl font-bold tracking-[-0.03em] text-[#1F2937]">{value}</p>
                </article>
              ))}
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <div className="rounded-3xl border border-cyan-200/70 bg-cyan-50/55 p-4">
                <h3 className="text-sm font-semibold text-[#0f766e]">En cok satilan urunler</h3>
                <div className="mt-3 space-y-2">
                  {(adminAnalytics?.top_products ?? []).length === 0 ? (
                    <p className="rounded-2xl bg-white/75 p-3 text-xs text-slate-500">Henuz satis verisi yok.</p>
                  ) : (
                    adminAnalytics?.top_products.map((item) => (
                      <div key={item.name} className="rounded-2xl bg-white/80 p-3 text-sm">
                        <div className="flex items-start justify-between gap-3">
                          <p className="font-semibold text-[#1F2937]">{item.name}</p>
                          <span className="text-xs font-bold text-[#16C47F]">{item.quantity} adet</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">{item.revenue.toFixed(2)} TL ciro</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
              <div className="rounded-3xl border border-emerald-200/70 bg-emerald-50/55 p-4">
                <h3 className="text-sm font-semibold text-[#0f766e]">Siparis durum dagilimi</h3>
                <div className="mt-3 space-y-2">
                  {(adminAnalytics?.orders_by_status ?? []).length === 0 ? (
                    <p className="rounded-2xl bg-white/75 p-3 text-xs text-slate-500">Henuz siparis yok.</p>
                  ) : (
                    adminAnalytics?.orders_by_status.map((item) => (
                      <div key={item.status} className="rounded-2xl bg-white/80 p-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-semibold text-[#1F2937]">{ORDER_STATUS_LABELS[item.status] ?? item.status}</span>
                          <span className="font-bold text-[#0f766e]">{item.count}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {activeAdminModule === "users" && (
          <section className={`mt-5 ${PANEL_CLASS}`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0ea5b7]">Kullanici Yonetimi</p>
                <h2 className="mt-1 text-lg font-semibold">Uyeler</h2>
                <p className="mt-1 text-xs text-[#3f6d56]">Kullanicilari ara, rolunu ve aktif durumunu takip et.</p>
              </div>
              <div className="rounded-2xl border border-emerald-200/70 bg-emerald-50/75 px-4 py-3 text-sm font-semibold text-emerald-800">
                {visibleAdminUsers.length} / {adminUsers.length} kullanici
              </div>
            </div>
            <input
              value={userSearchQuery}
              onChange={(event) => setUserSearchQuery(event.target.value)}
              className={`mt-4 ${FIELD_CLASS}`}
              placeholder="Isim, e-posta veya telefon ara"
            />
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {visibleAdminUsers.map((item) => (
                <article key={item.id} className="rounded-3xl border border-emerald-200/70 bg-white/70 p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-bold text-[#1F2937]">{item.full_name}</p>
                      <p className="mt-1 break-all text-xs text-slate-500">{item.email}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.phone || "Telefon yok"}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${item.is_active ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                      {item.is_active ? "Aktif" : "Pasif"}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-cyan-50 px-2.5 py-1 font-semibold text-cyan-800">{item.is_admin ? "Admin" : "Kullanici"}</span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 font-semibold text-slate-600">{item.is_verified ? "Dogrulandi" : "Dogrulanmadi"}</span>
                    <span className="rounded-full bg-white px-2.5 py-1 font-semibold text-slate-500">Kayit: {formatDateTime(item.created_at)}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleUpdateUserStatus(item)}
                    disabled={busyUserId === item.id || item.id === user.id}
                    className="mt-3 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                  >
                    {busyUserId === item.id ? "Guncelleniyor..." : item.is_active ? "Pasife Al" : "Aktif Et"}
                  </button>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeAdminModule === "notifications" && (
        <section className={`mt-5 ${PANEL_CLASS}`}>
          <div className="grid gap-4 lg:grid-cols-[minmax(0,0.8fr)_minmax(260px,0.45fr)]">
            <form onSubmit={handleSendManualNotification} className="rounded-3xl border border-cyan-200/70 bg-white/60 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0ea5b7]">Bildirim Merkezi</p>
              <h2 className="mt-1 text-lg font-semibold">Manuel bildirim gonder</h2>
              <p className="mt-1 text-xs text-[#3f6d56]">Tum kullanicilarin bildirim kutusuna duyuru, kampanya veya operasyon mesaji dusur.</p>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <label>
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Tip</span>
                  <select
                    value={notificationForm.type}
                    onChange={(event) =>
                      setNotificationForm((prev) => ({
                        ...prev,
                        type: event.target.value as ManualNotificationForm["type"],
                      }))
                    }
                    className={FIELD_CLASS}
                  >
                    <option value="announcement">Duyuru</option>
                    <option value="campaign">Kampanya</option>
                    <option value="stock">Stok</option>
                    <option value="order">Siparis</option>
                  </select>
                </label>

                <label>
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Baslik</span>
                  <input
                    value={notificationForm.title}
                    onChange={(event) => setNotificationForm((prev) => ({ ...prev, title: event.target.value }))}
                    className={FIELD_CLASS}
                    placeholder="Bugun temel gida firsati"
                    required
                  />
                </label>

                <label className="md:col-span-2">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Mesaj</span>
                  <textarea
                    value={notificationForm.body}
                    onChange={(event) => setNotificationForm((prev) => ({ ...prev, body: event.target.value }))}
                    className={`${FIELD_CLASS} min-h-24`}
                    placeholder="Temel gida urunlerinde bugune ozel kampanyalari kacirma."
                    required
                  />
                </label>

                <div className="md:col-span-2">
                  <button type="submit" disabled={notificationSaving} className={`w-full justify-center ${PRIMARY_BUTTON_CLASS}`}>
                    {notificationSaving ? "Gonderiliyor..." : "Bildirimi Gonder"}
                  </button>
                </div>
              </div>
            </form>

            <div className="rounded-3xl border border-cyan-200/70 bg-cyan-50/60 p-4 text-sm shadow-sm">
              <h3 className="font-semibold text-[#0f766e]">Kullanim ornekleri</h3>
              <div className="mt-3 space-y-2 text-xs text-slate-600">
                <p className="rounded-2xl bg-white/75 p-3">Kampanya: Temel gida urunlerinde bugune ozel indirim basladi.</p>
                <p className="rounded-2xl bg-white/75 p-3">Duyuru: Teslimat saatleri aksam yogunluguna gore guncellendi.</p>
                <p className="rounded-2xl bg-white/75 p-3">Stok: Yeni meyve-sebze urunleri raflara eklendi.</p>
              </div>
            </div>
          </div>
        </section>
        )}

        {(activeAdminModule === "product-add" || activeAdminModule === "products") && (
        <section className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
          {activeAdminModule === "product-add" && (
          <article className={`lg:col-span-3 ${PANEL_CLASS}`}>
            <h2 className="text-lg font-semibold">Yeni Ürün Ekle</h2>
            <form onSubmit={handleCreateProduct} className="mt-3 space-y-2">
              <input
                value={productForm.name}
                onChange={(event) => setProductForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="Ürün adı"
                required
                className={FIELD_CLASS}
              />
              <input
                value={productForm.slug}
                onChange={(event) => setProductForm((prev) => ({ ...prev, slug: event.target.value }))}
                placeholder="Slug (opsiyonel)"
                className={FIELD_CLASS}
              />
              <textarea
                value={productForm.description}
                onChange={(event) => setProductForm((prev) => ({ ...prev, description: event.target.value }))}
                placeholder="Açıklama"
                required
                className={`${FIELD_CLASS} min-h-20`}
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={productForm.price}
                  onChange={(event) => setProductForm((prev) => ({ ...prev, price: event.target.value }))}
                  placeholder="Fiyat"
                  required
                  className={FIELD_CLASS}
                />
                <input
                  type="number"
                  min="0"
                  value={productForm.stock}
                  onChange={(event) => setProductForm((prev) => ({ ...prev, stock: event.target.value }))}
                  placeholder="Stok"
                  required
                  className={FIELD_CLASS}
                />
              </div>
              <select
                value={productForm.category_id}
                onChange={(event) => setProductForm((prev) => ({ ...prev, category_id: event.target.value }))}
                required
                className={FIELD_CLASS}
              >
                <option value="">Kategori seçin</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={productForm.brand}
                  onChange={(event) => setProductForm((prev) => ({ ...prev, brand: event.target.value }))}
                  placeholder="Marka"
                  className={FIELD_CLASS}
                />
                <input
                  value={productForm.unit}
                  onChange={(event) => setProductForm((prev) => ({ ...prev, unit: event.target.value }))}
                  placeholder="Birim (adet/kg/litre)"
                  className={FIELD_CLASS}
                />
              </div>
              <input
                value={productForm.image_url}
                onChange={(event) => setProductForm((prev) => ({ ...prev, image_url: event.target.value }))}
                placeholder="Görsel URL (opsiyonel)"
                className={FIELD_CLASS}
              />
              <div className="space-y-2 rounded-2xl border border-amber-200/80 bg-amber-50/70 p-3 shadow-sm">
                <label className="flex items-center gap-2 text-sm font-semibold text-amber-900">
                  <input
                    type="checkbox"
                    checked={productForm.is_promoted}
                    onChange={(event) =>
                      setProductForm((prev) => ({
                        ...prev,
                        is_promoted: event.target.checked,
                        promotion_type: event.target.checked ? prev.promotion_type || "buy_x_pay_y" : "",
                        promotion_label: event.target.checked ? prev.promotion_label || "3 Al 2 Ode" : "",
                        promotion_buy_quantity: event.target.checked ? prev.promotion_buy_quantity || "3" : "",
                        promotion_pay_quantity: event.target.checked ? prev.promotion_pay_quantity || "2" : "",
                      }))
                    }
                  />
                  Kampanyali urun
                </label>
                {productForm.is_promoted ? (
                  <>
                    <select
                      value={productForm.promotion_type}
                      onChange={(event) => setProductForm((prev) => ({ ...prev, promotion_type: event.target.value }))}
                      className="w-full rounded-2xl border border-amber-200/80 bg-white/85 px-3 py-2.5 text-sm outline-none transition focus:border-amber-300 focus:ring-2 focus:ring-amber-200/70"
                    >
                      <option value="buy_x_pay_y">X al Y ode</option>
                      <option value="discount_price">Indirimli fiyat</option>
                    </select>
                    <input
                      value={productForm.promotion_label}
                      onChange={(event) => setProductForm((prev) => ({ ...prev, promotion_label: event.target.value }))}
                      placeholder="Kampanya etiketi (3 Al 2 Ode)"
                      className="w-full rounded-2xl border border-amber-200/80 bg-white/85 px-3 py-2.5 text-sm outline-none transition focus:border-amber-300 focus:ring-2 focus:ring-amber-200/70"
                    />
                    {productForm.promotion_type === "discount_price" ? (
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={productForm.discounted_price}
                        onChange={(event) => setProductForm((prev) => ({ ...prev, discounted_price: event.target.value }))}
                        placeholder="Indirimli fiyat"
                        className="w-full rounded-2xl border border-amber-200/80 bg-white/85 px-3 py-2.5 text-sm outline-none transition focus:border-amber-300 focus:ring-2 focus:ring-amber-200/70"
                      />
                    ) : (
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="number"
                          min="1"
                          value={productForm.promotion_buy_quantity}
                          onChange={(event) => setProductForm((prev) => ({ ...prev, promotion_buy_quantity: event.target.value }))}
                          placeholder="Alinan adet"
                          className="w-full rounded-2xl border border-amber-200/80 bg-white/85 px-3 py-2.5 text-sm outline-none transition focus:border-amber-300 focus:ring-2 focus:ring-amber-200/70"
                        />
                        <input
                          type="number"
                          min="1"
                          value={productForm.promotion_pay_quantity}
                          onChange={(event) => setProductForm((prev) => ({ ...prev, promotion_pay_quantity: event.target.value }))}
                          placeholder="Odenecek adet"
                          className="w-full rounded-2xl border border-amber-200/80 bg-white/85 px-3 py-2.5 text-sm outline-none transition focus:border-amber-300 focus:ring-2 focus:ring-amber-200/70"
                        />
                      </div>
                    )}
                  </>
                ) : null}
              </div>
              <button
                type="submit"
                disabled={productSaving}
                className={`w-full justify-center ${PRIMARY_BUTTON_CLASS}`}
              >
                {productSaving ? "Ekleniyor..." : "Ürün Ekle"}
              </button>
            </form>
          </article>
          )}

          {activeAdminModule === "products" && (
          <article className={`lg:col-span-3 ${PANEL_CLASS}`}>
            <h2 className="text-lg font-semibold">Ürün Yönetimi</h2>
            <p className="mt-1 text-xs text-[#3f6d56]">Kategori sec, sadece ilgili urunleri yonet.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Kategori</span>
                <select
                  value={selectedProductCategoryId}
                  onChange={(event) => setSelectedProductCategoryId(event.target.value)}
                  className={FIELD_CLASS}
                >
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name} ({productCountByCategory.get(category.id) ?? 0})
                    </option>
                  ))}
                </select>
              </label>
              <div className="rounded-2xl border border-emerald-200/70 bg-emerald-50/75 px-4 py-3 text-sm font-semibold text-emerald-800">
                {selectedCategoryProducts.length} urun
              </div>
            </div>
            <div className="mt-4">
              {selectedProductCategoryId ? (
                <div className="rounded-3xl border border-emerald-200/70 bg-white/60 p-3 shadow-sm">
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-sm font-semibold">{selectedProductCategoryName}</h3>
                    <span className="text-xs text-[#3f6d56]">{selectedCategoryProducts.length} urun</span>
                  </div>
                  <div className="overflow-auto">
                    <table className="w-full min-w-[1080px] text-sm">
                      <thead>
                        <tr className="border-b border-emerald-200/70 text-left text-slate-500">
                          <th className="py-2">Gorsel</th>
                          <th className="py-2">Urun</th>
                          <th className="py-2">Fiyat</th>
                          <th className="py-2">Stok</th>
                          <th className="py-2">Kampanya</th>
                          <th className="py-2">Durum</th>
                          <th className="py-2">Aksiyon</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedCategoryProducts.map((product) => (
                          <tr key={product.id} className="border-b border-emerald-100/80">
                            <td className="py-2 pr-3">
                              {product.image_url ? (
                                <img
                                  src={product.image_url}
                                  alt={product.name}
                                  className="h-12 w-12 rounded-2xl border border-emerald-200/70 object-cover"
                                  loading="lazy"
                                />
                              ) : (
                                <div className="h-12 w-12 rounded-2xl border border-dashed border-emerald-200/80 bg-emerald-50/70" />
                              )}
                            </td>
                            <td className="py-2 pr-3">
                              <p className="font-medium">{product.name}</p>
                              <p className="text-xs text-[#567864]">{product.slug}</p>
                            </td>
                            <td className="py-2 pr-3">
                              <input
                                type="number"
                                min="0"
                                step="0.01"
                                defaultValue={product.price}
                                onBlur={(event) => {
                                  const value = Number(event.target.value);
                                  if (!Number.isNaN(value) && value !== product.price) {
                                    void handleUpdateProduct(product.id, { price: value });
                                  }
                                }}
                                className={`w-24 ${COMPACT_FIELD_CLASS}`}
                              />
                            </td>
                            <td className="py-2 pr-3">
                              <input
                                type="number"
                                min="0"
                                defaultValue={product.stock}
                                onBlur={(event) => {
                                  const value = Number(event.target.value);
                                  if (!Number.isNaN(value) && value !== product.stock) {
                                    void handleUpdateProduct(product.id, { stock: value });
                                  }
                                }}
                                className={`w-20 ${COMPACT_FIELD_CLASS}`}
                              />
                            </td>
                            <td className="py-2 pr-3">
                              <div className="flex flex-col gap-1.5">
                                <span
                                  className={`inline-flex w-fit rounded-full px-2 py-1 text-xs ${
                                    product.is_promoted ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"
                                  }`}
                                >
                                  {product.is_promoted ? product.promotion_label || "Kampanyali" : "Kampanya yok"}
                                </span>
                                <div className="flex flex-wrap gap-1">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void handleUpdateProduct(product.id, {
                                        is_promoted: true,
                                        promotion_type: "buy_x_pay_y",
                                        promotion_label: "3 Al 2 Ode",
                                        promotion_buy_quantity: 3,
                                        promotion_pay_quantity: 2,
                                      })
                                    }
                                    disabled={busyProductId === product.id}
                                    className="rounded-xl border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11px] font-semibold text-amber-800 transition hover:bg-amber-100 disabled:opacity-70"
                                  >
                                    3 Al 2 Ode
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void handleUpdateProduct(product.id, {
                                        is_promoted: true,
                                        promotion_type: "discount_price",
                                        promotion_label: "Indirimli Urun",
                                        discounted_price: Number((product.price * 0.85).toFixed(2)),
                                      })
                                    }
                                    disabled={busyProductId === product.id}
                                    className="rounded-xl border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-800 transition hover:bg-emerald-100 disabled:opacity-70"
                                  >
                                    %15 Indir
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void handleUpdateProduct(product.id, {
                                        is_promoted: false,
                                        promotion_type: "",
                                        promotion_label: "",
                                      })
                                    }
                                    disabled={busyProductId === product.id}
                                    className="rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-70"
                                  >
                                    Kaldir
                                  </button>
                                </div>
                              </div>
                            </td>
                            <td className="py-2 pr-3">
                              <span
                                className={`inline-flex rounded-full px-2 py-1 text-xs ${
                                  product.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-700"
                                }`}
                              >
                                {product.is_active ? "Aktif" : "Pasif"}
                              </span>
                            </td>
                            <td className="py-2">
                              <button
                                onClick={() => void handleDeleteProduct(product.id)}
                                disabled={busyProductId === product.id}
                                className="rounded-xl border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-100 disabled:opacity-70"
                              >
                                {busyProductId === product.id ? "Isleniyor..." : "Sil (Pasife Al)"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="rounded-3xl border border-dashed border-emerald-200/80 bg-white/55 px-4 py-10 text-center text-sm text-slate-500">
                  Urunleri listelemek icin bir kategori secin.
                </div>
              )}
            </div>
          </article>
          )}
        </section>
        )}

        {activeAdminModule === "campaigns" && (
        <section className={`mt-5 ${PANEL_CLASS}`}>
          <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0ea5b7]">Kampanya Merkezi</p>
              <h2 className="mt-1 text-lg font-semibold">Kampanya olustur</h2>
              <p className="mt-1 text-xs text-[#3f6d56]">Urun sec, kampanya tipini belirle; bildirim otomatik olusur.</p>
            </div>
            <span className="mt-2 w-fit rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 sm:mt-0">
              {activeCampaignProducts.length} aktif kampanya
            </span>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.75fr)]">
            <form onSubmit={handleCreateCampaign} className="rounded-3xl border border-emerald-200/70 bg-white/60 p-4 shadow-sm">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="md:col-span-2">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Urun</span>
                  <select
                    value={campaignForm.product_id}
                    onChange={(event) => setCampaignForm((prev) => ({ ...prev, product_id: event.target.value }))}
                    className={FIELD_CLASS}
                  >
                    {sortedProducts.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name} - {categoryNameMap.get(product.category_id) || "Kategori yok"}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Kampanya tipi</span>
                  <select
                    value={campaignForm.promotion_type}
                    onChange={(event) =>
                      setCampaignForm((prev) => ({
                        ...prev,
                        promotion_type: event.target.value as CampaignForm["promotion_type"],
                        promotion_label: event.target.value === "discount_price" ? "Indirimli Urun" : "3 Al 2 Ode",
                      }))
                    }
                    className={FIELD_CLASS}
                  >
                    <option value="buy_x_pay_y">X al Y ode</option>
                    <option value="discount_price">Indirimli fiyat</option>
                  </select>
                </label>

                <label>
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Etiket</span>
                  <input
                    value={campaignForm.promotion_label}
                    onChange={(event) => setCampaignForm((prev) => ({ ...prev, promotion_label: event.target.value }))}
                    className={FIELD_CLASS}
                    placeholder="3 Al 2 Ode"
                  />
                </label>

                {campaignForm.promotion_type === "discount_price" ? (
                  <label>
                    <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Indirimli fiyat</span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={campaignForm.discounted_price}
                      onChange={(event) => setCampaignForm((prev) => ({ ...prev, discounted_price: event.target.value }))}
                      className={FIELD_CLASS}
                      placeholder={selectedCampaignProduct ? String(Number((selectedCampaignProduct.price * 0.85).toFixed(2))) : "0"}
                    />
                  </label>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    <label>
                      <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Al</span>
                      <input
                        type="number"
                        min="1"
                        value={campaignForm.promotion_buy_quantity}
                        onChange={(event) => setCampaignForm((prev) => ({ ...prev, promotion_buy_quantity: event.target.value }))}
                        className={FIELD_CLASS}
                      />
                    </label>
                    <label>
                      <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Ode</span>
                      <input
                        type="number"
                        min="1"
                        value={campaignForm.promotion_pay_quantity}
                        onChange={(event) => setCampaignForm((prev) => ({ ...prev, promotion_pay_quantity: event.target.value }))}
                        className={FIELD_CLASS}
                      />
                    </label>
                  </div>
                )}

                <div className="flex items-end">
                  <button type="submit" disabled={campaignSaving || !campaignForm.product_id} className={`w-full justify-center ${PRIMARY_BUTTON_CLASS}`}>
                    {campaignSaving ? "Uygulaniyor..." : "Kampanyayi Uygula"}
                  </button>
                </div>
              </div>
            </form>

            <div className="rounded-3xl border border-amber-200/70 bg-amber-50/60 p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-amber-900">Aktif kampanyalar</h3>
              <div className="mt-3 max-h-80 space-y-2 overflow-auto pr-1">
                {activeCampaignProducts.length === 0 ? (
                  <p className="rounded-2xl border border-amber-100 bg-white/70 px-3 py-4 text-xs text-amber-800">
                    Henuz aktif kampanya yok.
                  </p>
                ) : (
                  activeCampaignProducts.map((product) => (
                    <div key={product.id} className="rounded-2xl border border-white/70 bg-white/82 p-3 text-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-[#1F2937]">{product.name}</p>
                          <p className="mt-1 text-xs text-slate-500">{product.promotion_label || "Kampanyali"}</p>
                          <p className="mt-1 text-xs text-slate-500">{product.price.toFixed(2)} TL</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => void handleRemoveCampaign(product.id)}
                          disabled={busyProductId === product.id}
                          className="rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-70"
                        >
                          Kaldir
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>
        )}

        {activeAdminModule === "orders" && (
        <section className={`mt-5 ${PANEL_CLASS}`}>
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0ea5b7]">Operasyon</p>
              <h2 className="mt-1 text-lg font-semibold">Siparis Yonetimi</h2>
              <p className="mt-1 text-xs text-[#3f6d56]">Siparisleri filtrele, adres ve urun detayini gor, durum guncelle.</p>
            </div>
            <div className="rounded-2xl border border-emerald-200/70 bg-emerald-50/75 px-4 py-3 text-sm font-semibold text-emerald-800">
              {visibleOrders.length} / {orders.length} siparis
            </div>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px]">
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setSelectedOrderFilter("ALL")}
                className={`rounded-full px-3 py-2 text-xs font-semibold transition ${
                  selectedOrderFilter === "ALL"
                    ? "bg-gradient-to-r from-[#16C47F] to-[#22D3EE] text-white shadow-sm"
                    : "border border-emerald-200/70 bg-white/80 text-slate-600"
                }`}
              >
                Tumu ({orders.length})
              </button>
              {ORDER_STATUS_OPTIONS.map((statusOption) => (
                <button
                  key={statusOption}
                  type="button"
                  onClick={() => setSelectedOrderFilter(statusOption)}
                  className={`rounded-full px-3 py-2 text-xs font-semibold transition ${
                    selectedOrderFilter === statusOption
                      ? "bg-gradient-to-r from-[#16C47F] to-[#22D3EE] text-white shadow-sm"
                      : "border border-emerald-200/70 bg-white/80 text-slate-600"
                  }`}
                >
                  {ORDER_STATUS_LABELS[statusOption]} ({orderCountsByStatus.get(statusOption) ?? 0})
                </button>
              ))}
            </div>
            <input
              value={orderSearchQuery}
              onChange={(event) => setOrderSearchQuery(event.target.value)}
              className={FIELD_CLASS}
              placeholder="Siparis, kullanici, adres veya urun ara"
            />
          </div>

          <div className="mt-4 space-y-3">
            {visibleOrders.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-emerald-200/80 bg-white/55 px-4 py-10 text-center text-sm text-slate-500">
                Bu filtreye uygun siparis yok.
              </div>
            ) : (
              visibleOrders.map((order) => (
                <article key={order.id} className="rounded-3xl border border-emerald-200/70 bg-white/68 p-4 shadow-sm">
                  <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
                    <div>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Siparis</p>
                          <h3 className="mt-1 break-all text-sm font-semibold text-[#1F2937]">{order.id}</h3>
                          <p className="mt-1 text-xs text-slate-500">Kullanici: {order.user_id}</p>
                        </div>
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${ORDER_STATUS_CLASSES[order.status]}`}>
                          {ORDER_STATUS_LABELS[order.status]}
                        </span>
                      </div>

                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/55 p-3">
                          <p className="text-xs text-slate-500">Tutar</p>
                          <p className="mt-1 text-sm font-bold text-[#16C47F]">{order.total_price.toFixed(2)} TL</p>
                        </div>
                        <div className="rounded-2xl border border-cyan-100 bg-cyan-50/55 p-3">
                          <p className="text-xs text-slate-500">Urun adedi</p>
                          <p className="mt-1 text-sm font-bold text-[#0f766e]">{order.items.length}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-100 bg-white/80 p-3">
                          <p className="text-xs text-slate-500">Tarih</p>
                          <p className="mt-1 text-xs font-semibold text-slate-700">{formatDateTime(order.created_at)}</p>
                        </div>
                      </div>

                      <div className="mt-3 rounded-2xl border border-slate-100 bg-white/82 p-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Teslimat adresi</p>
                        <p className="mt-1 text-sm text-slate-700">{order.delivery_address}</p>
                        <p className="mt-2 text-xs text-slate-500">Odeme: {order.payment_method}</p>
                      </div>

                      <div className="mt-3 rounded-2xl border border-slate-100 bg-white/82 p-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Urunler</p>
                        <div className="mt-2 space-y-2">
                          {order.items.map((item) => (
                            <div key={`${order.id}-${item.product_id}`} className="flex items-center justify-between gap-3 text-sm">
                              <div>
                                <p className="font-medium text-[#1F2937]">{item.name}</p>
                                <p className="text-xs text-slate-500">
                                  {item.quantity} x {item.price.toFixed(2)} TL
                                </p>
                              </div>
                              <span className="text-sm font-semibold text-slate-700">{item.subtotal.toFixed(2)} TL</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="rounded-3xl border border-emerald-100 bg-emerald-50/55 p-4">
                      <p className="text-sm font-semibold text-[#1F2937]">Durum guncelle</p>
                      <select
                        value={selectedOrderStatus[order.id] || order.status}
                        onChange={(event) =>
                          setSelectedOrderStatus((prev) => ({
                            ...prev,
                            [order.id]: event.target.value as OrderStatus,
                          }))
                        }
                        className={`mt-3 ${FIELD_CLASS}`}
                      >
                        {ORDER_STATUS_OPTIONS.map((statusOption) => (
                          <option key={statusOption} value={statusOption}>
                            {ORDER_STATUS_LABELS[statusOption]}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => void handleUpdateOrderStatus(order.id)}
                        disabled={busyOrderId === order.id || (selectedOrderStatus[order.id] || order.status) === order.status}
                        className={`mt-3 w-full justify-center ${PRIMARY_BUTTON_CLASS}`}
                      >
                        {busyOrderId === order.id ? "Guncelleniyor..." : "Durumu Guncelle"}
                      </button>
                      <p className="mt-3 text-xs leading-5 text-slate-500">
                        Iptal durumunda stoklar backend tarafinda otomatik iade edilir. Durum guncellemesi kullanici bildirim kutusuna duser.
                      </p>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
        )}

        {activeAdminModule === "stock" && (
          <section className={`mt-5 ${PANEL_CLASS}`}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0ea5b7]">Stok Uyarilari</p>
                <h2 className="mt-1 text-lg font-semibold">Dusuk stoklu urunler</h2>
                <p className="mt-1 text-xs text-[#3f6d56]">Stogu 5 ve altina dusen urunleri hizlica takip et.</p>
              </div>
              <span className="w-fit rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">
                {lowStockProducts.length} kritik urun
              </span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {lowStockProducts.length === 0 ? (
                <p className="rounded-3xl border border-dashed border-emerald-200/80 bg-white/55 px-4 py-10 text-center text-sm text-slate-500 md:col-span-2 xl:col-span-3">
                  Dusuk stoklu urun yok.
                </p>
              ) : (
                lowStockProducts.map((product) => (
                  <article key={product.id} className="rounded-3xl border border-rose-100 bg-white/75 p-4 shadow-sm">
                    <p className="text-sm font-semibold text-[#1F2937]">{product.name}</p>
                    <p className="mt-1 text-xs text-slate-500">{categoryNameMap.get(product.category_id) || "Kategori yok"}</p>
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">{product.stock} stok</span>
                      <span className="text-sm font-bold text-[#16C47F]">{product.price.toFixed(2)} TL</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => void handleCreateCampaignForProduct(product)}
                      disabled={busyProductId === product.id}
                      className="mt-3 w-full rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 disabled:opacity-70"
                    >
                      {busyProductId === product.id ? "Isleniyor..." : "3 Al 2 Ode Yap"}
                    </button>
                  </article>
                ))
              )}
            </div>
          </section>
        )}

        {!loading && adminCheck && (
          <section className="mt-5 rounded-3xl border border-emerald-200/70 bg-white/75 p-5 text-sm shadow-sm backdrop-blur-xl">
            <p>
              <strong>Admin doğrulama:</strong> {adminCheck.message}
            </p>
            <p className="text-[#3f6d56]">Hesap: {adminCheck.user_email}</p>
          </section>
        )}

        {!loading && error && (
          <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 shadow-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 shadow-sm">
            Admin panel verileri yükleniyor...
          </div>
        )}

        <section className="mt-5 rounded-3xl border border-emerald-200/70 bg-white/75 p-5 shadow-sm backdrop-blur-xl">
          <h2 className="text-sm font-semibold">Not</h2>
          <p className="text-xs text-[#3f6d56] mt-1">
            Sipariş durumu <code>CANCELLED</code> yapılırsa backend stokları otomatik iade eder. Bu, sipariş düşmesi/iptal
            senaryosunu yönetmek için kullanılır.
          </p>
        </section>
      </div>
    </main>
  );
}
