// The six phases: See it → Stop it → Confirm it → Treat it → Cost it → Plan it.
// Each reads from the engine (screening, safety gate, economics, KB). The full
// recommendation/assumptions/safety block appears ONCE here (Phase 6) + sidebar.

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Coins,
  Leaf,
  Lock,
  ShieldCheck,
  Sprout,
  Stethoscope,
} from "lucide-react";
import type { AppAnalysis } from "../appTypes";
import type { TreatmentCatalog, TreatmentProduct } from "../appTypes";
import { diseaseByKey, type Bi, type Lang } from "../data/diseases";
import { generateAreaCases, type AreaCase, type SeverityEstimate, type TreatmentModeId } from "../data/economics";
import { APC_PESTICIDE_DB_URL, QCAP_RESIDUE_LAB_URL } from "../data/sources";
import { STRINGS } from "../data/i18n";
import { marketPriceLabel, marketProvenance } from "../lib/market";
import { evaluateGate } from "../lib/safety";
import { fetchTreatmentCatalog } from "../lib/treatments";
import { severityFromExtent, type CertaintyBand } from "../lib/screening";
import { weatherPressure } from "../lib/weather";
import { BulletList, Card, CertaintyChip, PhaseHeader, ProvenanceBadge, SourcedValue } from "./ui";

const tr = (bi: Bi, lang: Lang) => bi[lang];

export interface Workflow {
  confirmed: boolean;
  apcVerified: boolean;
  mode: TreatmentModeId;
  farmerArea: number | null;
  farmerPrice: number | null;
  customTreatmentCost: number | null;
  confirmAnswers: Record<string, number>;
}

interface Ctx {
  analysis: AppAnalysis;
  lang: Lang;
  wf: Workflow;
  set: <K extends keyof Workflow>(k: K, v: Workflow[K]) => void;
}

function bump(b: CertaintyBand, dir: 1 | -1): CertaintyBand {
  const order: CertaintyBand[] = ["low", "medium", "high"];
  return order[Math.min(2, Math.max(0, order.indexOf(b) + dir))];
}

const CAUSE_LABEL: Record<string, Bi> = {
  fungal: { en: "Fungal", ar: "فطري" },
  oomycete: { en: "Water-mould (oomycete)", ar: "عفن مائي" },
  bacterial: { en: "Bacterial", ar: "بكتيري" },
  viral: { en: "Viral", ar: "فيروسي" },
  mite: { en: "Mite (pest)", ar: "حلم/آفة" },
  none: { en: "None", ar: "لا يوجد" },
};

// ── Phase 1 — Diagnosis ──────────────────────────────────────────────────────
export function Phase1Diagnosis({ analysis, lang }: Ctx) {
  const S = STRINGS[lang];
  const s = analysis.screening;
  const [expand, setExpand] = useState<string | null>(null);
  const entry = s.topKey ? diseaseByKey(s.topKey) : null;

  return (
    <Card>
      <PhaseHeader index={1} title={S.phase1} subtitle={S.phase1Sub} icon={<Stethoscope size={18} />} />

      {/* Verdict line */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <CertaintyChip band={s.certainty} lang={lang} />
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-300">
          {S.notConfirmed}
        </span>
      </div>

      {/* Top-3 candidates with evidence note */}
      <p className="mb-1 text-xs font-semibold text-emerald-200/60">{S.topCandidates}</p>
      <div className="space-y-1.5">
        {s.candidates.map((c, i) => (
          <div key={c.key} className="flex items-center gap-2">
            <span className="w-5 text-xs text-emerald-200/40">{i + 1}</span>
            <span className="flex-1 text-sm text-emerald-50">{tr(c.name, lang)}</span>
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-emerald-400" style={{ width: `${Math.round(c.prob * 100)}%` }} />
            </div>
            <span className="w-10 text-end text-xs tabular-nums text-emerald-200/70">{Math.round(c.prob * 100)}%</span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[11px] text-emerald-200/40">
        {S.evidenceNote}: {analysis.local.modelFile} · {analysis.local.engine} · {S.matchScore}. {S.uncalibratedNote}
      </p>

      {entry && (
        <div className="mt-4 space-y-3">
          <div>
            <p className="text-sm leading-relaxed text-emerald-50/90">{tr(entry.summary, lang)}</p>
            <span className="mt-2 inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-1 text-xs text-emerald-200/70">
              {S.causeType}: {tr(CAUSE_LABEL[entry.cause], lang)}
            </span>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <SymptomCol title={S.symptomsLeaf} items={entry.symptomsLeaf.map((b) => tr(b, lang))} />
            <SymptomCol title={S.symptomsFruit} items={entry.symptomsFruit.map((b) => tr(b, lang))} />
            <SymptomCol title={S.symptomsStem} items={entry.symptomsStem.map((b) => tr(b, lang))} />
          </div>

          {entry.lookalikes.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold text-emerald-200/60">{S.lookalikes}</p>
              <div className="flex flex-wrap gap-1.5">
                {entry.lookalikes.map((k) => {
                  const la = diseaseByKey(k);
                  if (!la) return null;
                  return (
                    <button
                      key={k}
                      onClick={() => setExpand(expand === k ? null : k)}
                      className="rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-xs text-emerald-100 hover:border-emerald-400/40"
                    >
                      {tr(la.name, lang)}
                    </button>
                  );
                })}
              </div>
              {expand && (
                <p className="mt-2 rounded-lg border border-white/10 bg-black/20 p-2 text-xs text-emerald-100/80">
                  {tr(diseaseByKey(expand)!.summary, lang)}
                </p>
              )}
            </div>
          )}

          <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] p-3">
            <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-emerald-200">
              <Activity size={15} /> {S.todayCheck}
            </p>
            <BulletList items={entry.todayCheck.map((b) => tr(b, lang))} />
          </div>
        </div>
      )}

      {/* Photo quality & crop verification card */}
      <div className="mt-4 grid gap-3 rounded-xl border border-white/10 bg-black/20 p-3 sm:grid-cols-[auto_1fr]">
        <img src={analysis.previewUrl} alt="" className="h-20 w-20 rounded-lg object-cover" />
        <div className="text-xs text-emerald-100/80">
          <p className="font-semibold text-emerald-200/70">{S.photoCropCard}</p>
          <p className="mt-1">
            {analysis.quality.resolutionOk ? "✓" : "⚠"} {analysis.quality.shortEdge}px ·{" "}
            {analysis.quality.blurry ? "⚠ blur" : "✓ sharp"} ({analysis.quality.blurVariance}) ·{" "}
            {analysis.quality.tooDark ? "⚠ dark" : analysis.quality.tooBright ? "⚠ bright" : "✓ light"}
          </p>
          <p className="mt-1 text-emerald-200/50">{tr(analysis.screening.leafGate.reason, lang)}</p>
          <p className="mt-1 text-emerald-200/40">{S.hostCropNote}</p>
        </div>
      </div>
    </Card>
  );
}

function SymptomCol({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <p className="mb-1 text-xs font-semibold text-emerald-200/60">{title}</p>
      {items.length ? <BulletList items={items} /> : <p className="text-xs text-emerald-200/30">—</p>}
    </div>
  );
}

// ── Phase 2 — Protect Now ────────────────────────────────────────────────────
const PROTECT_STEPS: Bi[] = [
  { en: "Mark and separate the affected plants so you can re-find them.", ar: "علّم واعزل النباتات المصابة عشان تلاقيها تاني." },
  { en: "Inspect nearby healthy plants for the first signs.", ar: "افحص النباتات السليمة القريبة على أول علامة." },
  { en: "Remove heavily affected tissue — only if it won't spread contamination.", ar: "شيل الأنسجة المصابة بشدة — بس لو مش هتنشر العدوى." },
  { en: "Clean tools between plants.", ar: "نضّف الأدوات بين النبات والتاني." },
  { en: "Re-inspect the marked plants in 3 days.", ar: "افحص النباتات المعلّمة تاني بعد ٣ أيام." },
  { en: "Never work the crop while the leaves are wet.", ar: "ما تشتغلش في الزرع والورق مبلّل." },
  { en: "Never leave infected debris under the plants.", ar: "ما تسيبش مخلّفات مصابة تحت الزرع." },
];

const SCENARIOS: Array<{ title: keyof typeof STRINGS.en; do: Bi[]; avoid: Bi[] }> = [
  {
    title: "scenarioHome",
    do: [
      { en: "Pick off spotted leaves by hand and bin them.", ar: "اقطف الورق المبقّع باليد وارميه في الزبالة." },
      { en: "Water at the base, in the morning.", ar: "اروي من تحت الصبح." },
    ],
    avoid: [
      { en: "Don't compost infected leaves next to the plants.", ar: "ما تعملش سماد من الورق المصاب جنب الزرع." },
      { en: "Don't wet the foliage in the evening.", ar: "ما تبلّلش الورق بالليل." },
    ],
  },
  {
    title: "scenarioField",
    do: [
      { en: "Scout in blocks; flag hotspots; widen spacing where you can.", ar: "افحص بلوكات؛ علّم البؤر؛ وسّع المسافات قد ما تقدر." },
      { en: "Direct traffic from clean blocks to infected ones last.", ar: "اشتغل في البلوكات النضيفة الأول والمصابة في الآخر." },
    ],
    avoid: [
      { en: "Don't move workers/tools from infected to clean blocks.", ar: "ما تنقلش العمال/الأدوات من المصاب للنضيف." },
      { en: "Don't irrigate by sprinkler late in the day.", ar: "ما تروّيش بالرشّاش آخر النهار." },
    ],
  },
  {
    title: "scenarioGreenhouse",
    do: [
      { en: "Vent and heat to cut humidity — humidity control IS protection.", ar: "هوّي وسخّن عشان تقلّل الرطوبة — التحكّم في الرطوبة هو الحماية." },
      { en: "Increase spacing and air movement; water early.", ar: "زوّد المسافات وحركة الهوا؛ واروي بدري." },
    ],
    avoid: [
      { en: "Don't let the canopy stay wet overnight.", ar: "ما تسيبش الورق مبلّل طول الليل." },
      { en: "Don't pack plants tightly together.", ar: "ما تزحّمش النباتات على بعض." },
    ],
  },
];

export function Phase2Protect({ analysis, lang }: Ctx) {
  const S = STRINGS[lang];
  const entry = analysis.screening.topKey ? diseaseByKey(analysis.screening.topKey) : null;
  return (
    <Card>
      <PhaseHeader index={2} title={S.phase2} subtitle={S.phase2Sub} icon={<ShieldCheck size={18} />} />
      <p className="mb-3 text-sm text-emerald-100/80">{S.appliesAnyConfidence}</p>
      <BulletList tone="do" items={PROTECT_STEPS.map((b) => tr(b, lang))} />
      {entry?.protectNote && (
        <p className="mt-3 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.06] p-2 text-sm text-emerald-100">
          {tr(entry.protectNote, lang)}
        </p>
      )}
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {SCENARIOS.map((sc) => (
          <div key={sc.title} className="rounded-xl border border-white/10 bg-black/20 p-3">
            <p className="mb-2 text-sm font-semibold text-emerald-200">{S[sc.title] as string}</p>
            <p className="text-[11px] font-semibold uppercase text-emerald-400/70">{S.doThis}</p>
            <BulletList tone="do" items={sc.do.map((b) => tr(b, lang))} />
            <p className="mt-2 text-[11px] font-semibold uppercase text-rose-400/70">{S.avoidThis}</p>
            <BulletList tone="avoid" items={sc.avoid.map((b) => tr(b, lang))} />
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Phase 3 — Confirm It (collapsible) ───────────────────────────────────────
interface ConfirmQuestion {
  id: string;
  q: Bi;
  options: Array<{ label: Bi; weight: number }>;
}
const CONFIRM_QUESTIONS: ConfirmQuestion[] = [
  { id: "part", q: { en: "Which part is affected?", ar: "أي جزء مصاب؟" }, options: [
    { label: { en: "Lower/older leaves", ar: "ورق سفلي/كبير" }, weight: 1 },
    { label: { en: "Upper/new leaves", ar: "ورق علوي/جديد" }, weight: 1 },
    { label: { en: "Stem", ar: "الساق" }, weight: 1 },
    { label: { en: "Fruit", ar: "الثمرة" }, weight: 1 },
  ] },
  { id: "start", q: { en: "Where did it start?", ar: "بدأ منين؟" }, options: [
    { label: { en: "Older leaves first", ar: "الورق الكبير الأول" }, weight: 1 },
    { label: { en: "Uniform all over", ar: "منتشر بالتساوي" }, weight: 1 },
  ] },
  { id: "speed", q: { en: "Spread speed?", ar: "سرعة الانتشار؟" }, options: [
    { label: { en: "Slow", ar: "بطيء" }, weight: 1 },
    { label: { en: "Moderate", ar: "متوسط" }, weight: 1 },
    { label: { en: "Fast", ar: "سريع" }, weight: 1 },
  ] },
  { id: "incidence", q: { en: "Plants per 100 affected?", ar: "كام نبات من ١٠٠ مصاب؟" }, options: [
    { label: { en: "A few (<10)", ar: "قليل (<١٠)" }, weight: 1 },
    { label: { en: "Many (>30)", ar: "كتير (>٣٠)" }, weight: 1 },
  ] },
  { id: "irrigation", q: { en: "Irrigation method?", ar: "طريقة الري؟" }, options: [
    { label: { en: "Drip", ar: "تنقيط" }, weight: 1 },
    { label: { en: "Flood/canal", ar: "غمر/ترعة" }, weight: 1 },
    { label: { en: "Sprinkler", ar: "رشّاش" }, weight: 1 },
  ] },
  { id: "nearby", q: { en: "Are nearby plants affected?", ar: "النباتات القريبة مصابة؟" }, options: [
    { label: { en: "Just one plant", ar: "نبات واحد بس" }, weight: 1 },
    { label: { en: "A whole patch", ar: "بقعة كاملة" }, weight: 1 },
  ] },
  { id: "harvest", q: { en: "Days to harvest?", ar: "كام يوم للحصاد؟" }, options: [
    { label: { en: ">21 days", ar: "أكتر من ٢١ يوم" }, weight: 1 },
    { label: { en: "<21 days (PHI matters)", ar: "أقل من ٢١ يوم (فترة الأمان مهمة)" }, weight: 1 },
  ] },
];

export function Phase3Confirm({ analysis, lang, wf, set }: Ctx) {
  const S = STRINGS[lang];
  const [open, setOpen] = useState(false);
  const answers = wf.confirmAnswers || {};
  const answered = Object.keys(answers).length;
  const enough = answered >= 4;

  function answer(id: string, idx: number) {
    const next = { ...answers, [id]: idx };
    set("confirmAnswers", next);
    // Answering most questions "confirms" the case (raises certainty for the gate).
    set("confirmed", Object.keys(next).length >= 4);
  }

  return (
    <Card>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-3 text-start">
        <PhaseHeader index={3} title={S.phase3} subtitle={S.phase3Sub} icon={<ClipboardList size={18} />} />
        <span className="ms-auto text-xs text-emerald-200/50">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="mt-2 animate-rise">
          <p className="mb-3 text-sm text-emerald-100/80">{S.confirmItIntro}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {CONFIRM_QUESTIONS.map((cq) => (
              <div key={cq.id} className="rounded-xl border border-white/10 bg-black/20 p-3">
                <p className="mb-2 text-sm font-medium text-emerald-50">{tr(cq.q, lang)}</p>
                <div className="flex flex-wrap gap-1.5">
                  {cq.options.map((o, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => answer(cq.id, i)}
                      className={`rounded-full border px-2.5 py-1 text-xs transition cursor-pointer ${
                        answers[cq.id] === i
                          ? "border-emerald-400 bg-emerald-400/20 text-emerald-100 font-semibold"
                          : "border-white/15 bg-white/5 text-emerald-100/70 hover:border-emerald-400/40"
                      }`}
                    >
                      {tr(o.label, lang)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-emerald-200/70">{S.addMorePhotos}</p>
          <div
            className={`mt-3 flex items-center gap-2 rounded-xl border p-2.5 text-xs ${
              enough ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/5 text-amber-200/80"
            }`}
          >
            {enough ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
            {enough
              ? lang === "ar"
                ? `تم رفع التأكيد (${answered}/7 إجابات). الوضع المقترح اتحدّث.`
                : `Confidence raised (${answered}/7 answered). Recommended mode updated.`
              : lang === "ar"
                ? `جاوب على ٤ أسئلة على الأقل لرفع التأكيد (${answered}/7).`
                : `Answer at least 4 questions to raise confidence (${answered}/7).`}
          </div>
          
          {/* Explanation Visualizer of what Phase 3 does */}
          <div className="mt-3 rounded-xl border border-white/10 bg-black/30 p-3 text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-emerald-200/50">{lang === "ar" ? "درجة التأكيد الأساسية:" : "Initial Certainty:"}</span>
              <CertaintyChip band={analysis.screening.certainty} lang={lang} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-emerald-200/50">{lang === "ar" ? "درجة التأكيد بعد الإجابات:" : "Upgraded Certainty:"}</span>
              <CertaintyChip band={enough ? bump(analysis.screening.certainty, 1) : analysis.screening.certainty} lang={lang} />
            </div>
            <div className="text-[11px] leading-relaxed text-emerald-200/40 border-t border-white/5 pt-2">
              {lang === "ar"
                ? "الإجابة على ٤ أسئلة أو أكتر بتثبت تشخيص الصورة وترفع مستوى ثقة النظام درجة كاملة، مما يسمح بمكافحة كيميائية متوازنة/أقوى بمجرد تفعيل تأكيد تسجيل لجنة المبيدات (APC) في المرحلة ٤."
                : "Answering 4+ questions validates the visual screening diagnosis and upgrades the confidence level by a full band. This will unlock chemical mode selections once you verify APC registration in Phase 4."}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── Phase 4 — Treatment Options (gated) ──────────────────────────────────────
export function Phase4Treatment({ analysis, lang, wf, set }: Ctx) {
  const S = STRINGS[lang];
  const treatmentKey = analysis.screening.topKey ?? analysis.screening.candidates[0]?.key ?? null;
  const entry = treatmentKey ? diseaseByKey(treatmentKey) : null;
  const [catalog, setCatalog] = useState<TreatmentCatalog | null>(null);
  const effectiveCertainty: CertaintyBand = wf.confirmed ? bump(analysis.screening.certainty, 1) : analysis.screening.certainty;
  const gate = useMemo(
    () => evaluateGate({
      certainty: effectiveCertainty,
      confirmed: wf.confirmed,
      apcVerified: wf.apcVerified,
      isViral: entry?.cause === "viral",
      isPest: entry?.cause === "mite",
    }),
    [effectiveCertainty, wf.confirmed, wf.apcVerified, entry?.cause],
  );

  useEffect(() => {
    const key = treatmentKey;
    if (!key) {
      setCatalog(null);
      return;
    }
    const controller = new AbortController();
    fetchTreatmentCatalog(key, controller.signal).then(setCatalog);
    return () => controller.abort();
  }, [treatmentKey]);

  return (
    <Card>
      <PhaseHeader index={4} title={S.phase4} subtitle={S.phase4Sub} icon={<Sprout size={18} />} />
      <p className="mb-2 text-sm text-emerald-100/80">{S.nonChemicalFirst}</p>
      <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-2 text-xs text-amber-100/80">
        {tr(gate.reason, lang)}
      </div>

      {/* APC verification toggle (simulated registration check) */}
      <label className="mb-3 flex items-center gap-2 text-xs text-emerald-100/80">
        <input type="checkbox" checked={wf.apcVerified} onChange={(e) => set("apcVerified", e.target.checked)} />
        {S.apcVerify}
        <a href={APC_PESTICIDE_DB_URL} target="_blank" rel="noreferrer" className="text-sky-300 underline">APC</a>
      </label>

      <div className="grid gap-2.5 sm:grid-cols-2">
        {gate.modes.map(({ mode, locked, lockReason, apcStatus }) => {
          const selected = wf.mode === mode.id;
          return (
            <button
              key={mode.id}
              disabled={locked}
              onClick={() => !locked && set("mode", mode.id)}
              className={`rounded-xl border p-3 text-start transition ${
                locked
                  ? "cursor-not-allowed border-white/10 bg-black/30 opacity-60"
                  : selected
                    ? "border-emerald-400 bg-emerald-400/10"
                    : "border-white/15 bg-white/[0.03] hover:border-emerald-400/40"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-emerald-50">{tr(mode.name, lang)}</span>
                {locked ? (
                  <span className="inline-flex items-center gap-1 text-[11px] text-rose-300"><Lock size={12} /> {S.chemicalGateLocked}</span>
                ) : selected ? (
                  <CheckCircle2 size={15} className="text-emerald-400" />
                ) : null}
              </div>
              <dl className="mt-1.5 space-y-0.5 text-[11px] text-emerald-100/70">
                <div><span className="text-emerald-200/40">{S.modeCost}:</span> {tr(mode.costBand, lang)}</div>
                <div><span className="text-emerald-200/40">{S.modeBenefit}:</span> {tr(mode.benefit, lang)}</div>
                <div><span className="text-emerald-200/40">{S.modeRisk}:</span> {tr(mode.risk, lang)}</div>
                <div><span className="text-emerald-200/40">{S.modeFarmSize}:</span> {tr(mode.bestFarmSize, lang)}</div>
                {mode.chemical && <div className="text-amber-200/70">{tr(apcStatus, lang)}</div>}
              </dl>
              {locked && lockReason && <p className="mt-1 text-[11px] text-rose-200/70">{S.chemicalGateWhy}: {tr(lockReason, lang)}</p>}
            </button>
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
        <a href={APC_PESTICIDE_DB_URL} target="_blank" rel="noreferrer" className="text-sky-300 underline">{S.apcVerify}</a>
        <a href={QCAP_RESIDUE_LAB_URL} target="_blank" rel="noreferrer" className="text-sky-300 underline">{S.qcapResidue}</a>
      </div>
      <p className="mt-3 rounded-lg border border-white/10 bg-black/20 p-2 text-xs text-emerald-200/60">{S.seeProtectNow}</p>

      <div className="mt-4 rounded-xl border border-sky-400/20 bg-sky-400/[0.05] p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-sm font-bold text-sky-100">
              {lang === "ar" ? "كتالوج العلاج المسجل والمراجَع" : "Reviewed Treatment Catalog"}
            </p>
            <p className="mt-1 text-xs text-sky-100/70">
              {lang === "ar"
                ? "دي أسماء وجرعات مرجعية للمراجعة مع المهندس. مش أمر رش، والكيماوي يفضل مقفول لحد التأكيد والتسجيل."
                : "These are reviewed names and label-reference doses for discussion with an engineer. This is not a spray order; chemicals stay gated until confirmation and registration."}
            </p>
          </div>
          <a href={catalog?.availability.apc_url || APC_PESTICIDE_DB_URL} target="_blank" rel="noreferrer" className="rounded-lg border border-sky-300/25 px-2 py-1 text-xs text-sky-200 underline">
            {S.apcVerify}
          </a>
        </div>

        {catalog ? (
          <>
            <p className="mt-3 rounded-lg border border-white/10 bg-black/20 p-2 text-xs text-sky-100/70">
              {lang === "ar" ? catalog.availability.status_ar : catalog.availability.status_en}
              {" "}
              {lang === "ar" ? catalog.availability.price_status_ar : catalog.availability.price_status_en}
            </p>
            <div className="mt-3 grid gap-2">
              {catalog.treatments.length ? (
                catalog.treatments.map((product) => <TreatmentProductCard key={`${product.rank}-${product.name_en}`} product={product} lang={lang} />)
              ) : (
                <p className="rounded-lg border border-amber-500/25 bg-amber-500/[0.06] p-2 text-xs text-amber-100/80">
                  {lang === "ar"
                    ? "مفيش علاج كيميائي موثق للحالة دي؛ ركّز على الوقاية والنظافة واستشارة مهندس."
                    : "No reviewed chemical treatment is listed for this condition; focus on prevention, sanitation, and expert confirmation."}
                </p>
              )}
            </div>
            <div className="mt-3 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.05] p-2">
              <p className="mb-1 text-xs font-bold text-emerald-200">
                {lang === "ar" ? "وقاية قبل ظهور المرض" : "Protection Before Symptoms"}
              </p>
              <BulletList tone="do" items={catalog.prevention[lang]} />
            </div>
          </>
        ) : (
          <p className="mt-3 text-xs text-sky-100/60">
            {lang === "ar" ? "اختار/أكد تشخيص طماطم عشان يظهر كتالوج العلاج." : "Confirm a tomato diagnosis to show the treatment catalog."}
          </p>
        )}
      </div>
    </Card>
  );
}

function TreatmentProductCard({ product, lang }: { product: TreatmentProduct; lang: Lang }) {
  const ar = lang === "ar";
  const name = ar ? product.name_ar : product.name_en;
  const dose = ar ? product.dose_ar : product.dose_en;
  const application = ar ? product.application_ar : product.application_en;
  const phi = ar ? product.phi_ar : product.phi_en;
  const hazard = ar ? product.hazard_ar : product.hazard_en;
  const price = ar ? product.price_ar : product.price_en;
  const note = ar ? product.note_ar : product.note_en;
  return (
    <article className="rounded-xl border border-white/10 bg-black/25 p-3 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-sky-400/15 px-2 py-0.5 font-bold text-sky-200">#{product.rank}</span>
        <h3 className="text-sm font-bold text-emerald-50">{name}</h3>
      </div>
      <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
        <InfoLine label={ar ? "المجموعة" : "Group"} value={product.frac} />
        <InfoLine label={ar ? "الجرعة" : "Dose"} value={dose} />
        <InfoLine label={ar ? "فترة الأمان" : "PHI"} value={phi} />
        <InfoLine label={ar ? "السعر" : "Price"} value={price || (ar ? "أكّد محليًا" : "Confirm locally")} />
      </div>
      {product.price_sources?.length > 0 && (
        <div className="mt-2 rounded-lg border border-sky-400/20 bg-sky-400/[0.04] p-2">
          <p className="mb-1 text-[11px] font-bold text-sky-200">
            {ar ? "فحص أسعار أونلاين" : "Online Price Checks"}
          </p>
          <div className="space-y-1.5">
            {product.price_sources.map((source) => (
              <a
                key={`${source.source}-${source.url}`}
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-md border border-white/10 bg-black/20 p-2 hover:border-sky-300/35"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-sky-100">{source.source}: {source.title}</span>
                  <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] text-emerald-100/70">
                    {source.price_text || (ar ? "لا يوجد سعر مقروء" : "no parsed price")}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-sky-100/65">
                  {ar ? source.availability_ar : source.availability_en}
                  {source.checked_at ? ` · ${source.checked_at}` : ""}
                </p>
                <p className="mt-0.5 text-[10px] text-sky-100/40">{ar ? source.note_ar : source.note_en}</p>
              </a>
            ))}
          </div>
        </div>
      )}
      <p className="mt-2 text-emerald-100/75"><span className="text-emerald-300/60">{ar ? "الاستخدام: " : "Apply: "}</span>{application}</p>
      <p className="mt-1 text-amber-100/75"><span className="text-amber-300/70">{ar ? "الأمان: " : "Safety: "}</span>{hazard}</p>
      {note && <p className="mt-1 text-emerald-200/45">{note}</p>}
    </article>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
      <span className="text-emerald-200/40">{label}: </span>
      <span className="text-emerald-50/85">{value || "-"}</span>
    </div>
  );
}

// ── Phase 5 — Is It Worth It? ────────────────────────────────────────────────
function NumberInput({
  label,
  value,
  onChange,
  step = 1,
  min = 0,
  placeholder = "",
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  step?: number;
  min?: number;
  placeholder?: string;
}) {
  const handleDec = () => {
    const curr = value ?? 0;
    const next = Math.max(min, curr - step);
    onChange(next === 0 && min === 0 ? null : Number(next.toFixed(2)));
  };
  const handleInc = () => {
    const curr = value ?? 0;
    const next = curr + step;
    onChange(Number(next.toFixed(2)));
  };
  return (
    <div className="flex flex-col gap-1.5 w-full">
      <span className="text-xs text-emerald-100/70">{label}</span>
      <div className="flex items-center gap-1.5 w-full">
        <button
          type="button"
          onClick={handleDec}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-emerald-100 hover:border-emerald-400/40 hover:bg-emerald-400/10 transition cursor-pointer select-none font-bold text-sm"
        >
          -
        </button>
        <input
          type="number"
          min={min}
          step={step}
          placeholder={placeholder}
          className="w-full h-9 text-center rounded-xl border border-white/10 bg-black/40 px-2 text-xs text-emerald-50 focus:border-emerald-400/30 focus:outline-none"
          value={value ?? ""}
          onChange={(e) => {
            const val = e.target.value;
            onChange(val === "" ? null : Number(val));
          }}
        />
        <button
          type="button"
          onClick={handleInc}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-emerald-100 hover:border-emerald-400/40 hover:bg-emerald-400/10 transition cursor-pointer select-none font-bold text-sm"
        >
          +
        </button>
      </div>
    </div>
  );
}

export function Phase5Economics({ analysis, lang, wf, set }: Ctx) {
  const S = STRINGS[lang];
  const entry = analysis.screening.topKey ? diseaseByKey(analysis.screening.topKey) : null;
  const severity: SeverityEstimate = severityFromExtent(analysis.extent);
  const cases = useMemo(
    () => generateAreaCases({
      mode: wf.mode,
      severity,
      isPest: entry?.cause === "mite",
      liveTomatoPrice:
        analysis.marketPrice?.live && analysis.marketPrice.low_egp_per_kg != null && analysis.marketPrice.high_egp_per_kg != null
          ? {
              low: analysis.marketPrice.low_egp_per_kg,
              high: analysis.marketPrice.high_egp_per_kg,
              source: analysis.marketPrice.source,
              asOf: analysis.marketPrice.as_of,
            }
          : null,
      farmerPriceEgpPerKg: wf.farmerPrice ?? undefined,
      farmerAreaFeddan: wf.farmerArea ?? undefined,
      customTreatmentCostPerFeddan: wf.customTreatmentCost ?? undefined,
    }),
    [wf.mode, wf.farmerPrice, wf.farmerArea, wf.customTreatmentCost, severity, entry?.cause, analysis.marketPrice],
  );

  const fmt = (lo: number | null, hi: number | null) => (lo == null ? "—" : lo === hi ? `${lo}` : `${lo}–${hi}`);
  const exact = wf.farmerPrice != null || wf.farmerArea != null || wf.customTreatmentCost != null;

  return (
    <Card>
      <PhaseHeader index={5} title={S.phase5} subtitle={S.phase5Sub} icon={<Coins size={18} />} />
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        <ProvenanceBadge p={exact ? "generated" : marketProvenance(analysis.marketPrice)} lang={lang} />
        <span className="text-emerald-200/60">{exact ? "" : S.enterRealNumbers}</span>
      </div>
      
      {/* Live Market Price Sourced Panel */}
      <div className="mb-3">
        <SourcedValue
          label={lang === "ar" ? "سعر الطماطم المباشر" : "Live tomato market price"}
          value={marketPriceLabel(analysis.marketPrice)}
          provenance={marketProvenance(analysis.marketPrice)}
          assumption={
            analysis.marketPrice?.note ??
            (lang === "ar" ? "مفيش سعر مباشر متاح؛ دخّل سعرك المحلي." : "No live price available; enter your local quote.")
          }
          lang={lang}
        />
      </div>

      {/* Input controls layout: 2 cols on desktop */}
      <div className="mb-4 grid gap-4 sm:grid-cols-2 bg-emerald-950/20 border border-emerald-500/10 rounded-xl p-3.5 animate-rise">
        {/* Left Col: Area & Local Market Price */}
        <div className="space-y-3">
          <h4 className="text-[11px] font-bold text-emerald-200/60 uppercase tracking-wider border-b border-emerald-500/5 pb-1">
            {lang === "ar" ? "بيانات المزرعة والسوق" : "Farm & Market Inputs"}
          </h4>
          
          <NumberInput
            label={lang === "ar" ? "مساحتك (فدان)" : "Your area (feddan)"}
            value={wf.farmerArea}
            onChange={(v) => set("farmerArea", v)}
            step={0.1}
          />
          
          <NumberInput
            label={lang === "ar" ? "سعر محلي (ج/كجم)" : "Local price (EGP/kg)"}
            value={wf.farmerPrice}
            onChange={(v) => set("farmerPrice", v)}
            step={0.5}
          />
        </div>

        {/* Right Col: Treatment Option & Custom Cost Override */}
        <div className="space-y-3">
          <h4 className="text-[11px] font-bold text-emerald-200/60 uppercase tracking-wider border-b border-emerald-500/5 pb-1">
            {lang === "ar" ? "خيارات العلاج والتكلفة" : "Treatment & Cost Selection"}
          </h4>
          
          <div className="flex flex-col gap-1.5 w-full">
            <span className="text-xs text-emerald-100/70">
              {lang === "ar" ? "خيار العلاج المختار" : "Selected Treatment Option"}
            </span>
            <div className="relative w-full">
              <select
                value={wf.mode}
                onChange={(e) => set("mode", e.target.value as any)}
                className={`w-full h-9 rounded-xl border border-white/10 bg-black/40 text-xs text-emerald-50 focus:border-emerald-400/30 focus:outline-none cursor-pointer appearance-none ${
                  lang === "ar" ? "pl-8 pr-2.5" : "pr-8 pl-2.5"
                }`}
              >
                <option value="confirm_first" className="bg-emerald-950 text-emerald-50">{lang === "ar" ? "أكّد الأول" : "Confirm first"}</option>
                <option value="sanitation_only" className="bg-emerald-950 text-emerald-50">{lang === "ar" ? "نظافة فقط" : "Sanitation only"}</option>
                <option value="prevention_only" className="bg-emerald-950 text-emerald-50">{lang === "ar" ? "وقاية فقط" : "Prevention only"}</option>
                <option value="balanced" className="bg-emerald-950 text-emerald-50">{lang === "ar" ? "رش متوازن" : "Balanced spray"}</option>
                <option value="strongest" className="bg-emerald-950 text-emerald-50">{lang === "ar" ? "الرش الأقوى" : "Strongest spray"}</option>
              </select>
              <div className={`pointer-events-none absolute inset-y-0 flex items-center px-2.5 text-emerald-300 ${
                lang === "ar" ? "left-0" : "right-0"
              }`}>
                <ChevronDown size={14} />
              </div>
            </div>
          </div>

          <NumberInput
            label={lang === "ar" ? "تكلفة الرشة المخصصة (جنية/رشة/فدان)" : "Custom Treatment Cost (EGP/spray/feddan)"}
            value={wf.customTreatmentCost}
            onChange={(v) => set("customTreatmentCost", v)}
            step={50}
            placeholder={lang === "ar" ? "اختياري (مثال: ٦٠٠ جنية)" : "Optional (e.g. 600 EGP)"}
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="text-emerald-200/50">
              <th className="p-1.5 text-start">{lang === "ar" ? "الحجم" : "Size"}</th>
              <th className="p-1.5 text-end">{lang === "ar" ? "رشّات" : "Sprays"}</th>
              <th className="p-1.5 text-end">{lang === "ar" ? "تكلفة" : "Treat EGP"}</th>
              <th className="p-1.5 text-end">{lang === "ar" ? "خسارة" : "Loss EGP"}</th>
              <th className="p-1.5 text-end">{S.netBenefit} EGP</th>
              <th className="p-1.5 text-end">{lang === "ar" ? "يستاهل؟" : "Worth?"}</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.key} className="border-t border-white/5">
                <td className="p-1.5 text-emerald-50">{tr(c.name, lang)}</td>
                <td className="p-1.5 text-end tabular-nums">{fmt(c.sprays.low, c.sprays.high)}</td>
                <td className="p-1.5 text-end tabular-nums">{fmt(c.treatmentCost.low, c.treatmentCost.high)}</td>
                <td className="p-1.5 text-end tabular-nums text-rose-300/80">{fmt(c.lossWithoutAction.low, c.lossWithoutAction.high)}</td>
                <td className="p-1.5 text-end font-semibold tabular-nums text-emerald-300">{fmt(c.netBenefit.low, c.netBenefit.high)}</td>
                <td className="p-1.5 text-end">
                  <WorthChip worth={c.worth} lang={lang} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px] text-emerald-200/40">
        {lang === "ar"
          ? "الإنتاجية الأساس من CAPMAS (≈ ١٦٬٣٤٦–١٦٬٥٨٣ كجم/فدان). الأسعار مرجعية مش مباشرة لحد ما تدخّل سعرك."
          : "Yield basis: CAPMAS (≈16,346–16,583 kg/feddan). Prices are reference, not live, until you enter your own."}
      </p>
    </Card>
  );
}

function WorthChip({ worth, lang }: { worth: AreaCase["worth"]; lang: Lang }) {
  const map = {
    likely_worth: { c: "text-emerald-300", t: STRINGS[lang].worthLikely },
    ask_engineer: { c: "text-amber-300", t: STRINGS[lang].worthAsk },
    maybe_not_worth: { c: "text-rose-300", t: STRINGS[lang].worthMaybeNot },
  } as const;
  return <span className={`text-[11px] font-medium ${map[worth].c}`}>{map[worth].t}</span>;
}

// ── Phase 6 — Your Action Plan (+ the safety block, shown once) ───────────────
export function Phase6ActionPlan({ analysis, lang, wf }: Ctx) {
  const S = STRINGS[lang];
  const s = analysis.screening;
  const entry = s.topKey ? diseaseByKey(s.topKey) : null;
  const lowConf = s.certainty === "low";
  const headline: Bi = lowConf
    ? { en: "Confirm first — confidence is low, so don't spray yet.", ar: "أكّد الأول — الثقة منخفضة، فما ترشّش لسه." }
    : entry
      ? { en: `Most likely ${entry.name.en} — start protection now and confirm before any chemical.`, ar: `الأرجح ${entry.name.ar} — ابدأ الحماية دلوقتي وأكّد قبل أي كيماوي.` }
      : { en: "Not sure yet — retake photos and answer the confirm questions.", ar: "لسه مش متأكّد — أعد التصوير وجاوب أسئلة التأكيد." };

  return (
    <Card>
      <PhaseHeader index={6} title={S.phase6} subtitle={S.phase6Sub} icon={<ClipboardList size={18} />} />
      <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/[0.07] p-3">
        <p className="text-xs font-semibold uppercase text-emerald-300/70">{S.headline}</p>
        <p className="mt-1 text-sm font-medium text-emerald-50">{tr(headline, lang)}</p>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <PlanCol title={S.today} items={[
          tr({ en: "Do the Protect Now steps (Phase 2).", ar: "اعمل خطوات الحماية الفورية (المرحلة ٢)." }, lang),
          tr({ en: "Mark affected plants and re-photo close-ups.", ar: "علّم النباتات المصابة وصوّر قريب تاني." }, lang),
        ]} />
        <PlanCol title={S.next37} items={[
          tr({ en: "Re-inspect marked plants; answer the confirm questions.", ar: "افحص النباتات المعلّمة؛ وجاوب أسئلة التأكيد." }, lang),
          tr({ en: "Verify APC registration before any chemical.", ar: "أكّد تسجيل لجنة المبيدات قبل أي كيماوي." }, lang),
        ]} />
        <PlanCol title={S.callExpertWhen} items={[
          tr({ en: "Spread is fast or many plants are affected.", ar: "الانتشار سريع أو نباتات كتير مصابة." }, lang),
          tr({ en: "You are within the pre-harvest window, or it's a virus.", ar: "إنت قريّب من الحصاد، أو الحالة فيروس." }, lang),
        ]} />
      </div>

      {/* Key decision breakdown */}
      <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
        <Decision label={S.bestOverall} value={wf.confirmed && !lowConf ? tr({ en: "Balanced (once APC verified)", ar: "متوازن (بعد تأكيد لجنة المبيدات)" }, lang) : tr({ en: "Confirm first", ar: "أكّد الأول" }, lang)} />
        <Decision label={S.cheapestSafe} value={tr({ en: "Sanitation only (0 EGP)", ar: "نظافة فقط (٠ ج)" }, lang)} />
        <Decision label={S.strongestAllowed} value={wf.confirmed && wf.apcVerified && !lowConf ? tr({ en: "Strongest (registered dose only)", ar: "الأقوى (بالجرعة المسجّلة بس)" }, lang) : tr({ en: "Locked", ar: "مقفول" }, lang)} />
        <Decision label={S.avoidChoice} value={tr({ en: "Spraying on the AI/photo alone.", ar: "الرش على الذكاء الاصطناعي/الصورة لوحدها." }, lang)} />
      </div>

      <SafetyBlock lang={lang} />
    </Card>
  );
}

function PlanCol({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <p className="mb-1.5 text-sm font-semibold text-emerald-200">{title}</p>
      <BulletList items={items} />
    </div>
  );
}

function Decision({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-2">
      <span className="text-emerald-200/40">{label}:</span> <span className="text-emerald-50">{value}</span>
    </div>
  );
}

export function SafetyBlock({ lang }: { lang: Lang }) {
  const S = STRINGS[lang];
  return (
    <div className="mt-4 rounded-xl border border-rose-500/25 bg-rose-500/[0.05] p-3">
      <p className="mb-2 flex items-center gap-1.5 text-sm font-bold text-rose-200">
        <ShieldCheck size={16} /> {S.safetyTitle}
      </p>
      <ol className="space-y-1.5 text-xs text-rose-50/85">
        {S.safetyRules.map((r, i) => (
          <li key={i} className="flex gap-2">
            <span className="font-bold text-rose-400">{i + 1}.</span>
            <span>{r}</span>
          </li>
        ))}
      </ol>
      <div className="mt-2 flex flex-wrap gap-3 text-xs">
        <a href={APC_PESTICIDE_DB_URL} target="_blank" rel="noreferrer" className="text-sky-300 underline">{S.apcVerify}</a>
        <a href={QCAP_RESIDUE_LAB_URL} target="_blank" rel="noreferrer" className="text-sky-300 underline">{S.qcapResidue}</a>
      </div>
    </div>
  );
}

export const PHASE_ICON = Leaf; // re-exported to keep lucide tree-shake happy
