"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Home,
  Loader2,
  Minus,
  PackageCheck,
  Phone,
  Plus,
  ShieldCheck,
  ShoppingBag,
  Trash2,
  Truck,
} from "lucide-react";

import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

type CartItem = {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
  image_url?: string | null;
  original_price?: number | null;
  promotion_label?: string | null;
};

type CartResponse = {
  id: string;
  user_id: string;
  items: CartItem[];
  total_price: number;
};

type PaymentMethod = "CASH_ON_DELIVERY" | "CREDIT_CARD";
type CheckoutStep = "cart" | "address" | "delivery" | "payment" | "review";

type OrderResponse = {
  id: string;
  total_price: number;
};

const DEFAULT_ADDRESS = "Ornek Mah. 100 Sok. No:10 Kadikoy/Istanbul";
const FREE_SHIPPING_THRESHOLD = 750;
const DEFAULT_SHIPPING = 29.99;

const CHECKOUT_STEPS: Array<{ id: CheckoutStep; title: string; icon: typeof ShoppingBag }> = [
  { id: "cart", title: "Sepet", icon: ShoppingBag },
  { id: "address", title: "Adres", icon: Home },
  { id: "delivery", title: "Teslimat", icon: Truck },
  { id: "payment", title: "Odeme", icon: CreditCard },
  { id: "review", title: "Onay", icon: ShieldCheck },
];

const DELIVERY_SLOTS = [
  "Bugun 18:00-20:00",
  "Bugun 20:00-22:00",
  "Yarin 10:00-12:00",
  "Yarin 12:00-14:00",
];

function formatTL(value: number): string {
  return `${value.toFixed(2)} TL`;
}

function toHighResMigrosImage(imageUrl: string): string {
  if (!imageUrl) return imageUrl;
  return imageUrl.replace(/-\d+x\d+(?=\.(jpg|jpeg|png|webp)$)/i, "");
}

function onlyDigits(value: string): string {
  return value.replace(/\D/g, "");
}

function formatCardNumber(value: string): string {
  return onlyDigits(value).slice(0, 19).replace(/(\d{4})(?=\d)/g, "$1 ");
}

function passesLuhn(cardNumber: string): boolean {
  const digits = onlyDigits(cardNumber).split("").map(Number);
  if (digits.length < 13) return false;
  let sum = 0;
  let doubleNext = false;
  for (let index = digits.length - 1; index >= 0; index -= 1) {
    let digit = digits[index];
    if (doubleNext) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    doubleNext = !doubleNext;
  }
  return sum % 10 === 0;
}

export default function CartPage() {
  const router = useRouter();
  const { user, token, isReady, logout } = useAuth();

  const [cart, setCart] = useState<CartResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [busyProductId, setBusyProductId] = useState("");
  const [error, setError] = useState("");
  const [couponCode, setCouponCode] = useState("");
  const [discountRate, setDiscountRate] = useState(0);
  const [couponFeedback, setCouponFeedback] = useState("");
  const [checkoutStep, setCheckoutStep] = useState<CheckoutStep>("cart");
  const [deliveryAddress, setDeliveryAddress] = useState(DEFAULT_ADDRESS);
  const [addressTitle, setAddressTitle] = useState("Ev");
  const [contactPhone, setContactPhone] = useState("");
  const [deliverySlot, setDeliverySlot] = useState(DELIVERY_SLOTS[0]);
  const [deliveryNote, setDeliveryNote] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("CASH_ON_DELIVERY");
  const [cardNumber, setCardNumber] = useState("");
  const [cardHolder, setCardHolder] = useState("");
  const [expMonth, setExpMonth] = useState("");
  const [expYear, setExpYear] = useState("");
  const [cvv, setCvv] = useState("");
  const [agreementAccepted, setAgreementAccepted] = useState(false);
  const [createdOrderId, setCreatedOrderId] = useState("");

  const fetchCart = useCallback(async () => {
    try {
      setIsLoading(true);
      setError("");
      const { data } = await api.get<CartResponse>("/api/v1/cart");
      setCart(data);
      if (!data.items?.length) {
        setCheckoutStep("cart");
      }
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) {
        setError("Oturum sureniz dolmus olabilir. Lutfen tekrar giris yapin.");
        logout();
        return;
      }
      setError("Sepet yuklenemedi.");
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    if (!isReady) return;
    if (!user && !token) {
      router.push("/login");
      return;
    }
    void fetchCart();
  }, [isReady, user, token, router, fetchCart]);

  const stepIndex = CHECKOUT_STEPS.findIndex((step) => step.id === checkoutStep);
  const totalItems = useMemo(() => (cart?.items ?? []).reduce((acc, item) => acc + item.quantity, 0), [cart]);
  const subTotal = useMemo(
    () => (cart?.items ?? []).reduce((acc, item) => acc + Number(item.subtotal || item.price * item.quantity), 0),
    [cart],
  );
  const discountAmount = useMemo(() => subTotal * discountRate, [subTotal, discountRate]);
  const shippingFee = useMemo(
    () => (subTotal - discountAmount >= FREE_SHIPPING_THRESHOLD ? 0 : DEFAULT_SHIPPING),
    [subTotal, discountAmount],
  );
  const freeShippingRemaining = useMemo(
    () => Math.max(0, FREE_SHIPPING_THRESHOLD - (subTotal - discountAmount)),
    [subTotal, discountAmount],
  );
  const grandTotal = useMemo(
    () => Number(Math.max(0, subTotal - discountAmount + shippingFee).toFixed(2)),
    [subTotal, discountAmount, shippingFee],
  );

  const phoneIsValid = onlyDigits(contactPhone).length >= 10;
  const cardIsValid =
    paymentMethod === "CASH_ON_DELIVERY" ||
    (passesLuhn(cardNumber) &&
      cardHolder.trim().length >= 3 &&
      Number(expMonth) >= 1 &&
      Number(expMonth) <= 12 &&
      Number(expYear) >= new Date().getFullYear() &&
      onlyDigits(cvv).length >= 3);

  function validateStep(step: CheckoutStep): string {
    if (step === "cart" && !cart?.items?.length) return "Sepetiniz bos. Once urun ekleyin.";
    if (step === "address") {
      if (addressTitle.trim().length < 2) return "Adres basligi girin.";
      if (deliveryAddress.trim().length < 10) return "Teslimat adresini detayli girin.";
      if (!phoneIsValid) return "Gecerli bir telefon numarasi girin.";
    }
    if (step === "delivery" && !deliverySlot) return "Teslimat zamanini secin.";
    if (step === "payment") {
      if (!cardIsValid) return "Kart bilgilerini kontrol edin. Test karti: 4111 1111 1111 1111.";
      if (!agreementAccepted) return "Mesafeli satis ve on bilgilendirme onayini isaretleyin.";
    }
    return "";
  }

  function goNext() {
    const validation = validateStep(checkoutStep);
    if (validation) {
      setError(validation);
      return;
    }
    setError("");
    const next = CHECKOUT_STEPS[Math.min(stepIndex + 1, CHECKOUT_STEPS.length - 1)];
    setCheckoutStep(next.id);
  }

  function goBack() {
    setError("");
    const previous = CHECKOUT_STEPS[Math.max(stepIndex - 1, 0)];
    setCheckoutStep(previous.id);
  }

  async function updateItem(productId: string, quantity: number) {
    try {
      setBusyProductId(productId);
      const { data } = await api.put<CartResponse>(`/api/v1/cart/items/${productId}`, { quantity });
      setCart(data);
    } catch {
      setError("Sepet guncellenemedi.");
    } finally {
      setBusyProductId("");
    }
  }

  async function removeItem(productId: string) {
    try {
      setBusyProductId(productId);
      const { data } = await api.delete<CartResponse>(`/api/v1/cart/items/${productId}`);
      setCart(data);
    } catch {
      setError("Urun sepetten silinemedi.");
    } finally {
      setBusyProductId("");
    }
  }

  async function clearCart() {
    try {
      setBusyProductId("all");
      const { data } = await api.delete<CartResponse>("/api/v1/cart");
      setCart(data);
      setCouponCode("");
      setCouponFeedback("");
      setDiscountRate(0);
      setCreatedOrderId("");
    } catch {
      setError("Sepet bosaltilamadi.");
    } finally {
      setBusyProductId("");
    }
  }

  function applyCoupon() {
    const normalized = couponCode.trim().toUpperCase();
    if (!normalized) {
      setDiscountRate(0);
      setCouponFeedback("Kupon kodu giriniz.");
      return;
    }
    if (normalized === "SAVE10") {
      setDiscountRate(0.1);
      setCouponFeedback("Kupon uygulandi: %10 indirim");
      return;
    }
    if (normalized === "SAVE20") {
      setDiscountRate(0.2);
      setCouponFeedback("Kupon uygulandi: %20 indirim");
      return;
    }
    setDiscountRate(0);
    setCouponFeedback("Gecersiz kupon kodu.");
  }

  async function createOrderFromCart() {
    const reviewValidation = validateStep("review") || validateStep("address") || validateStep("delivery") || validateStep("payment");
    if (!cart?.items.length || !user?.id) return;
    if (reviewValidation) {
      setError(reviewValidation);
      return;
    }

    try {
      setCheckoutLoading(true);
      setError("");
      setCreatedOrderId("");

      const { data } = await api.post<OrderResponse>("/api/v1/orders", {
        delivery_address: `[${addressTitle.trim()}] ${deliveryAddress.trim()}`,
        payment_method: paymentMethod,
        contact_phone: contactPhone.trim(),
        delivery_slot: deliverySlot,
        delivery_note: deliveryNote.trim() || undefined,
      });

      if (paymentMethod === "CREDIT_CARD") {
        await api.post(`/api/v1/orders/${data.id}/pay`, {
          card_number: onlyDigits(cardNumber),
          holder_name: cardHolder.trim(),
          exp_month: Number(expMonth),
          exp_year: Number(expYear),
          cvv: onlyDigits(cvv),
        });
      }

      await fetchCart();
      setDiscountRate(0);
      setCouponCode("");
      setCouponFeedback("");
      setCreatedOrderId(data.id);
    } catch (err) {
      const detail = isAxiosError(err) ? err.response?.data?.detail : "";
      setError(detail ? `Siparis olusturulamadi: ${detail}` : "Siparis olusturulamadi.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  if (!isReady) return null;
  if (!user && !token) return null;

  return (
    <main className="min-h-screen bg-[#eef8f3] p-4 md:p-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-5">
          <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-[#2f674b] hover:text-[#173728]">
            <ArrowLeft className="h-4 w-4" />
            Alisverise Devam Et
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-[#143323]">Sepetim</h1>
          <p className="text-sm text-[#4a715e]">{totalItems} urun - adimli ve guvenli odeme</p>
        </div>

        <div className="mb-4 grid grid-cols-5 gap-2 rounded-3xl border border-white/75 bg-white/75 p-2 shadow-sm">
          {CHECKOUT_STEPS.map((step, index) => {
            const Icon = step.icon;
            const active = step.id === checkoutStep;
            const completed = index < stepIndex;
            return (
              <button
                key={step.id}
                type="button"
                onClick={() => {
                  if (index <= stepIndex) setCheckoutStep(step.id);
                }}
                className={`flex min-h-16 flex-col items-center justify-center gap-1 rounded-2xl text-xs font-semibold transition ${
                  active
                    ? "bg-gradient-to-r from-[#16C47F] to-[#22D3EE] text-white shadow-lg"
                    : completed
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-white text-slate-500"
                }`}
              >
                <Icon className="h-4 w-4" />
                {step.title}
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <section className="rounded-3xl border border-white/75 bg-white p-4 shadow-sm lg:col-span-8">
            {checkoutStep === "cart" ? (
              <CartStep
                cart={cart}
                isLoading={isLoading}
                busyProductId={busyProductId}
                clearCart={clearCart}
                removeItem={removeItem}
                updateItem={updateItem}
              />
            ) : null}

            {checkoutStep === "address" ? (
              <div className="space-y-4">
                <StepHeader icon={Home} title="Teslimat Adresi" subtitle="Siparisin dogru yere ulasmasi icin adres ve telefon bilgilerini tamamla." />
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="space-y-1">
                    <span className="text-xs font-semibold text-[#24543f]">Adres Basligi</span>
                    <input
                      value={addressTitle}
                      onChange={(event) => setAddressTitle(event.target.value)}
                      className="w-full rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                      placeholder="Ev, Is, Yurt"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs font-semibold text-[#24543f]">Telefon</span>
                    <div className="flex items-center gap-2 rounded-2xl border border-emerald-900/15 px-3 py-3 focus-within:border-[#16C47F]">
                      <Phone className="h-4 w-4 text-[#2f8c68]" />
                      <input
                        value={contactPhone}
                        onChange={(event) => setContactPhone(event.target.value)}
                        className="w-full bg-transparent text-sm outline-none"
                        placeholder="+90 555 111 22 33"
                      />
                    </div>
                  </label>
                </div>
                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[#24543f]">Acik Adres</span>
                  <textarea
                    value={deliveryAddress}
                    onChange={(event) => setDeliveryAddress(event.target.value)}
                    rows={5}
                    className="w-full rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                    placeholder="Mahalle, sokak, bina, daire, ilce/il"
                  />
                </label>
              </div>
            ) : null}

            {checkoutStep === "delivery" ? (
              <div className="space-y-4">
                <StepHeader icon={Truck} title="Teslimat Secenekleri" subtitle="Uygun teslimat saatini ve kurye notunu belirle." />
                <div className="grid gap-3 sm:grid-cols-2">
                  {DELIVERY_SLOTS.map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => setDeliverySlot(slot)}
                      className={`rounded-2xl border p-4 text-left text-sm font-semibold transition ${
                        deliverySlot === slot
                          ? "border-[#16C47F] bg-emerald-50 text-[#165c3d]"
                          : "border-emerald-900/10 bg-white text-slate-600 hover:border-[#16C47F]/50"
                      }`}
                    >
                      <span className="block text-xs text-slate-500">Teslimat Araligi</span>
                      {slot}
                    </button>
                  ))}
                </div>
                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[#24543f]">Kurye Notu</span>
                  <textarea
                    value={deliveryNote}
                    onChange={(event) => setDeliveryNote(event.target.value)}
                    rows={4}
                    className="w-full rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                    placeholder="Orn. Zile basmayin, kapıya birakabilirsiniz."
                  />
                </label>
              </div>
            ) : null}

            {checkoutStep === "payment" ? (
              <div className="space-y-4">
                <StepHeader icon={CreditCard} title="Odeme Yontemi" subtitle="Kapida odeme veya test kredi karti ile mock odeme yapabilirsin." />
                <div className="grid gap-3 sm:grid-cols-2">
                  <PaymentCard
                    active={paymentMethod === "CASH_ON_DELIVERY"}
                    title="Kapida Nakit"
                    description="Siparis teslim edilirken nakit odeme."
                    onClick={() => setPaymentMethod("CASH_ON_DELIVERY")}
                  />
                  <PaymentCard
                    active={paymentMethod === "CREDIT_CARD"}
                    title="Kredi Karti"
                    description="Guvenli test karti dogrulamasi."
                    onClick={() => setPaymentMethod("CREDIT_CARD")}
                  />
                </div>

                {paymentMethod === "CREDIT_CARD" ? (
                  <div className="rounded-3xl border border-[#22D3EE]/25 bg-gradient-to-br from-white to-cyan-50/60 p-4">
                    <p className="mb-3 text-xs text-slate-500">Test karti: 4111 1111 1111 1111 - CVV: 123 - ileri tarih</p>
                    <div className="grid gap-3">
                      <input
                        value={cardHolder}
                        onChange={(event) => setCardHolder(event.target.value)}
                        placeholder="Kart uzerindeki isim"
                        className="rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                      />
                      <input
                        value={cardNumber}
                        onChange={(event) => setCardNumber(formatCardNumber(event.target.value))}
                        placeholder="Kart numarasi"
                        inputMode="numeric"
                        className="rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                      />
                      <div className="grid grid-cols-3 gap-3">
                        <input
                          value={expMonth}
                          onChange={(event) => setExpMonth(onlyDigits(event.target.value).slice(0, 2))}
                          placeholder="Ay"
                          inputMode="numeric"
                          className="rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                        />
                        <input
                          value={expYear}
                          onChange={(event) => setExpYear(onlyDigits(event.target.value).slice(0, 4))}
                          placeholder="Yil"
                          inputMode="numeric"
                          className="rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                        />
                        <input
                          value={cvv}
                          onChange={(event) => setCvv(onlyDigits(event.target.value).slice(0, 4))}
                          placeholder="CVV"
                          inputMode="numeric"
                          className="rounded-2xl border border-emerald-900/15 px-3 py-3 text-sm outline-none focus:border-[#16C47F]"
                        />
                      </div>
                    </div>
                  </div>
                ) : null}

                <label className="flex items-start gap-2 rounded-2xl border border-emerald-900/10 bg-white p-3 text-sm text-[#264f3d]">
                  <input
                    type="checkbox"
                    checked={agreementAccepted}
                    onChange={(event) => setAgreementAccepted(event.target.checked)}
                    className="mt-1"
                  />
                  Mesafeli satis sozlesmesini, on bilgilendirme formunu ve teslimat kosullarini okudum, onayliyorum.
                </label>
              </div>
            ) : null}

            {checkoutStep === "review" ? (
              <div className="space-y-4">
                <StepHeader icon={PackageCheck} title="Siparis Onayi" subtitle="Bilgileri kontrol et; onaydan sonra siparis olusturulur." />
                <div className="grid gap-3 md:grid-cols-2">
                  <ReviewBox title="Adres" lines={[addressTitle, deliveryAddress, contactPhone]} />
                  <ReviewBox title="Teslimat" lines={[deliverySlot, deliveryNote || "Kurye notu yok"]} />
                  <ReviewBox title="Odeme" lines={[paymentMethod === "CREDIT_CARD" ? `Kredi Karti - ${cardNumber.slice(-4).padStart(4, "*")}` : "Kapida Nakit"]} />
                  <ReviewBox title="Sepet" lines={[`${totalItems} urun`, `Genel toplam: ${formatTL(grandTotal)}`]} />
                </div>
              </div>
            ) : null}

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-emerald-900/10 pt-4">
              <button
                type="button"
                onClick={goBack}
                disabled={checkoutStep === "cart"}
                className="inline-flex items-center gap-1.5 rounded-2xl border border-emerald-900/10 bg-white px-4 py-2 text-sm font-semibold text-[#24543f] disabled:opacity-45"
              >
                <ChevronLeft className="h-4 w-4" />
                Geri
              </button>
              {checkoutStep === "review" ? (
                <button
                  type="button"
                  onClick={createOrderFromCart}
                  disabled={!cart?.items?.length || checkoutLoading}
                  className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-[#ff8a00] to-[#ff6a00] px-5 py-3 text-sm font-bold text-white shadow-[0_14px_26px_-16px_rgba(255,106,0,0.7)] disabled:opacity-60"
                >
                  {checkoutLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                  Siparisi Onayla
                </button>
              ) : (
                <button
                  type="button"
                  onClick={goNext}
                  disabled={!cart?.items?.length}
                  className="inline-flex items-center gap-1.5 rounded-2xl bg-[#16C47F] px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
                >
                  Devam Et
                  <ChevronRight className="h-4 w-4" />
                </button>
              )}
            </div>
          </section>

          <aside className="lg:col-span-4">
            <div className="rounded-3xl border border-white/75 bg-white p-4 shadow-sm lg:sticky lg:top-6">
              <div className="mb-3 flex items-center gap-2">
                <ShoppingBag className="h-4 w-4 text-[#2f8c68]" />
                <h2 className="text-base font-semibold text-[#173728]">Siparis Ozeti</h2>
              </div>
              <div className="space-y-2 text-sm">
                <SummaryRow label="Ara Toplam" value={formatTL(subTotal)} />
                <SummaryRow label="Kargo" value={shippingFee === 0 ? "Bedava" : formatTL(shippingFee)} />
                {discountAmount > 0 ? <SummaryRow label="Indirim" value={`- ${formatTL(discountAmount)}`} positive /> : null}
              </div>
              <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-3">
                <div className="mb-2 flex items-center justify-between text-xs font-semibold text-[#24543f]">
                  <span>Kargo Avantaji</span>
                  <span>{shippingFee === 0 ? "Kargo bedava" : `${formatTL(freeShippingRemaining)} kaldi`}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#16C47F] to-[#22D3EE]"
                    style={{ width: `${Math.min(100, ((subTotal - discountAmount) / FREE_SHIPPING_THRESHOLD) * 100)}%` }}
                  />
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <input
                  value={couponCode}
                  onChange={(event) => setCouponCode(event.target.value)}
                  placeholder="Kupon Kodu"
                  className="min-w-0 flex-1 rounded-2xl border border-emerald-900/15 px-3 py-2 text-sm outline-none focus:border-[#16C47F]"
                />
                <button type="button" onClick={applyCoupon} className="rounded-2xl border border-emerald-900/15 bg-white px-3 py-2 text-sm text-[#1f4b36]">
                  Uygula
                </button>
              </div>
              {couponFeedback ? <p className="mt-2 text-xs text-[#466b59]">{couponFeedback}</p> : null}
              <div className="mt-4 rounded-2xl bg-[#f3fbf7] p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[#3a6b52]">Genel Toplam</span>
                  <span className="text-2xl font-bold text-[#163f2e]">{formatTL(grandTotal)}</span>
                </div>
              </div>
              <p className="mt-3 rounded-2xl border border-[#22D3EE]/25 bg-cyan-50/60 p-3 text-xs text-[#24543f]">
                Siparis olusturmadan once adres, teslimat saati, odeme bilgisi ve sozlesme onayi zorunludur.
              </p>
            </div>
          </aside>
        </div>

        {error ? <div className="mt-4 rounded-2xl border border-red-200 bg-red-50/90 p-3 text-sm text-red-700">{error}</div> : null}

        {createdOrderId ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
            <div className="w-full max-w-md rounded-3xl bg-white p-5 shadow-xl">
              <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-[#173728]">Siparisiniz Basariyla Alindi</h3>
              <p className="mt-2 text-sm text-[#466b59]">
                Siparis kodunuz: <span className="font-semibold text-[#1d4a35]">{createdOrderId}</span>
              </p>
              <p className="mt-1 text-sm text-[#466b59]">Siparis hazirlaniyor. Teslimat sureci profilinizdeki siparislerden takip edilebilir.</p>
              <button
                type="button"
                onClick={() => {
                  setCreatedOrderId("");
                  router.push("/dashboard");
                }}
                className="mt-4 w-full rounded-2xl bg-[#1f8f63] py-3 text-sm font-semibold text-white hover:bg-[#18734f]"
              >
                Alisverise Devam Et
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}

function StepHeader({ icon: Icon, title, subtitle }: { icon: typeof ShoppingBag; title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="rounded-2xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] p-3 text-white">
        <Icon className="h-5 w-5" />
      </span>
      <div>
        <h2 className="text-lg font-bold text-[#173728]">{title}</h2>
        <p className="text-sm text-[#6a8b7b]">{subtitle}</p>
      </div>
    </div>
  );
}

function PaymentCard({ active, title, description, onClick }: { active: boolean; title: string; description: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-3xl border p-4 text-left transition ${
        active ? "border-[#16C47F] bg-emerald-50 text-[#165c3d]" : "border-emerald-900/10 bg-white text-slate-600 hover:border-[#16C47F]/50"
      }`}
    >
      <span className="block text-sm font-bold">{title}</span>
      <span className="mt-1 block text-xs">{description}</span>
    </button>
  );
}

function ReviewBox({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-3xl border border-emerald-900/10 bg-[#fcfffd] p-4">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#16C47F]">{title}</p>
      <div className="mt-2 space-y-1 text-sm text-[#264f3d]">
        {lines.filter(Boolean).map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
    </div>
  );
}

function SummaryRow({ label, value, positive = false }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className={`flex items-center justify-between ${positive ? "text-emerald-700" : "text-[#466b59]"}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

function CartStep({
  cart,
  isLoading,
  busyProductId,
  clearCart,
  removeItem,
  updateItem,
}: {
  cart: CartResponse | null;
  isLoading: boolean;
  busyProductId: string;
  clearCart: () => void;
  removeItem: (productId: string) => void;
  updateItem: (productId: string, quantity: number) => void;
}) {
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <StepHeader icon={ShoppingBag} title="Sepet Urunleri" subtitle="Adet guncelle, urun sil veya sepeti tamamen bosalt." />
        {cart?.items?.length ? (
          <button
            type="button"
            onClick={clearCart}
            disabled={busyProductId === "all"}
            className="inline-flex items-center gap-1.5 rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-100 disabled:opacity-60"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Sepeti Bosalt
          </button>
        ) : null}
      </div>
      {isLoading ? (
        <p className="text-sm text-[#37654e]">Sepet yukleniyor...</p>
      ) : !(cart?.items?.length) ? (
        <div className="rounded-3xl border border-dashed border-emerald-200 bg-emerald-50/60 p-8 text-center">
          <ShoppingBag className="mx-auto h-8 w-8 text-[#2f8c68]" />
          <p className="mt-3 text-sm font-semibold text-[#173728]">Sepetiniz su an bos.</p>
          <p className="mt-1 text-xs text-[#6a8b7b]">Kategorilerden urun secerek alisverise baslayabilirsiniz.</p>
          <Link href="/dashboard" className="mt-4 inline-flex rounded-2xl bg-[#16C47F] px-4 py-2 text-sm font-semibold text-white">
            Urunlere Git
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {cart.items.map((item) => {
            const isBusy = busyProductId === item.product_id;
            return (
              <div key={item.product_id} className="rounded-2xl border border-emerald-900/10 bg-white/95 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl border border-emerald-900/10 bg-[#f6fff9]">
                      {item.image_url ? (
                        <img src={toHighResMigrosImage(item.image_url)} alt={item.name} className="h-full w-full object-cover" loading="lazy" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-[10px] text-[#7a9387]">Gorsel yok</div>
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[#173728]">{item.name}</p>
                      <p className="text-xs text-[#6a8b7b]">
                        {item.quantity} x {formatTL(item.price)}
                      </p>
                      {item.promotion_label ? (
                        <span className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                          {item.promotion_label}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <p className="shrink-0 text-sm font-semibold text-[#1d4a35]">{formatTL(item.subtotal)}</p>
                </div>
                <div className="mt-3 flex items-center justify-between gap-2">
                  <div className="inline-flex items-center rounded-xl border border-emerald-900/15 bg-white">
                    <button
                      type="button"
                      onClick={() => (item.quantity <= 1 ? removeItem(item.product_id) : updateItem(item.product_id, item.quantity - 1))}
                      disabled={isBusy}
                      className="px-2 py-1 text-[#24543f] disabled:opacity-60"
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                    <input value={item.quantity} readOnly className="w-10 border-x border-emerald-900/15 bg-transparent py-1 text-center text-sm outline-none" />
                    <button
                      type="button"
                      onClick={() => updateItem(item.product_id, item.quantity + 1)}
                      disabled={isBusy}
                      className="px-2 py-1 text-[#24543f] disabled:opacity-60"
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeItem(item.product_id)}
                    disabled={isBusy}
                    className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-700 disabled:opacity-60"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Sil
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
