# AgroVision Egypt — Tomato Edition (web app)

A free, **Arabic-first** web app that lets an Egyptian tomato farmer upload **one leaf
photo** and get an honest screening + a full action plan. Rebuilt to the literal spec:

- **On device.** The tomato classifier (PlantVillage MobileNetV2) runs in the browser
  via `onnxruntime-web` — "checked on your device". No model keys in the browser.
- **One gateway.** The AI second opinion goes through a single Supabase Edge Function
  (`supabase/functions/analyze`); the provider key stays server-side.
- **Honest by construction.** Confidence is an *uncalibrated visual-match* value, never
  a diagnosis. A hard safety gate blocks chemical advice at low confidence and keeps the
  strong modes locked until the diagnosis is confirmed **and** APC registration is
  verified. The AI can never set a dose or unlock the gate.
- **6 phases:** Diagnosis → Protect Now → Confirm It → Treatment Options → Is It Worth It
  → Your Action Plan, with provenance badges (`live` / `official` / `estimated_range` /
  `generated`) on every number and a sidebar (assistant, Egypt sources, downloads,
  saved cases).

### Run the web app

```powershell
pnpm install
pnpm --filter @agrovision/web dev   # http://localhost:5173
```

The model is served from `apps/web/public/models/` (on-device); the ONNX **wasm runtime**
is loaded from the version-matched jsDelivr CDN (`ort.env.wasm.wasmPaths` in
`src/lib/onnx.ts`, pinned to the `onnxruntime-web` version in `package.json`) and is
HTTP-cached after first load — the model and inference still run on-device. The app runs **without** Supabase
(local-only screening, no AI second opinion). To enable the AI second opinion + cloud
logging, copy `apps/web/.env.example` → `apps/web/.env`, set `VITE_SUPABASE_URL` /
`VITE_SUPABASE_ANON_KEY`, apply the migrations in `supabase/migrations/`, deploy the
`analyze` function, and set its secrets (`EXTERNAL_LLM_API_URL`, `EXTERNAL_LLM_API_KEY`,
`EXTERNAL_VISION_MODEL=mimo-v2.5-free`). Build: `pnpm --filter @agrovision/web build`.
Tests: `pnpm --filter @agrovision/web exec vitest run`.

The legacy FastAPI-backed UI lives under `apps/web/src/legacy/` (excluded from
build/tests); the Python services below still exist but the web app no longer needs them.

---

# AgroVision Egypt Local Analysis (legacy Python services)

CPU-first **tomato** crop-screening application for Windows laptops. From one uploaded leaf
photo it gives a single honest diagnosis, the auto-detected case phase, visible infection
extent, resistant-variety options, and a clearly labelled fixed Egypt weather reference.

## How the diagnosis works (local model + AI second opinion)

A real tomato field photo is hard for any single model. AgroVision fuses two real signals:

1. **Local ONNX model** — PlantVillage MobileNetV2 with test-time augmentation (averaged over a
   few deterministic views), conditioned on tomato, runs fully on-device and offline.
2. **Hosted vision second opinion** — the leaf image is sent to a multimodal model
   (`mimo-v2.5-free` by default, reusing `EXTERNAL_LLM_API_KEY`) which returns an honest, ranked
   tomato-disease guess. It is constrained to the app's disease list and may say "not sure".

The two are fused into **one honest result with three states**: `confident` (both agree),
`screening` (most likely disease, not confirmed — protection is offered but chemicals stay
locked), or `not sure` / `not a tomato leaf`. Confidence is always a screening match, never the
probability that the diagnosis is correct, and each model's contribution is shown. With no
internet (or `EXTERNAL_VISION_ENABLED=false`) it falls back to the local model and the original
honest gate. Banana support has been retired; the app focuses on tomato.

The implementation blueprint for the broader multi-crop diagnosis, consulting, protection,
treatment, economics, prediction, and reporting system is in
[`docs/AGROVISION_DECISION_SUPPORT_ARCHITECTURE.md`](docs/AGROVISION_DECISION_SUPPORT_ARCHITECTURE.md).

## Quick start

1. Start Docker Desktop if you want the local Supabase backend.
2. Run `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`.
3. Run `powershell -ExecutionPolicy Bypass -File scripts/dev.ps1`.
4. Open `http://localhost:5173`.

The API and UI remain usable without Supabase. When local Supabase is running, setup
configures it automatically and analyses, uploaded images, feature results, alerts,
recommendations, and generated reports are persisted. If Supabase is unavailable, the
API safely falls back to in-memory storage.

Local services:

- Dashboard: `http://localhost:5173`
- API documentation: `http://localhost:8765/docs`
- Supabase Studio: `http://127.0.0.1:54323`

The local seed creates a demo account, farm, mission, sample image, and sample analysis.
No production credentials are required.

## Tests

Run `powershell -ExecutionPolicy Bypass -File scripts/test.ps1`.

The normal suite uses deterministic adapters and runs the tomato PlantVillage MobileNetV2
model. The hosted vision second opinion is disabled during tests (`conftest.py`) and exercised
separately with the network mocked, so the suite stays offline and deterministic.

To see the fused engine on a real photo, run the opt-in live smoke (makes a real vision call):

```powershell
uv run --project services/api python scripts/vision_smoke.py "C:\path\to\tomato-leaf.jpg"
```

Run `powershell -ExecutionPolicy Bypass -File scripts/benchmark.ps1` for a repeatable
CPU latency and peak-memory benchmark. `scripts/model_audit.py` verifies the installed
model checksum and prevents a model with missing field metrics from being labeled
validated.

## Train a lightweight disease model

Install the optional training stack and fine-tune MobileNetV3-Small from an ImageFolder
dataset:

```powershell
uv sync --project services/api --extra training --extra onnx
uv run --project services/api python ml/training/train_mobilenetv3.py path\to\dataset
uv run --project services/api python ml/training/export_onnx.py ml/models/disease_mobilenetv3_fp32.pt
```

Update `ml/models/manifest.json` with verified labels, checksum, and evaluation metrics
only after the release gates pass.

## Accuracy and safety

Both locally installed classifiers perform real ONNX inference and are labeled
`experimental`, not field validated. Confidence is uncalibrated. The deterministic
fallback remains `sample-data` when weights are absent or fail checksum verification.

Every other number on the dashboard is **honest by construction** — it is either a
directly measured image statistic or a transparent, documented formula over those
measurements, never a fabricated or inflated value:

- **Visible infection extent** is an experimental discoloration estimate, not biological severity.
- **Resistant varieties** are reviewed examples that still require local availability and seed-code checks.
- **Weather** is a fixed Egypt demo reference: `24°C, partly cloudy, wind 9 km/h`; it is not live.
- **Treatments, greenhouse management, prevention, and irrigation schemes** stay in the
  case-grounded assistant and detailed PDF report, not the dashboard.

The previous prototype's yield "model" was fit on random numbers and has been removed.

To let a fresh setup download approved weights, set
`AGROVISION_DISEASE_MODEL_URL` to a trusted URL serving the exact checksum recorded in
`ml/models/manifest.json`.

## Bilingual assistant (Arabic + English)

The dashboard ships a bilingual farming assistant. Use the language toggle in the header:
the whole UI and the chat answer in **English by default and in Arabic when switched**
(the assistant also auto-detects Arabic text in a question). Answers are grounded in the
field analysis and a reviewed disease reference, explain the detected disease, and always
defer final treatment decisions to an agronomist.

When an online provider is configured, replies are generated live; otherwise the
assistant falls back to reviewed bilingual offline templates built from the same disease
reference. Configure these ignored `.env` values:

```text
EXTERNAL_LLM_API_KEY=your-key
EXTERNAL_LLM_API_URL=https://opencode.ai/zen/v1/chat/completions
EXTERNAL_LLM_MODEL=deepseek-v4-flash-free
EXTERNAL_LLM_MAX_TOKENS=1200
EXTERNAL_LLM_REASONING_EFFORT=low
```

Reasoning-capable providers can spend part of the token budget before producing the
visible answer, so `EXTERNAL_LLM_MAX_TOKENS` remains generous. Only the user's question
and bounded analysis results are sent, and the assistant falls back offline on provider
errors. Do not submit confidential or personal data to an external provider.

## Disease explanations

Each analysis uses the selected tomato or banana model. The diagnosis card opens a clear
bilingual dialog with the summary, symptoms, and immediate non-chemical management.
Treatment products are intentionally shown only in the assistant and detailed PDF.
