import { describe, expect, it } from "vitest";
import { diseaseByKey, HEALTHY, TOMATO_DISEASES } from "../data/diseases";
import { capmasYieldRange, generateAreaCases } from "../data/economics";
import { evaluateGate } from "./safety";
import { fuseDiagnosis, severityFromExtent } from "./screening";
import type { LocalCandidate, LocalInference } from "./onnx";
import type { InfectionExtent } from "./imageSignals";

function cand(key: string, prob: number): LocalCandidate {
  const d = diseaseByKey(key);
  return { key, rawLabel: d?.rawLabel ?? key, name: d?.name ?? { en: key, ar: key }, prob };
}

function local(cands: LocalCandidate[], tomatoMass: number): LocalInference {
  const sorted = [...cands].sort((a, b) => b.prob - a.prob);
  return {
    candidates: sorted,
    top3: sorted.slice(0, 3),
    tomatoMass,
    topMargin: sorted.length > 1 ? sorted[0].prob - sorted[1].prob : sorted[0].prob,
    engine: "test",
    checkMs: 1,
    modelSizeMb: 9,
    heapUsedMb: null,
    modelFile: "test.onnx",
  };
}

const EXTENT: InfectionExtent = { extentPct: 12, discolorationPct: 6, yellowPct: 4, darkPct: 2, greenPct: 40 };

describe("disease KB", () => {
  it("has 9 disease classes + healthy = the 10 PlantVillage tomato classes (indices 28..37)", () => {
    expect(TOMATO_DISEASES).toHaveLength(9);
    expect(TOMATO_DISEASES.map((d) => d.modelIndex)).toEqual([28, 29, 30, 31, 32, 33, 34, 35, 36]);
    const all = [...TOMATO_DISEASES, HEALTHY];
    expect(all).toHaveLength(10);
    expect(diseaseByKey("tomato_target_spot")?.modelIndex).toBe(34);
    expect(HEALTHY.modelIndex).toBe(37);
  });

  it("only references look-alike keys that exist in the set", () => {
    const keys = new Set([...TOMATO_DISEASES, HEALTHY].map((d) => d.key));
    for (const d of TOMATO_DISEASES) for (const k of d.lookalikes) expect(keys.has(k)).toBe(true);
  });

  it("never embeds a chemical dose in the KB text", () => {
    const blob = JSON.stringify(TOMATO_DISEASES).toLowerCase();
    expect(blob).not.toMatch(/\bml\/(l|liter)|gram per|g\/l\b|cc\/|ppm\b/);
  });
});

describe("fuseDiagnosis", () => {
  it("returns confident when the local top-1 is strong and the AI agrees", () => {
    const r = fuseDiagnosis({
      local: local([cand("tomato_late_blight", 0.9), cand("tomato_early_blight", 0.2)], 0.9),
      ai: { isTomatoLeaf: true, notSure: false, ranked: [{ key: "tomato_late_blight", name: "Late blight", confidence: 0.8 }], visibleSigns: "", model: "m", latencyMs: 10 },
      extent: EXTENT,
    });
    expect(r.state).toBe("confident");
    expect(r.certainty).toBe("high");
    expect(r.topKey).toBe("tomato_late_blight");
  });

  it("flags not_tomato when crop mass and green are both very low", () => {
    const r = fuseDiagnosis({
      local: local([cand("tomato_late_blight", 0.5), cand("tomato_early_blight", 0.4)], 0.2),
      ai: null,
      extent: { ...EXTENT, greenPct: 2 },
    });
    expect(r.state).toBe("not_tomato");
  });

  it("rescues a split spot-complex top-1 to at least medium", () => {
    const r = fuseDiagnosis({
      local: local(
        [cand("tomato_target_spot", 0.4), cand("tomato_early_blight", 0.25), cand("tomato_bacterial_spot", 0.2), cand("tomato_late_blight", 0.1)],
        0.95,
      ),
      ai: null,
      extent: EXTENT,
    });
    expect(r.certainty).not.toBe("low");
    expect(r.state).toBe("screening");
  });

  it("never reports near-certain confidence (capped)", () => {
    const r = fuseDiagnosis({ local: local([cand("tomato_late_blight", 0.999)], 0.99), ai: null, extent: EXTENT });
    expect(r.displayConfidence).toBeLessThanOrEqual(0.95);
  });
});

describe("safety gate", () => {
  const base = { isViral: false, isPest: false };
  it("blocks all chemical modes at low confidence", () => {
    const g = evaluateGate({ certainty: "low", confirmed: true, apcVerified: true, ...base });
    expect(g.chemicalBlocked).toBe(true);
    expect(g.defaultMode).toBe("confirm_first");
    expect(g.modes.find((m) => m.mode.id === "balanced")?.locked).toBe(true);
  });

  it("keeps Balanced/Strongest locked until confirmed AND APC verified", () => {
    expect(evaluateGate({ certainty: "high", confirmed: false, apcVerified: true, ...base }).chemicalBlocked).toBe(true);
    expect(evaluateGate({ certainty: "high", confirmed: true, apcVerified: false, ...base }).chemicalBlocked).toBe(true);
    const ok = evaluateGate({ certainty: "high", confirmed: true, apcVerified: true, ...base });
    expect(ok.chemicalBlocked).toBe(false);
    expect(ok.modes.find((m) => m.mode.id === "strongest")?.locked).toBe(false);
  });

  it("never unlocks chemicals for a virus", () => {
    const g = evaluateGate({ certainty: "high", confirmed: true, apcVerified: true, isViral: true, isPest: false });
    expect(g.chemicalBlocked).toBe(true);
  });

  it("always allows the non-chemical modes", () => {
    const g = evaluateGate({ certainty: "low", confirmed: false, apcVerified: false, ...base });
    for (const id of ["confirm_first", "sanitation_only", "prevention_only"]) {
      expect(g.modes.find((m) => m.mode.id === id)?.allowed).toBe(true);
    }
  });
});

describe("economics", () => {
  it("derives the CAPMAS yield range (~16,346–16,583 kg/feddan)", () => {
    const [lo, hi] = capmasYieldRange();
    expect(Math.round(lo)).toBe(16346);
    expect(Math.round(hi)).toBe(16583);
  });

  it("generates all 8 area sizes; sanitation costs zero; defaults are reference estimates", () => {
    const cases = generateAreaCases({ mode: "balanced", severity: severityFromExtent(EXTENT) });
    expect(cases).toHaveLength(8);
    expect(cases.every((c) => c.treatmentCost.provenance === "estimated_range")).toBe(true);
    const san = generateAreaCases({ mode: "sanitation_only", severity: severityFromExtent(EXTENT) });
    expect(san.every((c) => c.treatmentCost.low === 0)).toBe(true);
  });

  it("switches money figures to 'generated' once a real local price is entered", () => {
    const cases = generateAreaCases({ mode: "balanced", severity: severityFromExtent(EXTENT), farmerPriceEgpPerKg: 8 });
    expect(cases.every((c) => c.revenue.provenance === "generated")).toBe(true);
  });
});
