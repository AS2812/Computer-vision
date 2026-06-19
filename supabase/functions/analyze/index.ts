// ─────────────────────────────────────────────────────────────────────────────
// `analyze` — the ONLY server-side gateway (Supabase Edge Function, Deno).
//
// The browser does the on-device ONNX pass itself; it then calls THIS function for:
//   1. the AI second opinion (a hosted multimodal model). The provider key stays
//      server-side here — never in the browser. Ported from services/api/app/
//      vision_llm.py (same prompt, same OpenAI-compatible request, same JSON parse).
//      Provider stays `mimo-v2.5-free` per the project decision.
//   2. merging the reviewed ARABIC advice from Postgres (tomato_advice) for the
//      predicted disease.
//   3. logging an ANONYMISED report row (no image, no GPS) for monitoring.
//
// HARD RULES honoured here: the AI is a second opinion only. It NEVER returns a
// chemical dose and NEVER unlocks the chemical gate — that lives in the client's
// safety.ts. Any failure degrades to `ai: null` so the app falls back to the
// on-device result. Nothing here blocks the request.
// ─────────────────────────────────────────────────────────────────────────────

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// Tomato diagnoses the vision model may choose from -> internal KB key.
const DISEASE_CHOICES: Record<string, string> = {
  "Septoria leaf spot": "septoria_leaf_spot_tomato",
  "Early blight": "tomato_early_blight",
  "Late blight": "tomato_late_blight",
  "Bacterial spot": "tomato_bacterial_spot",
  "Leaf mold": "tomato_leaf_mold",
  "Target spot": "tomato_target_spot",
  "Spider mites": "tomato_spider_mites",
  "Yellow leaf curl virus": "tomato_yellow_leaf_curl_virus",
  "Mosaic virus": "tomato_mosaic_virus",
  "Healthy": "healthy",
};

const ALIASES: Array<[string, string]> = [
  ["septoria", "septoria_leaf_spot_tomato"],
  ["early blight", "tomato_early_blight"],
  ["alternaria", "tomato_early_blight"],
  ["late blight", "tomato_late_blight"],
  ["phytophthora", "tomato_late_blight"],
  ["bacterial spot", "tomato_bacterial_spot"],
  ["bacterial speck", "tomato_bacterial_spot"],
  ["xanthomonas", "tomato_bacterial_spot"],
  ["leaf mold", "tomato_leaf_mold"],
  ["leaf mould", "tomato_leaf_mold"],
  ["target spot", "tomato_target_spot"],
  ["corynespora", "tomato_target_spot"],
  ["spider mite", "tomato_spider_mites"],
  ["two-spotted", "tomato_spider_mites"],
  ["yellow leaf curl", "tomato_yellow_leaf_curl_virus"],
  ["tylcv", "tomato_yellow_leaf_curl_virus"],
  ["leaf curl", "tomato_yellow_leaf_curl_virus"],
  ["mosaic", "tomato_mosaic_virus"],
  ["tomv", "tomato_mosaic_virus"],
  ["tmv", "tomato_mosaic_virus"],
  ["healthy", "healthy"],
  ["no disease", "healthy"],
];

const SYSTEM_PROMPT =
  "You are a tomato plant pathologist helping Egyptian farmers. Look ONLY at the " +
  "leaf photo and decide the most likely tomato disease. Choose disease names ONLY " +
  "from this list: " + Object.keys(DISEASE_CHOICES).join("; ") + ". " +
  "Be strictly honest: if the photo is blurry, too far, or not a tomato leaf, set " +
  "is_tomato_leaf or not_sure appropriately and lower your confidence. Never invent " +
  "a disease outside the list. Never give a chemical dose. Confidence is your visual " +
  "certainty from 0 to 100. Reply with ONLY a compact JSON object, no prose and no " +
  'markdown fences, using exactly these keys: {"is_tomato_leaf": true/false, ' +
  '"not_sure": true/false, "top": [{"disease": "<name from the list>", "confidence": 0-100}], ' +
  '"visible_signs": "<short phrase>"}. Give up to 3 ranked items in "top".';

function resolveKey(name: string): string | null {
  const text = (name || "").trim().toLowerCase();
  if (!text) return null;
  for (const [label, key] of Object.entries(DISEASE_CHOICES)) {
    if (text === label.toLowerCase()) return key;
  }
  for (const [needle, key] of ALIASES) {
    if (text.includes(needle)) return key;
  }
  return null;
}

function extractJson(content: string): Record<string, unknown> | null {
  let text = (content || "").trim();
  if (text.startsWith("```")) {
    text = text.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  }
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) return null;
  try {
    const parsed = JSON.parse(text.slice(start, end + 1));
    return typeof parsed === "object" && parsed ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

interface AiRanked { key: string; name: string; confidence: number; }
interface AiOpinion {
  isTomatoLeaf: boolean;
  notSure: boolean;
  ranked: AiRanked[];
  visibleSigns: string;
  model: string;
  latencyMs: number;
}

async function callVision(imageDataUrl: string): Promise<AiOpinion | null> {
  const apiUrl = Deno.env.get("EXTERNAL_LLM_API_URL");
  const apiKey = Deno.env.get("EXTERNAL_LLM_API_KEY");
  const model = Deno.env.get("EXTERNAL_VISION_MODEL") ?? "mimo-v2.5-free";
  if (!apiUrl || !apiKey) return null;

  const body = {
    model,
    temperature: 0.1,
    max_tokens: Number(Deno.env.get("EXTERNAL_VISION_MAX_TOKENS") ?? 2000),
    reasoning_effort: Deno.env.get("EXTERNAL_LLM_REASONING_EFFORT") ?? "low",
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: [
          { type: "text", text: "Diagnose this tomato leaf. Egyptian field photo." },
          { type: "image_url", image_url: { url: imageDataUrl } },
        ],
      },
    ],
  };

  const started = Date.now();
  let content = "";
  try {
    const res = await fetch(apiUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(Number(Deno.env.get("EXTERNAL_VISION_TIMEOUT_MS") ?? 45000)),
    });
    if (!res.ok) return null;
    const data = await res.json();
    content = (data?.choices?.[0]?.message?.content ?? "").trim();
  } catch {
    return null;
  }
  if (!content) return null;

  const parsed = extractJson(content);
  if (!parsed) return null;

  const ranked: AiRanked[] = [];
  const seen = new Set<string>();
  for (const item of (parsed.top as Array<Record<string, unknown>>) ?? []) {
    if (!item || typeof item !== "object") continue;
    const key = resolveKey(String(item.disease ?? ""));
    if (!key || seen.has(key)) continue;
    let confidence = Number(item.confidence ?? 0);
    if (Number.isNaN(confidence)) confidence = 0;
    confidence = Math.max(0, Math.min(1, confidence > 1 ? confidence / 100 : confidence));
    ranked.push({ key, name: String(item.disease ?? "").trim(), confidence });
    seen.add(key);
  }
  ranked.sort((a, b) => b.confidence - a.confidence);

  return {
    isTomatoLeaf: parsed.is_tomato_leaf !== false,
    notSure: parsed.not_sure === true || ranked.length === 0,
    ranked: ranked.slice(0, 3),
    visibleSigns: String(parsed.visible_signs ?? "").slice(0, 200),
    model,
    latencyMs: Date.now() - started,
  };
}

function getSupabaseSecretKey(): string | null {
  const legacy = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (legacy) return legacy;

  const secretKeys = Deno.env.get("SUPABASE_SECRET_KEYS");
  if (!secretKeys) return null;
  try {
    const parsed = JSON.parse(secretKeys) as Record<string, string>;
    return parsed.default ?? Object.values(parsed)[0] ?? null;
  } catch {
    return null;
  }
}

function serviceClient() {
  const url = Deno.env.get("SUPABASE_URL");
  const key = getSupabaseSecretKey();
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false } });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405, headers: CORS });

  let payload: {
    imageDataUrl?: string;
    localTop3?: Array<{ key: string; prob: number }>;
    signals?: Record<string, unknown>;
    lang?: string;
  };
  try {
    payload = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid JSON body" }), { status: 400, headers: { ...CORS, "Content-Type": "application/json" } });
  }

  const ai = payload.imageDataUrl ? await callVision(payload.imageDataUrl) : null;

  // Merge reviewed Arabic advice from Postgres for the agreed/most-likely key.
  const topKey = ai?.ranked?.[0]?.key ?? payload.localTop3?.[0]?.key ?? null;
  let advice: Record<string, unknown> | null = null;
  const supabase = serviceClient();
  if (supabase && topKey) {
    try {
      const { data } = await supabase.from("tomato_advice").select("*").eq("key", topKey).maybeSingle();
      advice = data ?? null;
    } catch {
      advice = null;
    }
  }

  // Log an ANONYMISED report (no image bytes, no coordinates).
  if (supabase) {
    try {
      await supabase.from("anonymized_reports").insert({
        local_top_key: payload.localTop3?.[0]?.key ?? null,
        ai_top_key: ai?.ranked?.[0]?.key ?? null,
        ai_agrees: ai && payload.localTop3 ? ai.ranked[0]?.key === payload.localTop3[0]?.key : null,
        ai_model: ai?.model ?? null,
        signals: payload.signals ?? {},
        lang: payload.lang ?? "ar",
      });
    } catch {
      // logging is best-effort; never block the response
    }
  }

  return new Response(JSON.stringify({ ai, advice }), {
    headers: { ...CORS, "Content-Type": "application/json" },
  });
});
