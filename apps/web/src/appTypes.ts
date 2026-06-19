// Shared app-level types tying the pipeline outputs into one analysis object.

import type { Lang } from "./data/diseases";
import type { InfectionExtent, QualityReport } from "./lib/imageSignals";
import type { TomatoMarketPrice } from "./lib/market";
import type { LocalInference } from "./lib/onnx";
import type { ScreeningResult } from "./lib/screening";
import type { WeatherNow, WeatherPressure } from "./lib/weather";

export type { Lang };

export interface AppAnalysis {
  id: string;
  fileName: string;
  /** Object URL for on-screen preview. */
  previewUrl: string;
  /** Downscaled JPEG data URL (only sent to the gateway if AI is enabled). */
  imageDataUrl: string;
  local: LocalInference;
  quality: QualityReport;
  extent: InfectionExtent;
  weather: WeatherNow;
  marketPrice?: TomatoMarketPrice | null;
  pressure: WeatherPressure;
  screening: ScreeningResult;
  aiVisibleSigns?: string;
  createdAt: number;
}

export type CaseStatusKey =
  | "collecting"
  | "needs_expert"
  | "diagnosis"
  | "economics"
  | "report";

export interface SavedCase {
  id: string;
  title: string;
  status: CaseStatusKey;
  topKey: string | null;
  createdAt: number;
}

export interface TreatmentProduct {
  rank: number;
  name_en: string;
  name_ar: string;
  frac: string;
  dose_en: string;
  dose_ar: string;
  application_en: string;
  application_ar: string;
  phi_en: string;
  phi_ar: string;
  hazard_en: string;
  hazard_ar: string;
  price_en: string;
  price_ar: string;
  price_sources: Array<{
    source: string;
    title: string;
    url: string;
    price_text: string;
    availability_en: string;
    availability_ar: string;
    checked_at: string;
    live: boolean;
    note_en: string;
    note_ar: string;
  }>;
  note_en: string;
  note_ar: string;
}

export interface TreatmentCatalog {
  disease_key: string;
  disease_name_en: string;
  disease_name_ar: string;
  crop: string;
  treatments: TreatmentProduct[];
  availability: {
    status_en: string;
    status_ar: string;
    apc_url: string;
    price_status_en: string;
    price_status_ar: string;
  };
  prevention: {
    en: string[];
    ar: string[];
  };
}

/** Pipeline progress for the capture animation. */
export type PipelineStage =
  | "idle"
  | "loading"
  | "quality"
  | "leaf"
  | "local"
  | "signals"
  | "ai"
  | "done"
  | "error";
