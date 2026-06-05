"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/context/AuthContext";
import { getApiErrorDetail } from "@/lib/errors";

const schema = z.object({
  email: z.string().email("Geçerli bir e-posta girin"),
  password: z.string().min(1, "Şifre gerekli"),
});

type FormData = z.infer<typeof schema>;

export default function AdminLoginPage() {
  const { loginAdmin } = useAuth();
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setIsLoading(true);
    setServerError("");
    try {
      await loginAdmin(data.email, data.password);
    } catch (err: unknown) {
      setServerError(getApiErrorDetail(err, "Admin girişi yapılamadı."));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0d1f1b] text-white flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl border border-emerald-200/20 bg-white/10 backdrop-blur-xl p-6 shadow-[0_24px_60px_-32px_rgba(16,185,129,0.65)]">
        <p className="text-xs uppercase tracking-[0.22em] text-emerald-200/80">CookWise Yönetim</p>
        <h1 className="text-2xl font-semibold mt-2">Admin Girişi</h1>
        <p className="text-sm text-emerald-100/80 mt-1">
          Bu alan sadece `is_admin=true` hesaplar içindir.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm mb-1.5">E-posta</label>
            <input
              {...register("email")}
              id="email"
              type="email"
              placeholder="admin@cookwise.com"
              className="w-full rounded-xl border border-white/25 bg-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300/45"
            />
            {errors.email && <p className="text-xs text-red-300 mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm mb-1.5">Şifre</label>
            <input
              {...register("password")}
              id="password"
              type="password"
              placeholder="••••••••"
              className="w-full rounded-xl border border-white/25 bg-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300/45"
            />
            {errors.password && <p className="text-xs text-red-300 mt-1">{errors.password.message}</p>}
          </div>

          {serverError && (
            <div className="rounded-xl border border-red-300/45 bg-red-500/15 px-3 py-2 text-sm text-red-100">
              {serverError}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-xl bg-gradient-to-r from-emerald-300 to-cyan-200 text-[#06332a] font-semibold py-2.5 disabled:opacity-70"
          >
            {isLoading ? "Giriş yapılıyor..." : "Admin Olarak Giriş Yap"}
          </button>
        </form>

        <div className="mt-5 text-sm text-emerald-100/85 flex items-center justify-between">
          <Link href="/login" className="hover:text-white">
            Kullanıcı girişine dön
          </Link>
          <Link href="/" className="hover:text-white">
            Ana sayfa
          </Link>
        </div>
      </div>
    </main>
  );
}
