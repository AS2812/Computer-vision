import type { ValidationLevel } from "../types";

const labels: Record<ValidationLevel, { en: string; ar: string }> = {
  validated: { en: "Measured result", ar: "نتيجة مقاسة" },
  experimental: { en: "Image estimate", ar: "تقدير من الصورة" },
  "sample-data": { en: "Reference only", ar: "مرجعي فقط" }
};

export function Badge({ level, feature, arabic }: { level: ValidationLevel; feature?: string; arabic?: boolean }) {
  let label = labels[level][arabic ? "ar" : "en"];
  let kind: string = level;
  if (feature === "disease") {
    if (level === "sample-data") {
      label = arabic ? "لا يوجد تطابق موثوق" : "No reliable match";
      kind = "experimental";
    } else {
      label = arabic ? "تطابق بصري قوي" : "Strong visual match";
      kind = "real-ai";
    }
  }
  return <span className={`badge badge-${kind}`}>{label}</span>;
}
