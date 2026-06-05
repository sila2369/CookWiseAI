"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { signInWithGoogleAndGetIdToken } from "@/lib/firebase";

export type AuthUser = {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at?: string;
  updated_at?: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  isReady: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginAdmin: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  registerWithGoogle: () => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  verifyEmail: (email: string, code: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = "cookwise_access_token";
const USER_KEY = "cookwise_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    try {
      const t = localStorage.getItem(TOKEN_KEY);
      const raw = localStorage.getItem(USER_KEY);
      if (t && raw) {
        setToken(t);
        setUser(JSON.parse(raw) as AuthUser);
        api.defaults.headers.common.Authorization = `Bearer ${t}`;
      }
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    setIsReady(true);
  }, []);

  useEffect(() => {
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common.Authorization;
    }
  }, [token]);

  const persistSession = useCallback((accessToken: string, authUser: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(USER_KEY, JSON.stringify(authUser));
    api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
    setToken(accessToken);
    setUser(authUser);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{
      access_token: string;
      token_type: string;
      expires_in: number;
      user: AuthUser;
    }>("/api/v1/auth/login", { email, password });

    persistSession(data.access_token, data.user);
    router.push(data.user.is_admin ? "/admin" : "/dashboard");
  }, [persistSession, router]);

  const loginAdmin = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{
      access_token: string;
      token_type: string;
      expires_in: number;
      user: AuthUser;
    }>("/api/v1/auth/login", { email, password });

    if (!data.user.is_admin) {
      throw new Error("Bu hesap admin yetkisine sahip değil.");
    }

    persistSession(data.access_token, data.user);
    router.push("/admin");
  }, [persistSession, router]);

  const loginWithGoogle = useCallback(async () => {
    const firebaseIdToken = await signInWithGoogleAndGetIdToken();
    const { data } = await api.post<{
      access_token: string;
      token_type: string;
      expires_in: number;
      user: AuthUser;
    }>("/api/v1/auth/firebase-login", { id_token: firebaseIdToken });

    persistSession(data.access_token, data.user);
    router.push(data.user.is_admin ? "/admin" : "/dashboard");
  }, [persistSession, router]);

  const registerWithGoogle = useCallback(async () => {
    // Firebase OAuth akışında yeni kullanıcı varsa backend upsert ile kaydedilir,
    // varsa mevcut hesapla giriş yapılır.
    await loginWithGoogle();
  }, [loginWithGoogle]);

  const register = useCallback(
    async (email: string, password: string, full_name: string) => {
      await api.post("/api/v1/auth/register", {
        full_name,
        email,
        password,
      });
      // Do not auto-login here because the user must verify their email first.
    },
    []
  );

  const verifyEmail = useCallback(async (email: string, code: string) => {
    const { data } = await api.post<{
      access_token: string;
      token_type: string;
      expires_in: number;
      user: AuthUser;
    }>("/api/v1/auth/verify-email", { email, code });

    persistSession(data.access_token, data.user);
    router.push(data.user.is_admin ? "/admin" : "/dashboard");
  }, [persistSession, router]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    router.push("/login");
  }, [router]);

  const value = useMemo(
    () => ({
      user,
      token,
      isReady,
      login,
      loginAdmin,
      loginWithGoogle,
      registerWithGoogle,
      register,
      verifyEmail,
      logout,
    }),
    [user, token, isReady, login, loginAdmin, loginWithGoogle, registerWithGoogle, register, verifyEmail, logout]
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth yalnızca AuthProvider içinde kullanılmalıdır");
  }
  return ctx;
}
