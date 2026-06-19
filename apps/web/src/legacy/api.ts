import type { Analysis, CaseImageView, CropCase, SystemReport } from "./types";

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8765";

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = body.detail || `Request failed (${response.status})`;
    if (response.status === 404 && detail === "Not Found") {
      throw new Error("API route not found — restart the backend server");
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  demo: () => fetch(`${API_URL}/api/demo`).then(json<Analysis>),
  analyze: (file: File, crop?: string, lat?: number, lon?: number) => {
    const form = new FormData();
    form.append("file", file);
    if (crop) form.append("crop", crop);
    if (lat !== undefined) form.append("lat", String(lat));
    if (lon !== undefined) form.append("lon", String(lon));
    return fetch(`${API_URL}/api/analyze`, { method: "POST", body: form }).then(json<Analysis>);
  },
  assistant: (question: string, analysisId?: string, language?: "en" | "ar") =>
    fetch(`${API_URL}/api/assistant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, analysis_id: analysisId, language })
    }).then(json<{ answer: string; sources: string[]; mode: string }>),
  reportUrl: (analysisId: string, format: "csv" | "pdf") =>
    `${API_URL}/api/reports/${analysisId}.${format}`,
  caseReportUrl: (caseId: string, format: "csv" | "pdf") =>
    `${API_URL}/api/v1/cases/${caseId}/report.${format}`,
  caseReport: (caseId: string) =>
    fetch(`${API_URL}/api/v1/cases/${caseId}/report.json`).then(json<SystemReport>),
  cases: (limit = 20) => fetch(`${API_URL}/api/v1/cases?limit=${limit}`).then(json<CropCase[]>),
  getCase: (caseId: string) => fetch(`${API_URL}/api/v1/cases/${caseId}`).then(json<CropCase>),
  createCase: (payload: {
    crop: "tomato";
    location: string;
    farm_type?: string;
    growth_stage?: string;
    symptoms?: string[];
  }) =>
    fetch(`${API_URL}/api/v1/cases`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(json<CropCase>),
  // Set a case diagnosis directly from an already-computed analysis so the unified
  // dashboard fills the whole 6-phase plan without a second (slow) vision call.
  setCaseDiagnosis: (
    caseId: string,
    payload: { candidates: { disease: string; confidence: number }[]; evidence?: string[]; missing_info?: string[] }
  ) =>
    fetch(`${API_URL}/api/v1/cases/${caseId}/diagnosis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(json<CropCase>),
  patchCase: (caseId: string, payload: {
    location?: string;
    farm_type?: string;
    growth_stage?: string;
    symptoms?: string[];
  }) =>
    fetch(`${API_URL}/api/v1/cases/${caseId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(json<CropCase>),
  addCaseObservations: (
    caseId: string,
    values: Record<string, string | number | boolean>,
    source = "farmer_answer"
  ) =>
    fetch(`${API_URL}/api/v1/cases/${caseId}/observations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values, source })
    }).then(json<CropCase>),
  analyzeCaseImage: (caseId: string, file: File, viewType: CaseImageView) => {
    const form = new FormData();
    form.append("file", file);
    form.append("view_type", viewType);
    return fetch(`${API_URL}/api/v1/cases/${caseId}/analyze-image`, { method: "POST", body: form }).then(json<CropCase>);
  },
  confirmCaseDiagnosis: (
    caseId: string,
    file: File,
    payload: {
      disease: string;
      confirmation_type: "egyptian_agronomist" | "egyptian_plant_pathology_lab";
      organization: string;
      report_reference: string;
      confirmer_name?: string;
      notes?: string;
    }
  ) => {
    const form = new FormData();
    form.append("file", file);
    Object.entries(payload).forEach(([key, value]) => {
      if (value) form.append(key, value);
    });
    return fetch(`${API_URL}/api/v1/cases/${caseId}/confirm-diagnosis`, {
      method: "POST",
      body: form
    }).then(json<CropCase>);
  },
  caseQuestions: (caseId: string, limit = 3) =>
    fetch(`${API_URL}/api/v1/cases/${caseId}/questions?limit=${limit}`).then(json<string[]>),
  buildCaseRecommendation: (caseId: string) =>
    fetch(`${API_URL}/api/v1/cases/${caseId}/recommendation`, { method: "POST" }).then(json<CropCase>),
  calculateCaseEconomics: (
    caseId: string,
    payload: {
      area_feddan?: number;
      expected_yield_kg_per_feddan?: number;
      market_price_egp_per_kg?: number;
      yield_loss_without_treatment_percent?: number;
      yield_loss_after_treatment_percent?: number;
      product_cost_egp_per_application?: number;
      labor_cost_egp_per_application?: number;
      sprayer_cost_egp_per_application?: number;
      water_fuel_cost_egp_per_application?: number;
      application_count?: number;
    }
  ) =>
    fetch(`${API_URL}/api/v1/cases/${caseId}/cost-benefit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(json<CropCase>)
};
