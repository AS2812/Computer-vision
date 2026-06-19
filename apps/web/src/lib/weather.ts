// ─────────────────────────────────────────────────────────────────────────────
// Weather (Open-Meteo, no API key) + a per-disease weather-PRESSURE heuristic.
//
// Pressure is a rule-of-thumb score (0..100) from the CURRENT weather, by disease
// ecology — e.g. late blight (oomycete) loves cool + wet + humid; spider mites
// (a pest) explode in hot + dry. It is NOT a forecast of infection, and it never
// drives the safety gate. Labelled a heuristic in the UI.
// ─────────────────────────────────────────────────────────────────────────────

import type { Bi, CauseType } from "../data/diseases";
import type { Provenance } from "../data/sources";

export interface WeatherNow {
  tempC: number;
  humidityPct: number | null;
  precipMm: number;
  windKph: number;
  code: number;
  condition: Bi;
  provenance: Provenance; // "live" when read from Open-Meteo, else "estimated_range"
  source: Bi;
}

// Alexandria, Egypt — the default when the farmer has not shared GPS.
export const DEFAULT_COORDS = { lat: 31.2001, lon: 29.9187 };

function conditionFor(code: number): Bi {
  if (code === 0) return { en: "clear", ar: "صحو" };
  if ([1, 2, 3].includes(code)) return { en: "partly cloudy", ar: "غائم جزئيًا" };
  if ([45, 48].includes(code)) return { en: "fog", ar: "ضباب" };
  if ([51, 53, 55, 56, 57].includes(code)) return { en: "drizzle", ar: "رذاذ" };
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return { en: "rain", ar: "أمطار" };
  if ([71, 73, 75, 77, 85, 86].includes(code)) return { en: "snow", ar: "ثلوج" };
  if ([95, 96, 99].includes(code)) return { en: "thunderstorm", ar: "عاصفة رعدية" };
  return { en: "unknown", ar: "غير معروف" };
}

/** A fixed, clearly-labelled Egypt reference used when no live reading is available. */
export function referenceWeather(): WeatherNow {
  return {
    tempC: 24,
    humidityPct: 55,
    precipMm: 0,
    windKph: 9,
    code: 2,
    condition: { en: "partly cloudy", ar: "غائم جزئيًا" },
    provenance: "estimated_range",
    source: { en: "Egypt reference (not live)", ar: "مرجع مصري (مش مباشر)" },
  };
}

/** Read current weather from Open-Meteo (no key). Returns null on any failure. */
export async function fetchWeather(lat: number, lon: number, signal?: AbortSignal): Promise<WeatherNow | null> {
  try {
    const url =
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
      `&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&timezone=auto`;
    const res = await fetch(url, { signal });
    if (!res.ok) return null;
    const data = await res.json();
    const c = data.current;
    const code = Number(c.weather_code);
    return {
      tempC: Math.round(Number(c.temperature_2m)),
      humidityPct: c.relative_humidity_2m != null ? Math.round(Number(c.relative_humidity_2m)) : null,
      precipMm: Number(c.precipitation) || 0,
      windKph: Math.round(Number(c.wind_speed_10m)),
      code,
      condition: conditionFor(code),
      provenance: "live",
      source: { en: "Open-Meteo (live)", ar: "Open-Meteo (مباشر)" },
    };
  } catch {
    return null;
  }
}

export type PressureLevel = "low" | "medium" | "high" | "na";

export interface WeatherPressure {
  score: number; // 0..100
  level: PressureLevel;
  reason: Bi;
}

function levelFor(score: number): PressureLevel {
  if (score >= 70) return "high";
  if (score >= 45) return "medium";
  return "low";
}

/**
 * Per-disease weather-pressure score from the current weather.
 * @param cause the disease cause type (drives the ecology window)
 */
export function weatherPressure(cause: CauseType, w: WeatherNow): WeatherPressure {
  const temp = w.tempC;
  const rh = w.humidityPct;
  const precip = w.precipMm;
  const wet = precip > 0.1 || (rh != null && rh >= 85);
  const humid = rh != null && rh >= 70;

  const factor = (en: string, ar: string): Bi => ({ en, ar });
  const parts: string[] = [];
  const partsAr: string[] = [];
  const note = (cond: boolean, en: string, ar: string) => {
    if (cond) {
      parts.push(en);
      partsAr.push(ar);
    }
  };

  let score = 20;
  if (cause === "oomycete") {
    const cool = temp >= 8 && temp <= 24;
    note(cool, "cool", "برودة");
    note(wet, "wet", "بلل");
    note(humid, "humid", "رطوبة");
    const hits = [cool, wet, humid].filter(Boolean).length;
    score = hits >= 3 ? 92 : hits === 2 ? 72 : hits === 1 ? 42 : 15;
  } else if (cause === "fungal") {
    const warm = temp >= 18 && temp <= 30;
    note(warm, "warm", "دفء");
    note(humid, "humid", "رطوبة");
    note(wet, "leaf wetness", "بلل الورق");
    const hits = [warm, humid, wet].filter(Boolean).length;
    score = hits >= 3 ? 88 : hits === 2 ? 66 : hits === 1 ? 42 : 18;
  } else if (cause === "bacterial") {
    const warm = temp >= 18 && temp <= 32;
    note(warm, "warm", "دفء");
    note(wet, "splashing wet", "بلل ورشّ");
    note(humid, "humid", "رطوبة");
    const hits = [warm, wet, humid].filter(Boolean).length;
    score = hits >= 3 ? 88 : hits === 2 ? 64 : hits === 1 ? 40 : 18;
  } else if (cause === "mite") {
    const hot = temp >= 30;
    const dry = (rh == null || rh < 50) && precip < 0.1;
    note(hot, "hot", "حرارة");
    note(dry, "dry/dusty", "جفاف وتربة");
    const hits = [hot, dry].filter(Boolean).length;
    score = hot && dry ? 85 : hits === 1 ? 55 : 22;
  } else if (cause === "viral") {
    // Driven by the whitefly vector (warm favours it), not by leaf wetness.
    const warm = temp >= 20 && temp <= 35;
    note(warm, "warm (favours whitefly)", "دفء (بيساعد الذبابة البيضا)");
    score = warm ? 55 : 30;
    const reason: Bi = {
      en: `Virus spread depends on the whitefly/contact, not the weather directly. ${parts.length ? "Now: " + parts.join(", ") + "." : ""}`,
      ar: `انتشار الفيروس بيعتمد على الذبابة البيضا/اللمس، مش الطقس مباشرة. ${partsAr.length ? "دلوقتي: " + partsAr.join("، ") + "." : ""}`,
    };
    return { score, level: levelFor(score), reason };
  } else {
    return { score: 0, level: "na", reason: factor("Not weather-driven.", "مش متأثّر بالطقس.") };
  }

  const reason: Bi = {
    en: parts.length ? `Favourable factors now: ${parts.join(", ")}.` : "Few favourable factors right now.",
    ar: partsAr.length ? `عوامل مساعدة دلوقتي: ${partsAr.join("، ")}.` : "عوامل مساعدة قليلة دلوقتي.",
  };
  return { score, level: levelFor(score), reason };
}
