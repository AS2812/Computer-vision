import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const analysis = {
  analysis_id: "an-1",
  filename: "leaf.png",
  crop: "tomato",
  width: 800,
  height: 600,
  processing_ms: 120,
  peak_memory_mb: 100,
  provider: "CPUExecutionProvider",
  alerts: [
    { en: "Screening result only: most likely Septoria leaf spot (tomato).", ar: "نتيجة فرز مبدئي بس." },
  ],
  recommendations: [{ en: "Start the safe protection steps.", ar: "ابدأ خطوات الوقاية الآمنة." }],
  assistant_questions: [{ en: "What is the safest tomato treatment plan?", ar: "ما هي خطة العلاج؟" }],
  fused_state: "screening",
  diagnosis_candidates: [
    { disease: "Septoria leaf spot (tomato)", confidence: 0.45 },
    { disease: "Early blight (tomato & potato)", confidence: 0.25 },
  ],
  results: [
    {
      feature: "disease",
      title: "Disease check (AI)",
      title_ar: "كشف المرض",
      level: "experimental",
      score: 0.45,
      value: "Most likely (screening): Septoria leaf spot (tomato) (45%) — not confirmed, verify",
      value_ar: "الأرجح (فرز مبدئي)",
      confidence: 0.45,
      evidence: ["AI second opinion (mimo-v2.5-free): Septoria leaf spot (tomato) 95%"],
      limitation: "Screening match from the local model and the AI second opinion.",
    },
  ],
};

const builtCase = {
  case_id: "case-1",
  status: "needs_expert",
  crop: "tomato",
  location: "",
  farm_type: null,
  growth_stage: null,
  symptoms: [],
  observations: {},
  egypt_sources: [],
  diagnosis: {
    top_disease: "Septoria leaf spot (tomato)",
    confidence: 0.45,
    alternatives: [],
    evidence: [],
    missing_info: [],
    confirmation_status: "unconfirmed",
    confirmation: null,
  },
  disease_class: "fungal",
  treatment_rule_version: "",
  protection_plan: [],
  treatment_plan: { non_chemical: [], chemical_category_if_needed: [], safety_notes: [] },
  cost_benefit: {
    treatment_cost_egp: null,
    estimated_saved_revenue_egp: null,
    net_benefit_egp: null,
    roi: null,
    break_even_yield_saved_kg: null,
    decision: "need_more_data",
    missing_inputs: [],
  },
  recommendation: { best_action_now: "", next_3_to_7_days: "", when_to_call_expert: "" },
  updated_at: "2026-06-15T00:00:00Z",
};

function ok(value: unknown): Promise<Response> {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(value) } as Response);
}

function routeFetch(url: RequestInfo | URL, options?: RequestInit): Promise<Response> {
  const u = String(url);
  const method = options?.method ?? "GET";
  if (u.includes("/api/analyze")) return ok(analysis);
  if (u.includes("/api/assistant")) return ok({ answer: "Use a protectant fungicide.", sources: ["ref"], mode: "offline-grounded-template" });
  if (u.includes("/diagnosis")) return ok(builtCase);
  if (/\/api\/v1\/cases$/.test(u) && method === "POST") return ok(builtCase);
  if (/\/api\/v1\/cases\/case-1$/.test(u)) return ok(builtCase);
  if (/\/api\/v1\/cases\?/.test(u)) return ok([]);
  return ok([]);
}

describe("AgroVision unified dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(routeFetch));
  });

  it("runs one photo through the fused engine and shows the auto-detected phase", async () => {
    const { container } = render(<App />);
    const file = new File(["bytes"], "leaf.png", { type: "image/png" });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(screen.getByText("Phase 1 — Screening")).toBeInTheDocument());
    expect(screen.getByText(/Screening result only/)).toBeInTheDocument();
    // The fixed crop chip shows tomato and there is no banana option anywhere.
    expect(screen.queryByRole("radio", { name: "Banana" })).not.toBeInTheDocument();
  });

  it("switches to Arabic display", () => {
    render(<App />);
    fireEvent.click(screen.getByText("العربية"));
    expect(screen.getByText("اعرف زرعك تعبان من إيه من صورة واحدة.")).toBeInTheDocument();
  });

  it("opens the chat drawer and sends a question to the assistant", async () => {
    render(<App />);
    fireEvent.click(screen.getByLabelText("Ask AI"));
    fireEvent.change(screen.getByPlaceholderText("Ask about your crop…"), { target: { value: "What is this disease?" } });
    fireEvent.click(screen.getByLabelText("Send question"));
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(screen.getByText("What is this disease?")).toBeInTheDocument();
  });
});
