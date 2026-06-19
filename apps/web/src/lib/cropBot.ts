import type { AppAnalysis, Lang } from "../appTypes";
import { diseaseByKey } from "../data/diseases";
import { apiBase } from "./apiBase";
import { marketPriceLabel } from "./market";
import { assistantFunctionUrl, ensureAnonAuth, supabase } from "./supabase";

// ── Offline template ──────────────────────────────────────────────────────────
// When all network paths are unavailable, generate a useful KB-grounded answer
// from the local disease knowledge base rather than a bare "unavailable" message.

function matchesPattern(text: string, patterns: RegExp[]): boolean {
  return patterns.some((p) => p.test(text));
}

const TREATMENT_Q = [/treat|علاج|رش|منتج|مبيد|price|أسعار|اسعار|سعر|buy|اشتري|مقاومة/i];
const PREVENT_Q = [/prevent|وقاية|وقائي|أمنع|حماية|الموسم الجاي|next season/i];
const TODAY_Q = [/today|النهارده|اليوم|الآن|الأسبوع|this week|now|أعمل إيه/i];
const COMPARE_Q = [/compar|قارن|compare|alternatives|بدائل|options/i];

export function buildOfflineAnswer(question: string, analysis: AppAnalysis | null, lang: Lang): string {
  const q = question.toLowerCase();
  const topKey = analysis?.screening.topKey;
  const disease = topKey ? diseaseByKey(topKey) : null;
  const name = disease?.name[lang] ?? (lang === "ar" ? "المرض المكتشف" : "the detected disease");
  const hasCase = !!disease;

  if (lang === "ar") {
    const header = hasCase
      ? `المساعد غير متصل الآن. الحالة الحالية: ${name} — معلومات من قاعدة البيانات المحلية:`
      : "المساعد غير متصل الآن. ردود عامة من قاعدة البيانات المحلية:";

    if (hasCase && matchesPattern(q, TODAY_Q)) {
      const checks = disease!.todayCheck.map((c) => `• ${c.ar}`).join("\n");
      return `${header}\n\nخطوات اليوم لـ${name}:\n${checks}\n\n⚠️ أي رش لازم تأكيد التشخيص ومراجعة مهندس زراعي أولاً.`;
    }
    if (hasCase && matchesPattern(q, PREVENT_Q)) {
      const note = disease!.protectNote?.ar ?? disease!.treatmentNote.ar;
      return `${header}\n\nوقاية ${name}:\n${note}\n\n⚠️ أكّد مع مهندس زراعي قبل أي رش.`;
    }
    if (hasCase && matchesPattern(q, TREATMENT_Q)) {
      return `${header}\n\nملاحظة علاج ${name}:\n${disease!.treatmentNote.ar}\n\nالأسعار: افتح كتالوج العلاج في مرحلة العلاج داخل التطبيق.\n\n⚠️ لا تبدأ رشًا كيميائيًا بدون تأكيد التشخيص وموافقة مهندس زراعي والجرعة من لافتة المنتج المصرية.`;
    }
    if (hasCase && matchesPattern(q, COMPARE_Q)) {
      const candidates = analysis!.screening.candidates.slice(0, 3);
      const list = candidates.map((c) => {
        const d = diseaseByKey(c.key);
        return `• ${d?.name.ar ?? c.key} (${Math.round(c.prob * 100)}٪)`;
      }).join("\n");
      return `${header}\n\nالمرشّحون من موديل الجهاز:\n${list}\n\nأكّد بعينك: ${disease!.todayCheck[0]?.ar ?? "راجع الأعراض الموضّحة في مرحلة التشخيص."}\n\n⚠️ هذا فرز أولي، مش تشخيص مؤكّد.`;
    }
    if (hasCase) {
      const symptoms = disease!.symptomsLeaf.slice(0, 2).map((s) => `• ${s.ar}`).join("\n");
      return `${header}\n\nملخّص ${name}:\n${disease!.summary.ar}\n\nأعراض الورق:\n${symptoms}\n\n${disease!.treatmentNote.ar}\n\n⚠️ أكّد التشخيص مع مهندس زراعي قبل أي تدخل.`;
    }
    return `${header}\n\nابدأ بالحماية الآمنة: شيل الأوراق المصابة، قلل بلل الورق، حسّن التهوية، وافحص ظهر الورقة.\nأي رش لازم تأكيد التشخيص ومراجعة مهندس زراعي.\nجرّب تحميل صورة ورقة الطماطم عشان نبدأ الفحص.`;
  }

  // English
  const header = hasCase
    ? `Assistant is offline. Case: ${name} — answers from local knowledge base:`
    : "Assistant is offline. General answers from local knowledge base:";

  if (hasCase && matchesPattern(q, TODAY_Q)) {
    const checks = disease!.todayCheck.map((c) => `• ${c.en}`).join("\n");
    return `${header}\n\nToday's steps for ${name}:\n${checks}\n\n⚠️ Any spray needs diagnosis confirmation and agronomist approval first.`;
  }
  if (hasCase && matchesPattern(q, PREVENT_Q)) {
    const note = disease!.protectNote?.en ?? disease!.treatmentNote.en;
    return `${header}\n\nPrevention for ${name}:\n${note}\n\n⚠️ Confirm with an agronomist before any spray.`;
  }
  if (hasCase && matchesPattern(q, TREATMENT_Q)) {
    return `${header}\n\nTreatment note for ${name}:\n${disease!.treatmentNote.en}\n\nFor prices: open the treatment catalog in Phase 4 in the app.\n\n⚠️ Do not spray chemicals without confirming the diagnosis, agronomist approval, and the dose from the Egyptian product label.`;
  }
  if (hasCase && matchesPattern(q, COMPARE_Q)) {
    const candidates = analysis!.screening.candidates.slice(0, 3);
    const list = candidates.map((c) => {
      const d = diseaseByKey(c.key);
      return `• ${d?.name.en ?? c.key} (${Math.round(c.prob * 100)}%)`;
    }).join("\n");
    return `${header}\n\nOn-device model candidates:\n${list}\n\nConfirm by eye: ${disease!.todayCheck[0]?.en ?? "Check the symptoms in the diagnosis phase."}\n\n⚠️ This is an initial screening, not a confirmed diagnosis.`;
  }
  if (hasCase) {
    const symptoms = disease!.symptomsLeaf.slice(0, 2).map((s) => `• ${s.en}`).join("\n");
    return `${header}\n\nSummary of ${name}:\n${disease!.summary.en}\n\nLeaf symptoms:\n${symptoms}\n\n${disease!.treatmentNote.en}\n\n⚠️ Confirm with an agronomist before any intervention.`;
  }
  return `${header}\n\nStart with safe protection: remove infected leaves, keep foliage dry, improve ventilation, and inspect leaf undersides.\nAny spray needs diagnosis confirmation and agronomist approval.\nUpload a tomato leaf photo to start the on-device check.`;
}

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

  if (apiBase) {
    try {
      const res = await fetch(`${apiBase}/api/assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(130_000),
      });
      if (res.ok) return (await res.json()) as CropBotAnswer;
    } catch {
      // Fall through to offline template.
    }
  }

  // All network paths failed — return an offline template answer from the local KB.
  return {
    answer: buildOfflineAnswer(question, analysis, lang),
    sources: ["AgroVision local knowledge base (offline)"],
    mode: "offline-template",
  };
}
