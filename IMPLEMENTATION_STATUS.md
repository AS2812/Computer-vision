# AgroVision Implementation Status

## Offline-first PWA, installability & front-end hardening (current)

Makes the "checked on your device" promise literally true on repeat/offline use and
raises the front-end quality bar. No change to the honest-by-construction engine.

- [x] **Service worker** (`apps/web/public/sw.js`): offline-first, versioned caches.
  App shell = network-first with cached `index.html` fallback (offline reloads work);
  the ~9 MB ONNX model = cache-first (cached once, served instantly forever); the
  onnxruntime-web wasm runtime (the cross-origin jsDelivr CDN) = cache-first on opaque
  responses, so **inference now runs fully offline** after the first load — partially
  closing the previously deferred "self-host the ORT wasm" item. Dynamic, sensitive
  calls (Supabase AI gateway/assistant, Open-Meteo weather, market prices, non-GET) are
  **never cached** and pass straight to the network.
- [x] **Installable** (`apps/web/public/manifest.webmanifest` + `icon.svg` / `favicon.svg`,
  AR-first `dir:rtl`): "Install" button in the header (shown only when the browser offers
  it) and an "update ready → Update now" banner driven by `src/lib/pwa.ts` (`usePwa`).
  SW registered in production only (dev stays SW-free so Vite HMR is untouched);
  `netlify.toml` serves `/sw.js` with `must-revalidate` so new deploys are detected.
- [x] **Error boundary** (`src/components/ErrorBoundary.tsx`, wraps `<App/>` in
  `main.tsx`): a render crash shows a calm bilingual recovery card + reload, not a white
  screen.
- [x] **UX / a11y**: intro splash now shows **once per session** and is **skipped for
  `prefers-reduced-motion`**; the assistant drawer closes on **Escape**, locks body
  scroll, and exposes `role="dialog"` / `aria-modal` / `aria-expanded` / `aria-controls`;
  `<html lang/dir>` is kept in sync with the AR↔EN toggle; `index.html` gains real
  metadata (description, manifest, icons, apple-touch, theme-color), a FOUC-preventing
  background, and a bilingual `<noscript>`.
- [x] Verified: `tsc --noEmit` clean, `vite build` succeeds (PWA assets emitted to
  `dist/`), `vitest run` → 14 passed.
- [ ] Deferred: pre-rendered PNG icons (currently SVG-only — fine for Chromium install +
  favicons; some platforms prefer PNG); precaching hashed build assets at install time
  (currently runtime-cached on first use).

## Literal-spec rebuild: in-browser ONNX + Edge-Function gateway (current)

A ground-up rebuild of the web app to the AgroVision Egypt — Tomato Edition spec.
The on-device pass and the 6-phase logic now run **in the browser**; the AI second
opinion goes through a **single Supabase Edge Function** (the only gateway). The
legacy FastAPI-coupled web UI was preserved under `apps/web/src/legacy/` (excluded
from build/tests), not deleted. The Python services (`services/api`) still exist but
the web app no longer depends on them.

- [x] **In-browser inference** (`apps/web/src/lib/onnx.ts`): the PlantVillage
  MobileNetV2 ONNX model runs via `onnxruntime-web` (wasm, single-threaded; the wasm
  runtime loads from the version-matched jsDelivr CDN — onnxruntime-web's `exports`
  blocks deep `?url` imports and a `/public` copy breaks Vite's dev transform — while
  the model + inference stay on device). Replicates the server `mobilenet_pv`
  preprocessing exactly (resize
  short-edge 256 → center-crop 224 → `(x−0.5)/0.5` → NCHW), softmaxes the 38 classes,
  crop-conditions to the 10 tomato classes, and reports engine + check-time(ms) +
  model size ("Checked on your device").
- [x] **Ported data layer** (TS, bilingual, faithful to `services/api`): 10-class
  tomato KB enriched with leaf/fruit/stem symptoms, cause type, lookalikes, and a
  "today check" (`data/diseases.ts`); Egypt sources + 4 provenance badges
  (`data/sources.ts`); CAPMAS yield (≈16,346–16,583 kg/feddan) + reference prices +
  the 8-area cost-benefit generator (`data/economics.ts`); bilingual UI copy
  (`data/i18n.ts`). No chemical doses anywhere in the KB.
- [x] **Heuristics** (`lib/imageSignals.ts`, `lib/weather.ts`): quality gate
  (resolution, Laplacian-variance blur, brightness — soft warn), HSV infection-extent
  (discoloration/yellow/dark, labelled a rough estimate), Open-Meteo current weather
  (no key) and a per-disease weather-pressure rule table.
- [x] **Honest fusion + hard safety gate** (`lib/screening.ts`, `lib/safety.ts`):
  confident/screening/not_sure/not_tomato states, tomato-leaf gate, spot-complex
  rescue, capped uncalibrated confidence; chemical modes blocked at low confidence
  and locked until the diagnosis is confirmed AND APC registration is verified
  (viruses never unlock). Residue → QCAP. AI never sets a dose or unlocks the gate.
- [x] **`analyze` Edge Function** (`supabase/functions/analyze/index.ts`, Deno): the
  only gateway. Calls the hosted vision model (provider stays `mimo-v2.5-free`,
  key server-side), merges Arabic advice from Postgres, logs an anonymised report.
  Degrades to local-only when offline/unconfigured.
- [x] **Schema migration** (`supabase/migrations/202606180001_…sql`): `tomato_advice`
  (public read), `anonymized_reports` (service-role only, no image/GPS), opt-in
  `case-images` storage bucket with owner-scoped RLS.
- [x] **UI**: Arabic-first RTL, AR/EN toggle, large tap targets. Capture pipeline
  (opt-in GPS/reminders, fixed tomato, quality+leaf gates, dual analysis, supporting
  signals, screening verdict) + the 6 phases + sidebar (grounded assistant, Egypt
  sources, provenance panel, downloads, saved cases). Safety block shown once
  (Phase 6 + sidebar). Client-side CSV (bilingual) + PDF (`lib/exports.ts`).
- [x] Verified: `tsc --noEmit` clean, `vite build` succeeds, `vitest run
  src/lib/engine.test.ts` → 14 passed (KB shape/look-alikes/no-dose, fusion states,
  safety-gate rules, CAPMAS economics + provenance).
- [ ] Deferred: self-hosting the ORT wasm runtime for full offline use (currently the
  version-matched CDN; needs a Vite static-copy step since the package blocks deep
  imports); porting the rich assistant to its own Edge Function; a fitted calibration
  sidecar from real Egyptian field photos.

## Photo-only report: six generated phases + sidebar assistant (current)

- [x] The case workspace is now photo-first and read-only: select a saved case or
  upload one photo, then inspect the generated report. The consultation form is no
  longer embedded in the report pane; follow-up help lives in the sidebar chatbot.
- [x] The backend generates a six-phase report with summary cards, disease info,
  protection, consulting Q&A, treatment safety, cost forecast, and conclusion.
  The report also carries source metadata, assumptions, safety notes, and a
  primary disease result with an explicit low-confidence warning.
- [x] The report exports stay in sync across UI, JSON, CSV, and PDF. The CSV/PDF
  routes now include the same generated phases, summary cards, source metadata,
  sidebar context, and conclusion text shown in the workspace.
- [x] Cost-benefit uses transparent area-range scenarios and CAPMAS-backed tomato
  reference ranges instead of invented numbers. Any missing farmer context stays
  labeled as an assumption rather than a fake measurement.
- [x] Tests: `uv run pytest -q` -> 124 passed; `pnpm exec vitest run` -> 4 files,
  12 tests passed.

## Forms-free report: no "missing information", generated cases instead (current)

- [x] Report is generated from the image alone — the detected disease is ALWAYS the
  primary result, even below 50 %, with an honest low-confidence warning (exact
  Egyptian-Arabic wording) that never blocks the six phases.
- [x] Cost-benefit is auto-generated as **area-range cases** (home garden, 1/6/12
  qirat, 1/3/5/10 feddan) — no area input. Every number carries value, unit,
  source_type (live_market / admin_table / csv_fallback / estimated_range),
  confidence, and the assumption behind it (`application/area_ranges.py`).
- [x] Fixed a honesty bug: the reference price source ("…not live") no longer
  mis-maps to `live_market` — reference prices are labelled `estimated_range`.
- [x] Unknown context (farm type, area) now becomes positive **assumptions** +
  generated scenarios, never "missing"/"completeness" notes (`completeness` is empty).
- [x] New schema: `primary_detected_disease`, `confidence_warning`, `area_range_cases`,
  `assumptions` on `SystemOutput` (each number a `SourcedRange`).
- [x] Frontend: removed the "Missing Inputs" panel and "Continue with missing data"
  button; phases read "auto-generated", render the area-range cases + assumptions +
  confidence warning; gentler, smoother card tilt (no jarring translateZ pop).
- [x] Tests: `test_forms_free_report.py` (area-range generation, sourced numbers,
  low-confidence-primary, exact warning, no "missing information" text); updated the
  report-contract + Phase-6 web tests. Backend 124 passed; web 13 passed.
- [ ] Deferred: voice/speech input, full single-language re-translation on switch,
  and hiding the legacy economics form behind an explicit "advanced mode" toggle
  (the form remains below the generated cases but is no longer required).

## Target Spot accuracy, honest calibration & decision policy (current)

- [x] Root-caused the "Target Spot doesn't diagnose" issue: its lesions split the
  model's softmax across look-alikes (Early Blight / Bacterial Spot / Septoria),
  so the correct class is top-1 but ~40 %, and a flat 0.65 gate buried it.
- [x] `services/api/app/calibration.py`: frozen tomato class index map (Target Spot
  at index 34, guarded by tests), confusion groups, temperature scaling
  (`apply_temperature` / `fit_temperature` + sidecar loader, identity until fitted),
  per-class thresholds, and an honest high/medium/low decision policy.
- [x] Confusion-group rescue in `fuse_diagnosis`: a split-but-coherent Target-Spot
  top-1 (high combined group mass, clear margin over other diseases, host
  supported) is promoted from "no reliable diagnosis" to **"Probable Target spot —
  medium confidence"**. The displayed number stays the raw value (never inflated).
- [x] Raw vs calibrated confidence + uncertainty level reported end-to-end
  (`DiseasePrediction.raw_scores`, `AnalysisResponse.raw_confidence` /
  `calibrated_confidence` / `calibration_method` / `uncertainty_level`).
- [x] `services/api/app/target_spot.py`: image symptom evidence (brown spots, ring
  texture, yellow halo, blur / leaf-size) as bilingual *supporting-only* bullets
  that always disclose the Early Blight / Bacterial Spot look-alikes.
- [x] `ml/training/evaluate_tomato.py`: confusion matrix, per-class precision /
  recall / F1, confidence distribution, Target-Spot focus block, and an optional
  `--fit-temperature` that writes the calibration sidecar. Pure metric functions
  unit-tested; runs over a `Tomato___<Class>/` ImageFolder.
- [x] Tests: class-index mapping guard (catches re-ordering), Target Spot
  low-confidence→medium behaviour, no-inflation guarantee, calibration output,
  temperature fit, symptom evidence, and evaluation metric maths.
- [ ] Real fine-tuning / a fitted temperature still needs real Egyptian Target Spot
  field photos (none in the repo); the harness + sidecar are ready for them.

## Complete six-phase report from one photo (current)

- [x] Phase 5 image-derived severity (`severity.py`): visible-discoloration band → yield-loss
  range + recovery + weather-risk, as a clearly-labelled estimate (never a measurement).
- [x] Phase 5 reference cost estimate so it is never blank: uses the farmer's real numbers when
  entered, otherwise an Egyptian reference-price estimate (treatment cost vs potential EGP loss).
- [x] Egypt price-provider abstraction (`prices.py`): reviewed reference ranges by default,
  swappable for a live API, admin table, or CSV (`CsvPriceProvider`) with transparent fallback.
- [x] Phase 6 generates all six Egyptian farm scenarios (home garden, open field, greenhouse,
  desert/new-land, small commercial, coastal/Alexandria), each saying how confidence, protection,
  treatment, cost, and recommendation change — bilingual, never blank.
- [x] Report completeness notes: which phases used generated estimates because farmer data was
  missing (transparency, not failure). Severity/cost/scenarios added to the PDF + CSV exports.
- [x] No-GPS analyze defaults to live Alexandria weather, falling back to the labelled reference.
- [x] Tests: price provider + CSV swap, severity scaling, reference cost estimate + farmer-input
  deference, six scenarios, no-cure handling, report completeness; Phase-6 scenario UI test.

## Fused tomato diagnosis + unified dashboard (current)

- [x] Hosted vision "second opinion" (`services/api/app/vision_llm.py`) that sends the leaf image
  to a real multimodal model (`mimo-v2.5-free`, reusing the LLM key), constrained to the tomato
  disease list, with robust JSON parsing, name→knowledge-base mapping, retry-on-empty for
  reasoning models, and graceful `None` (offline/local-only) on any failure.
- [x] Test-time augmentation on the local ONNX model (averaged over center, flip, tighter crop)
  for steadier real-field-photo predictions.
- [x] Honest three-state fusion of the local model + vision opinion (`confident` / `screening`
  / `not sure` / `not a tomato leaf`), capped confidence (never near-certain), per-model
  attribution, and disagreement disclosure — surfaced identically in the quick check and the case.
- [x] Verified live: the Septoria sample now reads "Most likely (screening): Septoria leaf spot",
  honestly labelled, instead of a flat "no reliable diagnosis".
- [x] Tomato-only across the UI and analyze flow; banana retired from active paths (kept on disk).
- [x] One-photo-driven unified dashboard: the upload runs the fused diagnosis, auto-detects the
  case phase as a headline, and auto-builds the full 6-phase plan from the same analysis (one
  vision call, no second model run).
- [x] Opt-in live smoke `scripts/vision_smoke.py`; vision disabled in the test suite (`conftest.py`).

## Completed Local Capabilities

- [x] Versioned crop-case API foundation under `/api/v1/cases`.
- [x] Strict case, diagnosis, treatment, economics, prediction, recommendation, and report contracts.
- [x] Explicit crop-case state machine with guarded transitions.
- [x] Replaceable thread-safe in-memory case repository for local development.
- [x] Deterministic useful-question engine with batches limited to five and no repeated questions.
- [x] Low-confidence safety gate that blocks chemical treatment categories.
- [x] Decimal-based cost-benefit calculator that returns `need_more_data` instead of inventing inputs.
- [x] Stable system-output JSON report matching `docs/system-output.schema.json`.
- [x] Case image-analysis adapter connected to the installed tomato/banana ONNX runtimes.
- [x] Supabase persistence and owner-based RLS for crop cases, observations, diagnoses, treatment plans, assets, and reports.
- [x] Private typed case-image storage with persisted image-model evidence.
- [x] Resumable case-list API: `GET /api/v1/cases`.
- [x] Reliable Windows launcher that verifies the current case API before reporting startup success.
- [x] Explicit browser GPS and notification permission controls with GPS case-form prefill.
- [x] Photo-to-case transfer preserving crop, selected image, measured location, and detected symptom labels.
- [x] Consented device-GPS provenance that clearly distinguishes analysis-time position from an unverified photo capture location.
- [x] Observation provenance for farmer answers, direct RGB image measurements, image models, device sensors, reviewed rules, experts, and labs.
- [x] Direct case-image measurements for dimensions, visible discoloration, yellow/dark pixels, green coverage, Excess Green, and VARI.
- [x] Automatic six-phase generation after photo analysis: protection, treatment safety, consulting questions, missing economics, prediction limits, and recommendation.
- [x] Rejected visual diagnoses retain ranked hypotheses as alternatives without promoting them to a confirmed disease.
- [x] Egypt-only official-source registry covering ARC plant-disease diagnosis, APC pesticide registration, and QCAP food-safety/residue testing.
- [x] Evidence-backed Egyptian diagnosis-confirmation workflow requiring an uploaded agronomist/lab PDF or image, organization, and report reference.
- [x] Confirmation evidence SHA-256 integrity record and private Supabase asset type.
- [x] Separate visual-model score and Egyptian expert/lab confirmation status; confirmation never changes a visual score to a fake 100%.
- [x] Confirmation-aware treatment and economics gates that still restrict chemicals to category-only guidance and require current Egyptian APC registration.
- [x] Exact supplied tomato photo safety check remains unconfirmed and blocks chemical guidance when the local model cannot reliably identify disease.
- [x] Blank-by-default farmer and economics forms; partial values are accepted and unavailable inputs remain explicit instead of becoming zeroes or assumptions.
- [x] Dedicated crop-case PDF and CSV export routes.
- [x] Versioned internal disease-class treatment safety rules for fungal, bacterial, viral, insect, nutrient, abiotic, and unknown cases.
- [x] Viral/no-cure/nutrient/low-confidence gates that prevent unsafe curative or chemical claims.
- [x] Polished 6-phase case workspace dashboard: Phase 1 (Diagnosis: setup + image), Phase 2 (Protection: field hygiene + risk level), Phase 3 (Consulting: batched chatbot Q&A), Phase 4 (Treatment: safety gates), Phase 5 (Cost-Benefit + Heuristic Prediction), Phase 6 (Recommendation + Conclusion report).
- [x] Phase stepper UI with locked/incomplete/ready/complete status badges and missing-inputs guidance.
- [x] Risk level badge (unknown/low/medium/high) derived only from collected farmer observations.
- [x] Egypt-specific context notes (flood irrigation splash risk, greenhouse humidity) in Protection phase.
- [x] Responsive React case workspace with quick-photo/case-workflow navigation.
- [x] Create and resume persistent crop cases from the dashboard.
- [x] Guided farmer-context form for irrigation, spread speed, and affected-plant percentage.
- [x] Typed case-image upload connected to tomato/banana inference.
- [x] Case diagnosis, alternatives, missing evidence, protection, treatment-safety, questions, and recommendation UI.
- [x] Case cost-benefit UI using farmer-supplied EGP/feddan values and deterministic backend calculations.
- [x] Frontend mutation lock preventing stale responses from overwriting newer diagnosis results.
- [x] Windows-first React/Vite and FastAPI local application.
- [x] Arabic/English RTL dashboard and grounded bilingual assistant.
- [x] Separate checksum-verified ONNX tomato and banana model selection.
- [x] Confidence threshold, low-confidence rejection, and model limitations.
- [x] Honest visual-diagnosis gate using crop-label support, top-match separation, host-selection disclosure, and treatment/economics locks.
- [x] RGB vegetation indices, tiled processing, plant clusters, and honest image-derived indicators.
- [x] Clearly labelled fixed Egypt demo weather reference.
- [x] Case-specific treatment, irrigation, prevention, and greenhouse assistant prompts.
- [x] Detailed PDF and CSV reports with model, diagnosis, varieties, irrigation, and treatment fields.
- [x] Optional local Supabase Auth, Postgres, private Storage, and RLS.
- [x] Persisted uploads, analyses, feature results, alerts, recommendations, and reports.
- [x] Recent-analysis history API: `GET /api/analyses`.
- [x] Automatic local demo account, farm, mission, image, and analysis seed.
- [x] CPU/DirectML/CUDA provider detection with CPU default.
- [x] Repeatable CPU latency and memory benchmark.
- [x] Model checksum and validation-metadata audit.
- [x] Backend, frontend, model-smoke, E2E, and expanded pgTAP RLS tests.
- [x] GitHub Actions workflow including Supabase database tests.

## Still Requires Real Data, Credentials, Or External Deployment

- [ ] Independent agronomist review and Egyptian label validation for the versioned treatment rules.
- [ ] External fact adapters with source/date provenance for live weather, prices, and alerts.
- [ ] Independently field-validated disease model.
- [ ] Independently validated Egyptian tomato field model and calibrated fusion weights/thresholds.
- [ ] Separate trained water-stress classifier.
- [ ] Real weed, nutrient-deficiency, and pest detectors.
- [ ] Calibrated yield model trained on harvest records.
- [ ] Soil/crop/weather planting-suitability model.
- [ ] Georeferenced field heatmaps and drone-mission workflow.
- [ ] Multispectral NDVI/NDRE processing.
- [ ] React Native Android/iOS application and TFLite on-device inference.
- [ ] Production Supabase project, Edge Function gateway, and cloud deployment.
- [ ] Independent Egyptian field-photo evaluation, confusion matrices, and failure report.
- [ ] Legally cleared production model weights and datasets.
