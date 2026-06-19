import type { Provenance } from "../data/sources";
import { apiBase } from "./apiBase";

export interface TomatoMarketPrice {
  crop: string;
  market: string;
  low_egp_per_kg: number | null;
  high_egp_per_kg: number | null;
  unit: string;
  source: string;
  source_url: string;
  as_of: string;
  live: boolean;
  note: string;
}

export function marketProvenance(price: TomatoMarketPrice | null | undefined): Provenance {
  return price?.live ? "live" : "estimated_range";
}

export function marketPriceLabel(price: TomatoMarketPrice | null | undefined): string {
  if (!price?.live || price.low_egp_per_kg == null || price.high_egp_per_kg == null) return "not live";
  const low = Number.isInteger(price.low_egp_per_kg) ? price.low_egp_per_kg.toFixed(0) : String(price.low_egp_per_kg);
  const high = Number.isInteger(price.high_egp_per_kg) ? price.high_egp_per_kg.toFixed(0) : String(price.high_egp_per_kg);
  return `${low}-${high} EGP/kg`;
}

export async function fetchTomatoMarketPrice(signal?: AbortSignal): Promise<TomatoMarketPrice | null> {
  try {
    const base = apiBase ?? "";
    const res = await fetch(`${base}/api/market/tomato`, { signal });
    if (!res.ok) return null;
    return (await res.json()) as TomatoMarketPrice;
  } catch {
    return null;
  }
}
