export type ValidationLevel = "validated" | "experimental" | "sample-data";

export interface LocalizedText {
  en: string;
  ar: string;
}

export interface Treatment {
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
  note_en: string;
  note_ar: string;
}

export interface DiseaseInfo {
  key: string;
  name_en: string;
  name_ar: string;
  crop_en?: string;
  crop_ar?: string;
  summary_en: string;
  summary_ar: string;
  symptoms_en: string[];
  symptoms_ar: string[];
  management_en: string[];
  management_ar: string[];
  treatments?: Treatment[];
}

export interface FeatureResult {
  feature: string;
  title: string;
  title_ar: string;
  level: ValidationLevel;
  score: number;
  value: string;
  value_ar: string;
  confidence: number;
  evidence: string[];
  limitation?: string;
  disease_info?: DiseaseInfo | null;
}

export type FusedState = "" | "confident" | "screening" | "not_sure" | "not_tomato";

export interface Analysis {
  analysis_id: string;
  filename: string;
  crop: "tomato";
  width: number;
  height: number;
  processing_ms: number;
  peak_memory_mb: number;
  provider: string;
  results: FeatureResult[];
  alerts: LocalizedText[];
  recommendations: LocalizedText[];
  assistant_questions: LocalizedText[];
  fused_state?: FusedState;
  diagnosis_candidates?: DiagnosisCandidate[];
  image_measurements?: Record<string, number>;
}

export type CaseStatus =
  | "draft"
  | "collecting_evidence"
  | "diagnosis_ready"
  | "consulting"
  | "protection_ready"
  | "treatment_ready"
  | "economics_ready"
  | "prediction_ready"
  | "recommendation_ready"
  | "report_ready"
  | "needs_expert"
  | "closed"
  | "failed";

export interface DiagnosisCandidate {
  disease: string;
  confidence: number;
}

export interface DiagnosisConfirmation {
  disease: string;
  confirmation_type: "egyptian_agronomist" | "egyptian_plant_pathology_lab";
  organization: string;
  report_reference: string;
  confirmer_name: string | null;
  notes: string | null;
  evidence_filename: string;
  evidence_sha256: string;
  jurisdiction: "Egypt";
  recorded_at: string;
  verification_notice: string;
}

export interface CaseDiagnosis {
  top_disease: string;
  confidence: number;
  alternatives: DiagnosisCandidate[];
  evidence: string[];
  missing_info: string[];
  confirmation_status:
    | "unconfirmed"
    | "confirmed_by_egyptian_agronomist"
    | "confirmed_by_egyptian_plant_pathology_lab";
  confirmation: DiagnosisConfirmation | null;
}

export interface EgyptSource {
  title: string;
  organization: string;
  url: string;
  purpose: string;
  source_kind: "diagnosis" | "pesticide_registration" | "food_safety";
  jurisdiction: "Egypt";
  status: "official";
  retrieved_on: string;
}

export interface CaseTreatmentPlan {
  non_chemical: string[];
  chemical_category_if_needed: string[];
  safety_notes: string[];
}

export interface CostBenefitResult {
  treatment_cost_egp: number | null;
  estimated_saved_revenue_egp: number | null;
  net_benefit_egp: number | null;
  roi: number | null;
  break_even_yield_saved_kg: number | null;
  decision: string;
  missing_inputs: string[];
}

export interface CaseRecommendation {
  best_action_now: string;
  next_3_to_7_days: string;
  when_to_call_expert: string;
}

export interface PredictionResult {
  damage_degree: "low" | "medium" | "high" | "severe" | "unknown" | "";
  yield_loss_percent: number | null;
  yield_kg_per_feddan: number | null;
  main_risk_factors: string[];
}

export interface CropCase {
  case_id: string;
  status: CaseStatus;
  crop: "tomato" | "banana" | "potato" | "cucumber" | "grape" | "mango" | "citrus" | "wheat";
  location: string;
  farm_type: "open_field" | "greenhouse" | "rooftop" | "home_garden" | null;
  growth_stage: string | null;
  symptoms: string[];
  observations: Record<string, string | number | boolean>;
  observation_sources?: Record<string, string>;
  egypt_sources: EgyptSource[];
  consulting_questions?: string[];
  diagnosis: CaseDiagnosis;
  disease_class: string;
  treatment_rule_version: string;
  protection_plan: string[];
  treatment_plan: CaseTreatmentPlan;
  cost_benefit: CostBenefitResult;
  prediction?: PredictionResult;
  recommendation: CaseRecommendation;
  updated_at: string;
}

export type CaseImageView =
  | "close_up_leaf"
  | "whole_plant"
  | "leaf_underside"
  | "fruit"
  | "stem"
  | "root"
  | "healthy_comparison"
  | "other";

export interface SeverityEstimate {
  severity_label: "unknown" | "low" | "moderate" | "high" | "severe";
  visible_affected_percent: number | null;
  estimated_yield_loss_low_percent: number | null;
  estimated_yield_loss_high_percent: number | null;
  recovery_probability_label: "unknown" | "low" | "fair" | "good";
  weather_risk_label: "unknown" | "low" | "medium" | "high";
  drivers: string[];
  basis: string;
}

export interface PriceReference {
  item: string;
  unit: string;
  low_egp: number;
  high_egp: number;
  source: string;
  as_of: string;
  note: string;
}

export interface CostEstimate {
  basis: "farmer_inputs" | "reference_estimate" | "need_more_data";
  area_feddan_assumed: number | null;
  treatment_cost_egp_low: number | null;
  treatment_cost_egp_high: number | null;
  potential_loss_egp_low: number | null;
  potential_loss_egp_high: number | null;
  net_benefit_egp_low: number | null;
  net_benefit_egp_high: number | null;
  decision_hint: string;
  prices_used: PriceReference[];
  assumptions: string[];
  note: string;
}

export interface ScenarioOutput {
  key: string;
  name_en: string;
  name_ar: string;
  confidence_en: string;
  confidence_ar: string;
  protection_en: string;
  protection_ar: string;
  treatment_en: string;
  treatment_ar: string;
  cost_en: string;
  cost_ar: string;
  recommendation_en: string;
  recommendation_ar: string;
}

export type DataSourceKind =
  | "visual_model"
  | "disease_information"
  | "variety_knowledge"
  | "weather"
  | "market_price"
  | "pesticide_registration"
  | "tomato_statistics"
  | "treatment_knowledge"
  | "fallback_assumption";

export type DataSourceOrigin = "live" | "official" | "admin_table" | "csv_fallback" | "estimated_range" | "generated";

export interface CompactValue {
  label_en: string;
  label_ar: string;
  value: string | number | null;
  unit: string;
  source_type: DataSourceOrigin;
  confidence: Certainty;
  assumption_en: string;
  assumption_ar: string;
  measured_zero: boolean;
}

export interface EngineStats {
  analysis_time_ms: number | null;
  engine: string;
  memory_used_mb: number | null;
  source_status: string;
}

export interface SummaryCards {
  numbers_only: true;
  detected_disease: CompactValue;
  visual_score: CompactValue;
  top_candidates: CompactValue[];
  infection_extent: CompactValue;
  weather_risk: CompactValue;
  engine_stats: EngineStats;
}

export interface DiseaseCandidateInsight {
  rank: number;
  disease_name_en: string;
  disease_name_ar: string;
  confidence: number;
  confidence_label: Certainty;
  support_en: string[];
  support_ar: string[];
  source_type: DataSourceOrigin;
  source_note_en: string;
  source_note_ar: string;
}

export interface ResistantVarietyOption {
  name_en: string;
  name_ar: string;
  resistance_codes_en: string;
  resistance_codes_ar: string;
  disease_coverage_en: string[];
  disease_coverage_ar: string[];
  resistance_strength_en: string;
  resistance_strength_ar: string;
  prevention_only_warning_en: string;
  prevention_only_warning_ar: string;
  egypt_availability_status: "verified_in_egypt" | "not_verified_in_egypt" | "unknown";
  source_kind: DataSourceKind;
  source_type: DataSourceOrigin;
  source_title: string;
  source_organization: string;
  source_url: string | null;
  source_note_en: string;
  source_note_ar: string;
  farmer_wording_en: string;
  farmer_wording_ar: string;
}

export interface TreatmentModeOption {
  key: string;
  label_en: string;
  label_ar: string;
  summary_en: string;
  summary_ar: string;
  cost_egp: SourcedRange;
  budget_egp: SourcedRange;
  expected_benefit_en: string;
  expected_benefit_ar: string;
  risk_en: string;
  risk_ar: string;
  apc_gate_en: string;
  apc_gate_ar: string;
  requires_apc_verification: boolean;
  requires_engineer_confirmation: boolean;
  source_kind: DataSourceKind;
  source_type: DataSourceOrigin;
  source_note_en: string;
  source_note_ar: string;
  farmer_wording_ar: string;
}

export interface ScenarioSection {
  title_en: string;
  title_ar: string;
  bullets_en: string[];
  bullets_ar: string[];
  source_type: DataSourceOrigin;
  confidence: Certainty;
  assumption_en: string;
  assumption_ar: string;
}

export interface ScenarioCase {
  key: string;
  name_en: string;
  name_ar: string;
  summary_en: string;
  summary_ar: string;
  sections: ScenarioSection[];
}

export interface ConsultingQuestionAnswer {
  key: string;
  question_en: string;
  question_ar: string;
  answer_en: string;
  answer_ar: string;
  why_it_matters_en: string;
  why_it_matters_ar: string;
  decision_change_en: string;
  decision_change_ar: string;
  scenario_notes_en: string[];
  scenario_notes_ar: string[];
  source_type: DataSourceOrigin;
  assumption_en: string;
  assumption_ar: string;
}

export interface DiseaseInformationPhase {
  disease_name_en: string;
  disease_name_ar: string;
  cause_type_en: string;
  cause_type_ar: string;
  meaning_en: string;
  meaning_ar: string;
  leaf_symptoms_en: string[];
  leaf_symptoms_ar: string[];
  fruit_symptoms_en: string[];
  fruit_symptoms_ar: string[];
  stem_symptoms_en: string[];
  stem_symptoms_ar: string[];
  spread_en: string;
  spread_ar: string;
  why_it_appears_en: string;
  why_it_appears_ar: string;
  irrigation_conditions_en: string;
  irrigation_conditions_ar: string;
  worse_weather_en: string;
  worse_weather_ar: string;
  lookalikes_en: string[];
  lookalikes_ar: string[];
  danger_en: string;
  danger_ar: string;
  top_candidates: DiseaseCandidateInsight[];
  resistant_varieties: ResistantVarietyOption[];
  today_check_en: string[];
  today_check_ar: string[];
  worsening_en: string[];
  worsening_ar: string[];
  stable_en: string[];
  stable_ar: string[];
  scenario_cases: ScenarioCase[];
  higher_accuracy_hint_en: string;
  higher_accuracy_hint_ar: string;
}

export interface ProtectionPhase {
  scenario_cases: ScenarioCase[];
  higher_accuracy_hint_en: string;
  higher_accuracy_hint_ar: string;
}

export interface ConsultingPhase {
  auto_questions_with_answers: ConsultingQuestionAnswer[];
  higher_accuracy_hint_en: string;
  higher_accuracy_hint_ar: string;
}

export interface TreatmentPhase {
  scenario_cases: ScenarioCase[];
  treatment_options: TreatmentModeOption[];
  selected_mode_key: string;
  higher_accuracy_hint_en: string;
  higher_accuracy_hint_ar: string;
}

export interface CostForecastPhase {
  area_range_cases: AreaRangeCase[];
  provider_priority: string[];
  treatment_comparison: TreatmentModeOption[];
  selected_mode_key: string;
  higher_accuracy_hint_en: string;
  higher_accuracy_hint_ar: string;
}

export interface ConclusionRecommendationPhase {
  scenario_recommendations: ScenarioCase[];
  action_plan: ScenarioSection[];
  selected_mode_key: string;
  best_balanced_choice_en: string;
  best_balanced_choice_ar: string;
  comparison_summary_en: string;
  comparison_summary_ar: string;
  higher_accuracy_hint_en: string;
  higher_accuracy_hint_ar: string;
}

export interface GeneratedPhases {
  disease_information: DiseaseInformationPhase;
  protection: ProtectionPhase;
  consulting: ConsultingPhase;
  treatment: TreatmentPhase;
  cost_forecast: CostForecastPhase;
  conclusion_recommendation: ConclusionRecommendationPhase;
}

export interface SidebarChatbotContext {
  summary_en: string;
  summary_ar: string;
  quick_questions_en: string[];
  quick_questions_ar: string[];
  allowed_topics_en: string[];
  allowed_topics_ar: string[];
  source_keys: string[];
}

export interface SourceMetadata {
  key: string;
  title: string;
  organization: string;
  source_kind: DataSourceKind;
  source_type: DataSourceOrigin;
  url: string | null;
  confidence: Certainty;
  retrieved_on: string | null;
  note_en: string;
  note_ar: string;
}

export type SourceType = "live_market" | "admin_table" | "csv_fallback" | "estimated_range";
export type Certainty = "low" | "medium" | "high";

export interface SourcedRange {
  label_en: string;
  label_ar: string;
  low: number | null;
  high: number | null;
  unit: string;
  source_type: SourceType;
  confidence: Certainty;
  assumption_en: string;
  assumption_ar: string;
  measured_zero: boolean;
}

export interface AreaRangeCase {
  key: string;
  name_en: string;
  name_ar: string;
  area_feddan: number;
  sprays: SourcedRange;
  treatment_cost_egp: SourcedRange;
  labor_cost_egp: SourcedRange;
  expected_yield_kg: SourcedRange;
  loss_without_action_egp: SourcedRange;
  saved_with_action_egp: SourcedRange;
  revenue_egp: SourcedRange;
  net_benefit_egp: SourcedRange;
  worth_spraying: "likely_worth" | "maybe_not_worth" | "ask_engineer";
  recommendation_en: string;
  recommendation_ar: string;
}

export interface PrimaryDisease {
  name_en: string;
  name_ar: string;
  confidence: number;
  certainty_level: Certainty;
  detected: boolean;
}

export interface ConfidenceWarning {
  level: Certainty;
  text_en: string;
  text_ar: string;
}

export interface Assumption {
  text_en: string;
  text_ar: string;
  source_type: SourceType;
}

export interface PhotoQuality {
  status: string;
  leaf_area_score: number | null;
  host_crop_support: string;
  warnings: string[];
}

export interface TreatmentOptionSchema {
  id: string;
  name: string;
  type: string;
  budget_level: string;
  allowed_status: string;
  cost_range: Record<string, number | null>;
  labor_range: Record<string, number | null>;
  source_type: string;
  assumptions: string[];
  safety_gate: Record<string, any>;
}

export interface CostBenefitBySelectedTreatment {
  selected_treatment_id: string;
  area_scenarios: any[];
}

export interface ForecastRecalculation {
  function_used: string;
  last_selected_treatment_id: string;
  updated_at: string;
}

export interface SystemReport {
  photo_quality: PhotoQuality;
  treatment_options: TreatmentOptionSchema[];
  selected_treatment_id: string;
  cost_benefit_by_selected_treatment: CostBenefitBySelectedTreatment;
  cost_benefit_comparison: any[];
  forecast_recalculation: ForecastRecalculation;

  case_id: string;
  crop: string;
  location: string;
  farm_type: string | null;
  growth_stage: string | null;
  symptoms: string[];
  observations: Record<string, string | number | boolean>;
  observation_sources: Record<string, string>;
  egypt_sources: EgyptSource[];
  source_metadata: SourceMetadata[];
  diagnosis: CaseDiagnosis;
  chatbot_followup_questions: string[];
  protection_plan: string[];
  treatment_plan: CaseTreatmentPlan;
  cost_benefit: CostBenefitResult;
  severity: SeverityEstimate;
  cost_estimate: CostEstimate;
  prediction: PredictionResult;
  recommendation: CaseRecommendation;
  scenarios: ScenarioOutput[];
  primary_detected_disease: PrimaryDisease;
  confidence_warning: ConfidenceWarning | null;
  area_range_cases: AreaRangeCase[];
  summary_cards: SummaryCards;
  phases: GeneratedPhases;
  sidebar_chatbot_context: SidebarChatbotContext;
  assumptions: Assumption[];
  safety_notes: string[];
  completeness: string[];
  conclusion: string;
  disclaimer: string;
}
