// AgroVision hosted crop assistant (Supabase Edge Function).
//
// This keeps the OpenCode/Zen key server-side. The browser sends only a bounded
// tomato-case context and the farmer question. The assistant must not invent
// treatment products, prices, doses, or disease facts outside that context.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

interface AssistantRequest {
  question?: string;
  language?: "en" | "ar";
  analysis_id?: string;
  case_context?: string;
}

function isArabic(text: string): boolean {
  return /[\u0600-\u06ff]/.test(text);
}

function fallbackAnswer(question: string, lang: "en" | "ar", context: string): string {
  const hasCase = context.trim().length > 20;
  if (lang === "ar") {
    return [
      hasCase
        ? "أنا شايف سياق حالة الطماطم الحالية، لكن المساعد الأونلاين غير متصل الآن."
        : "المساعد الأونلاين غير متصل الآن، ومفيش سياق تحليل صورة كفاية.",
      "استخدم كتالوج العلاج داخل التطبيق، وابدأ بالوقاية الآمنة: إزالة الأوراق المصابة، تقليل بلل الورق، تهوية كويسة، ومتابعة ظهر الورقة.",
      "لو السؤال عن الرش أو السعر: أكّد التشخيص والتسجيل في لجنة المبيدات، واقرأ لافتة المنتج، وخلي مهندس زراعي يراجع الجرعة قبل أي استخدام.",
      `سؤالك: ${question}`,
    ].join("\n");
  }
  return [
    hasCase
      ? "I can see the current tomato-case context, but the online assistant provider is unavailable right now."
      : "The online assistant provider is unavailable right now, and there is not enough attached case context.",
    "Use the treatment catalog in the app, and start with safe protection: remove infected leaves, keep foliage dry, improve ventilation, and inspect leaf undersides.",
    "For spraying or prices: confirm the diagnosis, verify APC registration, read the product label, and ask an agronomist to approve the dose before use.",
    `Your question: ${question}`,
  ].join("\n");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...CORS, "Content-Type": "application/json" },
    });
  }

  let payload: AssistantRequest;
  try {
    payload = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid JSON body" }), {
      status: 400,
      headers: { ...CORS, "Content-Type": "application/json" },
    });
  }

  const question = String(payload.question ?? "").trim().slice(0, 500);
  if (!question) {
    return new Response(JSON.stringify({ error: "question is required" }), {
      status: 400,
      headers: { ...CORS, "Content-Type": "application/json" },
    });
  }

  const lang: "en" | "ar" = payload.language === "ar" || isArabic(question) ? "ar" : "en";
  const caseContext = String(payload.case_context ?? "").slice(0, 5000);
  const apiUrl = Deno.env.get("EXTERNAL_LLM_API_URL") ?? "https://opencode.ai/zen/v1/chat/completions";
  const apiKey = Deno.env.get("EXTERNAL_LLM_API_KEY");
  const model = Deno.env.get("EXTERNAL_LLM_MODEL") ?? "deepseek-v4-flash-free";

  if (!apiKey) {
    return new Response(JSON.stringify({
      answer: fallbackAnswer(question, lang, caseContext),
      sources: ["AgroVision hosted assistant fallback", "Frontend case context"],
      mode: "api-unavailable",
    }), { headers: { ...CORS, "Content-Type": "application/json" } });
  }

  const system = lang === "ar"
    ? "أنت مساعد AgroVision Egypt الزراعي للطماطم فقط. جاوب بالعربي المصري البسيط. استخدم سياق الحالة المرسل فقط ولا تخترع أسماء منتجات أو جرعات أو أسعار. لو السعر أو الجرعة غير موجودة قل أكدها محليا. لا تعطي أمر رش نهائي؛ ذكّر دائما بقراءة اللافتة ومراجعة مهندس زراعي."
    : "You are AgroVision Egypt's farming assistant for tomato only. Reply in simple English. Use only the supplied case context. Never invent product names, doses, prices, or facts. If an exact price or dose is missing, say to confirm locally. Do not issue a final spray order; always remind the farmer to read the label and consult an agronomist.";

  const body = {
    model,
    temperature: Number(Deno.env.get("EXTERNAL_LLM_TEMPERATURE") ?? 0.3),
    max_tokens: Number(Deno.env.get("EXTERNAL_LLM_MAX_TOKENS") ?? 2000),
    reasoning_effort: Deno.env.get("EXTERNAL_LLM_REASONING_EFFORT") ?? "low",
    messages: [
      { role: "system", content: system },
      {
        role: "user",
        content: [
          lang === "ar" ? "سؤال المزارع:" : "Farmer question:",
          question,
          "",
          lang === "ar" ? "سياق الحالة من التطبيق:" : "Case context from the app:",
          caseContext || (lang === "ar" ? "لا يوجد تحليل صورة مرفق." : "No attached image analysis."),
        ].join("\n"),
      },
    ],
  };

  try {
    const res = await fetch(apiUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(Number(Deno.env.get("EXTERNAL_LLM_TIMEOUT_MS") ?? 90000)),
    });
    if (!res.ok) throw new Error(`provider ${res.status}`);
    const data = await res.json();
    const answer = String(data?.choices?.[0]?.message?.content ?? "").trim();
    if (!answer) throw new Error("empty provider answer");

    return new Response(JSON.stringify({
      answer,
      sources: ["Online grounded assistant", "Frontend case context", "AgroVision reviewed tomato guidance"],
      mode: "external-grounded-assistant",
    }), { headers: { ...CORS, "Content-Type": "application/json" } });
  } catch {
    return new Response(JSON.stringify({
      answer: fallbackAnswer(question, lang, caseContext),
      sources: ["AgroVision hosted assistant fallback", "Frontend case context"],
      mode: "api-unavailable",
    }), { headers: { ...CORS, "Content-Type": "application/json" } });
  }
});
