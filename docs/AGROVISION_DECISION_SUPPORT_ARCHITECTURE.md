# AgroVision Decision-Support Architecture

Status: implementation blueprint  
Target: Egyptian small farms, greenhouses, rooftop farms, and home gardens  
Deployment: Windows-first local modular monolith, with optional Supabase and external-data adapters  
Current repository fit: extends the existing React/Vite, FastAPI, ONNX Runtime, and Supabase application

## 1. Product Architecture

### 1.1 Safety and Product Principles

1. The system is a decision-support tool, not a laboratory diagnosis.
2. Image models produce visual hypotheses only. Farmer answers and reviewed agronomy rules refine the ranking.
3. The LLM never invents facts, pesticide products, active ingredients, doses, prices, weather, or confidence.
4. The LLM may:
   - choose useful follow-up questions from an approved question bank;
   - explain structured results in farmer-friendly English or Egyptian Arabic;
   - summarize reviewed evidence and deterministic calculations.
5. The LLM may not:
   - independently diagnose from an image;
   - create chemical recommendations not already present in reviewed knowledge;
   - calculate economics or yield predictions;
   - turn missing data into estimated facts.
6. Non-chemical protection steps always appear before treatment categories.
7. Every external fact stores source name, source URL or identifier, retrieval date, and effective date.
8. Low-confidence cases stop at information gathering or expert escalation.
9. Advice is versioned. A report must be reproducible using its model, rule-set, knowledge, and price-snapshot versions.
10. Farmer data and historical comparisons are stored only after explicit permission.

### 1.2 Recommended Deployment Shape

Use a modular monolith for the local laptop demo. Do not split into microservices until independent scaling or team ownership requires it.

```text
React/Vite Web
    |
    v
FastAPI Application
    |
    +-- Case State Machine
    +-- Image Validation and Model Router
    +-- Diagnosis Ranking Engine
    +-- Follow-up Question Engine
    +-- Protection Rule Engine
    +-- Treatment Safety Engine
    +-- Cost-Benefit Calculator
    +-- Damage/Yield Prediction Adapter
    +-- Recommendation Composer
    +-- Report Generator
    +-- External Data Adapters
    +-- LLM Wording Adapter (optional)
    |
    +-- In-memory fallback
    +-- Local Supabase: Auth, Postgres, Storage, RLS
    +-- ONNX Runtime: CPU default, optional DirectML/CUDA
```

### 1.3 Case State Machine

Every case moves through explicit states. A phase can return to `collecting_evidence` if required facts are missing.

```text
draft
  -> collecting_evidence
  -> diagnosis_ready
  -> consulting
  -> protection_ready
  -> treatment_ready
  -> economics_ready
  -> prediction_ready
  -> recommendation_ready
  -> report_ready
  -> closed

Any state -> needs_expert
Any processing state -> failed
```

### 1.4 Phase Ownership

| Phase | Primary engine | LLM role | Blocking conditions |
|---|---|---|---|
| Diagnosis | ONNX adapters + deterministic evidence ranker | Explain ranked output only | Bad image, unknown crop, no useful symptoms |
| Consulting | Question-priority rules | Reword approved questions | More than 5 questions, repeated question |
| Protection | Reviewed crop/disease rules | Farmer-friendly summary | No reviewed guidance |
| Treatment | Reviewed treatment-category rules + safety validator | Explain approved plan | Missing crop registration, PHI, or category evidence |
| Cost-benefit | Decimal-based deterministic calculator | Explain calculation | Missing area, price, expected yield, severity, or cost |
| Prediction | Versioned regression adapter | Explain feature importance | Out-of-distribution or insufficient features |
| Recommendation | Deterministic policy engine | Simplify wording | Conflicting safety gates |
| Report | Structured case snapshot | Translate/summarize approved data | Missing audit versions |

### 1.5 Diagnosis Ranking

The system must not display raw softmax as agronomic certainty. Store and display separate values:

- `image_model_score`: calibrated image-model probability when calibration exists.
- `context_support_score`: support from crop, affected part, symptom location, spread speed, weather, and irrigation.
- `evidence_completeness`: fraction of required evidence supplied.
- `final_confidence`: a bounded, versioned ranker output.

Recommended first implementation:

```text
final_confidence =
  calibrated_image_probability
  x context_compatibility_factor
  x image_quality_factor
  x evidence_completeness_factor
```

Rules:

- Do not calculate `final_confidence` until the image model has calibration metadata.
- Until then, label the number `model match`, not `confidence`.
- Show at most three plausible diseases.
- Return `not_enough_evidence=true` when:
  - top score is below the crop-specific threshold;
  - top two candidates are too close;
  - image quality is below threshold;
  - crop or affected plant part is unconfirmed;
  - the case is outside the model's supported domain.

### 1.6 Useful-Question Selection

The follow-up engine chooses questions using information gain and safety priority.

Question score:

```text
priority =
  diagnostic_discrimination
  + safety_impact
  + treatment_impact
  + economic_impact
  - answer_already_known
  - recently_asked_penalty
```

Hard rules:

- Ask 3 questions by default, never more than 5 at once.
- Ask one concept per question.
- Prefer observable farmer language over scientific terminology.
- Ask for a specific extra photo when it can distinguish the top candidates.
- Stop asking when answers will not change the recommendation; escalate instead.

### 1.7 External Data Adapters

Each adapter implements the same interface:

```python
class ExternalFactProvider(Protocol):
    provider_name: str

    def fetch(self, case: CaseContext) -> list[ExternalFact]: ...
```

Required output:

```json
{
  "fact_type": "weather",
  "value": {},
  "source_name": "provider name",
  "source_url": "https://...",
  "retrieved_at": "2026-06-15T12:00:00Z",
  "effective_at": "2026-06-15T11:45:00Z",
  "confidence": "official|reviewed|unverified"
}
```

Unverified facts cannot affect treatment or safety decisions.

## 2. Database Schema

The current tables remain useful:

- `profiles`
- `farms`
- `missions`
- `uploaded_assets`
- `analysis_runs`
- `feature_results`
- `recommendations`
- `alerts`
- `reports`
- `model_versions`
- `knowledge_articles`

Add the following normalized tables in a reviewed migration.

### 2.1 Core Case Tables

```sql
create type public.case_status as enum (
  'draft', 'collecting_evidence', 'diagnosis_ready', 'consulting',
  'protection_ready', 'treatment_ready', 'economics_ready',
  'prediction_ready', 'recommendation_ready', 'report_ready',
  'needs_expert', 'closed', 'failed'
);

create type public.evidence_source as enum (
  'farmer_answer', 'image_model', 'image_measurement', 'external_source',
  'reviewed_rule', 'expert', 'lab'
);

create table public.crop_cases (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  farm_id uuid references public.farms(id) on delete set null,
  status public.case_status not null default 'draft',
  crop_type text not null,
  governorate text,
  village text,
  farm_type text check (farm_type in ('open_field', 'greenhouse', 'rooftop', 'home_garden', 'unknown')),
  crop_age_days integer check (crop_age_days is null or crop_age_days >= 0),
  growth_stage text,
  expected_harvest_date date,
  language text not null default 'ar',
  consent_store_history boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.case_observations (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  observation_type text not null,
  value jsonb not null,
  source public.evidence_source not null,
  supplied_at timestamptz not null default now(),
  unique (case_id, observation_type, source, supplied_at)
);

create table public.case_assets (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  asset_id uuid not null references public.uploaded_assets(id) on delete cascade,
  view_type text not null check (view_type in (
    'close_up_leaf', 'whole_plant', 'leaf_underside', 'fruit',
    'stem', 'root', 'healthy_comparison', 'other'
  )),
  image_quality_score numeric check (image_quality_score between 0 and 1),
  created_at timestamptz not null default now()
);
```

### 2.2 Diagnosis and Consulting Tables

```sql
create table public.diagnosis_candidates (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  rank smallint not null check (rank between 1 and 3),
  disease_key text not null,
  image_model_score numeric check (image_model_score between 0 and 1),
  context_support_score numeric check (context_support_score between 0 and 1),
  evidence_completeness numeric check (evidence_completeness between 0 and 1),
  final_confidence numeric check (final_confidence between 0 and 1),
  evidence jsonb not null default '[]'::jsonb,
  missing_info jsonb not null default '[]'::jsonb,
  look_alikes jsonb not null default '[]'::jsonb,
  model_version_id uuid references public.model_versions(id),
  rule_version text not null,
  created_at timestamptz not null default now(),
  unique (case_id, rank)
);

create table public.followup_questions (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  question_key text not null,
  question_en text not null,
  question_ar text not null,
  answer jsonb,
  priority numeric not null,
  purpose text not null,
  asked_at timestamptz,
  answered_at timestamptz,
  unique (case_id, question_key)
);
```

### 2.3 Decision Tables

```sql
create table public.protection_plans (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  risk_level text not null check (risk_level in ('low', 'medium', 'high')),
  immediate_steps jsonb not null,
  hygiene_steps jsonb not null,
  irrigation_advice jsonb not null,
  airflow_advice jsonb not null,
  rotation_advice jsonb not null,
  monitoring_schedule jsonb not null,
  knowledge_version text not null,
  created_at timestamptz not null default now()
);

create table public.treatment_plans (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  disease_class text not null check (disease_class in (
    'fungal', 'bacterial', 'viral', 'insect', 'nutrient', 'abiotic', 'unknown'
  )),
  non_chemical jsonb not null,
  chemical_categories jsonb not null default '[]'::jsonb,
  biological_categories jsonb not null default '[]'::jsonb,
  spray_timing jsonb not null default '[]'::jsonb,
  recheck_interval_days integer,
  safety_notes jsonb not null,
  prohibited_actions jsonb not null,
  requires_agronomist boolean not null default true,
  knowledge_version text not null,
  created_at timestamptz not null default now()
);

create table public.cost_benefit_inputs (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  area_feddan numeric check (area_feddan > 0),
  expected_yield_kg_per_feddan numeric check (expected_yield_kg_per_feddan >= 0),
  market_price_egp_per_kg numeric check (market_price_egp_per_kg >= 0),
  affected_plants_percent numeric check (affected_plants_percent between 0 and 100),
  expected_loss_percent_untreated numeric check (expected_loss_percent_untreated between 0 and 100),
  expected_loss_percent_treated numeric check (expected_loss_percent_treated between 0 and 100),
  product_cost_egp numeric check (product_cost_egp >= 0),
  labor_cost_egp numeric check (labor_cost_egp >= 0),
  machine_cost_egp numeric check (machine_cost_egp >= 0),
  water_fuel_cost_egp numeric check (water_fuel_cost_egp >= 0),
  applications_count integer not null default 1 check (applications_count >= 1),
  price_source_id uuid,
  created_at timestamptz not null default now(),
  unique (case_id)
);

create table public.cost_benefit_results (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  revenue_without_disease_egp numeric not null,
  revenue_untreated_egp numeric not null,
  revenue_after_treatment_egp numeric not null,
  total_treatment_cost_egp numeric not null,
  expected_saved_revenue_egp numeric not null,
  net_benefit_egp numeric not null,
  roi numeric,
  break_even_yield_saved_kg numeric,
  decision text not null,
  formula_version text not null,
  created_at timestamptz not null default now(),
  unique (case_id)
);
```

`cost_benefit_inputs.price_source_id` requires `external_facts`, defined below.

### 2.4 Prediction, Knowledge, and Audit Tables

```sql
create table public.prediction_feature_rows (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  features jsonb not null,
  targets jsonb,
  dataset_schema_version text not null,
  consented_for_training boolean not null default false,
  created_at timestamptz not null default now(),
  unique (case_id, dataset_schema_version)
);

create table public.prediction_results (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  damage_degree text,
  yield_loss_percent numeric,
  yield_kg_per_feddan numeric,
  revenue_loss_egp numeric,
  confidence_interval jsonb,
  main_risk_factors jsonb not null default '[]'::jsonb,
  insufficient_data boolean not null default false,
  model_version_id uuid references public.model_versions(id),
  created_at timestamptz not null default now()
);

create table public.external_facts (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid references auth.users(id) on delete cascade,
  case_id uuid references public.crop_cases(id) on delete cascade,
  fact_type text not null,
  value jsonb not null,
  source_name text not null,
  source_url text,
  source_confidence text not null check (source_confidence in ('official', 'reviewed', 'unverified')),
  retrieved_at timestamptz not null,
  effective_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.cost_benefit_inputs
add constraint cost_benefit_inputs_price_source_fk
foreign key (price_source_id) references public.external_facts(id) on delete set null;

create table public.knowledge_rules (
  id uuid primary key default uuid_generate_v4(),
  rule_key text not null,
  version text not null,
  crop_type text not null,
  disease_key text,
  rule_type text not null,
  conditions jsonb not null,
  output jsonb not null,
  sources jsonb not null,
  reviewed_by text not null,
  reviewed_at timestamptz not null,
  active boolean not null default false,
  unique (rule_key, version)
);

create table public.case_snapshots (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  phase text not null,
  payload jsonb not null,
  model_versions jsonb not null,
  rule_versions jsonb not null,
  created_at timestamptz not null default now()
);
```

Apply RLS using the same `owner_id = auth.uid()` policy pattern already used by the repository. Public read access is allowed only for active, reviewed knowledge without farmer data.

### 2.5 Regression-Ready Dataset Schema

One row represents one crop case at final observation or harvest reconciliation.

```json
{
  "case_id": "uuid",
  "crop_type": "tomato",
  "disease_type": "tomato_early_blight",
  "disease_confidence": 0.74,
  "severity_score_0_to_4": 2,
  "affected_plants_percent": 28,
  "affected_leaf_area_percent": 18,
  "days_since_first_symptom": 6,
  "crop_age_days": 68,
  "growth_stage": "fruit_set",
  "irrigation_method": "flood",
  "humidity_level": "high",
  "temperature_level": "warm",
  "recent_rain": false,
  "plant_spacing": "dense",
  "nitrogen_status": "unknown",
  "potassium_status": "unknown",
  "soil_drainage": "poor",
  "previous_crop": "tomato",
  "treatment_started_after_days": 7,
  "treatment_type": "protective_fungicide_category",
  "number_of_sprays": 2,
  "farmer_compliance_score": 0.8,
  "image_quality_score": 0.86,
  "governorate": "Beheira",
  "season_month": 6,
  "yield_kg_per_feddan": null,
  "yield_loss_percent": null,
  "revenue_loss_egp": null,
  "final_damage_score": null
}
```

Training rows require consent and reviewed target values. Never train on the AI's own prediction as ground truth.

## 3. API Endpoints

All write endpoints require authentication in production. The local demo may use the seeded demo account.

### 3.1 Case Lifecycle

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/cases` | Create a case with crop, location, farm type, age, and consent |
| `GET` | `/api/v1/cases/{case_id}` | Return current structured case state |
| `PATCH` | `/api/v1/cases/{case_id}` | Update farmer-supplied case fields |
| `POST` | `/api/v1/cases/{case_id}/observations` | Add symptoms, irrigation, weather, spraying, or nearby-crop observations |
| `POST` | `/api/v1/cases/{case_id}/assets` | Upload a typed case image |
| `POST` | `/api/v1/cases/{case_id}/diagnose` | Run image models and diagnosis ranker |
| `GET` | `/api/v1/cases/{case_id}/diagnosis` | Return top candidates and evidence |

### 3.2 Consulting and Decision Phases

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/cases/{case_id}/questions?limit=3` | Get the next useful questions |
| `POST` | `/api/v1/cases/{case_id}/answers` | Save answers and rerank the case |
| `POST` | `/api/v1/cases/{case_id}/protection-plan` | Generate reviewed protection steps |
| `POST` | `/api/v1/cases/{case_id}/treatment-plan` | Generate safe category-level treatment plan |
| `POST` | `/api/v1/cases/{case_id}/cost-benefit` | Calculate economics from supplied inputs |
| `POST` | `/api/v1/cases/{case_id}/prediction` | Run versioned prediction adapter |
| `POST` | `/api/v1/cases/{case_id}/recommendation` | Apply deterministic recommendation policy |
| `POST` | `/api/v1/cases/{case_id}/conclusion` | Build final structured conclusion |

### 3.3 Chat, Reports, and External Facts

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/cases/{case_id}/chat` | Explain existing structured case facts |
| `POST` | `/api/v1/cases/{case_id}/external-facts/refresh` | Fetch configured weather/price/alert facts |
| `GET` | `/api/v1/cases/{case_id}/report.json` | Required system-output JSON |
| `GET` | `/api/v1/cases/{case_id}/report.pdf` | Farmer-friendly PDF |
| `GET` | `/api/v1/cases/{case_id}/audit` | Sources, dates, model/rule versions, and safety gates |

### 3.4 Endpoint Example: Create Case

```http
POST /api/v1/cases
Content-Type: application/json
```

```json
{
  "crop_type": "tomato",
  "governorate": "Beheira",
  "village": null,
  "farm_type": "open_field",
  "crop_age_days": 68,
  "growth_stage": "fruit_set",
  "expected_harvest_date": "2026-07-20",
  "language": "ar",
  "consent_store_history": true
}
```

### 3.5 Endpoint Example: Diagnosis Response

```json
{
  "case_id": "uuid",
  "status": "consulting",
  "not_enough_evidence": false,
  "candidates": [
    {
      "rank": 1,
      "disease_key": "tomato_early_blight",
      "display_name": "Early blight",
      "confidence": 0.74,
      "confidence_label": "moderate",
      "evidence": ["Concentric-ring spots", "Symptoms started on lower leaves"],
      "missing_info": ["Recent overhead watering"],
      "look_alikes": ["Septoria leaf spot", "Bacterial spot"]
    }
  ],
  "next_questions": []
}
```

## 4. Prompt Templates

Prompts receive only validated structured context. They never receive unrestricted database access or permission to create facts.

### 4.1 Shared System Prompt

```text
You are AgroVision Egypt's wording assistant.

You do not diagnose, calculate, or invent facts.
Use only the STRUCTURED_CONTEXT supplied by the application.
If a field is null or missing, say it is not available.
Keep AI prediction separate from confirmed lab diagnosis.
Use simple farmer-friendly language.
When language=ar, use clear Egyptian farming Arabic without excessive scientific terms.
Use feddan, qirat, kilogram, ton, and EGP when those units exist in context.
Never invent pesticide brands, active ingredients, doses, prices, confidence, weather, or sources.
Never turn an unverified external fact into advice.
Always preserve safety warnings and pre-harvest interval warnings supplied in context.
Output valid JSON matching OUTPUT_SCHEMA. Do not add fields.
```

### 4.2 Diagnosis Explanation Prompt

```text
TASK: Explain the ranked diagnosis without increasing certainty.

STRUCTURED_CONTEXT:
{diagnosis_candidates_json}
{image_quality_json}
{farmer_observations_json}

RULES:
- Present at most three candidates in supplied order.
- State visual evidence and missing information.
- State look-alikes.
- If not_enough_evidence=true, clearly ask for the supplied extra photos/questions.
- Do not call a candidate confirmed.

OUTPUT_SCHEMA:
{
  "summary": "string",
  "top_candidates": [
    {
      "name": "string",
      "confidence_label": "low|moderate|high",
      "evidence": ["string"],
      "missing_info": ["string"],
      "look_alikes": ["string"]
    }
  ],
  "warning": "string|null"
}
```

### 4.3 Consulting Question Prompt

The deterministic question engine chooses `question_key` values first. The LLM only rewrites them.

```text
TASK: Rewrite the approved questions in simple farmer language.

APPROVED_QUESTIONS:
{approved_questions_json}

RULES:
- Return 3 to 5 questions only.
- Do not add a new question or remove its purpose.
- Ask one thing per question.
- Avoid scientific names unless included in the approved question.
- Preserve requested photo type exactly.

OUTPUT_SCHEMA:
{
  "questions": [
    {
      "question_key": "string",
      "question": "string",
      "why_it_matters": "string"
    }
  ]
}
```

### 4.4 Protection Prompt

```text
TASK: Explain the reviewed prevention plan.

STRUCTURED_CONTEXT:
{protection_plan_json}
{farm_context_json}

RULES:
- Put immediate low-cost actions first.
- Include flood-irrigation splash and humidity risks when supplied.
- Include hygiene, irrigation, spacing, rotation, and monitoring.
- Include do-not-over-spray warning.
- Do not add chemical treatment.

OUTPUT_SCHEMA:
{
  "risk_level": "low|medium|high",
  "today": ["string"],
  "field_hygiene": ["string"],
  "irrigation": ["string"],
  "airflow_spacing": ["string"],
  "rotation": ["string"],
  "monitoring": ["string"],
  "warning": "string"
}
```

### 4.5 Treatment Prompt

```text
TASK: Explain the reviewed treatment-category plan.

STRUCTURED_CONTEXT:
{treatment_plan_json}
{diagnosis_json}
{harvest_context_json}

RULES:
- Non-chemical steps first.
- Use only supplied active-ingredient categories. Do not create brand names.
- If disease_class=viral, clearly say sprays do not cure the virus.
- If disease_class=nutrient, require soil/water testing before heavy fertilization.
- Preserve local registration, label, dose, PPE, PHI, and agronomist warnings.
- If diagnosis confidence is low, recommend expert confirmation before chemicals.

OUTPUT_SCHEMA:
{
  "non_chemical_first": ["string"],
  "chemical_or_biological_categories": ["string"],
  "spray_timing": ["string"],
  "recheck": "string",
  "safety_notes": ["string"],
  "what_not_to_do": ["string"],
  "when_to_call_agronomist": "string"
}
```

### 4.6 Cost-Benefit Prompt

The calculator produces every number. The prompt explains only.

```text
TASK: Explain the deterministic cost-benefit calculation.

STRUCTURED_CONTEXT:
{cost_benefit_result_json}
{input_completeness_json}

RULES:
- Never recalculate or change a number.
- If decision=need_more_data, list the missing supplied fields.
- Explain the decision in practical terms.
- Use EGP and feddan exactly as supplied.

OUTPUT_SCHEMA:
{
  "decision": "string",
  "reason": "string",
  "important_numbers": ["string"],
  "missing_data": ["string"]
}
```

### 4.7 Prediction Prompt

```text
TASK: Explain the versioned prediction result.

STRUCTURED_CONTEXT:
{prediction_result_json}

RULES:
- Do not call a prediction certain.
- List supplied main risk factors only.
- Include the confidence interval if supplied.
- If insufficient_data=true, state which required features are missing.

OUTPUT_SCHEMA:
{
  "damage_degree": "low|medium|high|severe|unknown",
  "yield_loss_explanation": "string",
  "main_risk_factors": ["string"],
  "uncertainty": "string"
}
```

### 4.8 Final Report Prompt

```text
TASK: Convert the approved structured case result into a concise farmer report.

STRUCTURED_CONTEXT:
{complete_case_json}

RULES:
- Preserve all values and warnings.
- Separate AI prediction from confirmed diagnosis.
- If confidence is low, make collecting evidence the best action.
- Include what to do today and in 3 to 7 days.
- Include when to call an expert.
- Never introduce a new treatment, cost, or forecast.

OUTPUT_SCHEMA:
{
  "diagnosis_summary": "string",
  "risk_level": "string",
  "best_action_now": "string",
  "today": ["string"],
  "next_3_to_7_days": ["string"],
  "monitor": ["string"],
  "when_to_call_expert": "string",
  "expected_outcome": "string",
  "safety_warning": "string",
  "next_check_date": "YYYY-MM-DD|null"
}
```

## 5. Example Response: Tomato Early Blight

This example intentionally uses category-level treatment wording and marks unavailable economics/predictions as null.
The same response is stored as a standalone artifact at `docs/examples/early-blight-tomato.json`.

```json
{
  "case_id": "case-demo-early-blight-001",
  "crop": "tomato",
  "location": "Beheira, Egypt",
  "diagnosis": {
    "top_disease": "Early blight",
    "confidence": 0.74,
    "alternatives": [
      {
        "disease": "Septoria leaf spot",
        "confidence": 0.17
      },
      {
        "disease": "Bacterial spot",
        "confidence": 0.09
      }
    ],
    "evidence": [
      "Brown spots with visible concentric rings",
      "Symptoms started on older lower leaves",
      "Lower leaves show yellowing around the spots",
      "Farmer reports gradual spread"
    ],
    "missing_info": [
      "Whether the spots have a clear yellow halo",
      "Whether overhead watering was used recently",
      "Percent of plants affected across the field"
    ]
  },
  "chatbot_followup_questions": [
    "Do the brown spots look like circles inside circles?",
    "Did the problem start on the lower old leaves?",
    "How many plants out of every 100 show the same spots?",
    "Do you use flood, drip, or sprinkler irrigation?",
    "Please add one photo of the whole plant and one close photo of the underside of a spotted leaf."
  ],
  "protection_plan": [
    "Remove heavily affected lower leaves and take them out of the field.",
    "Avoid splashing soil onto leaves; flood irrigation can increase splash and humidity risk.",
    "Water early and keep foliage dry overnight.",
    "Improve airflow where plants are crowded.",
    "Inspect the field again in 3 days and record whether new upper leaves are affected.",
    "Do not over-spray."
  ],
  "treatment_plan": {
    "non_chemical": [
      "Remove infected lower leaves.",
      "Remove infected crop debris.",
      "Avoid overhead watering and reduce leaf wetness.",
      "Rotate away from tomato, potato, pepper, and eggplant in the next cycle where practical."
    ],
    "chemical_category_if_needed": [
      "If an agricultural engineer confirms fungal early blight and the local crop label allows it, use a locally registered protectant fungicide category or a registered systemic fungicide category in rotation.",
      "Do not repeat the same resistance-action group continuously."
    ],
    "safety_notes": [
      "Verify local registration, current product label, crop dose, PPE, and pre-harvest interval.",
      "Do not use a chemical treatment based only on the AI result.",
      "Ask a local agricultural engineer before spraying."
    ]
  },
  "cost_benefit": {
    "treatment_cost_egp": null,
    "estimated_saved_revenue_egp": null,
    "net_benefit_egp": null,
    "decision": "Need more data: farm area, expected yield, market price, percent affected, treatment cost, and harvest time remaining."
  },
  "prediction": {
    "damage_degree": "medium",
    "yield_loss_percent": null,
    "yield_kg_per_feddan": null,
    "main_risk_factors": [
      "Symptoms have reached multiple lower leaves",
      "Dense canopy",
      "Possible soil splash and prolonged humidity"
    ]
  },
  "recommendation": {
    "best_action_now": "Remove heavily affected lower leaves, improve leaf dryness, collect the missing photos and affected-plant percentage, then confirm the diagnosis before chemical treatment.",
    "next_3_to_7_days": "Recheck marked plants, record whether spots reach upper leaves, and ask an agricultural engineer if spread continues or fruit symptoms appear.",
    "when_to_call_expert": "Call an agricultural engineer now if spread is fast, more than about one third of plants are affected, fruit is affected, or harvest is close."
  },
  "conclusion": "The current evidence moderately supports early blight, but this is an AI prediction rather than a confirmed laboratory diagnosis. Immediate hygiene and moisture-control steps are low cost and appropriate while missing evidence is collected.",
  "disclaimer": "AI prediction only. Confirm with an agricultural engineer or lab when crop value or risk is high."
}
```

## 6. Clean Code Structure

Evolve the current repository toward this structure:

```text
apps/
  web/
    src/
      features/
        cases/
        diagnosis/
        consulting/
        protection/
        treatment/
        economics/
        prediction/
        reports/
      components/
      api/
      i18n/

services/
  api/
    app/
      main.py
      config.py
      api/
        cases.py
        assets.py
        diagnosis.py
        consulting.py
        protection.py
        treatment.py
        economics.py
        prediction.py
        recommendations.py
        reports.py
      domain/
        case.py
        diagnosis.py
        evidence.py
        protection.py
        treatment.py
        economics.py
        prediction.py
        recommendation.py
        safety.py
      application/
        case_service.py
        diagnosis_service.py
        question_service.py
        protection_service.py
        treatment_service.py
        cost_benefit_service.py
        prediction_service.py
        recommendation_service.py
        report_service.py
      adapters/
        persistence/
          memory.py
          supabase.py
        models/
          base.py
          tomato_onnx.py
          banana_onnx.py
          regression.py
        external/
          weather.py
          market_prices.py
          disease_alerts.py
          approved_guidance.py
        llm/
          base.py
          external_chat.py
          offline_templates.py
      knowledge/
        schemas.py
        repository.py
        rule_engine.py
      contracts/
        requests.py
        responses.py
        system_output.py
      reports/
        pdf.py
        csv.py
      tests/
        unit/
        integration/
        safety/
        model_smoke/

ml/
  models/
  training/
  evaluation/
  regression/
    schema.json
    train_baseline.py
    train_gradient_boosting.py
    evaluate.py
    explain.py

supabase/
  migrations/
  tests/

docs/
  AGROVISION_DECISION_SUPPORT_ARCHITECTURE.md
```

### 6.1 Domain Interface Examples

```python
class DiagnosisModelAdapter(Protocol):
    supported_crops: set[str]
    version: str

    def predict(self, images: list[TypedImage]) -> list[VisualCandidate]: ...


class DiagnosisRanker(Protocol):
    version: str

    def rank(
        self,
        visual_candidates: list[VisualCandidate],
        observations: CaseObservations,
    ) -> DiagnosisResult: ...


class SafetyValidator(Protocol):
    def validate_treatment(
        self,
        diagnosis: DiagnosisResult,
        plan: TreatmentPlan,
        context: CaseContext,
    ) -> list[SafetyViolation]: ...
```

### 6.2 Cost-Benefit Formulas

Use `Decimal`, never binary float, for currency.

```text
expected_revenue_without_disease =
  area_feddan x expected_yield_kg_per_feddan x market_price_egp_per_kg

expected_revenue_if_untreated =
  expected_revenue_without_disease x (1 - untreated_loss_percent / 100)

expected_revenue_after_treatment =
  expected_revenue_without_disease x (1 - treated_loss_percent / 100)

total_treatment_cost =
  (product_cost_per_application
   + labor_cost_per_application
   + machine_cost_per_application
   + water_fuel_cost_per_application)
  x applications_count

expected_revenue_saved =
  expected_revenue_after_treatment - expected_revenue_if_untreated

net_benefit =
  expected_revenue_saved - total_treatment_cost

roi =
  net_benefit / total_treatment_cost

break_even_yield_saved_kg =
  total_treatment_cost / market_price_egp_per_kg
```

Return `need_more_data` when any required input is null. Do not silently substitute averages.

### 6.3 Prediction Rollout

1. Start with no production yield-loss prediction. Collect consented, reviewed outcomes.
2. Add linear regression as a transparent baseline.
3. Add Random Forest and Gradient Boosting only after cross-governorate validation.
4. Use grouped validation by farm and season to prevent data leakage.
5. Compare against a simple crop/disease mean baseline.
6. Store model version, feature schema, training window, metrics, and limitations.
7. Add feature importance, prediction interval, and out-of-distribution checks.
8. Reject a new model when it worsens important crop/governorate subgroups.

## 7. Validation Rules Preventing Unsafe or Fake Advice

### 7.1 Input Validation

- Reject unsupported file types, corrupted images, oversized files, and images below the minimum useful resolution.
- Require crop confirmation before crop-specific model inference.
- Require a typed image view.
- Validate percentages within `0..100`, scores within `0..1`, and non-negative costs/yields.
- Validate governorate against an approved Egypt governorate list; village remains free text.
- Validate expected harvest date is not before the case date.
- Reject impossible combinations such as negative crop age or zero farm area for economics.

### 7.2 Diagnosis Safety Gates

- Never claim confirmed disease unless an expert or lab observation explicitly supplies confirmation.
- Always show top alternatives when confidence is not high.
- Mark raw uncalibrated softmax as `model_match`.
- Trigger `not_enough_evidence` for low quality, unsupported crop/part, close candidates, or missing critical context.
- Ask for additional photos before treatment when visual evidence is insufficient.
- Keep a visible distinction between image evidence, farmer answers, external facts, reviewed rules, expert findings, and lab findings.

### 7.3 Treatment Safety Gates

- Knowledge must be active, reviewed, versioned, sourced, and crop/disease compatible.
- Do not store or output invented brand names.
- Output active-ingredient category only when locally approved label data is available.
- A chemical category cannot be output without:
  - disease-class compatibility;
  - crop compatibility;
  - source and review date;
  - label/registration verification warning;
  - dose-from-label warning;
  - PPE warning;
  - PHI warning when harvestable crop is involved;
  - resistance-rotation warning where applicable.
- Viral disease: no curative spray claim.
- Bacterial disease: no fungicide-cure claim.
- Nutrient deficiency: no heavy-fertilizer recommendation before soil/water testing.
- Low diagnosis confidence blocks chemical recommendations.
- Close harvest date blocks advice that lacks verified PHI compatibility.
- Always put non-chemical actions first.
- Always include `do not over-spray`.

### 7.4 Economics Validation

- Every price has a source and retrieval date.
- Expired or missing price data returns `not_available`.
- Never assume expected yield, market price, disease loss, treatment efficacy, or treatment cost.
- Show every input and formula in the audit response.
- Use `Decimal` and explicit units.
- Prevent divide-by-zero ROI.
- Return `need_more_data` instead of an economic decision when inputs are incomplete.

### 7.5 Prediction Validation

- Never train using AI predictions as target labels.
- Require farmer consent before training use.
- Split validation by farm and season.
- Report MAE/RMSE for regression and class metrics for severity.
- Report subgroup metrics by crop and governorate.
- Detect out-of-distribution cases.
- Return `insufficient_data=true` when required features are missing.
- Do not output a narrow confidence interval without validated uncertainty estimation.

### 7.6 External Data Validation

- Store source name, URL/identifier, retrieval time, and effective time.
- Mark source confidence as official, reviewed, or unverified.
- Unverified external facts cannot drive treatment.
- If data is unavailable, output `not available`; never use a guessed fallback.
- Weather must identify whether it is live, historical, forecast, or sample/reference data.

### 7.7 LLM Output Validation

Every LLM response passes through:

1. Strict JSON-schema validation.
2. Unknown-field rejection.
3. Number provenance check: every number must exist in structured context.
4. Chemical-term allowlist and brand-name denylist.
5. Source provenance check.
6. Required disclaimer and safety-warning check.
7. Language and maximum-length check.
8. Fallback to deterministic templates on any failure.

### 7.8 Required System Output Contract

Every report endpoint returns this stable shape:

The executable validation schema is stored at `docs/system-output.schema.json`.

```json
{
  "case_id": "",
  "crop": "",
  "location": "",
  "diagnosis": {
    "top_disease": "",
    "confidence": 0,
    "alternatives": [],
    "evidence": [],
    "missing_info": []
  },
  "chatbot_followup_questions": [],
  "protection_plan": [],
  "treatment_plan": {
    "non_chemical": [],
    "chemical_category_if_needed": [],
    "safety_notes": []
  },
  "cost_benefit": {
    "treatment_cost_egp": null,
    "estimated_saved_revenue_egp": null,
    "net_benefit_egp": null,
    "decision": ""
  },
  "prediction": {
    "damage_degree": "",
    "yield_loss_percent": null,
    "yield_kg_per_feddan": null,
    "main_risk_factors": []
  },
  "recommendation": {
    "best_action_now": "",
    "next_3_to_7_days": "",
    "when_to_call_expert": ""
  },
  "conclusion": "",
  "disclaimer": "AI prediction only. Confirm with an agricultural engineer or lab when crop value or risk is high."
}
```

## 8. Recommended Implementation Order

1. Add the stable case JSON contract and case state machine.
2. Add normalized case, observation, diagnosis-candidate, and question tables with RLS.
3. Refactor current tomato/banana inference behind crop-model adapters.
4. Implement image-quality checks and top-three diagnosis output.
5. Implement deterministic useful-question selection.
6. Add reviewed protection and category-level treatment rules.
7. Add system-output JSON and expanded report generation.
8. Add deterministic cost-benefit calculations.
9. Add external fact adapters with provenance and unavailable states.
10. Collect consented outcome data before implementing production regression.
11. Add LLM wording only after strict JSON and provenance validators exist.
12. Expand crop support one crop at a time, only with model and knowledge validation.

## 9. Acceptance Criteria

- Every case produces the required stable JSON contract.
- Diagnosis presents up to three candidates and never claims laboratory confirmation.
- Low-confidence cases request more evidence and block chemical advice.
- Follow-up batches contain 3 to 5 useful, non-repeated questions.
- Treatment uses reviewed categories only, with required label, PHI, PPE, and expert warnings.
- Cost-benefit numbers are deterministic, auditable, and null when inputs are missing.
- Prediction is disabled or marked insufficient until validated training data exists.
- External facts include source and date or display `not available`.
- Farmer history is stored only with consent.
- All user-owned records have tested RLS.
- Unit, integration, safety, model-smoke, report, and browser tests pass.
