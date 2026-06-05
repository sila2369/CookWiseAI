import axios from "axios";

function resolveApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  const fallbackUrl = "http://localhost:8000";

  if (!envUrl) {
    return fallbackUrl;
  }

  // Geliştirmede yanlışlıkla frontend portu verilirse backend portuna sabitle.
  if (process.env.NODE_ENV !== "production") {
    try {
      const parsed = new URL(envUrl);
      if (parsed.hostname === "localhost" && parsed.port === "3000") {
        return fallbackUrl;
      }
    } catch {
      return fallbackUrl;
    }
  }

  return envUrl;
}

const baseURL = resolveApiBaseUrl();

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// Ensure token is attached on every request, even after refresh/hot-reload.
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("cookwise_access_token");
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
    }
  }
  return config;
});
