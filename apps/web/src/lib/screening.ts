// ─────────────────────────────────────────────────────────────────────────────
// Honest fusion of the on-device model + the AI second opinion into ONE verdict.
//
// Ported from the three-state honesty logic described in IMPLEMENTATION_STATUS
// (services/api diagnosis_evidence.fuse_diagnosis + calibration.py):
//   • states: confident / screening / not_sure / not_tomato,
//   • a tomato-leaf gate from the crop mass + green coverage,
//   • a "spot-complex" rescue so a split-but-coherent Target-Spot-like top-1 is
//     surfaced as "probable" instead of discarded,
//   • confidence is the renormalised, UNCALIBRATED visual match, capped so it can
//     never read as near-certain, and the AI never inflates the NUMBER — only the
//     certainty BAND can shift by one notch on agreement/disagreement.
// ─────────────────────────────────────────────────────────────────────────────

import type { Bi } from "../data/diseases";
import { diseaseByKey } from "../data/diseases";
import type { LocalCandidate, LocalInference } from "./onnx";
import type { InfectionExtent } from "./imageSignals";

export type FusedState = "confident" | "screening" | "not_sure" | "not_tomato";
export type CertaintyBand = "low" | "medium" | "high";

export interface AiRanked {
  key: string;
  name: string;
  confidence: number; // 0..1
}

export interface AiOpinion {
  isTomatoLeaf: boolean;
  notSure: boolean;
  ranked: AiRanked[];
  visibleSigns: string;
  model: string;
  latencyMs: number;
}

export interface ScreeningResult {
  state: FusedState;
  topKey: string | null;
  topName: Bi | null;
  /** 0..1 uncalibrated visual match, capped. NOT a probability of being correct. */
  displayConfidence: number;
  certainty: CertaintyBand;
  candidates: LocalCandidate[]; // local top-3
  agreement: "agree" | "disagree" | "partial" | "ai_offline";
  notes: Bi[];
  leafGate: { looksLikeTomato: boolean; reason: Bi };
}

// The "spot complex" — look-alikes the model routinely splits its score across.
const SPOT_COMPLEX = new Set([
  "tomato_target_spot",
  "tomato_early_blight",
  "tomato_bacterial_spot",
  "septoria_leaf_spot_tomato",
]);

const CONF_CAP = 0.95;
const TOMATO_MASS_MIN = 0.6; // crop-conditioning gate (matches server)
const MARGIN_MIN = 0.15;

function bandFromConfidence(c: number): CertaintyBand {
  if (c > 0.85) return "high";
  if (c >= 0.65) return "medium";
  return "low";
}

function bump(b: CertaintyBand, dir: 1 | -1): CertaintyBand {
  const order: CertaintyBand[] = ["low", "medium", "high"];
  const i = Math.min(2, Math.max(0, order.indexOf(b) + dir));
  return order[i];
}

export interface FuseInput {
  local: LocalInference;
  ai: AiOpinion | null;
  extent: InfectionExtent;
}

export function fuseDiagnosis({ local, ai, extent }: FuseInput): ScreeningResult {
  const notes: Bi[] = [];
  const top = local.candidates[0];
  const second = local.candidates[1];
  const localTopKey = top?.key ?? null;
  const localTopConf = Math.min(CONF_CAP, top?.prob ?? 0);

  // ── Tomato-leaf gate ──────────────────────────────────────────────────────
  // The image model can't confirm the host crop, but very low tomato mass + very
  // little green strongly suggests this is not a tomato leaf. The AI can confirm.
  const aiSaysNotTomato = ai != null && !ai.isTomatoLeaf;
  const looksLikeTomato =
    (local.tomatoMass >= TOMATO_MASS_MIN || extent.greenPct >= 8) && !(aiSaysNotTomato && local.tomatoMass < TOMATO_MASS_MIN);
  const leafGate = {
    looksLikeTomato,
    reason: looksLikeTomato
      ? { en: "Looks leaf-like enough to screen.", ar: "شكلها ورقة كفاية للفرز." }
      : { en: "Low tomato signal and little green — this may not be a tomato leaf.", ar: "إشارة طماطم ضعيفة وأخضر قليل — ممكن دي مش ورقة طماطم." },
  };

  if (!looksLikeTomato) {
    return {
      state: "not_tomato",
      topKey: null,
      topName: null,
      displayConfidence: localTopConf,
      certainty: "low",
      candidates: local.top3,
      agreement: ai ? "disagree" : "ai_offline",
      notes: [leafGate.reason],
      leafGate,
    };
  }

  // ── Certainty band from the (capped, uncalibrated) local top-1 ─────────────
  let band = bandFromConfidence(localTopConf);
  const margin = local.topMargin;

  // Spot-complex rescue: a split-but-coherent spot-complex top-1 with a clear
  // margin over everything OUTSIDE the group earns at least "medium" (probable).
  if (localTopKey && SPOT_COMPLEX.has(localTopKey)) {
    const groupMass = local.candidates
      .filter((c) => SPOT_COMPLEX.has(c.key))
      .reduce((s, c) => s + c.prob, 0);
    const outsideBest = local.candidates.filter((c) => !SPOT_COMPLEX.has(c.key)).reduce((m, c) => Math.max(m, c.prob), 0);
    if (groupMass >= 0.55 && top.prob - outsideBest >= 0.08) {
      if (band === "low") band = "medium";
      notes.push({
        en: "Probable spot-complex disease: the model spreads its evidence across look-alikes (target spot, early blight, bacterial spot, Septoria), which is why the single-class score looks low. Confirm the symptoms before treating.",
        ar: "الأرجح مرض من مجموعة التبقّع: الموديل بيوزّع الدليل على أمراض متشابهة (تبقّع هدفي، لفحة مبكرة، تبقّع بكتيري، سبتوريا)، علشان كده نسبة المرض الواحد بتبان قليلة. أكّد الأعراض قبل العلاج.",
      });
    }
  }

  // ── Reconcile with the AI second opinion (band only; never the number) ─────
  let agreement: ScreeningResult["agreement"] = "ai_offline";
  if (ai) {
    if (ai.notSure || ai.ranked.length === 0) {
      agreement = "partial";
      band = bump(band, -1);
      notes.push({ en: "The AI second opinion was not sure — treat the result as more uncertain.", ar: "الرأي الثاني مش متأكّد — اعتبر النتيجة أقل تأكيدًا." });
    } else if (ai.ranked[0].key === localTopKey) {
      agreement = "agree";
      if (margin >= 0.1 && localTopConf >= 0.6) band = bump(band, 1);
      notes.push({ en: "The AI second opinion agrees with the on-device model.", ar: "الرأي الثاني متفق مع موديل الجهاز." });
    } else if (local.candidates.slice(0, 3).some((c) => c.key === ai.ranked[0].key)) {
      agreement = "partial";
      notes.push({ en: "The AI second opinion picked a different top match within the same shortlist — confirm before treating.", ar: "الرأي الثاني اختار تطابق مختلف من نفس القايمة القصيرة — أكّد قبل العلاج." });
    } else {
      agreement = "disagree";
      band = bump(band, -1);
      notes.push({ en: "The on-device model and the AI disagree — this is uncertain. Confirm with an agronomist.", ar: "موديل الجهاز والذكاء الاصطناعي مختلفين — النتيجة مش مؤكّدة. أكّد مع مهندس زراعي." });
    }
  } else {
    notes.push({ en: "AI second opinion unavailable — showing the on-device result only.", ar: "الرأي الثاني غير متاح — بنعرض نتيجة الجهاز بس." });
  }

  // Weak crop-conditioning separation keeps us honest even if the number is okay.
  if (margin < MARGIN_MIN && band === "high") band = "medium";

  // ── State ──────────────────────────────────────────────────────────────────
  let state: FusedState;
  const veryAmbiguous = localTopConf < 0.35 && margin < 0.08;
  if (veryAmbiguous) {
    state = "not_sure";
  } else if (band === "high" && agreement !== "disagree") {
    state = "confident";
  } else {
    state = "screening";
  }

  // Persistent honesty notes.
  notes.push({
    en: "This is an uncalibrated visual-match value, not the probability the diagnosis is correct.",
    ar: "دي قيمة تطابق بصري غير معايَرة، مش احتمال إن التشخيص صح.",
  });
  notes.push({
    en: "Tomato was selected by you; the image model does not independently confirm the host crop.",
    ar: "إنت اللي اخترت الطماطم؛ موديل الصورة ما بيأكّدش المحصول لوحده.",
  });

  // ── AI-only disease override ───────────────────────────────────────────────
  // When the AI identifies a disease the local ONNX model cannot detect
  // (aiOnly === true) and the AI has sufficient confidence, surface the AI's
  // pick as the result rather than the local model's guess.
  let finalKey = state === "not_sure" ? null : localTopKey;
  let finalName: Bi | null = null;

  if (ai && !ai.notSure && ai.ranked.length > 0) {
    const aiTop = ai.ranked[0];
    const aiEntry = diseaseByKey(aiTop.key);
    if (
      aiEntry?.aiOnly === true &&
      aiTop.confidence >= 0.60 &&
      (state === "not_sure" || agreement === "disagree")
    ) {
      finalKey = aiTop.key;
      state = "screening";
      notes.push({
        en: `The AI identified ${aiTop.name} (${Math.round(aiTop.confidence * 100)}%) — a disease the on-device model cannot detect. Confirm visually before treating.`,
        ar: `الذكاء الاصطناعي تعرّف على ${aiEntry.name.ar} (${Math.round(aiTop.confidence * 100)}٪) — وهو مرض ما يقدرش موديل الجهاز يكتشفه. أكّد بعينك قبل العلاج.`,
      });
    }
  }

  const entry = finalKey ? diseaseByKey(finalKey) : undefined;
  const localEntry = localTopKey ? diseaseByKey(localTopKey) : undefined;
  finalName = entry?.name ?? localEntry?.name ?? top?.name ?? null;

  return {
    state,
    topKey: finalKey,
    topName: state === "not_sure" ? null : finalName,
    displayConfidence: localTopConf,
    certainty: band,
    candidates: local.top3,
    agreement,
    notes,
    leafGate,
  };
}

/** Map the visible-discoloration band onto a coarse severity estimate for Phase 5. */
export function severityFromExtent(extent: InfectionExtent): { lossLowPct: number; lossHighPct: number; label: string } {
  const e = extent.extentPct;
  if (e < 5) return { lossLowPct: 3, lossHighPct: 10, label: "low" };
  if (e < 15) return { lossLowPct: 8, lossHighPct: 20, label: "moderate" };
  if (e < 35) return { lossLowPct: 18, lossHighPct: 35, label: "high" };
  return { lossLowPct: 30, lossHighPct: 55, label: "severe" };
}
