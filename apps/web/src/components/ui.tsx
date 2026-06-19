// Small shared UI kit: bilingual text, provenance badges, certainty chips, cards.
// Tailwind utility classes; dark-green theme from styles.css.

import type { ReactNode } from "react";
import type { Bi, Lang } from "../data/diseases";
import { PROVENANCE_HINT, PROVENANCE_LABEL, type Provenance } from "../data/sources";
import type { CertaintyBand } from "../lib/screening";

export function t(bi: Bi, lang: Lang): string {
  return bi[lang];
}

/** Render a bilingual value in the active language. */
export function L({ bi, lang }: { bi: Bi; lang: Lang }): ReactNode {
  return <>{bi[lang]}</>;
}

const PROVENANCE_CLASS: Record<Provenance, string> = {
  live: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  official: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  estimated_range: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  generated: "bg-violet-500/15 text-violet-300 border-violet-500/30",
};

export function ProvenanceBadge({ p, lang }: { p: Provenance; lang: Lang }) {
  return (
    <span
      title={PROVENANCE_HINT[p][lang]}
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${PROVENANCE_CLASS[p]}`}
    >
      {PROVENANCE_LABEL[p][lang]}
    </span>
  );
}

const BAND_CLASS: Record<CertaintyBand, string> = {
  high: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  medium: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  low: "bg-rose-500/15 text-rose-300 border-rose-500/40",
};

export function CertaintyChip({ band, lang }: { band: CertaintyBand; lang: Lang }) {
  const label: Record<CertaintyBand, Bi> = {
    high: { en: "High certainty", ar: "تأكيد عالي" },
    medium: { en: "Medium certainty", ar: "تأكيد متوسط" },
    low: { en: "Low certainty", ar: "تأكيد منخفض" },
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-sm font-semibold ${BAND_CLASS[band]}`}>
      <span className="h-2 w-2 rounded-full bg-current" /> {label[band][lang]}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-white/10 bg-white/[0.03] p-4 sm:p-5 ${className}`}>
      {children}
    </section>
  );
}

export function PhaseHeader({ index, title, subtitle, icon }: { index: number; title: string; subtitle: string; icon: ReactNode }) {
  return (
    <div className="mb-3 flex items-center gap-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-400/15 text-emerald-300">{icon}</span>
      <div>
        <h2 className="text-lg font-bold leading-tight text-emerald-50">{title}</h2>
        <p className="text-xs text-emerald-200/50">{subtitle}</p>
      </div>
      <span className="ms-auto text-2xl font-black text-white/10">{index}</span>
    </div>
  );
}

/** A labelled value with a provenance badge — the provenance-everywhere pattern. */
export function SourcedValue({
  label,
  value,
  unit,
  provenance,
  assumption,
  lang,
}: {
  label: string;
  value: string;
  unit?: string;
  provenance: Provenance;
  assumption?: string;
  lang: Lang;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-emerald-200/60">{label}</span>
        <ProvenanceBadge p={provenance} lang={lang} />
      </div>
      <div className="mt-1 text-base font-semibold text-emerald-50">
        {value} {unit && <span className="text-xs font-normal text-emerald-200/50">{unit}</span>}
      </div>
      {assumption && <p className="mt-1 text-[11px] leading-snug text-emerald-200/40">{assumption}</p>}
    </div>
  );
}

export function BulletList({ items, tone = "neutral" }: { items: string[]; tone?: "do" | "avoid" | "neutral" }) {
  const marker = tone === "do" ? "✓" : tone === "avoid" ? "✕" : "•";
  const color = tone === "do" ? "text-emerald-400" : tone === "avoid" ? "text-rose-400" : "text-emerald-300/50";
  return (
    <ul className="space-y-1.5">
      {items.map((it, i) => (
        <li key={i} className="flex gap-2 text-sm text-emerald-50/90">
          <span className={`mt-0.5 shrink-0 font-bold ${color}`}>{marker}</span>
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}
