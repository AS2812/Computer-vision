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
    /(اخلط|امزج|mix)\s+.{0,80}(\d|مل|ml|لتر|liter)/i,
  ].some((pattern) => pattern.test(text));
}

function wantsTreatmentOrPrices(text) {
  const lower = String(text || "").toLowerCase();
  const arabicTerms = ["علاج", "خطة علاج", "أسعار", "اسعار", "سعر", "منتج", "منتجات", "رش", "مبيد", "مبيدات", "اشتري", "شراء", "هات"];
  return /(treat|treatment|price|prices|buy|product|spray|pesticide|miticide|acaricide)/i.test(lower)
    || arabicTerms.some((term) => lower.includes(term));
}

function isIdentityQuestion(text) {
  return /(who\s*are\s*you|what\s*are\s*you|introduce\s*yourself|من\s*[أا]نت|[أا]نت\s*مين|عرفني)/i.test(text);
}

function identityAnswer(lang) {
  if (lang === "ar") {
    return [
      "أنا مساعد AgroVision Egypt الزراعي الخاص بالطماطم.",
      "1. بساعدك تفسر نتيجة فحص الأوراق وتقرأ علامات الأمراض والآفات.",
      "2. بقدر أجاوب على أسئلة الوقاية وخطوات النهارده والأسبوع.",
      "3. ما بديش جرعات أو أسماء منتجات — أي قرار رش يحتاج تأكيد تشخيص وموافقة مهندس زراعي.",
      "4. أنا إشارة فرز تساعد المهندس الزراعي، مش بديله.",
    ].join("\n");
  }
  return [
    "I am AgroVision Egypt's tomato farming assistant.",
    "1. I help you interpret leaf scan results and read disease/pest signs.",
    "2. I can answer questions about prevention, today's steps, and this week's plan.",
    "3. I never give doses or product names — any spray decision needs diagnosis confirmation and an agronomist's approval.",
    "4. I am a triage signal that supports the agronomist, not a replacement.",
  ].join("\n");
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

function treatmentPriceInstructions(question, lang, context) {
  if (!wantsTreatmentOrPrices(`${question}\n${context}`)) return "";
  if (lang === "ar") {
    return [
      "",
      "طلب علاج/سعر مباشر: لا تكرر فقط جملة افتح كتالوج العلاج.",
      "اكتب خطة عملية للمزارع من الحالة نفسها: تأكيد الآفة/المرض، خطوات فورية بدون رش، متى نفكر في رش مسجل، وكيف يتحقق من السعر والتوفر.",
      "لو الحالة عنكبوت أحمر: وضح أنه آفة حلم وليس مرض فطري، وأنه يحتاج مبيد حلم/أكاروسيد مسجل للطماطم فقط إذا تأكد وانتشر.",
      "ممنوع اختراع أسماء منتجات أو جرعات أو أسعار دقيقة غير موجودة في سياق الحالة.",
    ].join("\n");
  }
  return [
    "",
    "Direct treatment/price request: do not repeat only 'open the treatment catalog'.",
    "Write a practical farmer plan from the case: confirm pest/disease, immediate non-spray steps, when to consider a registered spray, and how to verify price and availability.",
    "If the case is spider mites: state it is a mite pest, not a fungal disease, and may require a tomato-registered miticide/acaricide only if confirmed and spreading.",
    "Do not invent product names, doses, or exact prices that are not present in the case context.",
  ].join("\n");
}

function normalizeCaseContext(input) {
  if (!input) return "";
  if (typeof input === "string") return input.slice(0, 7000);
  try {
    return JSON.stringify(input, null, 2).slice(0, 7000);
  } catch {
    return String(input).slice(0, 7000);
  }
}

function inferDiseaseKey(payload, text) {
  const raw = payload?.case_context;
  if (raw && typeof raw === "object") {
    const keys = [
      raw.advice_key,
      raw.disease_key,
      raw.diagnosis_key,
      raw.key,
      raw?.primary?.advice_key,
      raw?.primary?.disease_key,
    ].filter(Boolean);
    const match = keys.find((key) => String(key).startsWith("tomato_"));
    if (match) return String(match);
  }
  const lower = text.toLowerCase();
  if (/spider|mite|two-spotted|tetranychus|العنكبوت|حلم/.test(lower)) return "tomato_spider_mites";
  if (/late blight|اللفحة المتأخرة/.test(lower)) return "tomato_late_blight";
  if (/early blight|اللفحة المبكرة/.test(lower)) return "tomato_early_blight";
  if (/target spot|التبقع الهدفي/.test(lower)) return "tomato_target_spot";
  if (/bacterial spot|التبقع البكتيري/.test(lower)) return "tomato_bacterial_spot";
  if (/septoria|سبتوريا/.test(lower)) return "septoria_leaf_spot_tomato";
  if (/leaf mold|العفن الورقي/.test(lower)) return "tomato_leaf_mold";
  return "";
}

function treatmentCatalogContext(diseaseKey) {
  if (diseaseKey !== "tomato_spider_mites") return "";
  return [
    "",
    "Reviewed Egypt treatment and price signals for tomato spider mites, checked 2026-06-19:",
    "- Diagnosis note: this is a mite pest, not a fungal disease. Fungicides do not treat it.",
    "- Must confirm live mites/webbing/stippling under leaves before any spray because current visual certainty can be low.",
    "- APC registration check is mandatory before buying or spraying: https://www1.apc.gov.eg/en/search.aspx",
    "- Treatment family: tomato-registered acaricide/miticide for spider mites. Use Egyptian label only for dose, PHI, PPE, and interval.",
    "- Price signal: AgriMisr listed Mectiam 1.8% acaricide 100 cc at 120 EGP and 250 cc at 270 EGP; page also listed Kani Mite 15% 500 ml at 3700 EGP with stock shown. Source: https://agrimisr.com/index.php?category_id=831&dispatch=categories.view&items_per_page=24&layout=products_without_options&sort_by=popularity&sort_order=asc",
    "- Price signal: Shoura Online listed Biomectin 120 cm acaricide at 220 EGP, marked out of stock. Source: https://shouraonline.com/product/Biomectin_120CM",
    "- Price signal: Mobidat Star listed Stra Mactin acaricide 100 ml at 85 EGP sale price. Source: https://mobidatstar.store/product/%D8%B3%D8%AA%D8%B1%D8%A7-%D9%85%D8%A7%D9%83%D8%AA%D9%8A%D9%86-100%D9%85%D9%84%D9%84/",
    "- Availability rule: online prices are dealer/market indicators, not official prices. The farmer must verify current stock, exact pack size, registration, label, and local shop price before purchase.",
  ].join("\n");
}

function appendCatalogPriceSignals(answer, diseaseKey, lang, question) {
  if (diseaseKey !== "tomato_spider_mites") return answer;
  if (/120|270|220|3700|85|EGP/i.test(answer)) return answer;
  const appendix = lang === "ar"
    ? [
      "",
      "إشارات أسعار أونلاين راجعتها AgroVision بتاريخ 2026-06-19:",
      "- AgriMisr: Mectiam 1.8% عبوة 100 cc بسعر 120 EGP، و250 cc بسعر 270 EGP، وKani Mite 15% عبوة 500 ml بسعر 3700 EGP.",
      "- Shoura Online: Biomectin 120 cm بسعر 220 EGP لكن الصفحة كانت marked out of stock.",
      "- Mobidat Star: Stra Mactin 100 ml بسعر 85 EGP.",
      "- الأسعار مؤشرات سوق فقط؛ أكد التسجيل في APC، اللافتة، العبوة، التوفر، والسعر المحلي قبل الشراء.",
    ].join("\n")
    : [
      "",
      "Reviewed online Egypt price signals checked by AgroVision on 2026-06-19:",
      "- AgriMisr: Mectiam 1.8% 100 cc at 120 EGP, 250 cc at 270 EGP, and Kani Mite 15% 500 ml at 3700 EGP.",
      "- Shoura Online: Biomectin 120 cm at 220 EGP, but the page was marked out of stock.",
      "- Mobidat Star: Stra Mactin 100 ml at 85 EGP.",
      "- These are market signals only; verify APC registration, label, pack size, stock, and local price before buying.",
    ].join("\n");
  return `${answer.trim()}\n${appendix}`;
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
  const caseContext = normalizeCaseContext(payload.case_context);
  const diseaseKey = inferDiseaseKey(payload, `${question}\n${caseContext}`);
  const apiKey = process.env.EXTERNAL_LLM_API_KEY;
  const apiUrl = process.env.EXTERNAL_LLM_API_URL || "https://opencode.ai/zen/v1/chat/completions";
  const model = process.env.EXTERNAL_LLM_MODEL || "deepseek-v4-flash-free";

  if (isIdentityQuestion(question)) {
    return json(200, {
      answer: identityAnswer(lang),
      sources: ["AgroVision Egypt assistant self-description"],
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
  const extraInstructions = [
    treatmentPriceInstructions(question, lang, caseContext),
    wantsTreatmentOrPrices(`${question}\n${caseContext}`) ? treatmentCatalogContext(diseaseKey) : "",
  ].filter(Boolean).join("\n");

  const controller = new AbortController();
  const timeoutMs =
    Number(process.env.EXTERNAL_LLM_TIMEOUT_MS || 0) ||
    Number(process.env.EXTERNAL_LLM_TIMEOUT_SECONDS || 0) * 1000 ||
    25000;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(apiUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        temperature: Number(process.env.EXTERNAL_LLM_TEMPERATURE || 0.3),
        // 1200 tokens: ~400 reasoning overhead + ~800 for 5 Arabic bullets.
        // Do NOT pass reasoning_effort — "low" caused 12s+ responses that exceeded
        // Netlify's 10s function timeout. Without it the model responds in 7-9s.
        max_tokens: Number(process.env.EXTERNAL_LLM_MAX_TOKENS || 1200),
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
              extraInstructions,
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
      const answer = appendCatalogPriceSignals(content, diseaseKey, lang, question);
      return json(200, {
        answer,
        sources: ["Online grounded assistant", "Frontend case context", "AgroVision reviewed tomato guidance"],
        mode: "external-grounded-assistant",
      });
    }
    // Fallback: extract the final formatted section from reasoning_content.
    const reasoning = String(msg?.reasoning_content || "").trim();
    if (reasoning) {
      const answer = extractFinalAnswer(reasoning);
      if (answer && !unsafeInventedTreatment(answer)) {
        const answerWithPrices = appendCatalogPriceSignals(answer, diseaseKey, lang, question);
        return json(200, {
          answer: answerWithPrices,
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
