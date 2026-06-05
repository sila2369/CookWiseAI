import axios from "axios";
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

const FALLBACK_API_URL =
  Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? FALLBACK_API_URL;

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 20000,
});

export const SESSION_TOKEN_KEY = "cookwise_mobile_access_token";

api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync(SESSION_TOKEN_KEY);
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
