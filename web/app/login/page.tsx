"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AnimatePresence, motion } from "framer-motion";
import { Apple, Bot, ChefHat, LockKeyhole, Mail, ShoppingCart, Sparkles, WandSparkles } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { getApiErrorDetail } from "@/lib/errors";

const schema = z.object({
  email: z.string().email("Geçerli bir e-posta girin"),
  password: z.string().min(1, "Şifre gerekli"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, loginWithGoogle, verifyEmail } = useAuth();
  const [step, setStep] = useState<"login" | "verify">("login");
  const [loginEmail, setLoginEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const isSocialInfo = serverError.includes("şu anda aktif değil");
  const isGoogleAuthReady = Boolean(
    process.env.NEXT_PUBLIC_FIREBASE_API_KEY &&
      process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN &&
      process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID &&
      process.env.NEXT_PUBLIC_FIREBASE_APP_ID
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setIsLoading(true);
    setServerError("");
    try {
      await login(data.email, data.password);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail === "Email adresi henüz doğrulanmadı") {
        setLoginEmail(data.email);
        setStep("verify");
      } else {
        setServerError(getApiErrorDetail(err, "Giriş yapılamadı."));
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleVerifySubmit(e: FormEvent) {
    e.preventDefault();
    if (!verificationCode || verificationCode.length !== 6) {
      setServerError("Lütfen 6 haneli kodu girin.");
      return;
    }
    setIsLoading(true);
    setServerError("");
    try {
      await verifyEmail(loginEmail, verificationCode);
    } catch (err: unknown) {
      setServerError(getApiErrorDetail(err, "Doğrulama başarısız."));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGoogleLogin() {
    if (!isGoogleAuthReady) {
      setServerError("Google ile giriş şu anda aktif değil. Lütfen e-posta ve şifre ile devam edin.");
      return;
    }
    setServerError("");
    try {
      await loginWithGoogle();
    } catch (err: unknown) {
      setServerError(getApiErrorDetail(err, "Google ile giriş yapılamadı."));
    }
  }

  function handleAppleLoginInfo() {
    setServerError("Apple ile giriş şu anda aktif değil. Şimdilik e-posta ve şifre ile giriş yapabilirsiniz.");
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#F4FFF8] text-[#1F2937] selection:bg-[#22D3EE]/35">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-28 -top-24 h-96 w-96 rounded-full bg-[#16C47F]/22 blur-[120px]" />
        <div className="absolute right-0 top-8 h-96 w-96 rounded-full bg-[#22D3EE]/20 blur-[130px]" />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-[#F59E0B]/16 blur-[130px]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle,rgba(16,185,129,0.12)_1px,transparent_1px)] [background-size:28px_28px] opacity-35" />
        {Array.from({ length: 10 }).map((_, idx) => (
          <motion.div
            key={`particle-${idx}`}
            className="absolute h-2 w-2 rounded-full bg-[#16C47F]/35"
            style={{ left: `${8 + idx * 9}%`, top: `${12 + (idx % 4) * 20}%` }}
            animate={{ y: [0, -12, 0], opacity: [0.25, 0.8, 0.25] }}
            transition={{ duration: 3 + idx * 0.4, repeat: Infinity, ease: "easeInOut" }}
          />
        ))}
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1380px] flex-col gap-6 px-4 py-6 md:px-8 lg:grid lg:grid-cols-[minmax(0,460px)_minmax(0,1fr)] lg:items-center lg:gap-10">
        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="relative mx-auto w-full max-w-[460px] rounded-[30px] border border-emerald-200/70 bg-white/78 p-5 shadow-[0_40px_100px_-45px_rgba(34,211,238,0.35)] backdrop-blur-2xl sm:p-7"
        >
          <div className="mb-6 flex items-center justify-between">
            <Link href="/" className="inline-flex items-center gap-2">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] shadow-lg">
                <ChefHat className="h-5 w-5 text-white" />
              </span>
              <span className="text-2xl font-semibold tracking-tight text-[#1F2937]">CookWise</span>
            </Link>
            <span className="rounded-full border border-emerald-200/70 bg-emerald-50/80 px-3 py-1 text-[11px] text-emerald-700">
              AI Kitchen Assistant
            </span>
          </div>

          <div className="mb-5">
            <h1 className="text-3xl font-semibold leading-tight text-[#1F2937]">
              {step === "login" ? "CookWise’a hoş geldin" : "E-postanı doğrula"}
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              {step === "login"
                ? "Tarif, akıllı sepet ve yapay zeka mutfak asistanına tek ekrandan ulaş."
                : "Hesabını aktifleştirmek için e-postana gelen 6 haneli kodu gir."}
            </p>
          </div>

          <AnimatePresence mode="wait">
            {step === "login" ? (
              <motion.form
                key="login-form"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                onSubmit={handleSubmit(onSubmit)}
                className="space-y-4"
              >
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
                  <label htmlFor="email" className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
                    E-posta
                  </label>
                  <div className="group relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-500/80" />
                    <input
                      {...register("email")}
                      id="email"
                      type="email"
                      placeholder="ornek@email.com"
                      className="w-full rounded-2xl border border-emerald-200/70 bg-white/85 py-3 pl-10 pr-4 text-sm text-[#1F2937] outline-none transition placeholder:text-slate-400 focus:border-[#22D3EE]/70 focus:ring-2 focus:ring-[#22D3EE]/30"
                    />
                  </div>
                  {errors.email ? <p className="ml-1 mt-1.5 text-xs text-rose-300">{errors.email.message}</p> : null}
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
                      Şifre
                    </label>
                    <Link href="#" className="text-xs text-[#0ea5b7] hover:text-[#0f766e] transition">
                      Şifremi Unuttum
                    </Link>
                  </div>
                  <div className="group relative">
                    <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-500/80" />
                    <input
                      {...register("password")}
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      className="w-full rounded-2xl border border-emerald-200/70 bg-white/85 py-3 pl-10 pr-4 text-sm text-[#1F2937] outline-none transition placeholder:text-slate-400 focus:border-[#22D3EE]/70 focus:ring-2 focus:ring-[#22D3EE]/30"
                    />
                  </div>
                  {errors.password ? <p className="ml-1 mt-1.5 text-xs text-rose-300">{errors.password.message}</p> : null}
                </motion.div>

                {serverError ? (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      isSocialInfo
                        ? "border-emerald-200/45 bg-emerald-50/95 text-emerald-800"
                        : "border-rose-200/55 bg-rose-50/95 text-rose-700"
                    }`}
                  >
                    {serverError}
                  </motion.div>
                ) : null}

                <motion.button
                  type="submit"
                  disabled={isLoading}
                  whileTap={{ scale: 0.98 }}
                  className="w-full rounded-2xl bg-gradient-to-r from-[#16C47F] via-[#22D3EE] to-[#16C47F] py-3 text-sm font-semibold text-white shadow-[0_20px_40px_-20px_rgba(34,211,238,0.85)] transition hover:-translate-y-0.5 disabled:opacity-70"
                >
                  {isLoading ? "Giriş yapılıyor..." : "Giriş Yap"}
                </motion.button>
              </motion.form>
            ) : (
              <motion.form
                key="verify-form"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                onSubmit={handleVerifySubmit}
                className="space-y-4"
              >
                <div>
                  <label htmlFor="code" className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
                    Doğrulama Kodu
                  </label>
                  <input
                    id="code"
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    placeholder="123456"
                    maxLength={6}
                    className="w-full rounded-2xl border border-emerald-200/70 bg-white/85 px-4 py-3 text-center text-xl tracking-[0.48em] text-[#1F2937] outline-none transition placeholder:text-slate-400 focus:border-[#22D3EE]/70 focus:ring-2 focus:ring-[#22D3EE]/30"
                  />
                </div>

                {serverError ? (
                  <div className="rounded-2xl border border-rose-200/55 bg-rose-50/95 px-4 py-3 text-sm text-rose-700">{serverError}</div>
                ) : null}

                <motion.button
                  type="submit"
                  disabled={isLoading}
                  whileTap={{ scale: 0.98 }}
                  className="w-full rounded-2xl bg-gradient-to-r from-[#16C47F] via-[#22D3EE] to-[#16C47F] py-3 text-sm font-semibold text-white shadow-[0_20px_40px_-20px_rgba(34,211,238,0.85)] transition hover:-translate-y-0.5 disabled:opacity-70"
                >
                  {isLoading ? "Doğrulanıyor..." : "Doğrula ve Giriş Yap"}
                </motion.button>
              </motion.form>
            )}
          </AnimatePresence>

          {step === "login" ? (
            <>
              <div className="my-5 flex items-center gap-3 text-xs text-slate-500">
                <div className="h-px flex-1 bg-emerald-200/70" />
                <span>veya</span>
                <div className="h-px flex-1 bg-emerald-200/70" />
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={handleGoogleLogin}
                  disabled={!isGoogleAuthReady}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200/70 bg-white/85 px-3 py-2.5 text-xs font-medium text-slate-700 transition hover:bg-emerald-50/85 disabled:opacity-50"
                >
                  <span className="font-semibold text-[#22D3EE]">G</span>
                  Google ile giriş
                </button>
                <button
                  type="button"
                  onClick={handleAppleLoginInfo}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200/70 bg-white/85 px-3 py-2.5 text-xs font-medium text-slate-700 transition hover:bg-emerald-50/85"
                >
                  <Apple className="h-4 w-4" />
                  Apple ile giriş
                </button>
              </div>
            </>
          ) : null}

          <p className="mt-5 text-center text-sm text-slate-600">
            Hesabın yok mu?{" "}
            <Link href="/register" className="font-semibold text-[#0ea5b7] hover:text-[#0f766e] transition">
              Hemen Kayıt Ol
            </Link>
          </p>
          <p className="mt-2 text-center text-xs text-slate-500">
            Yönetici misin?{" "}
            <Link href="/admin/login" className="font-semibold text-[#0ea5b7] hover:text-[#0f766e] transition">
              Admin girişi
            </Link>
          </p>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 26 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12, duration: 0.45 }}
          className="relative hidden min-h-[620px] rounded-[34px] border border-emerald-200/70 bg-white/72 p-6 shadow-[0_45px_120px_-56px_rgba(22,196,127,0.35)] backdrop-blur-2xl lg:block"
        >
          <div className="absolute right-6 top-6 rounded-full border border-emerald-200/70 bg-emerald-50/80 px-3 py-1 text-xs text-emerald-700">
            AI destekli mutfak deneyimi
          </div>

          <div className="mb-6 max-w-xl">
            <h2 className="text-3xl font-semibold leading-tight text-[#1F2937]">
              Tarif, alışveriş ve akıllı öneriler tek panelde
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              CookWise AI, ne pişireceğini planlar, stokta olan ürünlerle sepet önerir ve mutfak sürecini adım adım yönetir.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <motion.div
              whileHover={{ y: -4 }}
              className="rounded-3xl border border-emerald-200/70 bg-white/88 p-4 backdrop-blur-xl"
            >
              <div className="mb-3 inline-flex rounded-xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] p-2">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <p className="text-sm font-semibold text-[#1F2937]">AI Tarif Akışı</p>
              <div className="mt-3 space-y-2 text-xs text-slate-600">
                <div className="rounded-xl bg-emerald-50/80 px-3 py-2">“2 kişilik sebzeli makarna öner”</div>
                <div className="rounded-xl border border-[#22D3EE]/35 bg-white px-3 py-2">
                  Hazırlık 10 dk • Pişirme 18 dk
                </div>
              </div>
            </motion.div>

            <motion.div
              whileHover={{ y: -4 }}
              className="rounded-3xl border border-emerald-200/70 bg-white/88 p-4 backdrop-blur-xl"
            >
              <div className="mb-3 inline-flex rounded-xl bg-gradient-to-r from-[#22D3EE] to-[#16C47F] p-2">
                <ShoppingCart className="h-4 w-4 text-white" />
              </div>
              <p className="text-sm font-semibold text-[#1F2937]">Akıllı Sepet</p>
              <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
                <li>- Domates Kg</li>
                <li>- Soğan Demet</li>
                <li>- Makarna 500g</li>
              </ul>
            </motion.div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <motion.div
              whileHover={{ y: -4 }}
              className="rounded-3xl border border-emerald-200/70 bg-white/88 p-4 backdrop-blur-xl"
            >
              <p className="mb-2 inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#22D3EE]">
                <WandSparkles className="h-3.5 w-3.5" />
                Öneri Kartı
              </p>
              <p className="text-sm text-slate-700">Bugün için öneri: Mercimek çorbası + fırın sebze + ayran.</p>
            </motion.div>
            <motion.div
              whileHover={{ y: -4 }}
              className="rounded-3xl border border-emerald-200/70 bg-white/88 p-4 backdrop-blur-xl"
            >
              <p className="mb-2 inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#F59E0B]">
                <Sparkles className="h-3.5 w-3.5" />
                AI Notu
              </p>
              <p className="text-sm text-slate-700">Haftalık plan oluşturarak alışveriş maliyetini düşürebilirsin.</p>
            </motion.div>
          </div>
        </motion.section>
      </div>
    </main>
  );
}
