"use client";

import Link from "next/link";
import { ArrowRight, Bot, Check, ShoppingCart, Sparkles } from "lucide-react";

const ingredients = ["Dana Kiyma", "Lazanya", "Feslegen", "Ceri Domates", "Zeytinyagi", "Mozzarella"];

export default function LandingPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#F4FFF8] text-[#1F2937]">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-emerald-300/30 blur-3xl" />
        <div className="absolute right-0 top-10 h-[28rem] w-[28rem] rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="absolute bottom-[-8rem] left-[30%] h-80 w-80 rounded-full bg-amber-200/25 blur-3xl" />
      </div>

      <nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-8">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-[#16C47F] to-[#22D3EE] text-sm font-black text-white shadow-[0_18px_34px_-20px_rgba(34,211,238,0.8)]">
            CW
          </span>
          <span className="text-xl font-semibold tracking-tight text-[#1F2937]">CookWise</span>
        </Link>

        <div className="flex items-center gap-2">
          <a href="#how" className="hidden rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-white/80 md:inline-flex">
            Nasil Calisir?
          </a>
          <a href="#features" className="hidden rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-white/80 md:inline-flex">
            Ozellikler
          </a>
          <Link
            href="/login"
            className="rounded-2xl border border-emerald-200/80 bg-white/80 px-4 py-2 text-sm font-semibold text-[#0f766e] shadow-sm transition hover:bg-emerald-50"
          >
            Giris Yap
          </Link>
        </div>
      </nav>

      <section className="relative z-10 mx-auto grid min-h-[calc(100vh-86px)] max-w-7xl grid-cols-1 items-center gap-8 px-5 pb-8 pt-4 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
        <div className="max-w-2xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-200/80 bg-white/75 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700 shadow-sm backdrop-blur-xl">
            <Sparkles className="h-4 w-4 text-[#16C47F]" />
            AI destekli market
          </div>

          <h1 className="text-5xl font-semibold leading-[0.98] tracking-[-0.04em] text-[#1F2937] md:text-6xl xl:text-7xl">
            Tarif soyle,
            <span className="block bg-gradient-to-r from-[#16C47F] via-[#0ea5b7] to-[#22D3EE] bg-clip-text text-transparent">
              sepetin hazir olsun.
            </span>
          </h1>

          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
            Ne pisirmek istedigini yaz. CookWise malzemeleri eslestirir, stoktaki urunlerle sepet olusturur ve alisverisi tek ekranda toparlar.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-[#16C47F] via-[#22D3EE] to-[#16C47F] px-6 py-3 text-sm font-semibold text-white shadow-[0_24px_48px_-24px_rgba(34,211,238,0.9)] transition hover:-translate-y-0.5"
            >
              Hemen Basla
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#how"
              className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200/80 bg-white/80 px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-emerald-50"
            >
              Nasil Calisir?
            </a>
          </div>

          <div className="mt-8 grid max-w-xl grid-cols-3 gap-3">
            {[
              ["10k+", "aktif kullanici"],
              ["3 dk", "sepet hazirlama"],
              ["24/7", "AI asistan"],
            ].map(([value, label]) => (
              <div key={label} className="rounded-3xl border border-emerald-200/70 bg-white/70 p-4 shadow-sm backdrop-blur-xl">
                <p className="text-2xl font-semibold text-[#1F2937]">{value}</p>
                <p className="mt-1 text-xs font-medium text-slate-500">{label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative min-h-[560px]">
          <div className="absolute inset-0 rounded-[36px] border border-emerald-200/80 bg-white/60 p-4 shadow-[0_45px_120px_-60px_rgba(22,196,127,0.55)] backdrop-blur-2xl">
            <div className="relative h-full overflow-hidden rounded-[28px] border border-white/80 bg-emerald-50">
              <img src="/salad.png" alt="CookWise tarif ve market deneyimi" className="h-full w-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-tr from-white/80 via-white/20 to-transparent" />
            </div>
          </div>

          <div className="absolute left-6 top-8 rounded-3xl border border-emerald-200/80 bg-white/85 p-4 shadow-[0_24px_70px_-38px_rgba(15,118,110,0.55)] backdrop-blur-xl">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-[#16C47F] to-[#22D3EE]">
                <Bot className="h-5 w-5 text-white" />
              </span>
              <div>
                <p className="text-sm font-semibold text-[#1F2937]">CookWise Asistan</p>
                <p className="text-xs text-slate-500">Tarife gore sepet hazir</p>
              </div>
            </div>
          </div>

          <div className="absolute bottom-8 right-3 w-[min(92%,430px)] rounded-[28px] border border-emerald-200/80 bg-white/90 p-4 shadow-[0_30px_90px_-44px_rgba(15,118,110,0.65)] backdrop-blur-2xl md:right-8">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-[#1F2937]">Akdeniz salatasi + lazanya</p>
                <p className="mt-1 text-xs text-slate-500">Eksik malzemeler eslendi</p>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">6 urun</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {ingredients.map((item) => (
                <span key={item} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold text-[#0f766e]">
                  <Check className="h-3.5 w-3.5 text-[#16C47F]" />
                  {item}
                </span>
              ))}
            </div>

            <Link
              href="/register"
              className="mt-4 flex items-center justify-between rounded-2xl bg-gradient-to-r from-[#16C47F] to-[#22D3EE] px-4 py-3 text-sm font-semibold text-white shadow-[0_18px_35px_-24px_rgba(34,211,238,0.85)]"
            >
              <span className="inline-flex items-center gap-2">
                <ShoppingCart className="h-5 w-5" />
                Malzemeleri sepete ekle
              </span>
              <span>345.50 TL</span>
            </Link>
          </div>
        </div>
      </section>

      <section id="how" className="relative z-10 mx-auto grid max-w-7xl grid-cols-1 gap-4 px-5 pb-10 lg:grid-cols-3 lg:px-8">
        {[
          ["1", "Tarifini yaz", "Ne yapmak istedigini ya da elindeki malzemeleri yaz."],
          ["2", "AI eslestirsin", "CookWise stoktaki urunlerle eksik malzemeleri bulur."],
          ["3", "Sepetin hazir", "Urunleri tek hamlede sepete ekleyip siparise gecebilirsin."],
        ].map(([step, title, body]) => (
          <article key={step} className="rounded-3xl border border-emerald-200/70 bg-white/75 p-5 shadow-sm backdrop-blur-xl">
            <span className="grid h-9 w-9 place-items-center rounded-2xl bg-emerald-50 text-sm font-bold text-emerald-700">{step}</span>
            <h2 className="mt-4 text-lg font-semibold text-[#1F2937]">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
