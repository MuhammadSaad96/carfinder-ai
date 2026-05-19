export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CarListing {
  title: string;
  price: number | null;
  price_display: string;
  city: string | null;
  year: number | null;
  mileage: number | null;
  mileage_display: string | null;
  transmission: string | null;
  fuel_type: string | null;
  image: string | null;
  images: string[];
  url: string;
  score: number;
  ai_explanation: string | null;
  condition_note: string | null;
  source: string;
  is_recommended: boolean;
}

export interface ModelInfo {
  new_price?: string;
  fuel_average?: string;
  engine?: string;
  variants?: string[];
  known_for?: string;
  check_before_buy?: string;
}

export interface SearchResponse {
  query: string;
  filters: Record<string, unknown>;
  cars: CarListing[];
  total_found: number;
  ai_summary: string | null;
  model_info: ModelInfo;
  source: string;
}

export function proxyImage(url: string | null): string | null {
  if (!url) return null;
  return `${API_URL}/proxy-image?url=${encodeURIComponent(url)}`;
}

export async function searchCars(query: string): Promise<SearchResponse> {
  const res = await fetch(`${API_URL}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
    signal: AbortSignal.timeout(180_000),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail || `Server error: ${res.status}`
    );
  }

  return res.json();
}
