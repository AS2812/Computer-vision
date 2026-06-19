// ─────────────────────────────────────────────────────────────────────────────
// The SAFETY GATE — hard rules, enforced in logic, never bypassable by the AI.
//
//   1. Low confidence → ALL chemical-category advice is blocked; default = Confirm first.
//   2. Balanced / Strongest stay LOCKED until BOTH: the diagnosis is confirmed
//      (confidence raised via Phase 3 / better photos / an expert) AND APC
//      registration is verified for tomato + that specific pest.
//   3. When chemical is justified: only the registered Egyptian label dose, PPE,
//      REI, PHI — and an Egyptian agricultural engineer must sign off first.
//   4. Food-safety / residue concerns → QCAP lab.
//   5. Never recommend a chemical on the AI result alone; never over-spray.
//
// Viruses have no chemical cure, so curative chemical modes are never "applicable".
// ─────────────────────────────────────────────────────────────────────────────

import type { Bi } from "../data/diseases";
import type { TreatmentModeId } from "../data/economics";
import type { CertaintyBand } from "./screening";
import { APC_PESTICIDE_DB_URL, QCAP_RESIDUE_LAB_URL } from "../data/sources";

export interface GateContext {
  certainty: CertaintyBand;
  /** Diagnosis raised to confirmed via Phase 3 / better photos / an expert. */
  confirmed: boolean;
  /** APC registration verified for tomato + this specific pest. */
  apcVerified: boolean;
  /** Viruses: no chemical cures the pathogen itself. */
  isViral: boolean;
  isPest: boolean;
}

export interface TreatmentMode {
  id: TreatmentModeId;
  name: Bi;
  chemical: boolean;
  costBand: Bi;
  benefit: Bi;
  risk: Bi;
  bestFarmSize: Bi;
}

export interface ModeState {
  mode: TreatmentMode;
  allowed: boolean;
  locked: boolean;
  lockReason?: Bi;
  apcStatus: Bi;
}

export interface GateResult {
  defaultMode: TreatmentModeId;
  modes: ModeState[];
  chemicalBlocked: boolean;
  reason: Bi;
  links: { apc: string; qcap: string };
}

export const TREATMENT_MODES: TreatmentMode[] = [
  {
    id: "confirm_first",
    name: { en: "Confirm first", ar: "أكّد الأول" },
    chemical: false,
    costBand: { en: "~150–300 EGP (a check)", ar: "حوالي ١٥٠–٣٠٠ ج (فحص)" },
    benefit: { en: "Avoid wasted spend and the wrong spray.", ar: "تتجنّب صرف ضايع ورشّة غلط." },
    risk: { en: "A short delay — risky only for fast diseases like late blight.", ar: "تأخير بسيط — خطر بس مع الأمراض السريعة زي اللفحة المتأخرة." },
    bestFarmSize: { en: "Any — especially at low confidence.", ar: "أي حجم — خصوصًا لما الثقة منخفضة." },
  },
  {
    id: "sanitation_only",
    name: { en: "Sanitation only", ar: "نظافة فقط" },
    chemical: false,
    costBand: { en: "0 EGP (your labour)", ar: "٠ ج (مجهودك)" },
    benefit: { en: "Cuts spread with no purchase cost.", ar: "بتقلّل الانتشار من غير تكلفة شراء." },
    risk: { en: "Won't cure an established infection on its own.", ar: "ما بتشفيش إصابة متمكّنة لوحدها." },
    bestFarmSize: { en: "Home garden / small plots / early stages.", ar: "جنينة بيت / مساحات صغيرة / بدايات." },
  },
  {
    id: "prevention_only",
    name: { en: "Prevention only", ar: "وقاية فقط" },
    chemical: false,
    costBand: { en: "Low", ar: "منخفضة" },
    benefit: { en: "Protects still-healthy plants.", ar: "بتحمي النبات السليم لسه." },
    risk: { en: "Will NOT cure plants that are already infected.", ar: "مش هتشفي النبات المصاب أصلًا." },
    bestFarmSize: { en: "Before symptoms / the healthy block around a hotspot.", ar: "قبل الأعراض / البلوك السليم حوالين البؤرة." },
  },
  {
    id: "balanced",
    name: { en: "Balanced", ar: "متوازن" },
    chemical: true,
    costBand: { en: "Medium", ar: "متوسطة" },
    benefit: { en: "Good control at a reasonable cost.", ar: "مكافحة كويسة بتكلفة معقولة." },
    risk: { en: "Needs correct timing, rotation, PPE, and PHI.", ar: "محتاجة توقيت صح وتبديل ومهمات وقاية وفترة ما قبل الحصاد." },
    bestFarmSize: { en: "Open-field blocks ~1–5 feddan.", ar: "بلوكات حقل مكشوف ~١–٥ فدان." },
  },
  {
    id: "strongest",
    name: { en: "Strongest", ar: "الأقوى" },
    chemical: true,
    costBand: { en: "High", ar: "عالية" },
    benefit: { en: "Fastest knock-down under heavy pressure.", ar: "أسرع سيطرة تحت ضغط شديد." },
    risk: { en: "Cost, resistance, and residues — strict PHI and engineer sign-off.", ar: "تكلفة ومقاومة ومتبقّيات — التزام صارم بفترة ما قبل الحصاد وموافقة مهندس." },
    bestFarmSize: { en: "High pressure / larger fields.", ar: "ضغط عالي / حقول أكبر." },
  },
  {
    id: "custom",
    name: { en: "Custom (assistant)", ar: "مخصّص (المساعد)" },
    chemical: true,
    costBand: { en: "Varies", ar: "بتختلف" },
    benefit: { en: "Tailored to your real farm inputs.", ar: "متفصّل على مدخلات مزرعتك الحقيقية." },
    risk: { en: "Depends on your inputs; still needs engineer sign-off.", ar: "بيعتمد على مدخلاتك؛ وبرضه محتاج موافقة مهندس." },
    bestFarmSize: { en: "Any — once you give real numbers.", ar: "أي حجم — بعد ما تدّي أرقام حقيقية." },
  },
];

export function evaluateGate(ctx: GateContext): GateResult {
  const lowConfidence = ctx.certainty === "low";
  // Rule 1 + Rule 2 combined: chemical is only unlocked at non-low confidence AND
  // a confirmed diagnosis AND verified APC registration — and never for a virus.
  const chemicalUnlocked = !lowConfidence && ctx.confirmed && ctx.apcVerified && !ctx.isViral;
  const chemicalBlocked = !chemicalUnlocked;

  const apcVerifiedBadge: Bi = { en: "APC: verified", ar: "لجنة المبيدات: مُتحقَّق" };
  const apcVerifyBadge: Bi = { en: "APC: verify first (crop + pest)", ar: "لجنة المبيدات: تحقّق أولًا (محصول + آفة)" };
  const apcNa: Bi = { en: "APC: not applicable", ar: "لجنة المبيدات: لا ينطبق" };

  const lockReasonFor = (): Bi => {
    if (lowConfidence) return { en: "Low confidence — confirm the diagnosis first.", ar: "ثقة منخفضة — أكّد التشخيص الأول." };
    if (ctx.isViral) return { en: "No chemical cures the virus — manage the whitefly and hygiene instead.", ar: "مفيش كيماوي بيشفي الفيروس — اتعامل مع الذبابة البيضا والنظافة بدل كده." };
    if (!ctx.confirmed) return { en: "Raise confidence first: Phase 3 questions, better photos, or an expert.", ar: "ارفع الثقة الأول: أسئلة المرحلة ٣، صور أحسن، أو خبير." };
    if (!ctx.apcVerified) return { en: "Verify APC registration for tomato + this pest before any chemical.", ar: "تحقّق من تسجيل لجنة المبيدات للطماطم + الآفة دي قبل أي كيماوي." };
    return { en: "Locked.", ar: "مقفول." };
  };

  const modes: ModeState[] = TREATMENT_MODES.map((mode) => {
    if (!mode.chemical) {
      return { mode, allowed: true, locked: false, apcStatus: apcNa };
    }
    const locked = !chemicalUnlocked;
    return {
      mode,
      allowed: !locked,
      locked,
      lockReason: locked ? lockReasonFor() : undefined,
      apcStatus: ctx.apcVerified ? apcVerifiedBadge : apcVerifyBadge,
    };
  });

  const defaultMode: TreatmentModeId = chemicalUnlocked
    ? "balanced"
    : lowConfidence
      ? "confirm_first"
      : "sanitation_only";

  const reason: Bi = chemicalBlocked
    ? {
        en: lowConfidence
          ? "Confidence is low, so every chemical option is blocked. Start protection and confirm first."
          : ctx.isViral
            ? "This is a virus with no chemical cure — chemical curative options stay off; manage the vector and hygiene."
            : "Chemical options stay locked until the diagnosis is confirmed AND APC registration is verified.",
        ar: lowConfidence
          ? "الثقة منخفضة، فكل خيارات الكيماويات مقفولة. ابدأ الحماية وأكّد الأول."
          : ctx.isViral
            ? "ده فيروس مفيش له علاج كيميائي — الخيارات الكيميائية العلاجية مقفولة؛ اتعامل مع الناقل والنظافة."
            : "الخيارات الكيميائية بتفضل مقفولة لحد ما التشخيص يتأكّد وكمان تسجيل لجنة المبيدات يتحقق.",
      }
    : {
        en: "Chemical options are unlocked. Use ONLY the registered Egyptian label dose, PPE, REI, and PHI — and get an agricultural engineer to sign off first.",
        ar: "الخيارات الكيميائية اتفكّت. استخدم بس الجرعة المصرية المسجّلة ومهمات الوقاية وفترات الأمان — وخلّي مهندس زراعي يوافق الأول.",
      };

  return {
    defaultMode,
    modes,
    chemicalBlocked,
    reason,
    links: { apc: APC_PESTICIDE_DB_URL, qcap: QCAP_RESIDUE_LAB_URL },
  };
}
