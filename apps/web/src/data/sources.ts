// ─────────────────────────────────────────────────────────────────────────────
// Egypt official sources + the provenance-badge vocabulary.
//
// Ported from services/api/app/knowledge/egypt_sources.py and tomato_statistics.py.
// Every figure shown in the app carries one of these badges so the farmer can see
// where a number came from — a standout honesty feature of AgroVision.
// ─────────────────────────────────────────────────────────────────────────────

import type { Bi } from "./diseases";

// The four canonical provenance badges from the spec.
export type Provenance = "live" | "official" | "estimated_range" | "generated";

export const PROVENANCE_LABEL: Record<Provenance, Bi> = {
  live: { en: "live", ar: "مباشر" },
  official: { en: "official", ar: "رسمي" },
  estimated_range: { en: "estimated range", ar: "تقدير مرجعي" },
  generated: { en: "generated", ar: "مُولّد" },
};

export const PROVENANCE_HINT: Record<Provenance, Bi> = {
  live: { en: "Read live at analysis time (e.g. Open-Meteo weather).", ar: "اتقرى مباشرة وقت التحليل (زي طقس Open-Meteo)." },
  official: { en: "From an official Egyptian source (CAPMAS, ARC, APC, QCAP).", ar: "من مصدر مصري رسمي (الجهاز/مركز البحوث/لجنة المبيدات/معمل المتبقّيات)." },
  estimated_range: { en: "A reviewed reference range, not a live or exact figure — confirm locally.", ar: "شريحة مرجعية مراجَعة، مش رقم مباشر أو مضبوط — أكّده محليًا." },
  generated: { en: "Computed by the app from the inputs above; a transparent estimate.", ar: "محسوب بالتطبيق من المدخلات اللي فوق؛ تقدير شفّاف." },
};

// Hard links required by the safety gate.
export const APC_PESTICIDE_DB_URL = "https://www1.apc.gov.eg/en/search.aspx";
export const APC_REGISTRATION_RULES_URL = "https://www.apc.gov.eg/EN/PesticidesRegistration.aspx";
export const QCAP_RESIDUE_LAB_URL = "https://www.qcap-egypt.com/";

export type SourceKind = "diagnosis" | "pesticide_registration" | "food_safety" | "statistics";

export interface EgyptSource {
  title: Bi;
  organization: Bi;
  url: string;
  purpose: Bi;
  kind: SourceKind;
  badge: Provenance;
}

export const EGYPT_SOURCES: EgyptSource[] = [
  {
    title: { en: "Plant Pathology Research Institute", ar: "معهد بحوث أمراض النباتات" },
    organization: { en: "Egyptian Agricultural Research Center (ARC)", ar: "مركز البحوث الزراعية" },
    url: "https://www.arc.sci.eg/",
    purpose: { en: "Egyptian national plant-disease diagnosis, monitoring, and control expertise.", ar: "خبرة تشخيص ومتابعة ومكافحة أمراض النبات على المستوى القومي في مصر." },
    kind: "diagnosis",
    badge: "official",
  },
  {
    title: { en: "Vegetable Diseases Research Department", ar: "قسم بحوث أمراض الخضر" },
    organization: { en: "Egyptian Agricultural Research Center (ARC)", ar: "مركز البحوث الزراعية" },
    url: "https://www.arc.sci.eg/",
    purpose: { en: "Receives vegetable samples and examines them to identify disease causes.", ar: "بيستقبل عيّنات الخضر ويفحصها لتحديد سبب المرض." },
    kind: "diagnosis",
    badge: "official",
  },
  {
    title: { en: "Central Egyptian Pesticides Database (APC)", ar: "قاعدة بيانات المبيدات المصرية المركزية (لجنة المبيدات)" },
    organization: { en: "Agricultural Pesticides Committee", ar: "لجنة مبيدات الآفات الزراعية" },
    url: APC_PESTICIDE_DB_URL,
    purpose: { en: "Verify current Egyptian registration by crop AND pest before any pesticide use.", ar: "تأكيد التسجيل المصري الحالي حسب المحصول والآفة قبل أي استخدام مبيد." },
    kind: "pesticide_registration",
    badge: "official",
  },
  {
    title: { en: "Pesticide Registration Rules", ar: "قواعد تسجيل المبيدات" },
    organization: { en: "Agricultural Pesticides Committee", ar: "لجنة مبيدات الآفات الزراعية" },
    url: APC_REGISTRATION_RULES_URL,
    purpose: { en: "Official Egyptian pesticide registration and use requirements.", ar: "متطلبات تسجيل واستخدام المبيدات المصرية الرسمية." },
    kind: "pesticide_registration",
    badge: "official",
  },
  {
    title: { en: "Central Lab of Residue Analysis of Pesticides & Heavy Metals in Food (QCAP)", ar: "المعمل المركزي لتحليل متبقّيات المبيدات والمعادن الثقيلة في الغذاء (QCAP)" },
    organization: { en: "Egyptian Agricultural Research Center (ARC)", ar: "مركز البحوث الزراعية" },
    url: QCAP_RESIDUE_LAB_URL,
    purpose: { en: "Official Egyptian food-safety and pesticide-residue analysis route.", ar: "المسار المصري الرسمي لسلامة الغذاء وتحليل متبقّيات المبيدات." },
    kind: "food_safety",
    badge: "official",
  },
];

// CAPMAS tomato statistics references (implied yield kg/feddan), used by economics.ts.
export interface CapmasReference {
  key: string;
  title: Bi;
  organization: Bi;
  url: string;
  areaThousandFeddan: number;
  productionMillionTons: number;
  retrievedOn: string;
}

export const CAPMAS_REFERENCES: CapmasReference[] = [
  {
    key: "capmas_tomato_2017_2018",
    title: {
      en: "Annual Bulletin of Production, Foreign Trade & Consumption of Agricultural Commodities 2017/2018",
      ar: "النشرة السنوية لحركة إنتاج وتجارة وإتاحة السلع الزراعية 2017/2018",
    },
    organization: { en: "Central Agency for Public Mobilization and Statistics (CAPMAS)", ar: "الجهاز المركزي للتعبئة العامة والإحصاء" },
    url: "https://censusinfo.capmas.gov.eg/metadata-en-v4.2/index.php/catalog/399/download/819",
    areaThousandFeddan: 416.0,
    productionMillionTons: 6.8,
    retrievedOn: "2026-06-16",
  },
  {
    key: "capmas_tomato_2015_2016",
    title: {
      en: "Annual Bulletin of Agricultural Income Estimates 2015/2016",
      ar: "النشرة السنوية لتقديرات الدخل الزراعي 2015/2016",
    },
    organization: { en: "Central Agency for Public Mobilization and Statistics (CAPMAS)", ar: "الجهاز المركزي للتعبئة العامة والإحصاء" },
    url: "https://censusinfo.capmas.gov.eg/Metadata-ar-v4.2/index.php/catalog/1416/download/4729",
    areaThousandFeddan: 440.2,
    productionMillionTons: 7.3,
    retrievedOn: "2026-06-16",
  },
];

/** Implied tomato yield kg/feddan for a CAPMAS reference. */
export function capmasYieldKgPerFeddan(ref: CapmasReference): number {
  return (ref.productionMillionTons * 1_000_000) / ref.areaThousandFeddan;
}
