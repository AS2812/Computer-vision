import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import type { CropCase, SystemReport } from "../types";
import { CaseWorkspace } from "./CaseWorkspace";

vi.mock("../api", () => ({
  api: {
    cases: vi.fn(),
    getCase: vi.fn(),
    caseReport: vi.fn(),
    caseReportUrl: vi.fn((caseId: string, format: "csv" | "pdf") => `/api/v1/cases/${caseId}/report.${format}`),
  },
}));

const apiMock = vi.mocked(api);

const caseItem: CropCase = {
  case_id: "case-1",
  status: "diagnosis_ready",
  crop: "tomato",
  location: "Beheira, Egypt",
  farm_type: "open_field",
  growth_stage: "fruit set",
  symptoms: ["spots", "yellowing"],
  observations: {
    irrigation_method: "flood",
    spread_speed: "fast",
    affected_plants_percent: 35,
  },
  diagnosis: {
    top_disease: "Early blight",
    confidence: 0.82,
    alternatives: [{ disease: "Septoria leaf spot", confidence: 0.18 }],
    evidence: ["Ringed spots"],
    missing_info: ["Add a whole-plant photo"],
    confirmation_status: "unconfirmed",
    confirmation: null,
  },
  egypt_sources: [
    {
      title: "Central Egyptian Pesticides Database",
      organization: "Egyptian Agricultural Pesticides Committee",
      url: "https://www1.apc.gov.eg/en/search.aspx",
      purpose: "Verify current Egyptian registration.",
      source_kind: "pesticide_registration",
      jurisdiction: "Egypt",
      status: "official",
      retrieved_on: "2026-06-15",
    },
  ],
  disease_class: "fungal",
  treatment_rule_version: "egypt-safety-baseline-2026-06-15",
  protection_plan: ["Reduce leaf wetness and soil splash."],
  treatment_plan: {
    non_chemical: ["Remove heavily affected tissue."],
    chemical_category_if_needed: ["Use only a locally registered fungicide category."],
    safety_notes: ["Do not over-spray."],
  },
  cost_benefit: {
    treatment_cost_egp: 3000,
    estimated_saved_revenue_egp: 40000,
    net_benefit_egp: 37000,
    roi: 12.333,
    break_even_yield_saved_kg: 300,
    decision: "treat_now",
    missing_inputs: [],
  },
  recommendation: {
    best_action_now: "Remove affected lower leaves.",
    next_3_to_7_days: "Recheck marked plants.",
    when_to_call_expert: "Call if spread is fast.",
  },
  updated_at: "2026-06-15T00:00:00Z",
};

function compactValue(labelEn: string, labelAr: string, value: string | number | null, unit = "", confidence = "medium"): any {
  return {
    label_en: labelEn,
    label_ar: labelAr,
    value,
    unit,
    source_type: "generated",
    confidence,
    assumption_en: "",
    assumption_ar: "",
    measured_zero: value === 0,
  };
}

function sourcedRange(low: number | null, high: number | null, unit: string, confidence: "low" | "medium" | "high" = "medium"): any {
  return {
    low,
    high,
    unit,
    source_type: "estimated_range",
    confidence,
    assumption_en: "",
    assumption_ar: "",
    measured_zero: low === 0 && high === 0,
  };
}

function scenarioSection(titleEn: string, titleAr: string, bulletsEn: string[], bulletsAr: string[]): any {
  return {
    title_en: titleEn,
    title_ar: titleAr,
    bullets_en: bulletsEn,
    bullets_ar: bulletsAr,
    source_type: "generated",
    confidence: "medium",
    assumption_en: "",
    assumption_ar: "",
  };
}

function scenarioCase(key: string, nameEn: string, summaryEn: string): any {
  return {
    key,
    name_en: nameEn,
    name_ar: nameEn,
    summary_en: summaryEn,
    summary_ar: summaryEn,
    sections: [
      scenarioSection("What to do", "ما الذي تفعله", [summaryEn], [summaryEn]),
    ],
  };
}

const reportFixture = {
  case_id: "case-1",
  crop: "tomato",
  location: "Beheira, Egypt",
  farm_type: "open_field",
  growth_stage: "fruit set",
  symptoms: ["spots", "yellowing"],
  observations: {
    irrigation_method: "flood",
    spread_speed: "fast",
    affected_plants_percent: 35,
    analysis_processing_ms: 627,
    analysis_peak_memory_mb: 76.46,
    analysis_provider: "CPUExecutionProvider",
  },
  observation_sources: {
    irrigation_method: "farmer_answer",
    spread_speed: "farmer_answer",
    affected_plants_percent: "image_measurement",
    analysis_processing_ms: "image_model",
    analysis_peak_memory_mb: "image_model",
    analysis_provider: "image_model",
  },
  egypt_sources: [
    {
      title: "Central Egyptian Pesticides Database",
      organization: "Egyptian Agricultural Pesticides Committee",
      url: "https://www1.apc.gov.eg/en/search.aspx",
      purpose: "Verify current Egyptian registration.",
      source_kind: "pesticide_registration",
      jurisdiction: "Egypt",
      status: "official",
      retrieved_on: "2026-06-15",
    },
    {
      title: "CAPMAS tomato bulletin",
      organization: "CAPMAS",
      url: "https://www.capmas.gov.eg/",
      purpose: "Reference tomato yield statistics.",
      source_kind: "diagnosis",
      jurisdiction: "Egypt",
      status: "official",
      retrieved_on: "2026-06-15",
    },
  ],
  source_metadata: [
    {
      key: "visual_model",
      title: "Local tomato disease detector",
      organization: "AgroVision local runtime",
      source_kind: "visual_model",
      source_type: "generated",
      url: null,
      confidence: "high",
      retrieved_on: "2026-06-15",
      note_en: "Early blight was selected from the uploaded photo.",
      note_ar: "تم اختيار اللفحة المبكرة من الصورة المرفوعة.",
    },
    {
      key: "disease_information",
      title: "Reviewed tomato disease knowledge base",
      organization: "AgroVision knowledge layer",
      source_kind: "disease_information",
      source_type: "generated",
      url: null,
      confidence: "medium",
      retrieved_on: "2026-06-15",
      note_en: "The disease description was generated from reviewed tomato disease knowledge.",
      note_ar: "تم توليد وصف المرض من قاعدة المعرفة المراجعة للطماطم.",
    },
    {
      key: "weather",
      title: "Live weather from the analysis location",
      organization: "Open-Meteo",
      source_kind: "weather",
      source_type: "live",
      url: "https://api.open-meteo.com/v1/forecast",
      confidence: "high",
      retrieved_on: "2026-06-15",
      note_en: "Weather fetched for the photo location.",
      note_ar: "تم جلب الطقس لموقع الصورة.",
    },
    {
      key: "market_price",
      title: "Egypt tomato farmgate reference price",
      organization: "AgroVision reference price table",
      source_kind: "market_price",
      source_type: "estimated_range",
      url: null,
      confidence: "medium",
      retrieved_on: "2026-06-15",
      note_en: "Reference price only.",
      note_ar: "سعر مرجعي فقط.",
    },
  ],
  diagnosis: {
    top_disease: "Early blight",
    confidence: 0.82,
    alternatives: [{ disease: "Septoria leaf spot", confidence: 0.18 }],
    evidence: ["Ringed spots"],
    missing_info: ["Add a whole-plant photo"],
    confirmation_status: "unconfirmed",
    confirmation: null,
  },
  chatbot_followup_questions: [
    "What is the primary disease from this photo?",
    "What should I do today before spraying anything?",
    "Which treatment path is allowed by the safety gate?",
  ],
  protection_plan: ["Reduce leaf wetness and soil splash."],
  treatment_plan: {
    non_chemical: ["Remove heavily affected tissue."],
    chemical_category_if_needed: ["Use only a locally registered fungicide category."],
    safety_notes: ["Do not over-spray."],
  },
  cost_benefit: {
    treatment_cost_egp: 3000,
    estimated_saved_revenue_egp: 40000,
    net_benefit_egp: 37000,
    roi: 12.333,
    break_even_yield_saved_kg: 300,
    decision: "treat_now",
    missing_inputs: [],
  },
  severity: {
    severity_label: "high",
    visible_affected_percent: 35,
    estimated_yield_loss_low_percent: 20,
    estimated_yield_loss_high_percent: 50,
    recovery_probability_label: "fair",
    weather_risk_label: "high",
    drivers: ["Dense canopy", "Wet weather"],
    basis: "Image-derived estimate.",
  },
  cost_estimate: {
    basis: "reference_estimate",
    area_feddan_assumed: 1,
    treatment_cost_egp_low: 2280,
    treatment_cost_egp_high: 7980,
    potential_loss_egp_low: 30000,
    potential_loss_egp_high: 360000,
    net_benefit_egp_low: 1000,
    net_benefit_egp_high: 2000,
    decision_hint: "Protecting the crop is likely worth the cost.",
    prices_used: [],
    assumptions: [],
    note: "Estimate from reference prices.",
  },
  prediction: {
    damage_degree: "high",
    yield_loss_percent: 35,
    yield_kg_per_feddan: 15000,
    main_risk_factors: ["Wet weather", "Dense canopy"],
  },
  recommendation: {
    best_action_now: "Remove affected lower leaves.",
    next_3_to_7_days: "Recheck marked plants.",
    when_to_call_expert: "Call if spread is fast.",
  },
  scenarios: [
    { key: "home_garden", name_en: "Home garden", name_ar: "Home garden", confidence_en: "high", confidence_ar: "high", protection_en: "p", protection_ar: "p", treatment_en: "t", treatment_ar: "t", cost_en: "co", cost_ar: "co", recommendation_en: "r", recommendation_ar: "r" },
    { key: "open_field", name_en: "Open-field farm", name_ar: "Open-field farm", confidence_en: "high", confidence_ar: "high", protection_en: "p", protection_ar: "p", treatment_en: "t", treatment_ar: "t", cost_en: "co", cost_ar: "co", recommendation_en: "r", recommendation_ar: "r" },
    { key: "greenhouse", name_en: "Greenhouse", name_ar: "Greenhouse", confidence_en: "medium", confidence_ar: "medium", protection_en: "p", protection_ar: "p", treatment_en: "t", treatment_ar: "t", cost_en: "co", cost_ar: "co", recommendation_en: "r", recommendation_ar: "r" },
    { key: "desert_farm", name_en: "Desert / new-land farm", name_ar: "Desert / new-land farm", confidence_en: "medium", confidence_ar: "medium", protection_en: "p", protection_ar: "p", treatment_en: "t", treatment_ar: "t", cost_en: "co", cost_ar: "co", recommendation_en: "r", recommendation_ar: "r" },
    { key: "small_commercial", name_en: "Small commercial farm", name_ar: "Small commercial farm", confidence_en: "medium", confidence_ar: "medium", protection_en: "p", protection_ar: "p", treatment_en: "t", treatment_ar: "t", cost_en: "co", cost_ar: "co", recommendation_en: "r", recommendation_ar: "r" },
    { key: "coastal_humid", name_en: "Coastal / high-humidity (e.g. Alexandria)", name_ar: "Coastal / high-humidity (e.g. Alexandria)", confidence_en: "high", confidence_ar: "high", protection_en: "p", protection_ar: "p", treatment_en: "t", treatment_ar: "t", cost_en: "co", cost_ar: "co", recommendation_en: "r", recommendation_ar: "r" },
  ],
  primary_detected_disease: {
    name_en: "Early blight",
    name_ar: "اللفحة المبكرة",
    confidence: 0.82,
    certainty_level: "high",
    detected: true,
  },
  confidence_warning: null,
  area_range_cases: [
    {
      key: "home_garden",
      name_en: "Home garden",
      name_ar: "Home garden",
      area_feddan: 0.01,
      sprays: compactValue("Sprays", "الرشات", 2, "count"),
      treatment_cost_egp: compactValue("Treatment cost", "تكلفة العلاج", 230, "EGP"),
      labor_cost_egp: compactValue("Labor cost", "تكلفة العمالة", 80, "EGP"),
      expected_yield_kg: compactValue("Expected yield", "العائد المتوقع", 120, "kg"),
      loss_without_action_egp: compactValue("Loss without action", "الخسارة بدون تدخل", 300, "EGP"),
      saved_with_action_egp: compactValue("Saved with action", "المحفوظ بالتدخل", 250, "EGP"),
      revenue_egp: compactValue("Revenue", "الإيراد", 1500, "EGP"),
      net_benefit_egp: compactValue("Net benefit", "صافي العائد", 1000, "EGP"),
      worth_spraying: "likely_worth",
      recommendation_en: "Worth spraying with the registered path if the disease is confirmed.",
      recommendation_ar: "Worth spraying with the registered path if the disease is confirmed.",
    },
    {
      key: "one_feddan",
      name_en: "1 feddan",
      name_ar: "1 feddan",
      area_feddan: 1,
      sprays: compactValue("Sprays", "الرشات", 2, "count"),
      treatment_cost_egp: compactValue("Treatment cost", "تكلفة العلاج", 2280, "EGP"),
      labor_cost_egp: compactValue("Labor cost", "تكلفة العمالة", 800, "EGP"),
      expected_yield_kg: compactValue("Expected yield", "العائد المتوقع", 15000, "kg"),
      loss_without_action_egp: compactValue("Loss without action", "الخسارة بدون تدخل", 30000, "EGP"),
      saved_with_action_egp: compactValue("Saved with action", "المحفوظ بالتدخل", 25000, "EGP"),
      revenue_egp: compactValue("Revenue", "الإيراد", 150000, "EGP"),
      net_benefit_egp: compactValue("Net benefit", "صافي العائد", 127720, "EGP"),
      worth_spraying: "likely_worth",
      recommendation_en: "Protecting 1 feddan is likely worth the cost.",
      recommendation_ar: "Protecting 1 feddan is likely worth the cost.",
    },
    {
      key: "ten_feddan",
      name_en: "10 feddans",
      name_ar: "10 feddans",
      area_feddan: 10,
      sprays: compactValue("Sprays", "الرشات", 3, "count"),
      treatment_cost_egp: compactValue("Treatment cost", "تكلفة العلاج", 19800, "EGP"),
      labor_cost_egp: compactValue("Labor cost", "تكلفة العمالة", 7000, "EGP"),
      expected_yield_kg: compactValue("Expected yield", "العائد المتوقع", 150000, "kg"),
      loss_without_action_egp: compactValue("Loss without action", "الخسارة بدون تدخل", 300000, "EGP"),
      saved_with_action_egp: compactValue("Saved with action", "المحفوظ بالتدخل", 250000, "EGP"),
      revenue_egp: compactValue("Revenue", "الإيراد", 1500000, "EGP"),
      net_benefit_egp: compactValue("Net benefit", "صافي العائد", 1272200, "EGP"),
      worth_spraying: "likely_worth",
      recommendation_en: "Protecting 10 feddans is likely worth the cost.",
      recommendation_ar: "Protecting 10 feddans is likely worth the cost.",
    },
  ],
  summary_cards: {
    numbers_only: true,
    detected_disease: compactValue("Primary disease", "المرض الأساسي", "Early blight"),
    visual_score: compactValue("Visual match", "التطابق البصري", 82, "%"),
    top_candidates: [
      compactValue("Early blight", "اللفحة المبكرة", 82, "%"),
      compactValue("Septoria leaf spot", "تبقع سبتوريا", 18, "%"),
    ],
    infection_extent: compactValue("Visible infection", "الانتشار الظاهر", 35, "%"),
    weather_risk: compactValue("Weather pressure", "ضغط الطقس", 82, "%"),
    engine_stats: {
      analysis_time_ms: 627,
      engine: "CPUExecutionProvider",
      memory_used_mb: 76.46,
      source_status: "Open-Meteo; live weather + reference prices",
    },
  },
  phases: {
    disease_information: {
      disease_name_en: "Early blight",
      disease_name_ar: "اللفحة المبكرة",
      cause_type_en: "",
      cause_type_ar: "",
      meaning_en: "A tomato leaf disease that starts on older leaves and spreads under wet weather.",
      meaning_ar: "مرض ورقي في الطماطم يبدأ عادة في الأوراق الأكبر ويزداد مع الرطوبة.",
      leaf_symptoms_en: ["Brown ringed spots on the leaf surface.", "Yellowing around older lesions."],
      leaf_symptoms_ar: ["بقع بنية حلقية على سطح الورقة.", "اصفرار حول البقع الأقدم."],
      fruit_symptoms_en: ["Fruit is affected indirectly when canopy cover drops.", "Watch for sunscald where leaves thin out."],
      fruit_symptoms_ar: ["تتأثر الثمار بشكل غير مباشر عند ضعف الغطاء الورقي.", "راقب حروق الشمس عندما يخف الغطاء."],
      stem_symptoms_en: ["Stem lesions are usually secondary checks.", "Look near the base if the problem is severe."],
      stem_symptoms_ar: ["الساق غالباً نقطة فحص ثانوية.", "راقب القاعدة إذا زادت الشدة."],
      spread_en: "Warm, humid weather and wet leaves help the disease move faster.",
      spread_ar: "الجو الدافئ الرطب والأوراق المبللة يسرعان الانتشار.",
      why_it_appears_en: "Splash, dew, and crowding keep tissue wet long enough for spores to establish.",
      why_it_appears_ar: "الرذاذ والندى والتزاحم يبقون النسيج رطباً بما يكفي لبدء العدوى.",
      irrigation_conditions_en: "",
      irrigation_conditions_ar: "",
      worse_weather_en: "Wet weather at around 27C with wind still raises spread pressure.",
      worse_weather_ar: "الجو الرطب عند حوالى 27 درجة مئوية ما زال يرفع ضغط الانتشار.",
      lookalikes_en: ["nutrient stress", "sunscald", "water stress"],
      lookalikes_ar: ["إجهاد غذائي", "حروق شمس", "إجهاد مائي"],
      danger_en: "Leaf loss, weaker fruit fill, sunscald, and secondary infection are the real risks.",
      danger_ar: "فقدان الأوراق وضعف امتلاء الثمار وحروق الشمس والعدوى الثانوية هي المخاطر الحقيقية.",
      top_candidates: [],
      resistant_varieties: [],
      today_check_en: ["Inspect the lowest leaves first.", "Check the underside of the spots."],
      today_check_ar: ["افحص الأوراق السفلية أولاً.", "افحص الوجه السفلي للبقع."],
      worsening_en: ["More plants show the same spots.", "Yellowing moves upward.", "Spots merge into larger dead patches."],
      worsening_ar: ["ظهور نفس البقع في نباتات أكثر.", "انتقال الاصفرار لأعلى.", "اندماج البقع إلى مساحات ميتة أكبر."],
      stable_en: ["Only old leaves are touched.", "The pattern does not change after dry weather."],
      stable_ar: ["الأوراق القديمة فقط متأثرة.", "النمط لا يتغير بعد الجو الجاف."],
      scenario_cases: [
        scenarioCase("single_leaf", "Single leaf hit", "Treat the leaf and check nearby leaves daily."),
        scenarioCase("row_spread", "Row spread", "Treat the row as active pressure and watch the next row."),
      ],
      higher_accuracy_hint_en: "",
      higher_accuracy_hint_ar: "",
    },
    protection: {
      scenario_cases: [
        scenarioCase("dry_canopy", "Dry canopy", "Keep the canopy dry and open to reduce new infection."),
        scenarioCase("splash_control", "Splash control", "Reduce splash from irrigation and soil."),
      ],
    },
    consulting: {
      auto_questions_with_answers: [
        {
          key: "affected_part",
          question_en: "Which plant part is most affected?",
          question_ar: "أي جزء من النبات هو الأكثر تأثراً؟",
          answer_en: "The photo mainly shows the leaf surface, so check the underside and the lower leaves.",
          answer_ar: "الصورة تُظهر سطح الورقة، فافحص الوجه السفلي والأوراق السفلية.",
          why_it_matters_en: "The disease often starts low in the canopy.",
          why_it_matters_ar: "غالباً يبدأ المرض في الأوراق السفلية.",
          decision_change_en: "Lower-leaf hits mean sanitation matters more.",
          decision_change_ar: "إصابة الأوراق السفلية تعني أن النظافة أهم.",
          scenario_notes_en: ["Check the oldest leaves first.", "Move the inspection to the underside."],
          scenario_notes_ar: ["افحص الأوراق الأقدم أولاً.", "انقل الفحص للوجه السفلي."],
          source_type: "generated",
          assumption_en: "",
          assumption_ar: "",
        },
        {
          key: "spread_speed",
          question_en: "How fast is it spreading?",
          question_ar: "ما سرعة الانتشار؟",
          answer_en: "The pattern looks fast, so keep it under active watch today.",
          answer_ar: "النمط يبدو سريعاً، فتابعه اليوم بنشاط.",
          why_it_matters_en: "Spread speed changes whether you can monitor or need to move immediately.",
          why_it_matters_ar: "سرعة الانتشار تحدد هل تكتفي بالمراقبة أم تتحرك فوراً.",
          decision_change_en: "Fast spread means protect healthy leaves immediately.",
          decision_change_ar: "الانتشار السريع يعني حماية الأوراق السليمة فوراً.",
          scenario_notes_en: ["Quick spread raises urgency.", "Slow spread still needs sanitation."],
          scenario_notes_ar: ["الانتشار السريع يرفع الاستعجال.", "الانتشار البطيء ما زال يحتاج نظافة."],
          source_type: "generated",
          assumption_en: "",
          assumption_ar: "",
        },
      ],
    },
    treatment: {
      scenario_cases: [
        scenarioCase("non_chemical", "Non-chemical first", "Remove heavily affected tissue before any chemical path."),
        scenarioCase("registered_path", "Registered path", "Use a locally registered fungicide only if the safety gate stays open."),
      ],
    },
    cost_forecast: {
      area_range_cases: [
        {
          key: "home_garden",
          name_en: "Home garden",
          name_ar: "Home garden",
          area_feddan: 0.01,
          sprays: compactValue("Sprays", "الرشات", 2, "count"),
          treatment_cost_egp: compactValue("Treatment cost", "تكلفة العلاج", 230, "EGP"),
          labor_cost_egp: compactValue("Labor cost", "تكلفة العمالة", 80, "EGP"),
          expected_yield_kg: compactValue("Expected yield", "العائد المتوقع", 120, "kg"),
          loss_without_action_egp: compactValue("Loss without action", "الخسارة بدون تدخل", 300, "EGP"),
          saved_with_action_egp: compactValue("Saved with action", "المحفوظ بالتدخل", 250, "EGP"),
          revenue_egp: compactValue("Revenue", "الإيراد", 1500, "EGP"),
          net_benefit_egp: compactValue("Net benefit", "صافي العائد", 1000, "EGP"),
          worth_spraying: "likely_worth",
          recommendation_en: "Worth spraying with the registered path if the disease is confirmed.",
          recommendation_ar: "Worth spraying with the registered path if the disease is confirmed.",
        },
        {
          key: "one_feddan",
          name_en: "1 feddan",
          name_ar: "1 feddan",
          area_feddan: 1,
          sprays: compactValue("Sprays", "الرشات", 2, "count"),
          treatment_cost_egp: compactValue("Treatment cost", "تكلفة العلاج", 2280, "EGP"),
          labor_cost_egp: compactValue("Labor cost", "تكلفة العمالة", 800, "EGP"),
          expected_yield_kg: compactValue("Expected yield", "العائد المتوقع", 15000, "kg"),
          loss_without_action_egp: compactValue("Loss without action", "الخسارة بدون تدخل", 30000, "EGP"),
          saved_with_action_egp: compactValue("Saved with action", "المحفوظ بالتدخل", 25000, "EGP"),
          revenue_egp: compactValue("Revenue", "الإيراد", 150000, "EGP"),
          net_benefit_egp: compactValue("Net benefit", "صافي العائد", 127720, "EGP"),
          worth_spraying: "likely_worth",
          recommendation_en: "Protecting 1 feddan is likely worth the cost.",
          recommendation_ar: "Protecting 1 feddan is likely worth the cost.",
        },
        {
          key: "ten_feddan",
          name_en: "10 feddans",
          name_ar: "10 feddans",
          area_feddan: 10,
          sprays: compactValue("Sprays", "الرشات", 3, "count"),
          treatment_cost_egp: compactValue("Treatment cost", "تكلفة العلاج", 19800, "EGP"),
          labor_cost_egp: compactValue("Labor cost", "تكلفة العمالة", 7000, "EGP"),
          expected_yield_kg: compactValue("Expected yield", "العائد المتوقع", 150000, "kg"),
          loss_without_action_egp: compactValue("Loss without action", "الخسارة بدون تدخل", 300000, "EGP"),
          saved_with_action_egp: compactValue("Saved with action", "المحفوظ بالتدخل", 250000, "EGP"),
          revenue_egp: compactValue("Revenue", "الإيراد", 1500000, "EGP"),
          net_benefit_egp: compactValue("Net benefit", "صافي العائد", 1272200, "EGP"),
          worth_spraying: "likely_worth",
          recommendation_en: "Protecting 10 feddans is likely worth the cost.",
          recommendation_ar: "Protecting 10 feddans is likely worth the cost.",
        },
      ],
      provider_priority: [
        "CAPMAS tomato production bulletins for yield",
        "Egypt tomato farmgate reference price",
        "APC pesticide registration database",
      ],
    },
    conclusion_recommendation: {
      scenario_recommendations: [
        scenarioCase("act_now", "Act now", "Use this when the match is strong and spread pressure is visible."),
        scenarioCase("verify_first", "Verify first", "Use this when confidence is not high enough for chemicals."),
      ],
      action_plan: [
        scenarioSection("Today", "اليوم", ["Inspect the plant in person."], ["افحص النبات ميدانياً."]),
        scenarioSection("Next 3 to 7 days", "خلال 3 إلى 7 أيام", ["Re-check the nearest rows."], ["أعد فحص الصفوف القريبة."]),
      ],
    },
  },
  sidebar_chatbot_context: {
    summary_en: "Ground the assistant in the confirmed photo evidence, the weather source, CAPMAS yield references, and APC registration.",
    summary_ar: "أبقِ مساعد الشريط الجانبي مرتبطاً بأدلة الصورة ومصدر الطقس ومرجع CAPMAS وتسجل APC.",
    quick_questions_en: [
      "What is the primary disease from this photo?",
      "What should I do today before spraying anything?",
      "Which treatment path is allowed by the safety gate?",
    ],
    quick_questions_ar: [
      "ما المرض الأساسي من هذه الصورة؟",
      "ماذا أفعل اليوم قبل رش أي شيء؟",
      "ما مسار العلاج المسموح به بعد بوابة الأمان؟",
    ],
    allowed_topics_en: ["photo diagnosis", "weather and spread pressure", "protection steps", "cost forecast"],
    allowed_topics_ar: ["تشخيص الصورة", "الطقس وضغط الانتشار", "خطوات الوقاية", "توقع التكلفة"],
    source_keys: ["visual_model", "disease_information", "weather", "market_price"],
  },
  assumptions: [
    {
      text_en: "Area was not given, so the report generated common Egyptian area sizes.",
      text_ar: "المساحة لم تُعطَ، لذلك وُلدت أحجام المساحات المصرية الشائعة.",
      source_type: "estimated_range",
    },
  ],
  safety_notes: ["Do not over-spray.", "Keep the APC registration and pre-harvest interval in view."],
  completeness: [],
  conclusion: "Early blight is the lead match. The report stays conservative, keeps the chemical gate behind registration checks, and uses a reference-based cost forecast until live figures replace it.",
  disclaimer: "Diagnosis support only. Confirm with an agronomist before spraying.",
} as unknown as SystemReport;

reportFixture.confidence_warning = {
  level: "medium",
  text_en: "Confidence is not agronomist confirmation.",
  text_ar: "Confidence is not agronomist confirmation.",
};

reportFixture.summary_cards.top_candidates = [
  compactValue("Early blight", "Early blight", 82, "%", "high"),
  compactValue("Septoria leaf spot", "Septoria leaf spot", 18, "%", "medium"),
];

reportFixture.phases.disease_information = {
  ...reportFixture.phases.disease_information,
  cause_type_en: "Fungal disease from a real photo-based detector.",
  cause_type_ar: "Fungal disease from a real photo-based detector.",
  irrigation_conditions_en: "Risk rises when leaves stay wet after overhead irrigation or rainfall.",
  irrigation_conditions_ar: "Risk rises when leaves stay wet after overhead irrigation or rainfall.",
  top_candidates: [
    {
      rank: 1,
      disease_name_en: "Early blight",
      disease_name_ar: "Early blight",
      confidence: 0.82,
      confidence_label: "high",
      support_en: ["Ringed spots on older leaves", "Yellowing around lesions"],
      support_ar: ["Ringed spots on older leaves", "Yellowing around lesions"],
      source_type: "generated",
      source_note_en: "Best match from the local model.",
      source_note_ar: "Best match from the local model.",
    },
    {
      rank: 2,
      disease_name_en: "Septoria leaf spot",
      disease_name_ar: "Septoria leaf spot",
      confidence: 0.18,
      confidence_label: "medium",
      support_en: [],
      support_ar: [],
      source_type: "generated",
      source_note_en: "Still a plausible lookalike.",
      source_note_ar: "Still a plausible lookalike.",
    },
  ],
  resistant_varieties: [
    {
      name_en: "Stellar F1",
      name_ar: "Stellar F1",
      resistance_codes_en: "EB, LB, Septoria",
      resistance_codes_ar: "EB, LB, Septoria",
      disease_coverage_en: ["Early blight", "Late blight", "Septoria leaf spot"],
      disease_coverage_ar: ["Early blight", "Late blight", "Septoria leaf spot"],
      resistance_strength_en: "Reviewed resistance package, not a cure.",
      resistance_strength_ar: "Reviewed resistance package, not a cure.",
      prevention_only_warning_en: "Resistance lowers risk but does not replace crop hygiene.",
      prevention_only_warning_ar: "Resistance lowers risk but does not replace crop hygiene.",
      egypt_availability_status: "not_verified_in_egypt",
      source_kind: "variety_knowledge",
      source_type: "official",
      source_title: "Cornell disease-resistant tomato varieties",
      source_organization: "Cornell University",
      source_url: "https://www.vegetables.cornell.edu/pest-management/disease-factsheets/disease-resistant-vegetable-varieties/disease-resistant-tomato-varieties/",
      source_note_en: "Reviewed reference. Egypt stock not confirmed.",
      source_note_ar: "Reviewed reference. Egypt stock not confirmed.",
      farmer_wording_en: "Ask the seed seller for the resistance codes on the bag.",
      farmer_wording_ar: "Ask the seed seller for the resistance codes on the bag.",
    },
    {
      name_en: "Iron Lady",
      name_ar: "Iron Lady",
      resistance_codes_en: "EB, LB, Septoria, FW",
      resistance_codes_ar: "EB, LB, Septoria, FW",
      disease_coverage_en: ["Early blight", "Late blight", "Septoria leaf spot", "Fusarium wilt"],
      disease_coverage_ar: ["Early blight", "Late blight", "Septoria leaf spot", "Fusarium wilt"],
      resistance_strength_en: "Broad resistance package from reviewed sources.",
      resistance_strength_ar: "Broad resistance package from reviewed sources.",
      prevention_only_warning_en: "Still confirm the source and the planting season fit.",
      prevention_only_warning_ar: "Still confirm the source and the planting season fit.",
      egypt_availability_status: "unknown",
      source_kind: "variety_knowledge",
      source_type: "official",
      source_title: "Cornell tomato resistance reference",
      source_organization: "Cornell University",
      source_url: "https://www.vegetables.cornell.edu/pest-management/disease-factsheets/disease-resistant-vegetable-varieties/new-york-adapted-tomatoes-with-resistance-to-multiple-fungal-and-bacterial-diseases-created-at-cornell/",
      source_note_en: "Reviewed reference. Local availability not verified.",
      source_note_ar: "Reviewed reference. Local availability not verified.",
      farmer_wording_en: "Check the seed packet and confirm the codes before buying.",
      farmer_wording_ar: "Check the seed packet and confirm the codes before buying.",
    },
  ],
  higher_accuracy_hint_en: "Add a whole-plant photo and a leaf underside photo for a tighter match.",
  higher_accuracy_hint_ar: "Add a whole-plant photo and a leaf underside photo for a tighter match.",
};

reportFixture.phases.protection = {
  ...reportFixture.phases.protection,
  higher_accuracy_hint_en: "Share irrigation method and planting density to improve protection advice.",
  higher_accuracy_hint_ar: "Share irrigation method and planting density to improve protection advice.",
};

reportFixture.phases.consulting = {
  ...reportFixture.phases.consulting,
  higher_accuracy_hint_en: "Add a second photo and tell us whether the problem is moving up the plant.",
  higher_accuracy_hint_ar: "Add a second photo and tell us whether the problem is moving up the plant.",
};

const treatmentModeOptions = [
  {
    key: "sanitation_only",
    label_en: "Sanitation first",
    label_ar: "Sanitation first",
    summary_en: "Remove badly affected leaves and keep the canopy dry.",
    summary_ar: "Remove badly affected leaves and keep the canopy dry.",
    cost_egp: sourcedRange(180, 280, "EGP"),
    budget_egp: sourcedRange(200, 350, "EGP"),
    expected_benefit_en: "Lowest cost, but it only helps if pressure is still light.",
    expected_benefit_ar: "Lowest cost, but it only helps if pressure is still light.",
    risk_en: "May be too weak if the disease is already spreading fast.",
    risk_ar: "May be too weak if the disease is already spreading fast.",
    apc_gate_en: "No spray gate needed for sanitation.",
    apc_gate_ar: "No spray gate needed for sanitation.",
    requires_apc_verification: false,
    requires_engineer_confirmation: false,
    source_kind: "treatment_knowledge",
    source_type: "generated",
    source_note_en: "Supportive hygiene path.",
    source_note_ar: "Supportive hygiene path.",
    farmer_wording_ar: "Start here before any spray decision.",
  },
  {
    key: "registered_spray",
    label_en: "Registered spray path",
    label_ar: "Registered spray path",
    summary_en: "Use a locally registered product only after the safety gate stays open.",
    summary_ar: "Use a locally registered product only after the safety gate stays open.",
    cost_egp: sourcedRange(2280, 7980, "EGP"),
    budget_egp: sourcedRange(2500, 9000, "EGP"),
    expected_benefit_en: "Higher protection when disease pressure and confirmation are strong.",
    expected_benefit_ar: "Higher protection when disease pressure and confirmation are strong.",
    risk_en: "Requires APC label checks and residue discipline.",
    risk_ar: "Requires APC label checks and residue discipline.",
    apc_gate_en: "APC registration required before any spray.",
    apc_gate_ar: "APC registration required before any spray.",
    requires_apc_verification: true,
    requires_engineer_confirmation: true,
    source_kind: "treatment_knowledge",
    source_type: "generated",
    source_note_en: "Use only with label verification.",
    source_note_ar: "Use only with label verification.",
    farmer_wording_ar: "Only use after the label and crop match are confirmed.",
  },
] as const;

reportFixture.phases.treatment = {
  ...reportFixture.phases.treatment,
  treatment_options: treatmentModeOptions as any,
  selected_mode_key: "registered_spray",
  higher_accuracy_hint_en: "Add crop stage and nearby weather details if you want a tighter treatment gate.",
  higher_accuracy_hint_ar: "Add crop stage and nearby weather details if you want a tighter treatment gate.",
};

reportFixture.phases.cost_forecast = {
  ...reportFixture.phases.cost_forecast,
  treatment_comparison: treatmentModeOptions as any,
  selected_mode_key: "sanitation_only",
  higher_accuracy_hint_en: "Share the feddan count and product label to narrow the cost band.",
  higher_accuracy_hint_ar: "Share the feddan count and product label to narrow the cost band.",
};

reportFixture.phases.conclusion_recommendation = {
  ...reportFixture.phases.conclusion_recommendation,
  selected_mode_key: "registered_spray",
  best_balanced_choice_en: "Best balance: clean up first, then use a registered spray only if confirmation stays strong.",
  best_balanced_choice_ar: "Best balance: clean up first, then use a registered spray only if confirmation stays strong.",
  comparison_summary_en: "The sanitation path is cheapest, but the registered path protects more yield when the diagnosis is confirmed.",
  comparison_summary_ar: "The sanitation path is cheapest, but the registered path protects more yield when the diagnosis is confirmed.",
  higher_accuracy_hint_en: "Add a second photo, crop stage, and a field check if you want the final call tighter.",
  higher_accuracy_hint_ar: "Add a second photo, crop stage, and a field check if you want the final call tighter.",
};

function setupApiMocks() {
  apiMock.cases.mockResolvedValue([caseItem]);
  apiMock.getCase.mockResolvedValue(caseItem);
  apiMock.caseReport.mockResolvedValue(reportFixture);
}

beforeEach(() => {
  vi.clearAllMocks();
  globalThis.localStorage?.clear?.();
  setupApiMocks();
});

describe("CaseWorkspace", () => {
  it("shows the empty photo-only workspace when no case is selected", async () => {
    apiMock.cases.mockResolvedValueOnce([]);

    render(<CaseWorkspace arabic={false} />);

    await waitFor(() => expect(screen.getByText("No saved cases yet.")).toBeInTheDocument());
    expect(screen.getByText("Photo-only crop report")).toBeInTheDocument();
    expect(screen.queryByText("Start case")).not.toBeInTheDocument();
    expect(screen.queryByText("Save field context")).not.toBeInTheDocument();
  });

  it("loads a saved case and renders the generated report phases", async () => {
    render(<CaseWorkspace arabic={false} geoCoords={{ lat: 31.211, lng: 29.96 }} />);

    await waitFor(() => expect(screen.getByText("Early blight")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Early blight"));

    await waitFor(() => expect(screen.getByText("Generated report")).toBeInTheDocument());
    expect(screen.getByText("Top summary")).toBeInTheDocument();
    expect(screen.getByText("Sidebar assistant context")).toBeInTheDocument();
    expect(screen.getByText("Central Egyptian Pesticides Database")).toBeInTheDocument();
    expect(screen.getByText("Local tomato disease detector")).toBeInTheDocument();
    expect(screen.getByText("Confidence is not agronomist confirmation.")).toBeInTheDocument();
    expect(screen.getByText(/Device GPS captured in the photo flow:/)).toBeInTheDocument();
    expect(screen.getByText(/31\.21100, 29\.96000/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "PDF" })).toHaveAttribute("href", "/api/v1/cases/case-1/report.pdf");
    expect(screen.getByRole("link", { name: "CSV" })).toHaveAttribute("href", "/api/v1/cases/case-1/report.csv");
    expect(screen.getByText("Early blight: 82%")).toBeInTheDocument();
    expect(screen.getByText("Septoria leaf spot: 18%")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Protection/ }));
    await waitFor(() => expect(screen.getByText("Need a clearer protection check?")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Consulting/ }));
    await waitFor(() => expect(screen.getByText("Need more evidence?")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Treatment/ }));
    await waitFor(() => expect(screen.getByText("Treatment mode comparison")).toBeInTheDocument());
    expect(screen.getByText("Sanitation first")).toBeInTheDocument();
    expect(screen.getAllByText("Registered spray path")[0]).toBeInTheDocument();
    expect(screen.getByText("Current selected mode")).toBeInTheDocument();
    expect(screen.getByText("Need a clearer treatment decision?")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Cost & Forecast/ }));
    await waitFor(() => expect(screen.getByText("Treatment cost comparison")).toBeInTheDocument());
    expect(screen.getByText("Current economic choice")).toBeInTheDocument();
    expect(screen.getByText("Need a tighter cost estimate?")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Conclusion/ }));
    await waitFor(() => expect(screen.getByText("Balanced recommendation")).toBeInTheDocument());
    expect(screen.getByText("Best balance: clean up first, then use a registered spray only if confirmation stays strong.")).toBeInTheDocument();
    expect(screen.getByText("Selected mode: Registered spray path")).toBeInTheDocument();
    expect(screen.getByText("Need a clearer final call?")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Cost & Forecast/ }));
    await waitFor(() => expect(screen.getByText("1 feddan")).toBeInTheDocument());
    expect(screen.getByText("Home garden")).toBeInTheDocument();
    expect(screen.getByText("Protecting 1 feddan is likely worth the cost.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Conclusion/ }));
    await waitFor(() => expect(screen.getByText("Action plan")).toBeInTheDocument());
    expect(screen.getByText("Act now")).toBeInTheDocument();
    expect(screen.getByText("Verify first")).toBeInTheDocument();
    expect(screen.getAllByText(/reference-based cost forecast/i)).toHaveLength(2);
  });

  it("renders the same report flow in Arabic", async () => {
    render(<CaseWorkspace arabic geoCoords={{ lat: 31.211, lng: 29.96 }} />);

    await waitFor(() => expect(screen.getByText("مساحة الحالة")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Early blight"));

    await waitFor(() => expect(screen.getByText("تقرير مولد")).toBeInTheDocument());
    expect(screen.getByText("Confidence is not agronomist confirmation.")).toBeInTheDocument();
    expect(screen.getByText(/تم التقاط GPS الجهاز في مسار الصورة:/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /الوقاية/ }));
    await waitFor(() => expect(screen.getByText("الوقاية")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /الاستشارة/ }));
    await waitFor(() => expect(screen.getByText("الاستشارة")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /العلاج/ }));
    await waitFor(() => expect(screen.getByText("مقارنة أوضاع العلاج")).toBeInTheDocument());
    expect(screen.getAllByText("Registered spray path")[0]).toBeInTheDocument();
    expect(screen.getByText("Sanitation first")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /الخلاصة/ }));
    await waitFor(() => expect(screen.getByText("الخلاصة والتوصية")).toBeInTheDocument());
    expect(screen.getByText("الوضع المختار: Registered spray path")).toBeInTheDocument();
  });

  it("shows compact variety summary card with details toggle — not a giant variety grid", async () => {
    render(<CaseWorkspace arabic={false} />);

    await waitFor(() => expect(screen.getByText("Early blight")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Early blight"));

    await waitFor(() => expect(screen.getByText("Generated report")).toBeInTheDocument());

    // Navigate to Phase 1 — Disease Information
    fireEvent.click(screen.getByRole("button", { name: /1\. Disease Information/ }));

    // Compact variety section shows count and prevention warning
    await waitFor(() => expect(screen.getByText(/2 variet/i)).toBeInTheDocument());
    expect(screen.getByText(/reduce future risk/i)).toBeInTheDocument();

    // There must be a "View variety details" toggle (a <details> summary)
    const detailsToggle = screen.getByText(/View variety details/i);
    expect(detailsToggle).toBeInTheDocument();

    // The <details> element must be closed by default (no open attribute)
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    const detailsEl = detailsToggle.closest("details")!;
    expect(detailsEl).toBeInTheDocument();
    expect(detailsEl).not.toHaveAttribute("open");

    // After opening the toggle, the variety rows become accessible
    fireEvent.click(detailsToggle);
    expect(detailsEl).toHaveAttribute("open");
  });

  it("shows empty variety section without long paragraphs for bacterial disease", async () => {
    // Override the report fixture to use empty resistant_varieties (bacterial spot)
    const bacterialReport = {
      ...reportFixture,
      phases: {
        ...reportFixture.phases,
        disease_information: {
          ...reportFixture.phases.disease_information,
          resistant_varieties: [],
        },
      },
    };
    apiMock.caseReport.mockResolvedValueOnce(bacterialReport);

    render(<CaseWorkspace arabic={false} />);

    await waitFor(() => expect(screen.getByText("Early blight")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Early blight"));

    await waitFor(() => expect(screen.getByText("Generated report")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /1\. Disease Information/ }));

    // Must show empty state with short messages — no long paragraph
    await waitFor(() => expect(screen.getByText("No verified match")).toBeInTheDocument());
    expect(screen.getByText(/No verified disease-specific resistant variety found/i)).toBeInTheDocument();
    expect(screen.getByText(/Resistant varieties are for future planting only/i)).toBeInTheDocument();

    // Must NOT show the old long paragraph
    expect(screen.queryByText(/current source table/i)).not.toBeInTheDocument();
    // No "View variety details" toggle when empty
    expect(screen.queryByText(/View variety details/i)).not.toBeInTheDocument();
  });

  it("renders Arabic variety section without English mixed into headings", async () => {
    render(<CaseWorkspace arabic />);

    await waitFor(() => expect(screen.getByText("Early blight")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Early blight"));

    await waitFor(() => expect(screen.getByText("تقرير مولد")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /1\. معلومات المرض/ }));

    // Arabic compact count line must be visible (e.g. "2 أصناف — لا يوجد موثق في مصر")
    await waitFor(() => expect(screen.getByText(/\d+ أصناف/)).toBeInTheDocument());

    // Arabic prevention warning shown
    expect(screen.getByText(/الأصناف المقاومة تقلل خطر المستقبل/i)).toBeInTheDocument();

    // Arabic toggle label shown
    expect(screen.getByText("عرض تفاصيل الأصناف")).toBeInTheDocument();

    // In Arabic mode, the English section title "Resistant variety options" must NOT be shown
    // (it shows "خيارات الأصناف المقاومة" instead)
    expect(screen.queryByText("Resistant variety options")).not.toBeInTheDocument();
  });

  it("renders Arabic chrome and surfaces report failures", async () => {
    apiMock.caseReport.mockRejectedValueOnce(new Error("Case service unavailable"));

    render(<CaseWorkspace arabic />);

    await waitFor(() => expect(screen.getByText("مساحة الحالة")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Early blight"));

    await waitFor(() => expect(screen.getByText("Case service unavailable")).toBeInTheDocument());
    expect(screen.getByText("تقرير زراعي من الصورة فقط")).toBeInTheDocument();
  });
});
