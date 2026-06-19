import type { AppAnalysis, Lang } from "../appTypes";
import { diseaseByKey } from "../data/diseases";
import { apiBase } from "./apiBase";
import { marketPriceLabel } from "./market";
import { assistantFunctionUrl, ensureAnonAuth, supabase } from "./supabase";

export interface CropBotAnswer {
  answer: string;
  sources: string[];
  mode: string;
}

function contextFor(analysis: AppAnalysis | null, lang: Lang): string {
  if (!analysis) return "Crop: tomato. No photo analysis is attached.";
  const top = analysis.screening.topKey ? diseaseByKey(analysis.screening.topKey) : null;
  const name = top ? top.name[lang] : "not sure";
  const candidates = analysis.screening.candidates
    .slice(0, 3)
    .map((c) => `${c.name.en} ${Math.round(c.prob * 100)}%`)
    .join(", ");
  const lookalikes = top?.lookalikes
    ?.map((key) => diseaseByKey(key)?.name.en)
    .filter(Boolean)
    .join(", ");
  const market = analysis.marketPrice?.live
    ? `${marketPriceLabel(analysis.marketPrice)} from ${analysis.marketPrice.source} as of ${analysis.marketPrice.as_of}. ${analysis.marketPrice.note}`
    : marketPriceLabel(analysis.marketPrice);
  return [
    "Crop: tomato",
    `Analysis id: ${analysis.id}`,
    `Disease key: ${analysis.screening.topKey ?? "unknown"}`,
    `Current screening: ${name}`,
    `Certainty: ${analysis.screening.certainty}; not a confirmed lab diagnosis`,
    `Candidates: ${candidates || "not enough evidence"}`,
    `Look-alikes: ${lookalikes || "not listed"}`,
    `Visible affected area: ${analysis.extent.extentPct}%`,
    `Image quality: short edge ${analysis.quality.shortEdge}px, blurry=${analysis.quality.blurry}, dark=${analysis.quality.tooDark}`,
    `Weather: ${analysis.weather.tempC}C, ${analysis.weather.condition.en}`,
    `Weather pressure: ${analysis.pressure.score}/100 ${analysis.pressure.level}; ${analysis.pressure.reason.en}`,
    `Market tomato price: ${market}`,
    "Answer only for this crop disease case. If the farmer asks outside the case, bring them back to tomato disease, treatment, prevention, economics, prices, safety, irrigation, or next inspection steps.",
  ].join("\n");
}

export async function askCropBot(question: string, analysis: AppAnalysis | null, lang: Lang): Promise<CropBotAnswer | null> {
  const caseContext = contextFor(analysis, lang).slice(0, 1800);
  const payload = {
    question: question.trim().slice(0, 500),
    language: lang,
    analysis_id: analysis?.id,
    case_context: caseContext,
  };

  if (assistantFunctionUrl) {
    if (assistantFunctionUrl.includes("supabase.co")) await ensureAnonAuth();
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      const token = supabase ? (await supabase.auth.getSession()).data.session?.access_token : undefined;
      const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
      if (anonKey) headers.apikey = anonKey;
      if (token) headers.Authorization = `Bearer ${token}`;
      else if (anonKey) headers.Authorization = `Bearer ${anonKey}`;

      const res = await fetch(assistantFunctionUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(130_000),
      });
      if (res.ok) return (await res.json()) as CropBotAnswer;
    } catch {
      // Fall through to the optional local/Render FastAPI backend.
    }
  }

  if (!apiBase) return null;
  try {
    const res = await fetch(`${apiBase}/api/assistant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(130_000),
    });
    if (!res.ok) return null;
    return (await res.json()) as CropBotAnswer;
  } catch {
    return null;
  }
}
