import type { TreatmentCatalog } from "../appTypes";
import { apiBase } from "./apiBase";

export async function fetchTreatmentCatalog(diseaseKey: string, signal?: AbortSignal): Promise<TreatmentCatalog | null> {
  if (apiBase == null || !diseaseKey) return null;
  try {
    const url = apiBase === ""
      ? `/.netlify/functions/treatments-tomato?disease_key=${encodeURIComponent(diseaseKey)}`
      : `${apiBase}/api/treatments/tomato/${encodeURIComponent(diseaseKey)}`;
    const res = await fetch(url, { signal });
    if (!res.ok) return null;
    return (await res.json()) as TreatmentCatalog;
  } catch {
    return null;
  }
}
