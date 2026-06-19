import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Coins,
  Download,
  FileText,
  History,
  Leaf,
  LoaderCircle,
  MapPin,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api";
import type { CropCase, SystemReport } from "../types";

type PhaseIndex = 1 | 2 | 3 | 4 | 5 | 6;

function label(arabic: boolean, en: string, ar: string) {
  return arabic ? ar : en;
}

function prettyStatus(status: string, arabic: boolean) {
  const text = status.replaceAll("_", " ");
  if (!arabic) return text;
  return {
    draft: "مسودة",
    "collecting evidence": "جمع أدلة",
    "diagnosis ready": "تشخيص جاهز",
    consulting: "استشارة",
    "protection ready": "حماية جاهزة",
    "treatment ready": "علاج جاهز",
    "economics ready": "تكلفة جاهزة",
    "prediction ready": "توقع جاهز",
    "recommendation ready": "توصية جاهزة",
    "report ready": "تقرير جاهز",
    "needs expert": "يحتاج خبير",
    closed: "مغلق",
    failed: "فشل",
  }[text] || text;
}

function fmt(value: number, arabic: boolean, digits = 0) {
  return value.toLocaleString(arabic ? "ar-EG" : "en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtOptionalNumber(value: number | null | undefined, arabic: boolean, digits = 0) {
  if (value == null || Number.isNaN(value)) {
    return label(arabic, "n/a", "غير متاح");
  }
  return fmt(value, arabic, digits);
}

function fmtRange(low: number | null | undefined, high: number | null | undefined, arabic: boolean, unit = "") {
  if (low == null || high == null) {
    return label(arabic, "n/a", "غير متاح");
  }
  const suffix = unit ? (unit === "%" ? "%" : ` ${unit}`) : "";
  return `${fmt(low, arabic)} - ${fmt(high, arabic)}${suffix}`;
}

function renderBullets(items: string[], arabic: boolean) {
  return (
    <ul style={{ margin: 0, paddingInlineStart: 18, display: "grid", gap: 6, color: "#c9ded4", lineHeight: 1.6 }}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function renderValue(value: string | number | null | undefined, unit: string, arabic: boolean) {
  if (value == null) {
    return label(arabic, "n/a", "غير متاح");
  }
  const base = typeof value === "number" ? fmt(value, arabic) : value;
  if (!unit) return base;
  return unit === "%" ? `${base}%` : `${base} ${unit}`;
}

function renderCompactValue(
  item: { value: string | number | null; unit: string },
  arabic: boolean
) {
  return renderValue(item.value, item.unit, arabic);
}

function safeSourceType(value: string) {
  return value === "live" || value === "official" || value === "admin_table" || value === "csv_fallback" || value === "estimated_range" || value === "generated"
    ? value
    : "generated";
}

function getPriceRange(prices: any[] | undefined, item: string, fallbackLow: number, fallbackHigh: number) {
  const price = prices?.find((p: any) => p.item === item);
  return {
    low: price ? price.low_egp : fallbackLow,
    high: price ? price.high_egp : fallbackHigh
  };
}

function calculateCostBenefitByTreatment(
  report: SystemReport,
  selectedTreatmentId: string,
  areaScenario: any
) {
  const area = areaScenario.area_feddan;
  const home = areaScenario.key === "home_garden";
  const revenueLow = areaScenario.revenue_egp.low;
  const revenueHigh = areaScenario.revenue_egp.high;
  const lossLow = areaScenario.loss_without_action_egp.low;
  const lossHigh = areaScenario.loss_without_action_egp.high;

  const prices = report.cost_estimate?.prices_used;
  const pest = report.disease_class?.toLowerCase() === "pest" || report.primary_detected_disease?.name_en?.toLowerCase().includes("mite");
  const chemLow = getPriceRange(prices, pest ? "insecticide" : "contact_fungicide", pest ? 150 : 120, pest ? 450 : 280);
  const chemHigh = getPriceRange(prices, pest ? "insecticide" : "systemic_fungicide", pest ? 150 : 250, pest ? 450 : 600);
  const labor = getPriceRange(prices, "labor", 150, 400);
  const sprayer = getPriceRange(prices, "sprayer_use", 50, 150);
  const waterFuel = getPriceRange(prices, "water_fuel", 60, 180);
  const homeInputs = getPriceRange(prices, "home_garden_inputs", 100, 600);

  const perAppLow = chemLow.low + labor.low + sprayer.low + waterFuel.low;
  const perAppHigh = chemHigh.high + labor.high + sprayer.high + waterFuel.high;

  const sev = report.severity;
  const lossLowPct = sev?.estimated_yield_loss_low_percent ?? 8.0;
  const lossHighPct = sev?.estimated_yield_loss_high_percent ?? 20.0;
  const residualLossPercent = 5.0;
  const avoidableLow = Math.max(0.0, lossLowPct - residualLossPercent) / 100.0;
  const avoidableHigh = Math.max(0.0, lossHighPct - residualLossPercent) / 100.0;

  let spraysLow = 2;
  let spraysHigh = 4;
  let costLow = 0;
  let costHigh = 0;
  let laborTotalLow = 0;
  let laborTotalHigh = 0;

  if (selectedTreatmentId === "confirm_first") {
    spraysLow = spraysHigh = 0;
    costLow = home ? 50.0 : 150.0;
    costHigh = home ? 100.0 : 300.0;
    laborTotalLow = laborTotalHigh = 0.0;
  } else if (selectedTreatmentId === "sanitation_only") {
    spraysLow = spraysHigh = 0;
    costLow = costHigh = 0.0;
    laborTotalLow = laborTotalHigh = 0.0;
  } else if (selectedTreatmentId === "prevention_only") {
    spraysLow = 1;
    spraysHigh = 2;
    if (home) {
      costLow = homeInputs.low * 0.5;
      costHigh = homeInputs.high * 0.5;
      laborTotalLow = laborTotalHigh = 0.0;
    } else {
      costLow = perAppLow * 0.5 * spraysLow * area;
      costHigh = perAppHigh * 0.5 * spraysHigh * area;
      laborTotalLow = labor.low * spraysLow * area;
      laborTotalHigh = labor.high * spraysHigh * area;
    }
  } else if (selectedTreatmentId === "strongest") {
    spraysLow = 3;
    spraysHigh = 5;
    if (home) {
      costLow = homeInputs.low * 1.3;
      costHigh = homeInputs.high * 1.3;
      laborTotalLow = laborTotalHigh = 0.0;
    } else {
      costLow = perAppLow * 1.3 * spraysLow * area;
      costHigh = perAppHigh * 1.3 * spraysHigh * area;
      laborTotalLow = labor.low * spraysLow * area;
      laborTotalHigh = labor.high * spraysHigh * area;
    }
  } else { // balanced or custom
    spraysLow = 2;
    spraysHigh = 4;
    if (home) {
      costLow = homeInputs.low;
      costHigh = homeInputs.high;
      laborTotalLow = laborTotalHigh = 0.0;
    } else {
      costLow = perAppLow * spraysLow * area;
      costHigh = perAppHigh * spraysHigh * area;
      laborTotalLow = labor.low * spraysLow * area;
      laborTotalHigh = labor.high * spraysHigh * area;
    }
  }

  // Saved revenue
  let savedLow = 0;
  let savedHigh = 0;
  if (selectedTreatmentId === "confirm_first") {
    savedLow = savedHigh = 0.0;
  } else if (selectedTreatmentId === "sanitation_only") {
    savedLow = lossLow * 0.30;
    savedHigh = lossHigh * 0.30;
  } else if (selectedTreatmentId === "prevention_only") {
    savedLow = revenueLow * avoidableLow * 0.50;
    savedHigh = revenueHigh * avoidableHigh * 0.50;
  } else if (selectedTreatmentId === "strongest") {
    savedLow = revenueLow * avoidableLow * 0.95;
    savedHigh = revenueHigh * avoidableHigh * 0.95;
  } else if (selectedTreatmentId === "custom") {
    savedLow = revenueLow * avoidableLow * 0.80;
    savedHigh = revenueHigh * avoidableHigh * 0.80;
  } else { // balanced
    savedLow = revenueLow * avoidableLow * 0.85;
    savedHigh = revenueHigh * avoidableHigh * 0.85;
  }

  const netLow = savedLow - costHigh;
  const netHigh = savedHigh - costLow;

  let worth: "likely_worth" | "maybe_not_worth" | "ask_engineer" = "ask_engineer";
  let recEn = "";
  let recAr = "";

  const severityLabel = report.severity?.severity_label || "unknown";

  if (home) {
    worth = "likely_worth";
    if (selectedTreatmentId === "confirm_first") {
      recEn = "Confirm first: check underside of leaves; a small garden check costs very little.";
      recAr = "أكد أولاً: افحص الورقة من تحت؛ فحص الجنينة الصغيرة مش مكلف.";
    } else if (selectedTreatmentId === "sanitation_only") {
      recEn = "Pick off and bin spotted leaves by hand first; a small garden rarely needs a paid spray.";
      recAr = "شيل الورق المبقّع باليد الأول؛ الجنينة الصغيرة نادرًا ما تحتاج رشّة بفلوس.";
    } else {
      recEn = "Apply low-risk garden treatments only if symptoms persist.";
      recAr = "استخدم معالجات جنينة خفيفة إذا استمرت الأعراض.";
    }
  } else if (selectedTreatmentId === "confirm_first") {
    worth = "ask_engineer";
    recEn = "Hold chemical spending and confirm the diagnosis before buying anything.";
    recAr = "أوقف الصرف الكيميائي وتأكد من التشخيص قبل الشراء.";
  } else if (selectedTreatmentId === "sanitation_only") {
    worth = netLow > 0 ? "likely_worth" : "ask_engineer";
    recEn = "Sanitation program: manual hygiene saves yield with zero chemical purchase cost.";
    recAr = "تنظيف الحقل: النظافة اليدوية توفر المحصول بدون تكلفة شراء كيماويات.";
  } else if (netHigh <= 0) {
    worth = "maybe_not_worth";
    recEn = "The spray may not pay off at this size/severity — monitor first and re-check in a few days.";
    recAr = "الرش ممكن ما يستاهلش في الحجم/الخطورة دي — راقب الأول وافحص تاني بعد كام يوم.";
  } else if (netLow > 0 && (severityLabel === "moderate" || severityLabel === "high" || severityLabel === "severe")) {
    worth = "likely_worth";
    recEn = "Protecting the crop is likely worth it here — run a planned spray programme and keep records.";
    recAr = "حماية المحصول غالبًا بتستاهل هنا — اعمل برنامج رش مخطط وسجّل المواعيد.";
  } else {
    worth = "ask_engineer";
    recEn = "Borderline economics — confirm the disease and costs with an agricultural engineer before spraying.";
    recAr = "العائد على الحدّ — أكّد المرض والتكلفة مع مهندس زراعي قبل الرش.";
  }

  return {
    ...areaScenario,
    sprays: {
      ...areaScenario.sprays,
      low: spraysLow,
      high: spraysHigh,
      measured_zero: home || spraysLow === 0
    },
    treatment_cost_egp: {
      ...areaScenario.treatment_cost_egp,
      low: Math.round(costLow * 100) / 100,
      high: Math.round(costHigh * 100) / 100,
      measured_zero: costLow === 0.0
    },
    labor_cost_egp: {
      ...areaScenario.labor_cost_egp,
      low: Math.round(laborTotalLow * 100) / 100,
      high: Math.round(laborTotalHigh * 100) / 100,
      measured_zero: home || laborTotalLow === 0.0
    },
    saved_with_action_egp: {
      ...areaScenario.saved_with_action_egp,
      low: Math.round(savedLow * 100) / 100,
      high: Math.round(savedHigh * 100) / 100,
      measured_zero: savedLow === 0.0
    },
    net_benefit_egp: {
      ...areaScenario.net_benefit_egp,
      low: Math.round(netLow * 100) / 100,
      high: Math.round(netHigh * 100) / 100,
      measured_zero: netLow === 0.0
    },
    worth_spraying: worth,
    recommendation_en: recEn,
    recommendation_ar: recAr
  };
}

export function CaseWorkspace({
  arabic,
  initialCaseId,
  onClearInitialCaseId,
  geoCoords,
  previewUrl,
}: {
  arabic: boolean;
  initialCaseId?: string | null;
  onClearInitialCaseId?: () => void;
  geoCoords?: { lat: number; lng: number } | null;
  previewUrl?: string;
}) {
  const [cases, setCases] = useState<CropCase[]>([]);
  const [active, setActive] = useState<CropCase | null>(null);
  const [report, setReport] = useState<SystemReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<PhaseIndex>(1);
  const [selectedTreatmentId, setSelectedTreatmentId] = useState<string>("");

  const treatmentOptions = report?.phases?.treatment?.treatment_options ?? [];

  useEffect(() => {
    if (report) {
      setSelectedTreatmentId(report.selected_treatment_id || report.phases.treatment.selected_mode_key || "balanced");
    } else {
      setSelectedTreatmentId("");
    }
  }, [report]);

  const phaseTabs = useMemo(
    () => [
      { id: 1 as PhaseIndex, label: label(arabic, "1. Disease Information", "1. معلومات المرض"), icon: Leaf },
      { id: 2 as PhaseIndex, label: label(arabic, "2. Protection", "2. الوقاية"), icon: ShieldCheck },
      { id: 3 as PhaseIndex, label: label(arabic, "3. Consulting", "3. الاستشارة"), icon: MessageSquare },
      { id: 4 as PhaseIndex, label: label(arabic, "4. Treatment", "4. العلاج"), icon: Activity },
      { id: 5 as PhaseIndex, label: label(arabic, "5. Cost & Forecast", "5. التكلفة والتوقع"), icon: BarChart3 },
      { id: 6 as PhaseIndex, label: label(arabic, "6. Conclusion", "6. الخلاصة"), icon: FileText },
    ],
    [arabic]
  );

  useEffect(() => {
    void refreshCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!initialCaseId) return;
    void loadCaseById(initialCaseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCaseId]);

  useEffect(() => {
    if (!active) {
      setReport(null);
      return;
    }
    setActiveTab(1);
    void loadReport(active.case_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active?.case_id]);

  async function withBusy<T>(action: () => Promise<T>): Promise<T | null> {
    setLoading(true);
    setError("");
    try {
      return await action();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Request failed");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function refreshCases() {
    await withBusy(async () => {
      const items = await api.cases();
      const list = Array.isArray(items) ? items : [];
      setCases(list);
      try {
        const savedId = localStorage.getItem("agrovision_active_case_id");
        if (savedId && list.length > 0 && !initialCaseId) {
          const matched = list.find((item) => item.case_id === savedId);
          if (matched) {
            setActive(matched);
          }
        }
      } catch {
        // ignore storage errors
      }
    });
  }

  async function loadCaseById(caseId: string) {
    const item = await withBusy(() => api.getCase(caseId));
    if (!item) return;
    setActive(item);
    try {
      localStorage.setItem("agrovision_active_case_id", item.case_id);
    } catch {
      // ignore storage errors
    }
    onClearInitialCaseId?.();
  }

  async function loadReport(caseId: string) {
    const value = await withBusy(() => api.caseReport(caseId));
    if (value) {
      setReport(value);
    }
  }

  function selectCase(item: CropCase) {
    setActive(item);
    try {
      localStorage.setItem("agrovision_active_case_id", item.case_id);
    } catch {
      // ignore storage errors
    }
    onClearInitialCaseId?.();
  }

  function summaryCard(
    titleEn: string,
    titleAr: string,
    value: string | number,
    detail: string,
    accent = "#b9e978"
  ) {
    return (
      <div
        style={{
          padding: "14px",
          borderRadius: "14px",
          border: "1px solid rgba(255,255,255,.08)",
          background: "rgba(255,255,255,.025)",
          display: "grid",
          gap: "8px",
          minHeight: "110px",
        }}
      >
        <span style={{ color: "#88a99a", fontSize: "11px", textTransform: "uppercase", letterSpacing: ".08em" }}>
          {label(arabic, titleEn, titleAr)}
        </span>
        <strong style={{ color: accent, fontSize: "18px", letterSpacing: "-.03em" }}>{value}</strong>
        <span style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.5 }}>{detail}</span>
      </div>
    );
  }

  function renderSourceCard(source: SystemReport["source_metadata"][number]) {
    const sourceType = safeSourceType(source.source_type);
    return (
      <div
        key={source.key}
        style={{
          padding: "12px",
          borderRadius: "12px",
          border: "1px solid rgba(255,255,255,.08)",
          background: "rgba(255,255,255,.02)",
          display: "grid",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", alignItems: "start" }}>
          <strong style={{ color: "#e9f5ef", fontSize: "13px" }}>{label(arabic, source.title, source.title)}</strong>
          <span className="badge" style={{ background: "rgba(185,236,97,.1)", color: "#b9e978", border: "1px solid rgba(185,236,97,.16)" }}>
            {sourceType}
          </span>
        </div>
        <span style={{ color: "#88a99a", fontSize: "11px" }}>{source.organization}</span>
        <span style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>{arabic ? source.note_ar : source.note_en}</span>
        {source.url && (
          <a href={source.url} target="_blank" rel="noreferrer" style={{ color: "#b9e978", fontSize: "11px", textDecoration: "none" }}>
            {label(arabic, "Open source", "فتح المصدر")}
          </a>
        )}
      </div>
    );
  }

  function renderScenarioCase(caseItem: SystemReport["phases"]["disease_information"]["scenario_cases"][number]) {
    return (
      <article
        key={caseItem.key}
        className="treatment-option-card"
      >
        <div>
          <strong style={{ color: "#cdf58a", fontSize: "13px" }}>{arabic ? caseItem.name_ar : caseItem.name_en}</strong>
          <p style={{ margin: "6px 0 0", color: "#bcd8ca", fontSize: "12px", lineHeight: 1.6 }}>{arabic ? caseItem.summary_ar : caseItem.summary_en}</p>
        </div>
        <div style={{ display: "grid", gap: "10px" }}>
          {caseItem.sections.map((section) => (
            <section key={section.title_en} style={{ padding: "10px", borderRadius: "12px", background: "rgba(255,255,255,.015)" }}>
              <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{arabic ? section.title_ar : section.title_en}</strong>
              {renderBullets(arabic ? section.bullets_ar : section.bullets_en, arabic)}
            </section>
          ))}
        </div>
      </article>
    );
  }

  function renderQuestionAnswer(item: SystemReport["phases"]["consulting"]["auto_questions_with_answers"][number]) {
    return (
      <article
        key={item.key}
        style={{
          padding: "14px",
          borderRadius: "14px",
          border: "1px solid rgba(255,255,255,.08)",
          background: "rgba(255,255,255,.02)",
          display: "grid",
          gap: "8px",
        }}
      >
        <strong style={{ color: "#e9f5ef", fontSize: "13px", lineHeight: 1.45 }}>
          {arabic ? item.question_ar : item.question_en}
        </strong>
        <p style={{ margin: 0, color: "#c9ded4", fontSize: "12px", lineHeight: 1.65 }}>
          {arabic ? item.answer_ar : item.answer_en}
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div style={{ padding: "10px", borderRadius: "12px", background: "rgba(255,255,255,.015)" }}>
            <span style={{ color: "#88a99a", fontSize: "10px", textTransform: "uppercase" }}>
              {label(arabic, "Why it matters", "لماذا يهم")}
            </span>
            <p style={{ margin: "4px 0 0", color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
              {arabic ? item.why_it_matters_ar : item.why_it_matters_en}
            </p>
          </div>
          <div style={{ padding: "10px", borderRadius: "12px", background: "rgba(255,255,255,.015)" }}>
            <span style={{ color: "#88a99a", fontSize: "10px", textTransform: "uppercase" }}>
              {label(arabic, "Decision shift", "تغيير القرار")}
            </span>
            <p style={{ margin: "4px 0 0", color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
              {arabic ? item.decision_change_ar : item.decision_change_en}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {(arabic ? item.scenario_notes_ar : item.scenario_notes_en).map((note) => (
            <span
              key={note}
              style={{
                padding: "5px 8px",
                borderRadius: "999px",
                border: "1px solid rgba(185,236,97,.18)",
                background: "rgba(185,236,97,.07)",
                color: "#dff4e9",
                fontSize: "11px",
              }}
            >
              {note}
            </span>
          ))}
        </div>
      </article>
    );
  }

  function renderCandidateInsight(item: SystemReport["phases"]["disease_information"]["top_candidates"][number]) {
    return (
      <article
        key={`${item.rank}-${item.disease_name_en}`}
        style={{
          padding: "12px",
          borderRadius: "12px",
          background: "rgba(255,255,255,.02)",
          border: "1px solid rgba(255,255,255,.08)",
          display: "grid",
          gap: "8px",
        }}
      >
        <strong style={{ color: "#e9f5ef", fontSize: "13px" }}>
          {item.rank}. {arabic ? item.disease_name_ar : item.disease_name_en}
        </strong>
        <div style={{ color: "#cdf58a", fontSize: "12px" }}>
          {label(arabic, "Confidence", "الثقة")}: {fmt(Math.round(item.confidence * 100), arabic)}%
        </div>
        <div style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
          {arabic ? item.source_note_ar : item.source_note_en}
        </div>
        {item.support_en.length > 0 && (
          <div style={{ display: "grid", gap: "6px" }}>
            <strong style={{ color: "#88a99a", fontSize: "11px" }}>{label(arabic, "Why it appears", "لماذا ظهر")}</strong>
            {renderBullets(arabic ? item.support_ar : item.support_en, arabic)}
          </div>
        )}
      </article>
    );
  }

  function renderVarietyRow(item: SystemReport["phases"]["disease_information"]["resistant_varieties"][number]) {
    const availabilityBadge = {
      verified_in_egypt: <span className="badge" style={{ background: "rgba(185,236,97,.1)", color: "#b9e978", border: "1px solid rgba(185,236,97,.2)", fontSize: "10px" }}>{label(arabic, "Verified in Egypt", "موثق في مصر")}</span>,
      not_verified_in_egypt: <span className="badge" style={{ background: "rgba(242,207,152,.1)", color: "#f2cf98", border: "1px solid rgba(242,207,152,.2)", fontSize: "10px" }}>{label(arabic, "Not verified in Egypt", "غير موثق في مصر")}</span>,
      unknown: <span className="badge" style={{ background: "rgba(255,255,255,.06)", color: "#88a99a", border: "1px solid rgba(255,255,255,.1)", fontSize: "10px" }}>{label(arabic, "Availability unknown", "التوفر غير معروف")}</span>,
    }[item.egypt_availability_status];
    return (
      <div
        key={`${item.name_en}-${item.resistance_codes_en}`}
        style={{
          padding: "10px 12px",
          borderRadius: "10px",
          background: "rgba(255,255,255,.02)",
          border: "1px solid rgba(255,255,255,.06)",
          display: "grid",
          gridTemplateColumns: "1fr auto",
          gap: "6px 12px",
          alignItems: "start",
        }}
      >
        <div>
          <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{arabic ? item.name_ar : item.name_en}</strong>
          <span style={{ color: "#88a99a", fontSize: "11px", display: "block", marginTop: "2px" }}>
            {arabic ? item.resistance_codes_ar : item.resistance_codes_en}
          </span>
          <span style={{ color: "#bcd8ca", fontSize: "11px", display: "block", marginTop: "4px", lineHeight: 1.4 }}>
            {arabic ? item.farmer_wording_ar : item.farmer_wording_en}
          </span>
        </div>
        <div style={{ display: "grid", gap: "4px", textAlign: "right" }}>
          {availabilityBadge}
          <span style={{ color: "#88a99a", fontSize: "10px" }}>{item.source_organization}</span>
        </div>
      </div>
    );
  }

  function renderResistantVarietySection(varieties: SystemReport["phases"]["disease_information"]["resistant_varieties"]) {
    const verifiedCount = varieties.filter((v) => v.egypt_availability_status === "verified_in_egypt").length;
    const statusBadge = verifiedCount > 0
      ? <span className="badge" style={{ background: "rgba(185,236,97,.1)", color: "#b9e978", border: "1px solid rgba(185,236,97,.2)", fontSize: "10px" }}>{label(arabic, "Verified for disease", "موثق للمرض")}</span>
      : <span className="badge" style={{ background: "rgba(255,255,255,.06)", color: "#88a99a", border: "1px solid rgba(255,255,255,.1)", fontSize: "10px" }}>{label(arabic, "Reference only", "مرجعي فقط")}</span>;

    const countLine = arabic
      ? `${varieties.length} أصناف — ${verifiedCount > 0 ? `${verifiedCount} موثق في مصر` : "لا يوجد موثق في مصر"}`
      : `${varieties.length} ${varieties.length === 1 ? "variety" : "varieties"} — ${verifiedCount > 0 ? `${verifiedCount} verified in Egypt` : "none verified in Egypt"}`;

    return (
      <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)", border: "1px solid rgba(255,255,255,.06)", display: "grid", gap: "8px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#cdf58a", fontSize: "12px", fontWeight: 600 }}>{countLine}</span>
          {statusBadge}
        </div>
        <p style={{ margin: 0, color: "#f2cf98", fontSize: "11px", lineHeight: 1.5 }}>
          {label(arabic,
            "Resistant varieties reduce future risk — they do not cure infected plants.",
            "الأصناف المقاومة تقلل خطر المستقبل — لا تعالج النبات المصاب حاليًا."
          )}
        </p>
        <p style={{ margin: 0, color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
          {label(arabic,
            "Ask your seed supplier for resistance codes and verify local Egypt stock before buying.",
            "اسأل مورد البذور عن أكواد المقاومة وتأكد من توفرها في مصر قبل الشراء."
          )}
        </p>
        <details style={{ marginTop: "4px" }}>
          <summary style={{ cursor: "pointer", color: "#88a99a", fontSize: "12px", outline: "none", userSelect: "none", listStyle: "none" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
              <span>{"▸"}</span>
              {label(arabic, "View variety details", "عرض تفاصيل الأصناف")}
            </span>
          </summary>
          <div style={{ marginTop: "8px", display: "grid", gap: "6px" }}>
            {varieties.map(renderVarietyRow)}
          </div>
        </details>
      </div>
    );
  }

  function renderEmptyVarietySection() {
    return (
      <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)", border: "1px solid rgba(255,255,255,.06)", display: "grid", gap: "6px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#88a99a", fontSize: "12px" }}>
            {label(arabic, "No verified match", "لا يوجد تطابق موثق")}
          </span>
          <span className="badge" style={{ background: "rgba(255,255,255,.04)", color: "#88a99a", border: "1px solid rgba(255,255,255,.08)", fontSize: "10px" }}>
            {label(arabic, "Not in sources", "غير موجود في المصادر")}
          </span>
        </div>
        <p style={{ margin: 0, color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
          {label(arabic,
            "No verified disease-specific resistant variety found for this disease in current sources.",
            "لا يوجد صنف مقاوم مؤكد لهذا المرض في المصادر الحالية."
          )}
        </p>
        <p style={{ margin: 0, color: "#f2cf98", fontSize: "11px", lineHeight: 1.5 }}>
          {label(arabic,
            "Resistant varieties are for future planting only — ask your seed supplier for resistance codes.",
            "الأصناف المقاومة للزراعة القادمة فقط — اسأل مورد البذور عن أكواد المقاومة."
          )}
        </p>
      </div>
    );
  }

  function renderTreatmentOption(item: SystemReport["phases"]["treatment"]["treatment_options"][number], selectedModeKey: string) {
    const selected = item.key === selectedModeKey;

    let chipText = label(arabic, "Allowed", "مسموح");
    let chipStyle = { background: "rgba(185,236,97,.1)", color: "#b9e978", border: "1px solid rgba(185,236,97,.2)" };
    
    if (item.requires_apc_verification) {
      chipText = label(arabic, "locked until APC verification", "مغلق لحين التحقق من لجنة المبيدات (APC)");
      chipStyle = { background: "rgba(242,207,152,.1)", color: "#f2cf98", border: "1px solid rgba(242,207,152,.2)" };
    } else if (item.requires_engineer_confirmation) {
      chipText = label(arabic, "engineer confirmation recommended", "يوصى بتأكيد المهندس الزراعي");
      chipStyle = { background: "rgba(141,195,244,.1)", color: "#8dc3f4", border: "1px solid rgba(141,195,244,.2)" };
    } else if (item.key === "strongest" || item.key === "balanced" || item.key === "prevention_only") {
      chipText = label(arabic, "caution", "تنبيه");
      chipStyle = { background: "rgba(239,68,68,.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,.2)" };
    }

    return (
      <article
        key={item.key}
        className={`treatment-option-card ${selected ? "selected" : ""}`}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "start" }}>
          <strong style={{ color: "#e9f5ef", fontSize: "13px" }}>{arabic ? item.label_ar : item.label_en}</strong>
          {selected && <span className="badge">{label(arabic, "Selected", "المختار")}</span>}
        </div>
        <div style={{ color: "#c9ded4", fontSize: "12px", lineHeight: 1.55 }}>{arabic ? item.summary_ar : item.summary_en}</div>
        <div style={{ color: "#cdf58a", fontSize: "12px" }}>
          {label(arabic, "Cost", "التكلفة")}: {fmtRange(item.cost_egp.low, item.cost_egp.high, arabic, "EGP")}
        </div>
        <div style={{ color: "#88a99a", fontSize: "11px" }}>
          {label(arabic, "Budget band", "نطاق الميزانية")}: {fmtRange(item.budget_egp.low, item.budget_egp.high, arabic, "EGP")}
        </div>
        <div style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
          {label(arabic, "Benefit", "الفائدة")}: {arabic ? item.expected_benefit_ar : item.expected_benefit_en}
        </div>
        <div style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
          {label(arabic, "Risk", "المخاطر")}: {arabic ? item.risk_ar : item.risk_en}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          <span className="badge" style={chipStyle}>{chipText}</span>
        </div>
        <details style={{ marginTop: "6px" }}>
          <summary style={{ cursor: "pointer", color: "#88a99a", fontSize: "11px", outline: "none" }}>
            {label(arabic, "View safety gate & label info", "عرض تفاصيل الأمان والملصق")}
          </summary>
          <div style={{ marginTop: "6px", display: "grid", gap: "4px", paddingLeft: "8px", borderLeft: "1px solid rgba(255,255,255,.08)" }}>
            <div style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
              {label(arabic, "APC gate", "بوابة APC")}: {arabic ? item.apc_gate_ar : item.apc_gate_en}
            </div>
            <div style={{ color: "#88a99a", fontSize: "11px", lineHeight: 1.5 }}>
              {arabic ? item.source_note_ar : item.source_note_en}
            </div>
          </div>
        </details>
        {arabic && item.farmer_wording_ar && (
          <div style={{ color: "#c9ded4", fontSize: "12px", lineHeight: 1.55 }}>{item.farmer_wording_ar}</div>
        )}
      </article>
    );
  }

  function renderSelectedPhase() {
    if (!report) return null;

    const diseasePhase = report.phases.disease_information;
    const protectionPhase = report.phases.protection;
    const consultingPhase = report.phases.consulting;
    const treatmentPhase = report.phases.treatment;
    const costPhase = report.phases.cost_forecast;
    const conclusionPhase = report.phases.conclusion_recommendation;
    const diseaseTopCandidates = diseasePhase.top_candidates ?? [];
    const diseaseResistantVarieties = diseasePhase.resistant_varieties ?? [];
    const costComparisonOptions = costPhase.treatment_comparison ?? [];
    const selectedTreatmentModeKey = selectedTreatmentId || treatmentPhase.selected_mode_key || "";
    const selectedComparisonModeKey = selectedTreatmentId || costPhase.selected_mode_key || "";
    const selectedConclusionModeKey = conclusionPhase.selected_mode_key ?? "";
    const selectedTreatmentOption = treatmentOptions.find((item) => item.key === selectedTreatmentModeKey) ?? null;
    const selectedComparisonOption = costComparisonOptions.find((item) => item.key === selectedComparisonModeKey) ?? null;
    const selectedConclusionOption = selectedConclusionModeKey
      ? (treatmentOptions.find((item) => item.key === selectedConclusionModeKey) ?? selectedTreatmentOption)
      : selectedTreatmentOption;

    const recalculatedCases = (() => {
      const baseCases = costPhase.area_range_cases ?? [];
      const defaultId = report.selected_treatment_id || report.phases.treatment.selected_mode_key || "balanced";
      if (!selectedTreatmentId || selectedTreatmentId === defaultId) return baseCases;
      return baseCases.map((item) => calculateCostBenefitByTreatment(report, selectedTreatmentId, item));
    })();

    const recalculatedNetBenefit = (() => {
      if (!selectedTreatmentId) return null;
      const defaultId = report.selected_treatment_id || report.phases.treatment.selected_mode_key || "balanced";
      if (selectedTreatmentId === defaultId) {
        return {
          low: report.cost_benefit?.net_benefit_egp?.low ?? 0,
          high: report.cost_benefit?.net_benefit_egp?.high ?? 0
        };
      }
      const area = report.cost_estimate?.area_feddan_assumed ?? 1.0;
      const prices = report.cost_estimate?.prices_used;
      const yieldRef = getPriceRange(prices, "expected_yield", 12000, 22000);
      const priceRef = getPriceRange(prices, "tomato_farmgate", 5.0, 12.0);
      
      const eyLow = yieldRef.low * area;
      const eyHigh = yieldRef.high * area;
      const revenueLow = eyLow * priceRef.low;
      const revenueHigh = eyHigh * priceRef.high;
      
      const sev = report.severity;
      const lossLowPct = sev?.estimated_yield_loss_low_percent ?? 8.0;
      const lossHighPct = sev?.estimated_yield_loss_high_percent ?? 20.0;
      const lossLow = revenueLow * (lossLowPct / 100.0);
      const lossHigh = revenueHigh * (lossHighPct / 100.0);
      
      const residualLossPercent = 5.0;
      const avoidableLow = Math.max(0.0, lossLowPct - residualLossPercent) / 100.0;
      const avoidableHigh = Math.max(0.0, lossHighPct - residualLossPercent) / 100.0;
      
      let spraysLow = 2, spraysHigh = 4;
      if (selectedTreatmentId === "confirm_first" || selectedTreatmentId === "sanitation_only") {
        spraysLow = spraysHigh = 0;
      } else if (selectedTreatmentId === "prevention_only") {
        spraysLow = 1; spraysHigh = 2;
      } else if (selectedTreatmentId === "strongest") {
        spraysLow = 3; spraysHigh = 5;
      }
      
      let costLow = 0, costHigh = 0;
      const home = report.farm_type === "home_garden" || area <= 0.05;
      const labor = getPriceRange(prices, "labor", 150, 400);
      const sprayer = getPriceRange(prices, "sprayer_use", 50, 150);
      const waterFuel = getPriceRange(prices, "water_fuel", 60, 180);
      const homeInputs = getPriceRange(prices, "home_garden_inputs", 100, 600);
      const pest = report.disease_class?.toLowerCase() === "pest" || report.primary_detected_disease?.name_en?.toLowerCase().includes("mite");
      const chemLow = getPriceRange(prices, pest ? "insecticide" : "contact_fungicide", pest ? 150 : 120, pest ? 450 : 280);
      const chemHigh = getPriceRange(prices, pest ? "insecticide" : "systemic_fungicide", pest ? 150 : 250, pest ? 450 : 600);
      const perAppLow = chemLow.low + labor.low + sprayer.low + waterFuel.low;
      const perAppHigh = chemHigh.high + labor.high + sprayer.high + waterFuel.high;

      if (selectedTreatmentId === "confirm_first") {
        costLow = home ? 50.0 : 150.0;
        costHigh = home ? 100.0 : 300.0;
      } else if (selectedTreatmentId === "sanitation_only") {
        costLow = costHigh = 0.0;
      } else if (selectedTreatmentId === "prevention_only") {
        if (home) {
          costLow = homeInputs.low * 0.5;
          costHigh = homeInputs.high * 0.5;
        } else {
          costLow = perAppLow * 0.5 * spraysLow * area;
          costHigh = perAppHigh * 0.5 * spraysHigh * area;
        }
      } else if (selectedTreatmentId === "strongest") {
        if (home) {
          costLow = homeInputs.low * 1.3;
          costHigh = homeInputs.high * 1.3;
        } else {
          costLow = perAppLow * 1.3 * spraysLow * area;
          costHigh = perAppHigh * 1.3 * spraysHigh * area;
        }
      } else {
        if (home) {
          costLow = homeInputs.low;
          costHigh = homeInputs.high;
        } else {
          costLow = perAppLow * spraysLow * area;
          costHigh = perAppHigh * spraysHigh * area;
        }
      }
      
      let savedLow = 0, savedHigh = 0;
      if (selectedTreatmentId === "confirm_first") {
        savedLow = savedHigh = 0.0;
      } else if (selectedTreatmentId === "sanitation_only") {
        savedLow = lossLow * 0.30;
        savedHigh = lossHigh * 0.30;
      } else if (selectedTreatmentId === "prevention_only") {
        savedLow = revenueLow * avoidableLow * 0.50;
        savedHigh = revenueHigh * avoidableHigh * 0.50;
      } else if (selectedTreatmentId === "strongest") {
        savedLow = revenueLow * avoidableLow * 0.95;
        savedHigh = revenueHigh * avoidableHigh * 0.95;
      } else if (selectedTreatmentId === "custom") {
        savedLow = revenueLow * avoidableLow * 0.80;
        savedHigh = revenueHigh * avoidableHigh * 0.80;
      } else {
        savedLow = revenueLow * avoidableLow * 0.85;
        savedHigh = revenueHigh * avoidableHigh * 0.85;
      }
      
      const netLow = savedLow - costHigh;
      const netHigh = savedHigh - costLow;
      
      return { low: netLow, high: netHigh };
    })();

    switch (activeTab) {
      case 1:
        return (
          <section className="case-panel">
            <div className="case-panel-title">
              <Leaf size={17} />
              <strong>{label(arabic, "Disease Information", "معلومات المرض")}</strong>
            </div>
            <p style={{ margin: "0 0 12px", color: "#bcd8ca", lineHeight: 1.65 }}>
              {arabic ? diseasePhase.meaning_ar : diseasePhase.meaning_en}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
              <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)" }}>
                <strong style={{ color: "#cdf58a", fontSize: "12px" }}>{label(arabic, "Leaf symptoms", "أعراض الأوراق")}</strong>
                {renderBullets(arabic ? diseasePhase.leaf_symptoms_ar : diseasePhase.leaf_symptoms_en, arabic)}
              </div>
              <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)" }}>
                <strong style={{ color: "#cdf58a", fontSize: "12px" }}>{label(arabic, "Fruit symptoms", "أعراض الثمار")}</strong>
                {renderBullets(arabic ? diseasePhase.fruit_symptoms_ar : diseasePhase.fruit_symptoms_en, arabic)}
              </div>
              <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)" }}>
                <strong style={{ color: "#cdf58a", fontSize: "12px" }}>{label(arabic, "Stem symptoms", "أعراض الساق")}</strong>
                {renderBullets(arabic ? diseasePhase.stem_symptoms_ar : diseasePhase.stem_symptoms_en, arabic)}
              </div>
            </div>
            <div style={{ marginTop: "12px", display: "grid", gap: "10px" }}>
              <div className="case-warning">
                <AlertTriangle size={16} />
                <p>{arabic ? diseasePhase.danger_ar : diseasePhase.danger_en}</p>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
                <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)" }}>
                  <strong style={{ color: "#cdf58a", fontSize: "12px" }}>{label(arabic, "Lookalikes", "أشباه المرض")}</strong>
                  {renderBullets(arabic ? diseasePhase.lookalikes_ar : diseasePhase.lookalikes_en, arabic)}
                </div>
                <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)" }}>
                  <strong style={{ color: "#cdf58a", fontSize: "12px" }}>{label(arabic, "Today check", "فحص اليوم")}</strong>
                  {renderBullets(arabic ? diseasePhase.today_check_ar : diseasePhase.today_check_en, arabic)}
                </div>
              </div>
            </div>
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
                <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)" }}>
                  <strong style={{ color: "#cdf58a", fontSize: "12px" }}>{label(arabic, "Cause type", "نوع السبب")}</strong>
                  <p style={{ margin: "6px 0 0", color: "#bcd8ca", lineHeight: 1.6 }}>
                    {arabic ? diseasePhase.cause_type_ar : diseasePhase.cause_type_en}
                  </p>
                </div>
                <div style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)" }}>
                  <strong style={{ color: "#cdf58a", fontSize: "12px" }}>{label(arabic, "Irrigation conditions", "ظروف الري")}</strong>
                  <p style={{ margin: "6px 0 0", color: "#bcd8ca", lineHeight: 1.6 }}>
                    {arabic ? diseasePhase.irrigation_conditions_ar : diseasePhase.irrigation_conditions_en}
                  </p>
                </div>
              </div>
              {diseaseTopCandidates.length > 0 && (
                <div style={{ display: "grid", gap: "10px" }}>
                  <strong style={{ color: "#dcefe5" }}>{label(arabic, "Top model candidates", "أفضل المرشحين من النموذج")}</strong>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px" }}>
                    {diseaseTopCandidates.map(renderCandidateInsight)}
                  </div>
                </div>
              )}
              <div style={{ display: "grid", gap: "10px" }}>
                <strong style={{ color: "#dcefe5" }}>{label(arabic, "Resistant variety options", "خيارات الأصناف المقاومة")}</strong>
                {diseaseResistantVarieties.length > 0
                  ? renderResistantVarietySection(diseaseResistantVarieties)
                  : renderEmptyVarietySection()}
              </div>
              <div style={{ padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Need a clearer match?", "هل تحتاج مطابقة أوضح؟")}</strong>
                <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                  {arabic ? diseasePhase.higher_accuracy_hint_ar ?? "" : diseasePhase.higher_accuracy_hint_en ?? ""}
                </p>
              </div>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Scenario examples", "سيناريوهات")} </strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
                {diseasePhase.scenario_cases.map(renderScenarioCase)}
              </div>
            </div>
          </section>
        );
      case 2:
        return (
          <section className="case-panel">
            <div className="case-panel-title">
              <ShieldCheck size={17} />
              <strong>{label(arabic, "Protection", "الوقاية")}</strong>
            </div>
            <p style={{ margin: "0 0 12px", color: "#bcd8ca", lineHeight: 1.65 }}>
              {label(
                arabic,
                "Protection is the first layer: keep leaves dry, move cleanly through the crop, and reduce splash and crowding.",
                "الوقاية هي الطبقة الأولى: حافظ على جفاف الأوراق، وتحرك داخل الزراعة بنظافة، وقلل تناثر الماء والتزاحم."
              )}
            </p>
            {renderBullets(report.protection_plan, arabic)}
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Protection scenarios", "سيناريوهات الوقاية")}</strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
                {protectionPhase.scenario_cases.map(renderScenarioCase)}
              </div>
            </div>
              <div style={{ marginTop: "14px", padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Need a clearer protection check?", "هل تحتاج فحص وقاية أوضح؟")}</strong>
                <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                {arabic ? protectionPhase.higher_accuracy_hint_ar ?? "" : protectionPhase.higher_accuracy_hint_en ?? ""}
                </p>
              </div>
          </section>
        );
      case 3:
        return (
          <section className="case-panel">
            <div className="case-panel-title">
              <MessageSquare size={17} />
              <strong>{label(arabic, "Consulting", "الاستشارة")}</strong>
            </div>
            <p style={{ margin: "0 0 12px", color: "#bcd8ca", lineHeight: 1.65 }}>
              {arabic ? report.sidebar_chatbot_context.summary_ar : report.sidebar_chatbot_context.summary_en}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
              {consultingPhase.auto_questions_with_answers.map(renderQuestionAnswer)}
            </div>
              <div style={{ marginTop: "14px", padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Need more evidence?", "هل تحتاج أدلة أكثر؟")}</strong>
                <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                {arabic ? consultingPhase.higher_accuracy_hint_ar ?? "" : consultingPhase.higher_accuracy_hint_en ?? ""}
                </p>
              </div>
          </section>
        );
      case 4:
        return (
          <section className="case-panel">
            <div className="case-panel-title">
              <Activity size={17} />
              <strong>{label(arabic, "Treatment", "العلاج")}</strong>
            </div>
            <p style={{ margin: "0 0 12px", color: "#bcd8ca", lineHeight: 1.65 }}>
              {label(
                arabic,
                "Use the non-chemical path first. The chemical path stays behind a safety gate and depends on label registration and confidence.",
                "ابدأ بالمسار غير الكيميائي أولًا. المسار الكيميائي يظل خلف بوابة أمان ويعتمد على التسجيل والثقة."
              )}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
              <div style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,.02)" }}>
                <strong style={{ color: "#cdf58a", display: "block", marginBottom: "8px" }}>{label(arabic, "Non-chemical path", "المسار غير الكيميائي")}</strong>
                {renderBullets(report.treatment_plan.non_chemical, arabic)}
              </div>
              <div style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,.02)" }}>
                <strong style={{ color: "#f2cf98", display: "block", marginBottom: "8px" }}>{label(arabic, "Chemical path", "المسار الكيميائي")}</strong>
                {renderBullets(report.treatment_plan.chemical_category_if_needed, arabic)}
              </div>
              <div style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,.02)" }}>
                <strong style={{ color: "#8dc3f4", display: "block", marginBottom: "8px" }}>{label(arabic, "Safety notes", "ملاحظات الأمان")}</strong>
                {renderBullets(report.treatment_plan.safety_notes, arabic)}
              </div>
            </div>
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Treatment scenarios", "سيناريوهات العلاج")}</strong>
              <div className="treatment-scenarios-grid">
                {treatmentPhase.scenario_cases.map(renderScenarioCase)}
              </div>
            </div>
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Treatment mode comparison", "مقارنة أوضاع العلاج")}</strong>
              <div className="treatment-scenarios-grid">
                {treatmentOptions.map((item) => renderTreatmentOption(item, selectedTreatmentModeKey))}
              </div>
              {selectedTreatmentOption && (
                <div style={{ padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                  <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Current selected mode", "الوضع المختار الحالي")}</strong>
                  <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                    {arabic ? selectedTreatmentOption.summary_ar : selectedTreatmentOption.summary_en}
                  </p>
                  <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                    {arabic ? selectedTreatmentOption.expected_benefit_ar : selectedTreatmentOption.expected_benefit_en}
                  </p>
                </div>
              )}
                <div style={{ padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                  <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Need a clearer treatment decision?", "هل تحتاج قرار علاج أوضح؟")}</strong>
                  <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                  {arabic ? treatmentPhase.higher_accuracy_hint_ar ?? "" : treatmentPhase.higher_accuracy_hint_en ?? ""}
                  </p>
                </div>
            </div>
          </section>
        );
      case 5:
        return (
          <section className="case-panel">
            <div className="case-panel-title">
              <BarChart3 size={17} />
              <strong>{label(arabic, "Cost & Forecast", "التكلفة والتوقع")}</strong>
            </div>
            <div style={{ marginBottom: "16px", display: "flex", gap: "10px", alignItems: "center" }}>
              <span style={{ color: "#cdf58a", fontSize: "14px", fontWeight: "bold" }}>
                {label(arabic, "Select Treatment Mode:", "اختر وضع العلاج:")}
              </span>
              <select
                value={selectedTreatmentId}
                onChange={(e) => setSelectedTreatmentId(e.target.value)}
                style={{
                  background: "#1f2937",
                  color: "#e5e7eb",
                  border: "1px solid rgba(255,255,255,.2)",
                  borderRadius: "8px",
                  padding: "6px 12px",
                  fontSize: "14px",
                  outline: "none",
                  cursor: "pointer"
                }}
              >
                <option value="confirm_first">{label(arabic, "Confirm first", "أكد أولاً")}</option>
                <option value="sanitation_only">{label(arabic, "Sanitation only", "تنظيف فقط")}</option>
                <option value="balanced">{label(arabic, "Balanced program", "برنامج متوازن")}</option>
                <option value="strongest">{label(arabic, "Strongest program", "البرنامج الأقوى")}</option>
                <option value="prevention_only">{label(arabic, "Prevention only", "وقائي فقط")}</option>
                <option value="custom">{label(arabic, "Custom from sidebar chatbot", "تخصيص المساعد")}</option>
              </select>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginBottom: "14px" }}>
              {summaryCard(
                "Economic basis",
                "أساس اقتصادي",
                label(
                  arabic,
                  report.cost_estimate.basis.replaceAll("_", " "),
                  report.cost_estimate.basis.replaceAll("_", " ")
                ),
                label(arabic, "Reference estimate. Use the sidebar chatbot only if you want a more exact personal calculation.", "تقدير مرجعي. استخدم مساعد الشريط الجانبي فقط إذا كنت تريد حساباً شخصياً أكثر دقة."),
                "#f2cf98"
              )}
              {summaryCard(
                "Assumed area",
                "المساحة المفترضة",
                report.cost_estimate.area_feddan_assumed != null ? fmt(report.cost_estimate.area_feddan_assumed, arabic, 2) : label(arabic, "n/a", "غير متاح"),
                label(arabic, "Only used for reference pricing.", "يُستخدم فقط للتسعير المرجعي."),
                "#8dc3f4"
              )}
              {summaryCard(
                "Net benefit",
                "صافي العائد",
                recalculatedNetBenefit != null
                  ? fmtRange(recalculatedNetBenefit.low, recalculatedNetBenefit.high, arabic, "EGP")
                  : label(arabic, "Reference estimate. Use the sidebar chatbot only if you want a more exact personal calculation.", "تقدير مرجعي. استخدم مساعد الشريط الجانبي فقط إذا كنت تريد حساباً شخصياً أكثر دقة."),
                recalculatedNetBenefit != null
                  ? (selectedTreatmentId === "confirm_first"
                      ? label(arabic, "Delay risk check only.", "خطر التأخير فقط.")
                      : recalculatedNetBenefit.low > 0
                        ? label(arabic, "Likely worth spraying.", "غالباً يستاهل الرش.")
                        : label(arabic, "May not pay off.", "قد لا يكون مربحاً."))
                  : report.cost_estimate.decision_hint,
                "#b9e978"
              )}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "12px" }}>
              {recalculatedCases.map((item) => (
                <article key={item.key} style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#cdf58a" }}>{arabic ? item.name_ar : item.name_en}</strong>
                  <span style={{ color: "#88a99a", fontSize: "11px" }}>{arabic ? `${fmt(item.area_feddan, arabic, 2)} فدان` : `${fmt(item.area_feddan, arabic, 2)} feddan`}</span>
                  <div style={{ display: "grid", gap: "4px", color: "#c9ded4", fontSize: "12px", lineHeight: 1.5 }}>
                    <span>{label(arabic, "Number of sprays", "عدد الرشّات")}: {renderValue(item.sprays.low, item.sprays.unit, arabic)} - {renderValue(item.sprays.high, item.sprays.unit, arabic)}</span>
                    <span>{label(arabic, "Treatment cost", "تكلفة العلاج")}: {renderValue(item.treatment_cost_egp.low, item.treatment_cost_egp.unit, arabic)} - {renderValue(item.treatment_cost_egp.high, item.treatment_cost_egp.unit, arabic)}</span>
                    <span>{label(arabic, "Labor cost", "تكلفة العمالة")}: {renderValue(item.labor_cost_egp.low, item.labor_cost_egp.unit, arabic)} - {renderValue(item.labor_cost_egp.high, item.labor_cost_egp.unit, arabic)}</span>
                    <span>{label(arabic, "Expected saved yield", "المحصول المحفوظ المتوقع")}: {renderValue(item.expected_yield_kg.low, item.expected_yield_kg.unit, arabic)} - {renderValue(item.expected_yield_kg.high, item.expected_yield_kg.unit, arabic)}</span>
                    <span>{label(arabic, "Yield loss risk if ignored", "خطر فقدان المحصول إذا تم تجاهله")}: {renderValue(item.loss_without_action_egp.low, item.loss_without_action_egp.unit, arabic)} - {renderValue(item.loss_without_action_egp.high, item.loss_without_action_egp.unit, arabic)}</span>
                    <span>{label(arabic, "Tomato price assumption", "افتراض سعر الطماطم")}: {label(arabic, "5 - 12 EGP/kg", "5 - 12 جنيه/كيلو")}</span>
                    <span>{label(arabic, "Revenue saved range", "نطاق الإيراد المحفوظ")}: {renderValue(item.saved_with_action_egp.low, item.saved_with_action_egp.unit, arabic)} - {renderValue(item.saved_with_action_egp.high, item.saved_with_action_egp.unit, arabic)}</span>
                    <span>{label(arabic, "Net benefit range", "نطاق صافي الفائدة")}: {renderValue(item.net_benefit_egp.low, item.net_benefit_egp.unit, arabic)} - {renderValue(item.net_benefit_egp.high, item.net_benefit_egp.unit, arabic)}</span>
                  </div>
                  <p style={{ margin: 0, color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>
                    {arabic ? item.recommendation_ar : item.recommendation_en}
                  </p>
                </article>
              ))}
            </div>
            <div style={{ marginTop: "20px", overflowX: "auto" }}>
              <strong style={{ color: "#dcefe5", display: "block", marginBottom: "10px" }}>
                {label(arabic, "Cost-Benefit Treatment Comparison Table", "مقارنة الجدوى الاقتصادية لخيارات العلاج")}
              </strong>
              <table style={{ width: "100%", borderCollapse: "collapse", background: "rgba(255,255,255,.015)", borderRadius: "8px", overflow: "hidden", fontSize: "12px" }}>
                <thead>
                  <tr style={{ background: "rgba(255,255,255,.04)", borderBottom: "1px solid rgba(255,255,255,.1)" }}>
                    <th style={{ padding: "10px", textAlign: arabic ? "right" : "left", color: "#cdf58a" }}>{label(arabic, "Treatment Mode", "وضع العلاج")}</th>
                    <th style={{ padding: "10px", textAlign: arabic ? "right" : "left", color: "#cdf58a" }}>{label(arabic, "Cost Range", "نطاق التكلفة")}</th>
                    <th style={{ padding: "10px", textAlign: arabic ? "right" : "left", color: "#cdf58a" }}>{label(arabic, "When to Use", "متى يُستخدم")}</th>
                    <th style={{ padding: "10px", textAlign: arabic ? "right" : "left", color: "#cdf58a" }}>{label(arabic, "Expected Benefit", "الفائدة المتوقعة")}</th>
                    <th style={{ padding: "10px", textAlign: arabic ? "right" : "left", color: "#cdf58a" }}>{label(arabic, "Risk", "المخاطر")}</th>
                    <th style={{ padding: "10px", textAlign: arabic ? "right" : "left", color: "#cdf58a" }}>{label(arabic, "APC Status", "حالة التسجيل")}</th>
                    <th style={{ padding: "10px", textAlign: arabic ? "right" : "left", color: "#cdf58a" }}>{label(arabic, "Best Farm Size", "أفضل حجم مزرعة")}</th>
                    <th style={{ padding: "10px", textAlign: "center", color: "#cdf58a" }}>{label(arabic, "Recommended", "موصى به")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(report.cost_benefit_comparison || []).map((row: any) => {
                    const isRowSelected = row.treatment_mode === selectedTreatmentId;
                    return (
                      <tr
                        key={row.treatment_mode}
                        style={{
                          borderBottom: "1px solid rgba(255,255,255,.06)",
                          background: isRowSelected ? "rgba(185,236,97,.05)" : "transparent"
                        }}
                      >
                        <td style={{ padding: "10px", fontWeight: "bold", color: "#e9f5ef" }}>
                          {label(arabic, row.label_en, row.label_ar)}
                        </td>
                        <td style={{ padding: "10px", color: "#cdf58a" }}>
                          {fmtRange(row.cost_low, row.cost_high, arabic, "EGP")}
                        </td>
                        <td style={{ padding: "10px", color: "#c9ded4" }}>
                          {label(arabic, row.when_to_use_ar, row.when_to_use_en)}
                        </td>
                        <td style={{ padding: "10px", color: "#c9ded4" }}>
                          {label(arabic, row.expected_benefit_ar, row.expected_benefit_en)}
                        </td>
                        <td style={{ padding: "10px", color: "#bcd8ca" }}>
                          {label(arabic, row.risk_ar, row.risk_en)}
                        </td>
                        <td style={{ padding: "10px", color: "#bcd8ca" }}>
                          {label(arabic, row.apc_gate_ar, row.apc_gate_en)}
                        </td>
                        <td style={{ padding: "10px", color: "#c9ded4" }}>
                          {label(arabic, row.best_farm_size_ar, row.best_farm_size_en)}
                        </td>
                        <td style={{ padding: "10px", textAlign: "center" }}>
                          {row.treatment_mode === selectedTreatmentId ? (
                            <span style={{ color: "#cdf58a", fontWeight: "bold" }}>✓</span>
                          ) : (
                            <span style={{ color: "#88a99a" }}>-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: "14px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Provider priority", "ترتيب المصادر")}</strong>
              {renderBullets(costPhase.provider_priority, arabic)}
            </div>
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Treatment cost comparison", "مقارنة تكلفة العلاج")}</strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
                {costComparisonOptions.map((item) => renderTreatmentOption(item, selectedComparisonModeKey))}
              </div>
              {selectedComparisonOption && (
                <div style={{ padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                  <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Current economic choice", "الاختيار الاقتصادي الحالي")}</strong>
                  <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                    {arabic ? selectedComparisonOption.summary_ar : selectedComparisonOption.summary_en}
                  </p>
                  <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                    {arabic ? selectedComparisonOption.expected_benefit_ar : selectedComparisonOption.expected_benefit_en}
                  </p>
                </div>
              )}
                <div style={{ padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                  <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Need a tighter cost estimate?", "هل تحتاج تقدير تكلفة أدق؟")}</strong>
                  <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                  {arabic ? costPhase.higher_accuracy_hint_ar ?? "" : costPhase.higher_accuracy_hint_en ?? ""}
                  </p>
                </div>
            </div>
          </section>
        );
      case 6:
        return (
          <section className="case-panel">
            <div className="case-panel-title">
              <FileText size={17} />
              <strong>{label(arabic, "Conclusion & Recommendation", "الخلاصة والتوصية")}</strong>
            </div>
            <p style={{ margin: "0 0 12px", color: "#bcd8ca", lineHeight: 1.7 }}>
              {report.conclusion}
            </p>
            {report.confidence_warning && (
              <div className="case-warning">
                <AlertTriangle size={16} />
                <p>{arabic ? report.confidence_warning.text_ar : report.confidence_warning.text_en}</p>
              </div>
            )}
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Action plan", "خطة العمل")}</strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px" }}>
                {conclusionPhase.action_plan.map((section) => (
                  <article key={section.title_en} style={{ padding: "12px", borderRadius: "12px", background: "rgba(255,255,255,.02)", border: "1px solid rgba(255,255,255,.08)" }}>
                    <strong style={{ color: "#cdf58a", fontSize: "13px" }}>{arabic ? section.title_ar : section.title_en}</strong>
                    {renderBullets(arabic ? section.bullets_ar : section.bullets_en, arabic)}
                  </article>
                ))}
              </div>
            </div>
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Scenario recommendations", "سيناريوهات التوصية")}</strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
                {conclusionPhase.scenario_recommendations.map(renderScenarioCase)}
              </div>
            </div>
            
            <div style={{ marginTop: "16px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Key Decision Breakdown", "تفصيل القرار الأساسي")}</strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#b9e978", fontSize: "13px" }}>{label(arabic, "Best Overall Choice", "أفضل اختيار إجمالاً")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {arabic ? (treatmentOptions.find(o => o.key === selectedTreatmentModeKey)?.label_ar || "متوازن") : (treatmentOptions.find(o => o.key === selectedTreatmentModeKey)?.label_en || "Balanced")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#8dc3f4", fontSize: "13px" }}>{label(arabic, "Cheapest Safe Choice", "الخيار الأقل تكلفة والأمن")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {label(arabic, "Sanitation only (0 EGP cash cost; requires manual labor)", "تنظيف فقط (تكلفة نقدية 0 جنيه؛ يتطلب عمالة يدوية)")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#f2cf98", fontSize: "13px" }}>{label(arabic, "Strongest Allowed Choice", "الخيار الأقوى المسموح")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {report.primary_detected_disease.certainty_level === "high"
                      ? label(arabic, "Strongest Program (Verify APC label matching first)", "البرنامج الأقوى (تحقق من مطابقة ملصق APC أولاً)")
                      : label(arabic, "Balanced Program (Strongest is locked due to certainty level)", "البرنامج المتوازن (الأقوى مغلق لعدم كفاية مستوى اليقين)")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#ef4444", fontSize: "13px" }}>{label(arabic, "Choice to Avoid", "خيارات تجنبها")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {report.disease_class?.toLowerCase() === "pest" || report.primary_detected_disease?.name_en?.toLowerCase().includes("mite")
                      ? label(arabic, "Fungicides (molds/fungi treatment is completely useless for spider mites)", "المبيدات الفطرية (علاج العفن/الفطريات غير مفيد تماماً للعنكبوت الأحمر)")
                      : label(arabic, "Broad-spectrum chemical spray before diagnosis verification", "رش كيميائي عشوائي واسع المدى قبل التحقق من التشخيص")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#cdf58a", fontSize: "13px" }}>{label(arabic, "What to Do Today", "ما يجب فعله اليوم")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {arabic
                      ? "افحص النبات ميدانياً باليد، أزل الورق المصاب بشدة، وقلل الغبار."
                      : "Inspect plant in-person, rogue badly affected leaves, and reduce field dust."}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#bcd8ca", fontSize: "13px" }}>{label(arabic, "If Farmer Has 1 Feddan", "إذا كان لدى المزارع فدان واحد")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {label(arabic, "Economics justify a planned spray if confirmed; ensure water/fuel access.", "الاقتصاديات تبرر الرش المخطط إذا تأكد؛ تأكد من توفر المياه والوقود للرش.")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#bcd8ca", fontSize: "13px" }}>{label(arabic, "If Farmer Has 5 Feddans", "إذا كان لدى المزارع ٥ فدادين")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {label(arabic, "Hire helper labor; seek input volume discounts; schedule regular row checks.", "وظّف عمالة مساعدة؛ ابحث عن خصومات الكميات للمبيدات؛ وجدول فحصاً دورياً للخطوط.")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#bcd8ca", fontSize: "13px" }}>{label(arabic, "If Greenhouse", "في حالة الصوبة الزجاجية")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {label(arabic, "Avoid high-pressure water spray (promotes humidity/molds); focus on vector nets.", "تجنب الرش المائي عالي الضغط (يزيد الرطوبة والعفن)؛ وركز على شباك الحشرات.")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#bcd8ca", fontSize: "13px" }}>{label(arabic, "If Open Field", "في حالة الحقل المفتوح")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {label(arabic, "Dust management is critical (dust encourages mites). Spray borders on windy days.", "إدارة الغبار مهمة جداً (التراب يشجع العناكب). رش الحواف في الأيام العاصفة.")}
                  </p>
                </article>

                <article style={{ padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,.08)", background: "rgba(255,255,255,.02)", display: "grid", gap: "8px" }}>
                  <strong style={{ color: "#bcd8ca", fontSize: "13px" }}>{label(arabic, "If Confidence Stays Low", "إذا ظلت الثقة منخفضة")}</strong>
                  <p style={{ margin: 0, color: "#e9f5ef", fontSize: "12px" }}>
                    {label(arabic, "Do not buy chemical packages. Seek in-person agronomist review.", "لا تشترِ عبوات كيميائية. اطلب زيارة ميدانية من مهندس زراعي للتأكيد.")}
                  </p>
                </article>
              </div>
            </div>

            <div style={{ marginTop: "14px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Safety notes", "ملاحظات الأمان")}</strong>
              {renderBullets(report.safety_notes, arabic)}
            </div>
            <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
              <strong style={{ color: "#dcefe5" }}>{label(arabic, "Balanced recommendation", "التوصية المتوازنة")}</strong>
              <div style={{ padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                <div style={{ color: "#e9f5ef", fontSize: "12px", fontWeight: 700 }}>
                  {arabic ? conclusionPhase.best_balanced_choice_ar ?? "" : conclusionPhase.best_balanced_choice_en ?? ""}
                </div>
                <div style={{ color: "#c9ded4", fontSize: "12px", lineHeight: 1.6, marginTop: "6px" }}>
                  {arabic ? conclusionPhase.comparison_summary_ar ?? "" : conclusionPhase.comparison_summary_en ?? ""}
                </div>
                {selectedConclusionOption && (
                  <div style={{ color: "#c9ded4", fontSize: "12px", lineHeight: 1.6, marginTop: "6px" }}>
                    {label(arabic, "Selected mode:", "الوضع المختار:")} {arabic ? selectedConclusionOption.label_ar : selectedConclusionOption.label_en}
                  </div>
                )}
              </div>
              <div style={{ padding: "12px", borderRadius: "12px", border: "1px solid rgba(185,236,97,.12)", background: "rgba(185,236,97,.05)" }}>
                <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Need a clearer final call?", "هل تحتاج قرار نهائي أوضح؟")}</strong>
                <p style={{ margin: "6px 0 0", color: "#c9ded4", lineHeight: 1.6 }}>
                  {arabic ? conclusionPhase.higher_accuracy_hint_ar ?? "" : conclusionPhase.higher_accuracy_hint_en ?? ""}
                </p>
              </div>
            </div>
          </section>
        );
      default:
        return null;
    }
  }

  const activeLabel = active ? prettyStatus(active.status, arabic) : "";
  const geoLabel = geoCoords ? `${geoCoords.lat.toFixed(5)}, ${geoCoords.lng.toFixed(5)}` : "";

  return (
    <main className="case-page">
      <section className="case-intro">
        <div>
          <p className="eyebrow">{label(arabic, "Case workspace", "مساحة الحالة")}</p>
          <h1>{label(arabic, "Photo-only crop report", "تقرير زراعي من الصورة فقط")}</h1>
          <p>
            {label(
              arabic,
              "One photo builds the case, the report, the safety gates, the cost forecast, and the final recommendation. No forms are required inside the workspace.",
              "صورة واحدة تبني الحالة والتقرير وبوابات الأمان وتوقع التكلفة والتوصية النهائية. لا توجد نماذج مطلوبة داخل المساحة."
            )}
          </p>
          {geoLabel && (
            <p style={{ color: "#9bb8ab", fontSize: "13px", marginTop: "10px" }}>
              {label(arabic, "Device GPS captured in the photo flow:", "تم التقاط GPS الجهاز في مسار الصورة:")} {geoLabel}
            </p>
          )}
        </div>
        <div className="case-trust">
          <ShieldCheck size={20} />
          <div>
            <strong>{label(arabic, "Generated report", "تقرير مولد")}</strong>
            <span>{label(arabic, "Photo evidence plus source metadata and a readable safety plan.", "أدلة الصورة مع بيانات المصدر وخطة أمان قابلة للقراءة.")}</span>
          </div>
        </div>
      </section>

      {error && (
        <div className="case-error" style={{ marginBottom: "16px" }}>
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="case-layout">
        <aside className="case-sidebar">
          <section className="case-panel">
            <div className="case-panel-title">
              <History size={17} />
              <strong>{label(arabic, "Saved cases", "الحالات المحفوظة")}</strong>
              <button type="button" onClick={() => void refreshCases()} aria-label={label(arabic, "Refresh cases", "تحديث الحالات")}>
                <RefreshCw size={14} />
              </button>
            </div>
            <div className="case-history">
              {cases.length === 0 ? (
                <p style={{ color: "#8fae9f", fontSize: "12px", lineHeight: 1.6, margin: 0 }}>
                  {label(arabic, "No saved cases yet.", "لا توجد حالات محفوظة بعد.")}
                </p>
              ) : (
                cases.map((item) => (
                  <button
                    key={item.case_id}
                    type="button"
                    className={`case-history-item ${active?.case_id === item.case_id ? "active" : ""}`}
                    onClick={() => selectCase(item)}
                  >
                    <span>
                      <CheckCircle2 size={11} />
                      {prettyStatus(item.status, arabic)}
                    </span>
                    <strong>{item.diagnosis.top_disease || label(arabic, "Pending diagnosis", "في انتظار التشخيص")}</strong>
                    <small>
                      {item.location || label(arabic, "Location not recorded", "الموقع غير مسجل")}
                    </small>
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="case-panel">
            <div className="case-panel-title">
              <MapPin size={17} />
              <strong>{label(arabic, "Current case", "الحالة الحالية")}</strong>
            </div>
            {active ? (
              <div style={{ display: "grid", gap: "8px" }}>
                <div style={{ color: "#e9f5ef", fontWeight: 700 }}>{active.diagnosis.top_disease || label(arabic, "No diagnosis yet", "لا يوجد تشخيص بعد")}</div>
                <div style={{ color: "#88a99a", fontSize: "12px" }}>{active.case_id}</div>
                <div style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.55 }}>{active.location || label(arabic, "Location not recorded", "الموقع غير مسجل")}</div>
                <div style={{ color: "#bcd8ca", fontSize: "12px" }}>{activeLabel}</div>
              </div>
            ) : (
              <p style={{ color: "#8fae9f", fontSize: "12px", lineHeight: 1.6, margin: 0 }}>
                {label(arabic, "Start a case or resume a saved one from the list.", "ابدأ حالة أو استأنف حالة محفوظة من القائمة.")}
              </p>
            )}
          </section>

          {report && (
            <section className="case-panel">
              <div className="case-panel-title">
                <Download size={17} />
                <strong>{label(arabic, "Downloads", "التحميلات")}</strong>
              </div>
              <div className="report-actions" style={{ flexWrap: "wrap" }}>
                <a href={api.caseReportUrl(active!.case_id, "pdf")}>{label(arabic, "PDF", "بي دي إف")}</a>
                <a href={api.caseReportUrl(active!.case_id, "csv")}>{label(arabic, "CSV", "سي إس في")}</a>
                <a href={api.caseReportUrl(active!.case_id, "pdf")} target="_blank" rel="noreferrer">
                  {label(arabic, "Open report", "فتح التقرير")}
                </a>
              </div>
            </section>
          )}

          {report?.sidebar_chatbot_context && (
            <section className="case-panel">
              <div className="case-panel-title">
                <MessageSquare size={17} />
                <strong>{label(arabic, "Sidebar assistant context", "سياق مساعد الشريط الجانبي")}</strong>
              </div>
              <p style={{ color: "#bcd8ca", fontSize: "12px", lineHeight: 1.65, margin: "0 0 10px" }}>
                {arabic ? report.sidebar_chatbot_context.summary_ar : report.sidebar_chatbot_context.summary_en}
              </p>
              <strong style={{ color: "#dcefe5", fontSize: "12px" }}>{label(arabic, "Quick questions", "أسئلة سريعة")}</strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "8px" }}>
                {(arabic ? report.sidebar_chatbot_context.quick_questions_ar : report.sidebar_chatbot_context.quick_questions_en).map((question) => (
                  <span
                    key={question}
                    style={{
                      padding: "6px 9px",
                      borderRadius: "999px",
                      border: "1px solid rgba(185,236,97,.18)",
                      background: "rgba(185,236,97,.06)",
                      color: "#e9f5ef",
                      fontSize: "11px",
                    }}
                  >
                    {question}
                  </span>
                ))}
              </div>
            </section>
          )}

          {report && (
            <section className="case-panel">
              <div className="case-panel-title">
                <Coins size={17} />
                <strong>{label(arabic, "Egypt sources", "مصادر مصرية")}</strong>
              </div>
              <div style={{ display: "grid", gap: "10px" }}>
                {report.egypt_sources.map((source) => (
                  <div key={source.title} style={{ padding: "10px", borderRadius: "12px", background: "rgba(255,255,255,.02)", border: "1px solid rgba(255,255,255,.08)" }}>
                    <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{source.title}</strong>
                    <div style={{ color: "#88a99a", fontSize: "11px", marginTop: "4px" }}>{source.organization}</div>
                    <a href={source.url} target="_blank" rel="noreferrer" style={{ color: "#b9e978", fontSize: "11px", textDecoration: "none" }}>
                      {source.source_kind}
                    </a>
                  </div>
                ))}
              </div>
            </section>
          )}

          {report && (
            <section className="case-panel">
              <div className="case-panel-title">
                <Leaf size={17} />
                <strong>{label(arabic, "Source metadata", "بيانات المصادر")}</strong>
              </div>
              <div style={{ display: "grid", gap: "10px" }}>
                {report.source_metadata.map(renderSourceCard)}
              </div>
            </section>
          )}
        </aside>

        <section className="case-main">
          {active ? (
            <>
              <div className="case-active-head">
                <div>
                  <h2>{report?.primary_detected_disease.detected ? (arabic ? report.primary_detected_disease.name_ar : report.primary_detected_disease.name_en) : (active.diagnosis.top_disease || label(arabic, "Awaiting diagnosis", "في انتظار التشخيص"))}</h2>
                  <span>
                    {label(arabic, "Case", "الحالة")} {active.case_id} · {prettyStatus(active.status, arabic)}
                  </span>
                </div>
                <div style={{ display: "grid", gap: "6px", textAlign: arabic ? "right" : "left" as const }}>
                  <div style={{ color: "#88a99a", fontSize: "10px", textTransform: "uppercase", letterSpacing: ".08em" }}>
                    {label(arabic, "Location", "الموقع")}
                  </div>
                  <div style={{ color: "#e9f5ef", fontSize: "13px", fontWeight: 700, maxWidth: "320px" }}>
                    {active.location || label(arabic, "Not recorded", "غير مسجل")}
                  </div>
                </div>
              </div>

              {loading && (
                <div className="case-loading">
                  <LoaderCircle size={16} className="spin" />
                  <span>{label(arabic, "Loading case report...", "جارٍ تحميل التقرير...")}</span>
                </div>
              )}

              {report ? (
                <>
                  <section className="case-panel">
                    <div className="case-panel-title">
                      <CheckCircle2 size={17} />
                      <strong>{label(arabic, "Top summary", "الملخص العلوي")}</strong>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
                      {summaryCard(
                        "Primary visual match",
                        "التطابق البصري للمرض",
                        arabic ? report.primary_detected_disease.name_ar : report.primary_detected_disease.name_en,
                        `${label(arabic, "Certainty: ", "اليقين: ")}${report.primary_detected_disease.certainty_level}`,
                        "#cdf58a"
                      )}
                      {summaryCard(
                        "Score",
                        "نسبة التطابق البصري",
                        renderCompactValue(report.summary_cards.visual_score, arabic),
                        label(arabic, "AI model confidence", "ثقة نموذج الذكاء الاصطناعي"),
                        "#b9e978"
                      )}
                      {summaryCard(
                        "Certainty level",
                        "مستوى اليقين",
                        label(arabic, report.primary_detected_disease.certainty_level, report.primary_detected_disease.certainty_level),
                        label(arabic, "Based on host confirmation", "بناءً على تأكيد العائل"),
                        "#8dc3f4"
                      )}
                      {summaryCard(
                        "Visible infection estimate",
                        "تقدير الانتشار الظاهر",
                        renderCompactValue(report.summary_cards.infection_extent, arabic),
                        label(arabic, "Visible leaf spots", "بقع الأوراق الظاهرة"),
                        "#8dc3f4"
                      )}
                      {summaryCard(
                        "Weather pressure",
                        "خطر الطقس",
                        renderCompactValue(report.summary_cards.weather_risk, arabic),
                        label(arabic, "Environmental risk level", "مستوى الخطر البيئي"),
                        "#f2cf98"
                      )}
                      {summaryCard(
                        "Engine/runtime stats",
                        "إحصاءات المحرك",
                        `${fmtOptionalNumber(report.summary_cards.engine_stats.analysis_time_ms, arabic)} ms`,
                        `${report.summary_cards.engine_stats.engine} · ${fmtOptionalNumber(report.summary_cards.engine_stats.memory_used_mb, arabic, 2)} MB`,
                        "#dcefe5"
                      )}
                      {summaryCard(
                        "Selected treatment mode",
                        "وضع العلاج المختار",
                        selectedTreatmentId
                          ? (arabic
                              ? (treatmentOptions.find(o => o.key === selectedTreatmentId)?.label_ar || selectedTreatmentId)
                              : (treatmentOptions.find(o => o.key === selectedTreatmentId)?.label_en || selectedTreatmentId))
                          : label(arabic, "balanced", "متوازن"),
                        label(arabic, "Dynamically selected mode", "الوضع المختار ديناميكياً"),
                        "#b9e978"
                      )}
                    </div>
                    {report.summary_cards.top_candidates.length > 0 && (
                      <div style={{ marginTop: "12px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
                        {report.summary_cards.top_candidates.map((candidate) => (
                          <span
                            key={candidate.label_en}
                            style={{
                              padding: "6px 9px",
                              borderRadius: "999px",
                              border: "1px solid rgba(255,255,255,.08)",
                              background: "rgba(255,255,255,.02)",
                              color: "#dcefe5",
                              fontSize: "11px",
                            }}
                          >
                            {arabic ? candidate.label_ar : candidate.label_en}: {renderCompactValue(candidate, arabic)}
                          </span>
                        ))}
                      </div>
                    )}
                  </section>

                  <section className="case-panel" style={{ marginTop: "14px" }}>
                    <div className="case-panel-title">
                      <Leaf size={17} />
                      <strong>{label(arabic, "Photo Quality & Crop Verification", "جودة الصورة والتحقق من المحصول")}</strong>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", alignItems: "start" }}>
                      {previewUrl && (
                        <div style={{ borderRadius: "12px", overflow: "hidden", border: "1px solid rgba(255,255,255,.08)", background: "#000", display: "flex", justifyContent: "center", alignItems: "center", maxHeight: "200px" }}>
                          <img src={previewUrl} alt="Thumbnail" style={{ maxWidth: "100%", maxHeight: "200px", objectFit: "contain" }} />
                        </div>
                      )}
                      <div style={{ display: "grid", gap: "10px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ color: "#cdf58a", fontSize: "14px", fontWeight: "bold" }}>
                            {label(arabic, "Quality Status:", "حالة جودة الصورة:")}
                          </span>
                          <span className="badge" style={{ background: "rgba(185,236,97,.1)", color: "#b9e978", border: "1px solid rgba(185,236,97,.2)", fontSize: "12px", textTransform: "capitalize" }}>
                            {label(arabic, report.photo_quality?.status || "clear", report.photo_quality?.status || "clear")}
                          </span>
                        </div>
                        {report.photo_quality?.host_crop_support === "user_selected_not_visually_confirmed" && (
                          <div className="case-warning" style={{ margin: "4px 0" }}>
                            <AlertTriangle size={16} />
                            <p style={{ margin: 0, fontSize: "12px", color: "#f2cf98" }}>
                              {label(arabic, "Crop selected by user: tomato. Image model did not independently confirm host crop.", "المحصول المختار من المستخدم: طماطم. لم يؤكد نموذج الصور بشكل مستقل نبات العائل.")}
                            </p>
                          </div>
                        )}
                        {report.photo_quality?.warnings && report.photo_quality.warnings.length > 0 && (
                          <div style={{ display: "grid", gap: "6px" }}>
                            <strong style={{ color: "#e9f5ef", fontSize: "12px" }}>{label(arabic, "Quality Alerts:", "تنبيهات الجودة:")}</strong>
                            <ul style={{ margin: 0, paddingInlineStart: "18px", color: "#c9ded4", fontSize: "12px", display: "grid", gap: "4px" }}>
                              {report.photo_quality.warnings.map((warning, idx) => (
                                <li key={idx}>{warning}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <details style={{ marginTop: "6px" }}>
                          <summary style={{ cursor: "pointer", color: "#88a99a", fontSize: "12px", outline: "none", fontWeight: "bold" }}>
                            {label(arabic, "View Retake Photo Tips (Optional Guidance)", "عرض نصائح إعادة التصوير (إرشاد اختياري)")}
                          </summary>
                          <div style={{ marginTop: "6px", color: "#bcd8ca", fontSize: "12px", lineHeight: 1.5, display: "grid", gap: "4px", paddingLeft: "8px", borderLeft: "1px solid rgba(255,255,255,.08)" }}>
                            <p style={{ margin: 0 }}>1. {label(arabic, "Ensure leaf fills at least 20-30% of the frame.", "تأكد من أن الورقة تملأ على الأقل ٢٠-٣٠٪ من الإطار.")}</p>
                            <p style={{ margin: 0 }}>2. {label(arabic, "Shoot in bright daylight, avoiding harsh shadows.", "صور في ضوء النهار الساطع وتجنب الظلال الشديدة.")}</p>
                            <p style={{ margin: 0 }}>3. {label(arabic, "Focus cleanly on the symptoms (underside if possible).", "اضبط التركيز بوضوح على الأعراض (السطح السفلي إن أمكن).")}</p>
                          </div>
                        </details>
                      </div>
                    </div>
                  </section>
                    {report.confidence_warning && (
                      <div className="case-warning" style={{ marginTop: "14px" }}>
                        <AlertTriangle size={16} />
                        <p>{arabic ? report.confidence_warning.text_ar : report.confidence_warning.text_en}</p>
                      </div>
                    )}

                  <div className="phase-stepper" aria-label={label(arabic, "Workflow phases", "مراحل العمل")}>
                    {phaseTabs.map((tab) => {
                      const Icon = tab.icon;
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          className={`phase-tab ${activeTab === tab.id ? "active" : ""}`}
                          onClick={() => setActiveTab(tab.id)}
                        >
                          <span className="phase-tab-num">{String(tab.id).padStart(2, "0")}</span>
                          <Icon size={16} />
                          <span className="phase-tab-label">{tab.label}</span>
                        </button>
                      );
                    })}
                  </div>

                  <div className="phase-pane">
                    {renderSelectedPhase()}
                  </div>

                  <section className="case-panel">
                    <div className="case-panel-title">
                      <ClipboardList size={17} />
                      <strong>{label(arabic, "Recommendation details", "تفاصيل التوصية")}</strong>
                    </div>
                    <p style={{ margin: 0, color: "#bcd8ca", lineHeight: 1.7 }}>{report.conclusion}</p>
                    <div style={{ marginTop: "14px", display: "grid", gap: "10px" }}>
                      <strong style={{ color: "#dcefe5" }}>{label(arabic, "Assumptions", "الافتراضات")}</strong>
                      {renderBullets(arabic ? report.assumptions.map((item) => item.text_ar) : report.assumptions.map((item) => item.text_en), arabic)}
                    </div>
                    <div style={{ marginTop: "14px", display: "grid", gap: "10px" }}>
                      <strong style={{ color: "#dcefe5" }}>{label(arabic, "Safety notes", "ملاحظات الأمان")}</strong>
                      {renderBullets(report.safety_notes, arabic)}
                    </div>
                  </section>
                </>
              ) : (
                <section className="case-panel">
                  <div className="case-panel-title">
                    <LoaderCircle size={17} className="spin" />
                    <strong>{label(arabic, "Loading report", "جارٍ تحميل التقرير")}</strong>
                  </div>
                  <p style={{ margin: 0, color: "#bcd8ca", lineHeight: 1.7 }}>
                    {label(
                      arabic,
                      "The workspace is waiting for the generated report from the case API.",
                      "المساحة تنتظر التقرير المولد من واجهة الحالة."
                    )}
                  </p>
                </section>
              )}
            </>
          ) : (
            <section className="case-empty">
              <LoaderCircle size={26} className={loading ? "spin" : ""} />
              <h2>{label(arabic, "Start a case or resume a saved one to continue.", "ابدأ حالة أو استأنف حالة محفوظة للمتابعة.")}</h2>
              <p style={{ color: "#8fae9f", lineHeight: 1.7, margin: 0, maxWidth: "600px" }}>
                {label(
                  arabic,
                  "The report stays read-only: the photo flow creates the case, then this workspace shows the generated disease information, protection, consulting, treatment, cost forecast, and conclusion.",
                  "التقرير للقراءة فقط: مسار الصورة ينشئ الحالة، ثم تعرض هذه المساحة معلومات المرض والوقاية والاستشارة والعلاج والتكلفة والخلاصة."
                )}
              </p>
            </section>
          )}
        </section>
      </div>
    </main>
  );
}
