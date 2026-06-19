// ─────────────────────────────────────────────────────────────────────────────
// Phase 5 economics — auto-generated cost-benefit for every Egyptian area size.
//
// Faithful TS port of services/api/app/application/area_ranges.py + prices.py.
// The farmer never types an area. Every money figure is a reference estimate
// (badged "estimated_range") until they enter a real area + a local price quote,
// at which point recompute() re-runs with their numbers and badges "generated".
//
// HONESTY: prices are reviewed REFERENCE RANGES, never live or exact. The yield
// basis is official CAPMAS. No branded products; chemical category buckets only.
// ─────────────────────────────────────────────────────────────────────────────

import type { Bi } from "./diseases";
import type { Provenance } from "./sources";
import { CAPMAS_REFERENCES, capmasYieldKgPerFeddan } from "./sources";

export type TreatmentModeId =
  | "confirm_first"
  | "sanitation_only"
  | "balanced"
  | "strongest"
  | "prevention_only"
  | "custom";

export type Worth = "likely_worth" | "ask_engineer" | "maybe_not_worth";

export interface SourcedRange {
  label: Bi;
  low: number | null;
  high: number | null;
  unit: string;
  provenance: Provenance;
  assumption: Bi;
  /** A real measured/known zero (e.g. sanitation costs 0 EGP), not "no data". */
  measuredZero?: boolean;
}

export interface AreaCase {
  key: string;
  name: Bi;
  areaFeddan: number;
  sprays: SourcedRange;
  treatmentCost: SourcedRange;
  laborCost: SourcedRange;
  expectedYield: SourcedRange;
  lossWithoutAction: SourcedRange;
  savedByActing: SourcedRange;
  revenue: SourcedRange;
  netBenefit: SourcedRange;
  worth: Worth;
  recommendation: Bi;
}

export interface SeverityEstimate {
  lossLowPct: number;
  lossHighPct: number;
  /** "low" | "moderate" | "high" | "severe" | "unknown" */
  label: string;
}

const FEDDAN_PER_QIRAT = 1 / 24;

export const AREA_PRESETS: Array<{ key: string; name: Bi; area: number }> = [
  { key: "home_garden", name: { en: "Home garden", ar: "جنينة بيت" }, area: 0.02 },
  { key: "one_qirat", name: { en: "1 qirat", ar: "قيراط" }, area: 1 * FEDDAN_PER_QIRAT },
  { key: "six_qirat", name: { en: "6 qirat", ar: "٦ قراريط" }, area: 6 * FEDDAN_PER_QIRAT },
  { key: "twelve_qirat", name: { en: "12 qirat (½ feddan)", ar: "١٢ قيراط (نص فدان)" }, area: 12 * FEDDAN_PER_QIRAT },
  { key: "one_feddan", name: { en: "1 feddan", ar: "فدان" }, area: 1 },
  { key: "three_feddan", name: { en: "3 feddans", ar: "٣ فدادين" }, area: 3 },
  { key: "five_feddan", name: { en: "5 feddans", ar: "٥ فدادين" }, area: 5 },
  { key: "ten_feddan", name: { en: "10 feddans", ar: "١٠ فدادين" }, area: 10 },
];

// Reviewed Egyptian reference ranges (NOT live) — from prices.py. [low, high].
const REF = {
  tomato_farmgate: [5.0, 12.0], // EGP/kg
  contact_fungicide: [120.0, 280.0],
  systemic_fungicide: [250.0, 600.0],
  insecticide: [150.0, 450.0],
  labor: [150.0, 400.0],
  sprayer_use: [50.0, 150.0],
  water_fuel: [60.0, 180.0],
  home_garden_inputs: [100.0, 600.0],
} as const;

/** Official CAPMAS implied tomato yield range, kg/feddan (≈16,346–16,583). */
export function capmasYieldRange(): [number, number] {
  const ys = CAPMAS_REFERENCES.map(capmasYieldKgPerFeddan).sort((a, b) => a - b);
  return [ys[0], ys[ys.length - 1]];
}

const RESIDUAL_LOSS_PCT = 5;
const DEFAULT_LOSS: SeverityEstimate = { lossLowPct: 8, lossHighPct: 20, label: "unknown" };

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

function range(
  label: Bi,
  low: number,
  high: number,
  unit: string,
  provenance: Provenance,
  assumption: Bi,
  measuredZero = false,
): SourcedRange {
  const [lo, hi] = low <= high ? [low, high] : [high, low];
  return {
    label,
    low: round2(lo),
    high: round2(hi),
    unit,
    provenance,
    assumption,
    measuredZero: measuredZero || lo === 0 || hi === 0,
  };
}

export interface EconomicsOptions {
  mode: TreatmentModeId;
  severity?: SeverityEstimate;
  isPest?: boolean;
  /** Official/live tomato wholesale range, used until the farmer enters a local quote. */
  liveTomatoPrice?: {
    low: number;
    high: number;
    source: string;
    asOf: string;
  } | null;
  /** When set, this exact farmgate price (EGP/kg) is used and figures badge "generated". */
  farmerPriceEgpPerKg?: number;
  /** When set, only this single area is generated (the farmer's real area). */
  farmerAreaFeddan?: number;
  customTreatmentCostPerFeddan?: number | null;
}

export function generateAreaCases(opts: EconomicsOptions): AreaCase[] {
  const severity = opts.severity ?? DEFAULT_LOSS;
  const exact = opts.farmerPriceEgpPerKg != null;
  const livePrice = !exact && opts.liveTomatoPrice ? opts.liveTomatoPrice : null;
  const customCostDefined = opts.customTreatmentCostPerFeddan != null;
  const moneyBadge: Provenance = exact || customCostDefined ? "generated" : livePrice ? "live" : "estimated_range";

  const [yieldLow, yieldHigh] = capmasYieldRange();
  const [priceRefLow, priceRefHigh] = REF.tomato_farmgate;
  const priceLow = opts.farmerPriceEgpPerKg ?? livePrice?.low ?? priceRefLow;
  const priceHigh = opts.farmerPriceEgpPerKg ?? livePrice?.high ?? priceRefHigh;

  const chemLow = opts.isPest ? REF.insecticide[0] : REF.contact_fungicide[0];
  const chemHigh = opts.isPest ? REF.insecticide[1] : REF.systemic_fungicide[1];
  const perAppLow = chemLow + REF.labor[0] + REF.sprayer_use[0] + REF.water_fuel[0];
  const perAppHigh = chemHigh + REF.labor[1] + REF.sprayer_use[1] + REF.water_fuel[1];

  const appLow = opts.customTreatmentCostPerFeddan ?? perAppLow;
  const appHigh = opts.customTreatmentCostPerFeddan ?? perAppHigh;

  const lossLowPct = severity.lossLowPct;
  const lossHighPct = severity.lossHighPct;
  const avoidableLow = Math.max(0, lossLowPct - RESIDUAL_LOSS_PCT) / 100;
  const avoidableHigh = Math.max(0, lossHighPct - RESIDUAL_LOSS_PCT) / 100;

  const priceAssumption: Bi = exact
    ? { en: "Using the local price you entered.", ar: "باستخدام السعر المحلي اللي دخّلته." }
    : livePrice
      ? {
          en: `Using live wholesale tomato range from ${livePrice.source} (${livePrice.asOf}); farmgate and retail can differ.`,
          ar: `باستخدام سعر جملة مباشر للطماطم من ${livePrice.source} (${livePrice.asOf})؛ سعر المزرعة والقطاعي ممكن يختلف.`,
        }
      : { en: "Egyptian reference price (5–12 EGP/kg); not a live quote — confirm with your dealer/market.", ar: "سعر مرجعي مصري (٥–١٢ ج/كجم)؛ مش سعر مباشر — أكّده من التاجر/السوق." };

  const presets =
    opts.farmerAreaFeddan != null
      ? [{ key: "your_area", name: { en: `Your area (${opts.farmerAreaFeddan} fd)`, ar: `مساحتك (${opts.farmerAreaFeddan} ف)` }, area: opts.farmerAreaFeddan }]
      : AREA_PRESETS;

  return presets.map(({ key, name, area }) => {
    const home = key === "home_garden";
    let spraysLow = 0;
    let spraysHigh = 0;
    let costLow = 0;
    let costHigh = 0;
    let laborTotalLow = 0;
    let laborTotalHigh = 0;

    const homeInputs = REF.home_garden_inputs;
    switch (opts.mode) {
      case "confirm_first":
        costLow = home ? (customCostDefined ? opts.customTreatmentCostPerFeddan! * 0.2 : 50) : (customCostDefined ? opts.customTreatmentCostPerFeddan! : 150);
        costHigh = home ? (customCostDefined ? opts.customTreatmentCostPerFeddan! * 0.4 : 100) : (customCostDefined ? opts.customTreatmentCostPerFeddan! * 2 : 300);
        break;
      case "sanitation_only":
        // costs stay 0
        break;
      case "prevention_only":
        spraysLow = 1;
        spraysHigh = 2;
        if (home) {
          costLow = (customCostDefined ? opts.customTreatmentCostPerFeddan! : homeInputs[0]) * 0.5;
          costHigh = (customCostDefined ? opts.customTreatmentCostPerFeddan! : homeInputs[1]) * 0.5;
        } else {
          costLow = appLow * 0.5 * spraysLow * area;
          costHigh = appHigh * 0.5 * spraysHigh * area;
          laborTotalLow = customCostDefined ? 0 : REF.labor[0] * spraysLow * area;
          laborTotalHigh = customCostDefined ? 0 : REF.labor[1] * spraysHigh * area;
        }
        break;
      case "strongest":
        spraysLow = 3;
        spraysHigh = 5;
        if (home) {
          costLow = (customCostDefined ? opts.customTreatmentCostPerFeddan! : homeInputs[0]) * 1.3;
          costHigh = (customCostDefined ? opts.customTreatmentCostPerFeddan! : homeInputs[1]) * 1.3;
        } else {
          costLow = appLow * 1.3 * spraysLow * area;
          costHigh = appHigh * 1.3 * spraysHigh * area;
          laborTotalLow = customCostDefined ? 0 : REF.labor[0] * spraysLow * area;
          laborTotalHigh = customCostDefined ? 0 : REF.labor[1] * spraysHigh * area;
        }
        break;
      default: {
        // balanced & custom
        spraysLow = 2;
        spraysHigh = 4;
        if (home) {
          costLow = (customCostDefined ? opts.customTreatmentCostPerFeddan! : homeInputs[0]);
          costHigh = (customCostDefined ? opts.customTreatmentCostPerFeddan! : homeInputs[1]);
        } else {
          costLow = appLow * spraysLow * area;
          costHigh = appHigh * spraysHigh * area;
          laborTotalLow = customCostDefined ? 0 : REF.labor[0] * spraysLow * area;
          laborTotalHigh = customCostDefined ? 0 : REF.labor[1] * spraysHigh * area;
        }
      }
    }

    const eyLow = yieldLow * area;
    const eyHigh = yieldHigh * area;
    const revenueLow = eyLow * priceLow;
    const revenueHigh = eyHigh * priceHigh;
    const lossLow = revenueLow * (lossLowPct / 100);
    const lossHigh = revenueHigh * (lossHighPct / 100);

    let savedLow = 0;
    let savedHigh = 0;
    switch (opts.mode) {
      case "confirm_first":
        break;
      case "sanitation_only":
        savedLow = lossLow * 0.3;
        savedHigh = lossHigh * 0.3;
        break;
      case "prevention_only":
        savedLow = revenueLow * avoidableLow * 0.5;
        savedHigh = revenueHigh * avoidableHigh * 0.5;
        break;
      case "strongest":
        savedLow = revenueLow * avoidableLow * 0.95;
        savedHigh = revenueHigh * avoidableHigh * 0.95;
        break;
      case "custom":
        savedLow = revenueLow * avoidableLow * 0.8;
        savedHigh = revenueHigh * avoidableHigh * 0.8;
        break;
      default: // balanced
        savedLow = revenueLow * avoidableLow * 0.85;
        savedHigh = revenueHigh * avoidableHigh * 0.85;
    }

    const netLow = savedLow - costHigh;
    const netHigh = savedHigh - costLow;

    let worth: Worth;
    let rec: Bi;
    if (home) {
      worth = "likely_worth";
      if (opts.mode === "confirm_first") {
        rec = { en: "Confirm first: check the underside of the leaves; a small-garden check costs very little.", ar: "أكّد الأول: افحص الورق من تحت؛ فحص الجنينة الصغيرة مش مكلّف." };
      } else if (opts.mode === "sanitation_only") {
        rec = { en: "Pick off and bin spotted leaves by hand first; a small garden rarely needs a paid spray.", ar: "شيل الورق المبقّع باليد الأول؛ الجنينة الصغيرة نادرًا تحتاج رشّة بفلوس." };
      } else {
        rec = { en: "Use low-risk garden treatments only if symptoms persist.", ar: "استخدم معالجات جنينة خفيفة بس لو الأعراض استمرّت." };
      }
    } else if (opts.mode === "confirm_first") {
      worth = "ask_engineer";
      rec = { en: "Hold chemical spending and confirm the diagnosis before buying anything.", ar: "أوقف الصرف الكيميائي وأكّد التشخيص قبل ما تشتري حاجة." };
    } else if (opts.mode === "sanitation_only") {
      worth = netLow > 0 ? "likely_worth" : "ask_engineer";
      rec = { en: "Sanitation: manual hygiene saves yield with zero chemical purchase cost.", ar: "النظافة: المجهود اليدوي بيحفظ المحصول من غير تكلفة شراء كيماويات." };
    } else if (netHigh <= 0) {
      worth = "maybe_not_worth";
      rec = { en: "The spray may not pay off at this size/severity — monitor first and re-check in a few days.", ar: "الرش ممكن ما يستاهلش في الحجم/الخطورة دي — راقب الأول وافحص تاني بعد كام يوم." };
    } else if (netLow > 0 && ["moderate", "high", "severe"].includes(severity.label)) {
      worth = "likely_worth";
      rec = { en: "Protecting the crop is likely worth it here — run a planned spray programme and keep records.", ar: "حماية المحصول غالبًا بتستاهل هنا — اعمل برنامج رش مخطّط وسجّل المواعيد." };
    } else {
      worth = "ask_engineer";
      rec = { en: "Borderline economics — confirm the disease and costs with an agricultural engineer before spraying.", ar: "العائد على الحدّ — أكّد المرض والتكلفة مع مهندس زراعي قبل الرش." };
    }

    const areaNote: Bi = { en: `For ${name.en} (~${area} feddan).`, ar: `لـ ${name.ar} (حوالي ${area} فدان).` };
    const spraysAssumption: Bi = { en: `Assumes ${spraysLow}–${spraysHigh} protective applications this season.`, ar: `على افتراض ${spraysLow}–${spraysHigh} رشّات وقائية في الموسم.` };

    return {
      key,
      name,
      areaFeddan: round2(area),
      sprays: range({ en: "Number of sprays", ar: "عدد الرشّات" }, spraysLow, spraysHigh, "sprays/season", "generated", spraysAssumption, home || spraysLow === 0),
      treatmentCost: range({ en: "Treatment cost", ar: "تكلفة العلاج" }, costLow, costHigh, "EGP", moneyBadge, { en: `${areaNote.en} ${spraysAssumption.en}`, ar: `${areaNote.ar} ${spraysAssumption.ar}` }, costLow === 0),
      laborCost: range({ en: "Labour cost", ar: "أجرة العمالة" }, laborTotalLow, laborTotalHigh, "EGP", moneyBadge, areaNote, home || laborTotalLow === 0),
      expectedYield: range({ en: "Expected yield", ar: "الإنتاجية المتوقعة" }, eyLow, eyHigh, "kg", moneyBadge, { en: "Official CAPMAS reference yield/feddan × area.", ar: "إنتاجية الفدان المرجعية الرسمية (CAPMAS) × المساحة." }),
      lossWithoutAction: range({ en: "Loss without action", ar: "الخسارة من غير علاج" }, lossLow, lossHigh, "EGP", moneyBadge, { en: `Yield-loss band × revenue. ${priceAssumption.en}`, ar: `شريحة خسارة المحصول × الإيراد. ${priceAssumption.ar}` }),
      savedByActing: range({ en: "Saved by acting", ar: "اللي بيتحفظ بالعلاج" }, savedLow, savedHigh, "EGP", moneyBadge, { en: "Avoidable share of the loss after a spray programme.", ar: "الجزء اللي ينفع نتجنّبه من الخسارة بعد برنامج الرش." }, savedLow === 0),
      revenue: range({ en: "Revenue", ar: "الإيراد" }, revenueLow, revenueHigh, "EGP", moneyBadge, priceAssumption),
      netBenefit: range({ en: "Net benefit", ar: "صافي المكسب" }, netLow, netHigh, "EGP", moneyBadge, { en: "Saved revenue minus treatment cost (conservative).", ar: "اللي اتحفظ ناقص تكلفة العلاج (بتحفّظ)." }),
      worth,
      recommendation: rec,
    };
  });
}
