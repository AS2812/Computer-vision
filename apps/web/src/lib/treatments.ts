import type { TreatmentCatalog } from "../appTypes";
import { apiBase } from "./apiBase";

export async function fetchTreatmentCatalog(diseaseKey: string, signal?: AbortSignal): Promise<TreatmentCatalog | null> {
  if (!diseaseKey) return null;
  try {
    const base = apiBase ?? "";
    const url = base === ""
      ? `/api/treatments/tomato/${encodeURIComponent(diseaseKey)}`
      : `${base}/api/treatments/tomato/${encodeURIComponent(diseaseKey)}`;
    const res = await fetch(url, { signal });
    if (!res.ok) return null;
    return (await res.json()) as TreatmentCatalog;
  } catch {
    return null;
  }
}
