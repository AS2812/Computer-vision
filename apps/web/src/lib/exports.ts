// Client-side report export: CSV (bilingual, robust UTF-8) + PDF.
//
// PDF note: jsPDF's built-in fonts cannot shape Arabic glyphs, so the jsPDF path
// renders an English data report (reliable everywhere). For a pixel-perfect
// Arabic/RTL document we offer a browser print path (openPrintReport) — the
// browser shapes Arabic correctly and "Save as PDF" produces the file.

import { jsPDF } from "jspdf";
import type { AppAnalysis } from "../appTypes";
import { diseaseByKey, type Lang } from "../data/diseases";
import type { AreaCase } from "../data/economics";
import { fetchTreatmentCatalog } from "./treatments";
import type { Workflow } from "../components/Phases";
import { STRINGS } from "../data/i18n";

function download(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5_000);
}

function csvCell(v: string | number | null | undefined): string {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function exportCsv(analysis: AppAnalysis, cases: AreaCase[], lang: Lang): void {
  const rows: Array<Array<string | number>> = [];
  const s = analysis.screening;
  const topName = s.topKey ? diseaseByKey(s.topKey)?.name : undefined;

  rows.push(["AgroVision Egypt — Tomato screening report"]);
  rows.push(["Generated", new Date(analysis.createdAt).toISOString()]);
  rows.push([]);
  rows.push(["Screening (NOT a confirmed diagnosis)"]);
  rows.push(["Most likely (EN)", topName?.en ?? "not sure"]);
  rows.push(["Most likely (AR)", topName?.ar ?? "غير مؤكد"]);
  rows.push(["Visual match %", Math.round(s.displayConfidence * 100)]);
  rows.push(["Certainty band", s.certainty]);
  rows.push(["State", s.state]);
  rows.push(["AI agreement", s.agreement]);
  rows.push([]);
  rows.push(["Top candidates", "Visual match %"]);
  for (const c of s.candidates) rows.push([`${c.name.en} / ${c.name.ar}`, Math.round(c.prob * 100)]);
  rows.push([]);
  rows.push(["Signals (heuristics)"]);
  rows.push(["Infection extent %", analysis.extent.extentPct]);
  rows.push(["Discoloration %", analysis.extent.discolorationPct]);
  rows.push(["Yellow %", analysis.extent.yellowPct]);
  rows.push(["Dark %", analysis.extent.darkPct]);
  rows.push(["Weather pressure", `${analysis.pressure.score} (${analysis.pressure.level})`]);
  rows.push(["Weather", `${analysis.weather.tempC}C, RH ${analysis.weather.humidityPct ?? "?"}%, ${analysis.weather.condition.en}`]);
  rows.push(["Engine", analysis.local.engine]);
  rows.push(["Check time ms", analysis.local.checkMs]);
  rows.push([]);
  rows.push(["Economics (reference estimate unless you entered real numbers)"]);
  rows.push(["Area", "Sprays", "Treatment EGP", "Loss if ignored EGP", "Saved EGP", "Net benefit EGP", "Worth"]);
  for (const c of cases) {
    const r = (x: { low: number | null; high: number | null }) => `${x.low ?? ""}–${x.high ?? ""}`;
    rows.push([
      lang === "ar" ? c.name.ar : c.name.en,
      r(c.sprays),
      r(c.treatmentCost),
      r(c.lossWithoutAction),
      r(c.savedByActing),
      r(c.netBenefit),
      c.worth,
    ]);
  }

  const csv = "﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\n");
  download(`agrovision-tomato-${analysis.id}.csv`, new Blob([csv], { type: "text/csv;charset=utf-8" }));
}

export async function exportPdf(analysis: AppAnalysis, cases: AreaCase[], lang: Lang, wf: Workflow): Promise<void> {
  const s = analysis.screening;
  const topKey = s.topKey ?? s.candidates[0]?.key ?? null;
  const entry = topKey ? diseaseByKey(topKey) : null;
  const lowConf = s.certainty === "low";

  const printWindow = window.open("", "_blank");
  if (!printWindow) return;

  if (lang === "ar") {
    const topName = entry ? entry.name.ar : "غير مؤكد";
    const certaintyLabel = s.certainty === "high" ? "تأكيد عالي" : s.certainty === "medium" ? "تأكيد متوسط" : "تأكيد منخفض";
    const upgradedCertainty = wf.confirmed ? (s.certainty === "low" ? "تأكيد متوسط" : "تأكيد عالي") : certaintyLabel;
    
    // Formulate cases rows
    let casesRowsHtml = "";
    for (const c of cases) {
      const sprays = `${c.sprays.low}–${c.sprays.high}`;
      const cost = `${c.treatmentCost.low ?? 0}–${c.treatmentCost.high ?? 0}`;
      const loss = `${c.lossWithoutAction.low ?? 0}–${c.lossWithoutAction.high ?? 0}`;
      const benefit = `${c.netBenefit.low ?? 0}–${c.netBenefit.high ?? 0}`;
      const worth = c.worth === "likely_worth" ? "نعم" : c.worth === "ask_engineer" ? "اسأل مهندس" : "لا";
      casesRowsHtml += `
        <tr class="border-b border-emerald-900/10 text-slate-900 text-xs">
          <td class="p-2 font-medium">${c.name.ar}</td>
          <td class="p-2 text-center">${sprays}</td>
          <td class="p-2 text-end">${cost} ج</td>
          <td class="p-2 text-end">${loss} ج</td>
          <td class="p-2 text-end">${benefit} ج</td>
          <td class="p-2 text-center">${worth}</td>
        </tr>
      `;
    }

    // Formulate treatments
    let treatmentsHtml = "";
    const catalog = topKey ? await fetchTreatmentCatalog(topKey) : null;
    if (topKey === "healthy") {
      treatmentsHtml = `
        <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-100 text-xs text-slate-900">
          🌿 مفيش حاجة لعلاجات كيميائية. ورقة النبات تم فحصها وسليمة. استمر في الكشف الدوري والتسميد والنظافة للوقاية.
        </div>
      `;
    } else if (catalog && catalog.treatments && catalog.treatments.length > 0) {
      for (const t of catalog.treatments) {
        treatmentsHtml += `
          <div class="mb-3 p-3 bg-white rounded-xl border border-emerald-100 shadow-sm text-xs text-slate-900">
            <p class="font-bold text-emerald-900">🌿 ${t.name_ar} (FRAC: ${t.frac})</p>
            <p class="text-xs mt-1 text-slate-700"><strong>الجرعة:</strong> ${t.dose_ar} | <strong>فترة الأمان (PHI):</strong> ${t.phi_ar}</p>
            <p class="text-xs text-slate-800 mt-1"><strong>طريقة الاستخدام:</strong> ${t.application_ar}</p>
            ${t.hazard_ar ? `<p class="text-xs text-rose-700 mt-1 font-semibold">⚠️ <strong>تحذير أمان:</strong> ${t.hazard_ar}</p>` : ""}
          </div>
        `;
      }
    } else {
      treatmentsHtml = `
        <div class="p-3 bg-amber-50 rounded-xl border border-amber-100 text-xs text-slate-900">
          🌿 لا يوجد علاج كيميائي موثق لهذه الحالة. ركز على النظافة والوقاية واستشر مهندساً زراعياً.
        </div>
      `;
    }

    // Formulate Phase 3 Answers
    let phase3Html = "";
    const answeredCount = Object.keys(wf.confirmAnswers || {}).length;
    if (answeredCount > 0) {
      phase3Html = `
        <div class="mb-6 bg-emerald-50/50 border border-emerald-100 rounded-2xl p-4">
          <h3 class="text-sm font-bold text-emerald-800 mb-2.5">📋 أسئلة التأكيد الميدانية الإضافية (المرحلة ٣)</h3>
          <div class="grid gap-3 sm:grid-cols-2 text-xs">
      `;
      const questionLabelsAr: Record<string, { q: string; opts: string[] }> = {
        part: { q: "أي جزء مصاب؟", opts: ["ورق سفلي/كبير", "ورق علوي/جديد", "الساق", "الثمرة"] },
        start: { q: "بدأ منين؟", opts: ["الورق الكبير الأول", "منتشر بالتساوي"] },
        speed: { q: "سرعة الانتشار؟", opts: ["بطيء", "متوسط", "سريع"] },
        incidence: { q: "كام نبات من ١٠٠ مصاب؟", opts: ["قليل (<١٠)", "كتير (>٣٠)"] },
        irrigation: { q: "طريقة الري؟", opts: ["تنقيط", "غمر/ترعة", "رشّاش"] },
        nearby: { q: "النباتات القريبة مصابة؟", opts: ["نبات واحد بس", "بقعة كاملة"] },
        harvest: { q: "كام يوم للحصاد؟", opts: ["أكتر من ٢١ يوم", "أقل من ٢١ يوم"] }
      };

      for (const [id, idx] of Object.entries(wf.confirmAnswers)) {
        const qInfo = questionLabelsAr[id];
        if (qInfo) {
          phase3Html += `
            <div class="p-2.5 bg-white rounded-xl border border-emerald-500/10 shadow-sm">
              <span class="text-emerald-700 font-bold block mb-1">${qInfo.q}</span>
              <span class="text-slate-900 font-medium">${qInfo.opts[idx] ?? ""}</span>
            </div>
          `;
        }
      }
      phase3Html += `
          </div>
        </div>
      `;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html dir="rtl" lang="ar">
      <head>
        <title>تقرير فحص AgroVision - ${analysis.id}</title>
        <meta charset="utf-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
          @page { margin: 12mm; background: #042f24; }
          html { background: #042f24; }
          body { 
            font-family: 'Cairo', sans-serif; 
            background-color: #042f24; 
            color: #ecfdf5; 
            background-image: radial-gradient(rgba(110, 231, 183, 0.12) 1px, transparent 0);
            background-size: 24px 24px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          section, section.bg-white, .bg-white {
            background-color: #073d2d !important;
            border-color: rgba(110, 231, 183, 0.22) !important;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.26) !important;
            color: #ffffff !important;
          }
          section p, section li, section td, section th, section span, section div { color: #ffffff !important; }
          section h2, section h3, section strong, section .font-bold { color: #ffffff !important; }
          section .text-slate-900, section .text-rose-950, section .text-black { color: #ffffff !important; }
          section .text-emerald-800 { color: #ffffff !important; }
          section .text-emerald-700 { color: #d9f99d !important; }
          section .text-emerald-500\\/80, section .text-emerald-600\\/70 { color: rgba(240, 253, 244, 0.88) !important; }
          section .text-rose-700, section .text-rose-800 { color: #fda4af !important; }
          section .border-emerald-100, section .border-emerald-50, section .border-rose-100 {
            border-color: rgba(110, 231, 183, 0.18) !important;
          }
          section .bg-emerald-50 {
            background-color: #064e3b !important;
            color: #ffffff !important;
          }
          .document-note {
            background: #031f18 !important;
            color: #ffffff !important;
            border: 1px solid rgba(110, 231, 183, 0.28) !important;
            box-shadow: 0 14px 34px rgba(0, 0, 0, 0.22) !important;
          }
          .document-note * {
            color: #ffffff !important;
          }
          @media print { 
            html, body { background-color: #042f24 !important; color: #ecfdf5 !important; background-image: radial-gradient(rgba(110, 231, 183, 0.1) 1px, transparent 0) !important; } 
            section, section.bg-white, .bg-white { background-color: #073d2d !important; color: #ffffff !important; } 
            .no-print { display: none; } 
          }
        </style>
      </head>
      <body class="p-6 max-w-4xl mx-auto">
        <div class="no-print mb-4 flex justify-between items-center bg-emerald-800 text-emerald-50 p-3 rounded-xl shadow-md">
          <span>📄 تقرير فحص ورقة الطماطم (نسخة جاهزة للطباعة / الحفظ كـ PDF)</span>
          <button onclick="window.print()" class="bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-1.5 px-4 rounded-lg cursor-pointer text-xs">اطبع التقرير</button>
        </div>
        <header class="bg-emerald-900 text-emerald-50 p-6 rounded-2xl flex justify-between items-center relative overflow-hidden shadow-lg mb-6">
          <div>
            <h1 class="text-2xl font-bold flex items-center gap-2">
              <span class="text-emerald-400">🍃</span> AgroVision Egypt
            </h1>
            <p class="text-xs text-emerald-200 mt-1">تقرير فرز وفحص صحة الطماطم الميداني</p>
            <p class="text-[10px] text-emerald-300 mt-1">تاريخ الفحص: ${new Date(analysis.createdAt).toLocaleString("ar-EG")}</p>
          </div>
          <!-- Leaf SVG in header -->
          <div class="text-emerald-400 select-none opacity-20 absolute -right-6 -bottom-10 w-32 h-32 pointer-events-none">
            <svg viewBox="0 0 200 240" fill="none" class="w-full h-full" xmlns="http://www.w3.org/2000/svg">
              <path d="M 100 20 C 135 45, 175 90, 165 140 C 155 190, 120 210, 100 230 C 80 210, 45 190, 35 140 C 25 90, 65 45, 100 20 Z" fill="currentColor"/>
              <path d="M 100 20 L 100 235" stroke="white" stroke-width="4" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="flex gap-1 items-center bg-emerald-800/80 px-3 py-1 rounded-full text-xs font-semibold text-emerald-300 border border-emerald-700/50 shadow-sm z-10">
            <span class="animate-pulse">🌿</span> ثيم أوراق الشجر نشط
          </div>
        </header>
        <section class="document-note p-4 rounded-2xl mb-6 text-xs leading-relaxed">
          <h2 class="text-sm font-bold mb-2">ملخص توثيق التقرير</h2>
          <p>هذا التقرير يوثق صورة الورقة، نتيجة الفرز، مؤشرات جودة الصورة، ضغط الطقس، بدائل التشخيص، وخطة التعامل. الأرقام إرشادية للفحص الحقلي ولا تغني عن تأكيد مهندس زراعي أو معمل قبل أي رش.</p>
        </section>
        <div class="space-y-6">
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 1. تشخيص الفرز المبدئي</h2>
            <div class="grid gap-3 sm:grid-cols-2 text-xs">
              <div><span class="text-emerald-700 block font-semibold">الحالة المرجحة:</span> <span class="text-slate-900 font-bold text-sm">${topName}</span></div>
              <div><span class="text-emerald-700 block font-semibold">نسبة التطابق البصري:</span> <span class="text-slate-900 font-bold">${Math.round(s.displayConfidence * 100)}%</span></div>
              <div><span class="text-emerald-700 block font-semibold">مستوى التأكيد:</span> <span class="text-slate-900 font-bold">${upgradedCertainty}</span></div>
              <div><span class="text-emerald-700 block font-semibold">رأي الذكاء الاصطناعي الثاني:</span> <span class="text-slate-900 font-bold">${s.agreement === "agree" ? "متطابق" : s.agreement === "disagree" ? "مختلف" : "غير متاح"}</span></div>
            </div>
            <p class="text-[10px] text-emerald-500/80 mt-3 border-t border-emerald-50 pt-2">ملاحظة: هذه قيمة تطابق بصري ميكانيكية استرشادية، وليست تحليلاً معملياً دقيقاً.</p>
          </section>
          ${phase3Html}
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 2. الاحتمالات البديلة القريبة</h2>
            <ul class="space-y-1.5 text-xs text-slate-900">${s.candidates.map((c) => `<li>🌿 ${c.name.ar} — تطابق بصري: ${Math.round(c.prob * 100)}%</li>`).join("")}</ul>
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 3. المؤشرات البصرية وضغط الطقس</h2>
            <div class="grid gap-3 sm:grid-cols-2 text-xs">
              <div><span class="text-emerald-700 block font-semibold">مدى الإصابة التقريبي:</span> <span class="text-rose-700 font-bold text-sm">${analysis.extent.extentPct}%</span></div>
              <div><span class="text-emerald-700 block font-semibold">تفاصيل الألوان:</span> <span class="text-slate-900">تغير اللون: ${analysis.extent.discolorationPct}% | بكسلات صفرا: ${analysis.extent.yellowPct}% | بكسلات غامقة: ${analysis.extent.darkPct}%</span></div>
              <div><span class="text-emerald-700 block font-semibold">مستوى ضغط الطقس:</span> <span class="text-slate-900 font-bold">${analysis.pressure.score}/100 (${analysis.pressure.level === "high" ? "مرتفع" : analysis.pressure.level === "medium" ? "متوسط" : "منخفض"})</span></div>
              <div><span class="text-emerald-700 block font-semibold">طقس وقت التحليل:</span> <span class="text-slate-900">${analysis.weather.tempC}°م | رطوبة: ${analysis.weather.humidityPct ?? "?"}% | ${analysis.weather.condition.ar ?? ""}</span></div>
            </div>
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 4. الجدوى الاقتصادية وتحليل التكلفة/العائد</h2>
            <div class="overflow-x-auto"><table class="w-full text-xs text-right border-collapse text-slate-900"><thead><tr class="bg-emerald-50 text-emerald-800 border-b border-emerald-200"><th class="p-2">الحجم</th><th class="p-2 text-center">الرشات</th><th class="p-2 text-end">تكلفة الرش</th><th class="p-2 text-end">الخسارة المقدرة</th><th class="p-2 text-end">العائد الصافي</th><th class="p-2 text-center">يستاهل؟</th></tr></thead><tbody>${casesRowsHtml}</tbody></table></div>
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 5. كتالوج العلاج المعتمد والمراجَع</h2>
            ${treatmentsHtml}
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 6. القرارات الرئيسية الموصى بها</h2>
            <div class="grid gap-3 sm:grid-cols-2 text-xs">
              <div><span class="text-emerald-700 block font-semibold">أفضل خيار إجمالاً:</span> <span class="text-slate-900 font-bold">${wf.confirmed && !lowConf ? "متوازن (بعد تأكيد لجنة المبيدات)" : "أكّد الأول"}</span></div>
              <div><span class="text-emerald-700 block font-semibold">أرخص خيار آمن:</span> <span class="text-slate-900 font-bold">نظافة فقط (٠ ج)</span></div>
              <div><span class="text-emerald-700 block font-semibold">أقوى خيار مسموح:</span> <span class="text-slate-900 font-bold">${wf.confirmed && wf.apcVerified && !lowConf ? "الأقوى (بالجرعة المسجّلة بس)" : "مقفول"}</span></div>
              <div><span class="text-emerald-700 block font-semibold">خيار يجب تجنبه:</span> <span class="text-rose-700 font-bold">الرش على الذكاء الاصطناعي/الصورة لوحدها.</span></div>
            </div>
          </section>
          <section class="bg-rose-50/50 p-5 rounded-2xl border border-rose-500/10 text-xs">
            <h2 class="text-base font-bold text-rose-800 border-b border-rose-100 pb-2 mb-3">⚠️ 🍃 7. إرشادات السلامة ولجنة المبيدات</h2>
            <ul class="space-y-1.5 text-rose-950">
              <li>🌿 هذا التقرير هو إشارة فرز استرشادية، وليس بديلاً عن المعمل. أكد التشخيص قبل أي رش.</li>
              <li>🌿 الاستخدام الكيميائي يتطلب مطابقة تسجيل لجنة المبيدات (APC) للمحصول (طماطم) والآفة المحددة.</li>
              <li>🌿 التزم بجرعة الملصق الرسمية، مهمات الوقاية، فترة الأمان قبل الدخول (REI)، وفترة الأمان قبل الحصاد (PHI).</li>
              <li>🌿 يجب الحصول على موافقة مهندس زراعي مصري معتمد قبل الشروع في استخدام أي مبيد كيميائي.</li>
            </ul>
          </section>
        </div>
        <footer class="mt-8 text-center text-[10px] text-emerald-600/70 border-t border-emerald-100 pt-4">
          AgroVision مصر · جميع حقوق المعرفة والنصوص مراجعة طبقاً للممارسات الزراعية المصرية.
        </footer>
      </body>
      </html>
    `);
    printWindow.document.close();
  } else {
    const topName = entry ? entry.name.en : "Unconfirmed";
    const certaintyLabel = s.certainty === "high" ? "High certainty" : s.certainty === "medium" ? "Medium certainty" : "Low certainty";
    const upgradedCertainty = wf.confirmed ? (s.certainty === "low" ? "Medium certainty" : "High certainty") : certaintyLabel;
    
    // Formulate cases rows
    let casesRowsHtml = "";
    for (const c of cases) {
      const sprays = `${c.sprays.low}–${c.sprays.high}`;
      const cost = `${c.treatmentCost.low ?? 0}–${c.treatmentCost.high ?? 0}`;
      const loss = `${c.lossWithoutAction.low ?? 0}–${c.lossWithoutAction.high ?? 0}`;
      const benefit = `${c.netBenefit.low ?? 0}–${c.netBenefit.high ?? 0}`;
      const worth = c.worth === "likely_worth" ? "Yes" : c.worth === "ask_engineer" ? "Ask engineer" : "No";
      casesRowsHtml += `
        <tr class="border-b border-emerald-900/10 text-slate-900 text-xs">
          <td class="p-2 font-medium">${c.name.en}</td>
          <td class="p-2 text-center">${sprays}</td>
          <td class="p-2 text-end">${cost} EGP</td>
          <td class="p-2 text-end">${loss} EGP</td>
          <td class="p-2 text-end">${benefit} EGP</td>
          <td class="p-2 text-center">${worth}</td>
        </tr>
      `;
    }

    // Formulate treatments
    let treatmentsHtml = "";
    const catalog = topKey ? await fetchTreatmentCatalog(topKey) : null;
    if (topKey === "healthy") {
      treatmentsHtml = `
        <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-100 text-xs text-slate-900">
          🌿 No chemical treatments needed. The plant leaf was checked and is healthy. Continue routine scouting, proper fertilizing, and general hygiene for prevention.
        </div>
      `;
    } else if (catalog && catalog.treatments && catalog.treatments.length > 0) {
      for (const t of catalog.treatments) {
        treatmentsHtml += `
          <div class="mb-3 p-3 bg-white rounded-xl border border-emerald-100 shadow-sm text-xs text-slate-900">
            <p class="font-bold text-emerald-900">🌿 ${t.name_en} (FRAC: ${t.frac})</p>
            <p class="text-xs mt-1 text-slate-700"><strong>Dosage:</strong> ${t.dose_en} | <strong>Pre-Harvest Interval (PHI):</strong> ${t.phi_en}</p>
            <p class="text-xs text-slate-800 mt-1"><strong>Application:</strong> ${t.application_en}</p>
            ${t.hazard_en ? `<p class="text-xs text-rose-700 mt-1 font-semibold">⚠️ <strong>Safety Hazard:</strong> ${t.hazard_en}</p>` : ""}
          </div>
        `;
      }
    } else {
      treatmentsHtml = `
        <div class="p-3 bg-amber-50 rounded-xl border border-amber-100 text-xs text-slate-900">
          🌿 No chemical treatments documented for this case. Focus on prevention/hygiene and consult an agricultural engineer.
        </div>
      `;
    }

    // Formulate Phase 3 Answers
    let phase3Html = "";
    const answeredCount = Object.keys(wf.confirmAnswers || {}).length;
    if (answeredCount > 0) {
      phase3Html = `
        <div class="mb-6 bg-emerald-50/50 border border-emerald-100 rounded-2xl p-4">
          <h3 class="text-sm font-bold text-emerald-800 mb-2.5">📋 Additional Field Confirmation Questions (Phase 3)</h3>
          <div class="grid gap-3 sm:grid-cols-2 text-xs">
      `;
      const questionLabelsEn: Record<string, { q: string; opts: string[] }> = {
        part: { q: "Which part is affected?", opts: ["Lower/older leaves", "Upper/new leaves", "Stem", "Fruit"] },
        start: { q: "Where did it start?", opts: ["Older leaves first", "Uniform all over"] },
        speed: { q: "Spread speed?", opts: ["Slow", "Moderate", "Fast"] },
        incidence: { q: "Plants per 100 affected?", opts: ["A few (<10)", "Many (>30)"] },
        irrigation: { q: "Irrigation method?", opts: ["Drip", "Flood/canal", "Sprinkler"] },
        nearby: { q: "Are nearby plants affected?", opts: ["Just one plant", "A whole patch"] },
        harvest: { q: "Days to harvest?", opts: [">21 days", "<21 days (PHI matters)"] }
      };

      for (const [id, idx] of Object.entries(wf.confirmAnswers)) {
        const qInfo = questionLabelsEn[id];
        if (qInfo) {
          phase3Html += `
            <div class="p-2.5 bg-white rounded-xl border border-emerald-500/10 shadow-sm">
              <span class="text-emerald-700 font-bold block mb-1">${qInfo.q}</span>
              <span class="text-slate-900 font-medium">${qInfo.opts[idx] ?? ""}</span>
            </div>
          `;
        }
      }
      phase3Html += `
          </div>
        </div>
      `;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html dir="ltr" lang="en">
      <head>
        <title>AgroVision Screening Report - ${analysis.id}</title>
        <meta charset="utf-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
          @page { margin: 12mm; background: #042f24; }
          html { background: #042f24; }
          body { 
            font-family: 'Outfit', sans-serif; 
            background-color: #042f24; 
            color: #ecfdf5; 
            background-image: radial-gradient(rgba(110, 231, 183, 0.12) 1px, transparent 0);
            background-size: 24px 24px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          section, section.bg-white, .bg-white {
            background-color: #073d2d !important;
            border-color: rgba(110, 231, 183, 0.22) !important;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.26) !important;
            color: #ffffff !important;
          }
          section p, section li, section td, section th, section span, section div { color: #ffffff !important; }
          section h2, section h3, section strong, section .font-bold { color: #ffffff !important; }
          section .text-slate-900, section .text-rose-950, section .text-black { color: #ffffff !important; }
          section .text-emerald-800 { color: #ffffff !important; }
          section .text-emerald-700 { color: #d9f99d !important; }
          section .text-emerald-500\\/80, section .text-emerald-600\\/70 { color: rgba(240, 253, 244, 0.88) !important; }
          section .text-rose-700, section .text-rose-800 { color: #fda4af !important; }
          section .border-emerald-100, section .border-emerald-50, section .border-rose-100 {
            border-color: rgba(110, 231, 183, 0.18) !important;
          }
          section .bg-emerald-50 {
            background-color: #064e3b !important;
            color: #ffffff !important;
          }
          .document-note {
            background: #031f18 !important;
            color: #ffffff !important;
            border: 1px solid rgba(110, 231, 183, 0.28) !important;
            box-shadow: 0 14px 34px rgba(0, 0, 0, 0.22) !important;
          }
          .document-note * {
            color: #ffffff !important;
          }
          @media print { 
            html, body { background-color: #042f24 !important; color: #ecfdf5 !important; background-image: radial-gradient(rgba(110, 231, 183, 0.1) 1px, transparent 0) !important; } 
            section, section.bg-white, .bg-white { background-color: #073d2d !important; color: #ffffff !important; } 
            .no-print { display: none; } 
          }
        </style>
      </head>
      <body class="p-6 max-w-4xl mx-auto">
        <div class="no-print mb-4 flex justify-between items-center bg-emerald-800 text-emerald-50 p-3 rounded-xl shadow-md">
          <span>📄 Tomato Leaf Screening Report (Print-ready / Save as PDF)</span>
          <button onclick="window.print()" class="bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-1.5 px-4 rounded-lg cursor-pointer text-xs">Print Report</button>
        </div>
        <header class="bg-emerald-900 text-emerald-50 p-6 rounded-2xl flex justify-between items-center relative overflow-hidden shadow-lg mb-6">
          <div>
            <h1 class="text-2xl font-bold flex items-center gap-2">
              <span class="text-emerald-400">🍃</span> AgroVision Egypt
            </h1>
            <p class="text-xs text-emerald-200 mt-1">Tomato Field Screening & Health Report</p>
            <p class="text-[10px] text-emerald-300 mt-1">Screening Date: ${new Date(analysis.createdAt).toLocaleString("en-US")}</p>
          </div>
          <!-- Leaf SVG in header -->
          <div class="text-emerald-400 select-none opacity-20 absolute -right-6 -bottom-10 w-32 h-32 pointer-events-none">
            <svg viewBox="0 0 200 240" fill="none" class="w-full h-full" xmlns="http://www.w3.org/2000/svg">
              <path d="M 100 20 C 135 45, 175 90, 165 140 C 155 190, 120 210, 100 230 C 80 210, 45 190, 35 140 C 25 90, 65 45, 100 20 Z" fill="currentColor"/>
              <path d="M 100 20 L 100 235" stroke="white" stroke-width="4" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="flex gap-1 items-center bg-emerald-800/80 px-3 py-1 rounded-full text-xs font-semibold text-emerald-300 border border-emerald-700/50 shadow-sm z-10">
            <span class="animate-pulse">🌿</span> Leaf Theme Active
          </div>
        </header>
        <section class="document-note p-4 rounded-2xl mb-6 text-xs leading-relaxed">
          <h2 class="text-sm font-bold mb-2">Report Documentation Note</h2>
          <p>This report documents the leaf image, screening result, image-quality signals, weather pressure, close alternatives, and action plan. The numbers are field-screening guidance only and should be confirmed by an agronomist or lab before any spray decision.</p>
        </section>
        <div class="space-y-6">
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 1. Initial Screening Diagnosis</h2>
            <div class="grid gap-3 sm:grid-cols-2 text-xs">
              <div><span class="text-emerald-700 block font-semibold">Likely Diagnosis:</span> <span class="text-slate-900 font-bold text-sm">${topName}</span></div>
              <div><span class="text-emerald-700 block font-semibold">Visual Match Percentage:</span> <span class="text-slate-900 font-bold">${Math.round(s.displayConfidence * 100)}%</span></div>
              <div><span class="text-emerald-700 block font-semibold">Certainty Level:</span> <span class="text-slate-900 font-bold">${upgradedCertainty}</span></div>
              <div><span class="text-emerald-700 block font-semibold">AI Second Opinion:</span> <span class="text-slate-900 font-bold">${s.agreement === "agree" ? "Agreed" : s.agreement === "disagree" ? "Disagreed" : "Unavailable"}</span></div>
            </div>
            <p class="text-[10px] text-emerald-500/80 mt-3 border-t border-emerald-50 pt-2">Note: This is an advisory visual screening metric, not a definitive laboratory analysis.</p>
          </section>
          ${phase3Html}
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 2. Alternative Close Candidates</h2>
            <ul class="space-y-1.5 text-xs text-slate-900">${s.candidates.map((c) => `<li>🌿 ${c.name.en} — Visual Match: ${Math.round(c.prob * 100)}%</li>`).join("")}</ul>
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 3. Visual Indicators and Weather Pressure</h2>
            <div class="grid gap-3 sm:grid-cols-2 text-xs">
              <div><span class="text-emerald-700 block font-semibold">Approximate Infection Extent:</span> <span class="text-rose-700 font-bold text-sm">${analysis.extent.extentPct}%</span></div>
              <div><span class="text-emerald-700 block font-semibold">Color Details:</span> <span class="text-slate-900">Discoloration: ${analysis.extent.discolorationPct}% | Yellow pixels: ${analysis.extent.yellowPct}% | Dark pixels: ${analysis.extent.darkPct}%</span></div>
              <div><span class="text-emerald-700 block font-semibold">Weather Pressure Level:</span> <span class="text-slate-900 font-bold">${analysis.pressure.score}/100 (${analysis.pressure.level === "high" ? "High" : analysis.pressure.level === "medium" ? "Medium" : "Low"})</span></div>
              <div><span class="text-emerald-700 block font-semibold">Analysis Time Weather:</span> <span class="text-slate-900">${analysis.weather.tempC}°C | Humidity: ${analysis.weather.humidityPct ?? "?"}% | ${analysis.weather.condition.en ?? ""}</span></div>
            </div>
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 4. Economic Feasibility and Cost/Benefit Analysis</h2>
            <div class="overflow-x-auto">
              <table class="w-full text-xs text-left border-collapse text-slate-900">
                <thead>
                  <tr class="bg-emerald-50 text-emerald-800 border-b border-emerald-200">
                    <th class="p-2">Farm Size</th>
                    <th class="p-2 text-center">Sprays</th>
                    <th class="p-2 text-end">Treatment Cost</th>
                    <th class="p-2 text-end">Est. Loss Ignored</th>
                    <th class="p-2 text-end">Net Benefit</th>
                    <th class="p-2 text-center">Worth Action?</th>
                  </tr>
                </thead>
                <tbody>
                  ${casesRowsHtml}
                </tbody>
              </table>
            </div>
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 5. Certified and Reviewed Treatment Catalog</h2>
            ${treatmentsHtml}
          </section>
          <section class="bg-white p-5 rounded-2xl shadow-sm border border-emerald-500/10">
            <h2 class="text-base font-bold text-emerald-800 border-b border-emerald-100 pb-2 mb-3">🍃 6. Key Recommended Decisions</h2>
            <div class="grid gap-3 sm:grid-cols-2 text-xs">
              <div><span class="text-emerald-700 block font-semibold">Best Overall Option:</span> <span class="text-slate-900 font-bold">${wf.confirmed && !lowConf ? "Balanced Spray (Verify with Pesticide Committee)" : "Confirm First"}</span></div>
              <div><span class="text-emerald-700 block font-semibold">Cheapest Safe Option:</span> <span class="text-slate-900 font-bold">Hygiene Only (0 EGP)</span></div>
              <div><span class="text-emerald-700 block font-semibold">Strongest Allowed Option:</span> <span class="text-slate-900 font-bold">${wf.confirmed && wf.apcVerified && !lowConf ? "Strongest Registered (Strict dosage compliance)" : "Locked (Verify in Phase 4)"}</span></div>
              <div><span class="text-emerald-700 block font-semibold">Option to Avoid:</span> <span class="text-rose-700 font-bold">Spraying based only on screening/visual detection.</span></div>
            </div>
          </section>
          <section class="bg-rose-50/50 p-5 rounded-2xl border border-rose-500/10 text-xs">
            <h2 class="text-base font-bold text-rose-800 border-b border-rose-100 pb-2 mb-3">⚠️ 🍃 7. Safety Guidelines and Pesticide Committee</h2>
            <ul class="space-y-1.5 text-rose-950">
              <li>🌿 This report is a screening signal, not a definitive lab diagnosis. Always confirm before spraying.</li>
              <li>🌿 Chemical modes require APC database verification for both host crop (tomato) and specific target pest.</li>
              <li>🌿 Pesticide usage must strictly comply with official Egyptian labels (dosage, PPE, REI, and PHI).</li>
              <li>🌿 You must obtain approval from a certified Egyptian agricultural engineer before applying any pesticide.</li>
            </ul>
          </section>
        </div>
        <footer class="mt-8 text-center text-[10px] text-emerald-600/70 border-t border-emerald-100 pt-4">
          AgroVision Egypt · All knowledge rights and texts reviewed in accordance with agricultural practices.
        </footer>
      </body>
      </html>
    `);
    printWindow.document.close();
  }
}
