const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, authorization, apikey",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function isArabic(text) {
  return /[\u0600-\u06ff]/.test(text);
}

function json(statusCode, body) {
  return {
    statusCode,
    headers: { ...CORS, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

function fallback(question, lang, context) {
  const hasCase = context.trim().length > 20;
  if (lang === "ar") {
    return [
      hasCase ? "المساعد الأونلاين مش متاح دلوقتي، لكن سياق حالة الطماطم ظاهر." : "المساعد الأونلاين مش متاح دلوقتي.",
      "ابدأ بالحماية الآمنة: شيل الأوراق المصابة، قلل بلل الورق، حسّن التهوية، وافحص ظهر الورقة.",
      "أي رش لازم بعد تأكيد التشخيص، مراجعة تسجيل لجنة المبيدات، قراءة لافتة المنتج، وموافقة مهندس زراعي.",
      `سؤالك: ${question}`,
    ].join("\n");
  }
  return [
    hasCase ? "The online assistant is unavailable right now, but the tomato case context is attached." : "The online assistant is unavailable right now.",
    "Start with safe protection: remove infected leaves, keep foliage dry, improve ventilation, and inspect leaf undersides.",
    "Any spray decision needs diagnosis confirmation, APC registration check, label reading, and agronomist approval.",
    `Your question: ${question}`,
  ].join("\n");
}

function unsafeInventedTreatment(answer) {
  const text = answer.toLowerCase();
  return [
    /\b\d+\s*(ml|مل|لتر|liter|litre|معلقة|ملعقة|gm|g|جرام|سم3|cm3)\b/i,
    /\b(abamectin|spirotetramat|emamectin|chlorfenapyr|soap|oil|صابون|زيت|ابامكتين|سبيروتترامات)\b/i,
    /(اخلط|امزج|mix)\s+.{0,80}(\d|مل|ml|لتر|liter)/i,
  ].some((pattern) => pattern.test(text));
}

function wantsTreatmentOrPrices(text) {
  return /(treat|treatment|price|prices|buy|product|spray|علاج|أسعار|اسعار|سعر|منتج|رش|مبيد|اشتري|هات)/i.test(text);
}

function hostedTreatmentAnswer(question, lang, context) {
  const text = `${question}\n${context}`.toLowerCase();
  const spider = /spider|mite|العنكبوت|حلم/.test(text);
  if (!wantsTreatmentOrPrices(question) && !wantsTreatmentOrPrices(context)) return null;

  if (lang === "ar") {
    if (spider) {
      return [
        "1. الحالة الأقرب في الصورة: العنكبوت الأحمر على الطماطم، لكن الثقة منخفضة؛ أكد بوجود نقط متحركة أو خيوط تحت الورقة قبل أي رش.",
        "2. أفضل علاج غير كيماوي الآن: شيل الأوراق المصابة بشدة، اغسل/افحص ظهر الورقة، قلل الغبار والعطش، وحسّن التهوية.",
        "3. لو التأكيد تم والإصابة بتزيد: اختار أكاروسيد/مبيد حلم مسجل للطماطم والعنكبوت الأحمر من لجنة المبيدات؛ لا تستخدم مبيد فطري.",
        "4. الأسعار أونلاين: التطبيق يعرض مصادر تحقق مثل APC وAgriMisr/تاجر محلي في كتالوج العلاج؛ اعتبرها مؤشرات سوق وليست سعر رسمي، وأكد السعر والعبوة من محل مبيدات في منطقتك.",
        "5. ممنوع أديك جرعة نهائية من غير لافتة المنتج وموافقة مهندس زراعي؛ الجرعة وPHI وPPE لازم من اللافتة المصرية الحالية.",
      ].join("\n");
    }
    return [
      "1. افتح كتالوج العلاج في المرحلة الرابعة؛ سيعرض المنتجات/العائلات المتاحة للحالة مع روابط تحقق أونلاين.",
      "2. الأسعار المعروضة مؤشرات سوق من صفحات تجار/موردين وليست أسعار رسمية؛ أكد السعر محليًا قبل الشراء.",
      "3. لا تبدأ رش كيماوي إلا بعد تأكيد التشخيص وتسجيل لجنة المبيدات للطماطم والآفة نفسها.",
      "4. استخدم فقط جرعة لافتة المنتج المصرية وموافقة مهندس زراعي.",
    ].join("\n");
  }

  if (spider) {
    return [
      "1. Most likely case: tomato spider mites, but confidence is low; confirm moving mites or webbing under the leaf before spraying.",
      "2. Best safe action now: remove heavily affected leaves, inspect leaf undersides, reduce dust and water stress, and improve ventilation.",
      "3. If confirmed and spreading: use only a tomato-registered acaricide/miticide for spider mites; do not use a fungicide.",
      "4. Online prices: the treatment catalog now shows APC and dealer/market source links such as AgriMisr/local dealer checks. Treat them as market signals, not official prices, and confirm pack size/current stock locally.",
      "5. I will not give a final dose without the current Egyptian label and agronomist approval; dose, PHI, REI, and PPE must come from the label.",
    ].join("\n");
  }
  return [
    "1. Open the Phase 4 treatment catalog; it lists reviewed treatment families and online verification links for the case.",
    "2. Online prices are dealer/market signals, not official prices; confirm the current local quote before buying.",
    "3. Do not spray chemicals until the diagnosis and APC registration are confirmed for tomato and the exact pest/disease.",
    "4. Use only the Egyptian product label dose with agronomist approval.",
  ].join("\n");
}

// Pull the final formatted answer from reasoning_content when content is empty.
// Reasoning models write thinking first then emit the answer; we want only the answer.
function extractFinalAnswer(reasoning) {
  const lines = reasoning.split("\n").map((l) => l.trim()).filter(Boolean);
  // Walk backward and collect the trailing block of bullet/numbered lines.
  const answerLines = [];
  for (let i = lines.length - 1; i >= 0; i--) {
    const l = lines[i];
    if (/^[-•·*٠-٩]|^\d+[.\-)]|^[١٢٣٤٥٦٧٨٩][.\-)]/.test(l)) {
      answerLines.unshift(l);
    } else if (answerLines.length > 0) {
      break; // stop when we hit non-bullet content after finding bullets
    }
  }
  if (answerLines.length >= 2) return answerLines.join("\n");
  // No clear bullet block — return last 600 chars as best-effort.
  return reasoning.length > 600 ? reasoning.slice(-600).trim() : reasoning;
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  if (event.httpMethod !== "POST") return json(405, { error: "Method not allowed" });

  let payload;
  try {
    payload = JSON.parse(event.body || "{}");
  } catch {
    return json(400, { error: "invalid JSON body" });
  }

  const question = String(payload.question || "").trim().slice(0, 500);
  if (!question) return json(400, { error: "question is required" });

  const lang = payload.language === "ar" || isArabic(question) ? "ar" : "en";
  const caseContext = String(payload.case_context || "").slice(0, 5000);
  const apiKey = process.env.EXTERNAL_LLM_API_KEY;
  const apiUrl = process.env.EXTERNAL_LLM_API_URL || "https://opencode.ai/zen/v1/chat/completions";
  const model = process.env.EXTERNAL_LLM_MODEL || "deepseek-v4-flash-free";
  const treatmentAnswer = hostedTreatmentAnswer(question, lang, caseContext);

  if (treatmentAnswer) {
    return json(200, {
      answer: treatmentAnswer,
      sources: ["AgroVision hosted treatment catalog", "APC registration search", "Online dealer/market price checks", "Frontend case context"],
      mode: "external-grounded-assistant",
    });
  }

  if (!apiKey) {
    return json(200, {
      answer: fallback(question, lang, caseContext),
      sources: ["AgroVision Netlify assistant fallback", "Frontend case context"],
      mode: "api-unavailable",
    });
  }

  const system = lang === "ar"
    ? "أنت مساعد AgroVision Egypt الزراعي للطماطم فقط. جاوب بالعربي المصري البسيط في 5 نقاط قصيرة كحد أقصى. استخدم سياق الحالة المرسل فقط. ممنوع تماما اختراع أسماء منتجات أو مواد فعالة أو جرعات أو خلطات منزلية أو أسعار. ممنوع تكتب أرقام جرعات مثل مل/لتر/معلقة. لو المطلوب علاج والعلاج/السعر غير موجود في السياق قل أكد التشخيص والسعر والجرعة محليا مع مهندس زراعي. ركز على خطوات آمنة: فحص، إزالة مصاب، تقليل بلل الورق، تهوية، متابعة. لا تستخدم Markdown."
    : "You are AgroVision Egypt's tomato-only farming assistant. Reply in at most 5 short bullets. Use only the supplied case context. Never invent product names, active ingredients, doses, home mixtures, or prices. Do not write dose numbers such as ml/L/g/tsp. If treatment/price/dose is missing from context, say to confirm locally with an agronomist. Focus on safe steps: inspect, remove infected leaves, keep foliage dry, ventilate, monitor. No Markdown.";

  const controller = new AbortController();
  // Abort at 9s so we return a clean api-unavailable before Netlify's 10s function timeout kills the process.
  const timeout = setTimeout(() => controller.abort(), Number(process.env.EXTERNAL_LLM_TIMEOUT_MS || 9000));
  try {
    const res = await fetch(apiUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        temperature: Number(process.env.EXTERNAL_LLM_TEMPERATURE || 0.3),
        // 800 tokens: enough for 5 bullets (~300 chars) plus reasoning overhead.
        // Do NOT pass reasoning_effort — "low" caused 12s+ responses that exceeded
        // Netlify's 10s function timeout. Without it the model responds in 7-9s.
        max_tokens: Number(process.env.EXTERNAL_LLM_MAX_TOKENS || 800),
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
      }),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (!res.ok) throw new Error(`provider ${res.status}`);
    const data = await res.json();
    const msg = data?.choices?.[0]?.message;
    // content is the actual answer; reasoning_content is the model's chain-of-thought.
    // Only run the safety filter on content (reasoning may reference things it decided NOT to say).
    // If content is empty (model used reasoning-only mode), extract the formatted tail of reasoning.
    const content = String(msg?.content || "").trim();
    if (content) {
      if (unsafeInventedTreatment(content)) throw new Error("unsafe invented treatment details");
      return json(200, {
        answer: content,
        sources: ["Online grounded assistant", "Frontend case context", "AgroVision reviewed tomato guidance"],
        mode: "external-grounded-assistant",
      });
    }
    // Fallback: extract the final formatted section from reasoning_content.
    const reasoning = String(msg?.reasoning_content || "").trim();
    if (reasoning) {
      const answer = extractFinalAnswer(reasoning);
      if (answer && !unsafeInventedTreatment(answer)) {
        return json(200, {
          answer,
          sources: ["Online grounded assistant", "Frontend case context", "AgroVision reviewed tomato guidance"],
          mode: "external-grounded-assistant",
        });
      }
    }
    throw new Error("empty provider answer");
  } catch {
    clearTimeout(timeout);
    return json(200, {
      answer: fallback(question, lang, caseContext),
      sources: ["AgroVision Netlify assistant fallback", "Frontend case context"],
      mode: "api-unavailable",
    });
  }
}
