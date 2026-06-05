export function toHighResMigrosImage(imageUrl: string): string {
  if (!imageUrl) return imageUrl;
  return imageUrl.replace(/-\d+x\d+(?=\.(jpg|jpeg|png|webp)$)/i, "");
}

export function getProductImage(imageUrl?: string | null): string {
  if (imageUrl) return toHighResMigrosImage(imageUrl);
  return "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=80";
}

export async function withRetry<T>(fn: () => Promise<T>, retries = 2, delayMs = 800): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }
  throw lastError;
}
