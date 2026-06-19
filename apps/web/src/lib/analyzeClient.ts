// Calls the `analyze` Edge Function (the ONLY gateway) for the AI second opinion
// and merged advice. Degrades gracefully: any failure or missing config returns
// null, and the app keeps the on-device result.

import { analyzeFunctionUrl, ensureAnonAuth, supabase } from "./supabase";
import type { AiOpinion } from "./screening";

export interface SecondOpinion {
  ai: AiOpinion | null;
  advice: Record<string, unknown> | null;
}

/** Downscale a drawable source to a JPEG data URL for the gateway (keeps payload small). */
export function toJpegDataUrl(source: CanvasImageSource, w: number, h: number, maxSide = 1024, quality = 0.85): string {
  const scale = Math.min(1, maxSide / Math.max(w, h));
  const dw = Math.max(1, Math.round(w * scale));
  const dh = Math.max(1, Math.round(h * scale));
  const canvas = document.createElement("canvas");
  canvas.width = dw;
  canvas.height = dh;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("2D canvas context unavailable");
  ctx.drawImage(source, 0, 0, dw, dh);
  return canvas.toDataURL("image/jpeg", quality);
}

export async function requestSecondOpinion(args: {
  imageDataUrl: string;
  localTop3: Array<{ key: string; prob: number }>;
  signals: Record<string, unknown>;
  lang: string;
}): Promise<SecondOpinion | null> {
  if (!analyzeFunctionUrl) return null;
  await ensureAnonAuth();

  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    // Forward the anon session so the function can attribute (anonymised) logging.
    const token = supabase ? (await supabase.auth.getSession()).data.session?.access_token : undefined;
    const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
    if (anonKey) headers["apikey"] = anonKey;
    if (token) headers["Authorization"] = `Bearer ${token}`;
    else if (anonKey) headers["Authorization"] = `Bearer ${anonKey}`;

    const res = await fetch(analyzeFunctionUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(args),
      signal: AbortSignal.timeout(50_000),
    });
    if (!res.ok) return null;
    return (await res.json()) as SecondOpinion;
  } catch {
    return null;
  }
}
