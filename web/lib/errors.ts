import axios from "axios";

export function getApiErrorDetail(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) {
    return err.message;
  }
  if (!axios.isAxiosError(err)) {
    return fallback;
  }
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string }) => item.msg)
      .filter(Boolean)
      .join(" ");
  }
  return fallback;
}
