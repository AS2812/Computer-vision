import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bell,
  BellRing,
  Camera,
  CloudSun,
  Cpu,
  Languages,
  Leaf,
  LoaderCircle,
  MapPin,
  Upload,
  X,
  FolderOpen,
  Download,
  FileText,
  BadgeCheck,
  ArrowDownToLine,
  RefreshCw,
} from "lucide-react";
import type { AppAnalysis, CaseStatusKey, Lang, PipelineStage, SavedCase } from "./appTypes";
import { diseaseByKey } from "./data/diseases";
import { generateAreaCases } from "./data/economics";
import { STRINGS } from "./data/i18n";
import { EGYPT_SOURCES, PROVENANCE_HINT, PROVENANCE_LABEL, type Provenance } from "./data/sources";
import { assessQuality, infectionExtent } from "./lib/imageSignals";
import { runLocalInference, sourceFromFile, warmupModel } from "./lib/onnx";
import { requestSecondOpinion, toJpegDataUrl } from "./lib/analyzeClient";
import { fetchTomatoMarketPrice } from "./lib/market";
import { fuseDiagnosis, severityFromExtent } from "./lib/screening";
import { DEFAULT_COORDS, fetchWeather, referenceWeather, weatherPressure } from "./lib/weather";
import { exportCsv, exportPdf } from "./lib/exports";
import {
  Phase1Diagnosis,
  Phase2Protect,
  Phase3Confirm,
  Phase4Treatment,
  Phase5Economics,
  Phase6ActionPlan,
  type Workflow,
} from "./components/Phases";
import { Sidebar } from "./components/Sidebar";
import { LeafSplash } from "./components/LeafSplash";
import { CertaintyChip, ProvenanceBadge } from "./components/ui";
import { usePwa } from "./lib/pwa";

const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const DEFAULT_WF: Workflow = { confirmed: false, apcVerified: false, mode: "confirm_first", farmerArea: null, farmerPrice: null, customTreatmentCost: null, confirmAnswers: {} };

const STAGE_LABEL: Record<PipelineStage, { en: string; ar: string }> = {
  idle: { en: "", ar: "" },
  loading: { en: "Loading the on-device model…", ar: "بنحمّل موديل الجهاز…" },
  quality: { en: "Checking photo quality…", ar: "بنفحص جودة الصورة…" },
  leaf: { en: "Checking it's a tomato leaf…", ar: "بنتأكد إنها ورقة طماطم…" },
  local: { en: "Running on-device diagnosis…", ar: "بنشخّص على الجهاز…" },
  signals: { en: "Reading infection extent & weather…", ar: "بنقرا مدى الإصابة والطقس…" },
  ai: { en: "Asking the AI second opinion…", ar: "بنسأل الرأي الثاني…" },
  done: { en: "Done", ar: "تم" },
  error: { en: "Something went wrong", ar: "حصل خطأ" },
};

export default function App() {
  const [lang, setLang] = useState<Lang>("ar");
  const [analysis, setAnalysis] = useState<AppAnalysis | null>(null);
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [error, setError] = useState("");
  const [wf, setWf] = useState<Workflow>(DEFAULT_WF);
  const [savedCases, setSavedCases] = useState<SavedCase[]>([]);
  const [marketPrice, setMarketPrice] = useState<AppAnalysis["marketPrice"]>(null);
  const [geo, setGeo] = useState<{ lat: number; lon: number } | null>(null);
  const [locPerm, setLocPerm] = useState<"idle" | "requesting" | "granted" | "denied">("idle");
  const [notifPerm, setNotifPerm] = useState<"idle" | "granted" | "denied">("idle");
  // Show the immersive intro once per session, and never for reduced-motion users.
  const [introVisible, setIntroVisible] = useState(() => {
    if (typeof window === "undefined") return true;
    if (prefersReducedMotion()) return false;
    try {
      return sessionStorage.getItem("av_intro_seen") !== "1";
    } catch {
      return true;
    }
  });
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const S = STRINGS[lang];
  const analysesRef = useRef<Record<string, AppAnalysis>>({});
  const pwa = usePwa();

  useEffect(() => {
    warmupModel();
    fetchTomatoMarketPrice().then(setMarketPrice);
  }, []);

  // Keep the document language/direction in sync with the toggle (a11y + RTL).
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  // Drawer behaviour: Escape closes it and the body scroll is locked while open.
  useEffect(() => {
    if (!isSidebarOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsSidebarOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [isSidebarOpen]);

  function dismissIntro() {
    try {
      sessionStorage.setItem("av_intro_seen", "1");
    } catch {
      /* sessionStorage may be unavailable (private mode) — non-fatal */
    }
    setIntroVisible(false);
  }

  function setWfKey<K extends keyof Workflow>(k: K, v: Workflow[K]) {
    setWf((w) => ({ ...w, [k]: v }));
  }

  function requestLocation() {
    if (!("geolocation" in navigator)) return setLocPerm("denied");
    setLocPerm("requesting");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setGeo({ lat: coords.latitude, lon: coords.longitude });
        setLocPerm("granted");
      },
      () => setLocPerm("denied"),
      { enableHighAccuracy: true, timeout: 12_000, maximumAge: 300_000 },
    );
  }

  async function requestNotifications() {
    if (!("Notification" in window)) return setNotifPerm("denied");
    const p = await Notification.requestPermission();
    setNotifPerm(p === "granted" ? "granted" : "denied");
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setStage("loading");
    const previewUrl = URL.createObjectURL(file);
    try {
      const source = await sourceFromFile(file);
      const w = (source as { width?: number }).width ?? (source as HTMLImageElement).naturalWidth ?? 0;
      const h = (source as { height?: number }).height ?? (source as HTMLImageElement).naturalHeight ?? 0;

      setStage("quality");
      const quality = assessQuality(source, w, h);

      setStage("local");
      const local = await runLocalInference(source);

      setStage("signals");
      const extent = infectionExtent(source, w, h);
      const coords = geo ?? DEFAULT_COORDS;
      const weather = (await fetchWeather(coords.lat, coords.lon)) ?? referenceWeather();
      const liveMarket = marketPrice ?? (await fetchTomatoMarketPrice());
      if (liveMarket) setMarketPrice(liveMarket);

      setStage("ai");
      const imageDataUrl = toJpegDataUrl(source, w, h);
      const second = await requestSecondOpinion({
        imageDataUrl,
        localTop3: local.top3.map((c) => ({ key: c.key, prob: c.prob })),
        signals: { extentPct: extent.extentPct, tomatoMass: local.tomatoMass, weatherPressure: undefined },
        lang,
      });
      const ai = second?.ai ?? null;

      const screening = fuseDiagnosis({ local, ai, extent });
      const causeKey = screening.topKey ?? local.candidates[0]?.key;
      const cause = (causeKey && diseaseByKey(causeKey)?.cause) || "fungal";
      const pressure = weatherPressure(cause, weather);

      const id = `case_${Date.now().toString(36)}`;
      const built: AppAnalysis = {
        id,
        fileName: file.name,
        previewUrl,
        imageDataUrl,
        local,
        quality,
        extent,
        weather,
        marketPrice: liveMarket,
        pressure,
        screening,
        aiVisibleSigns: ai?.visibleSigns,
        createdAt: Date.now(),
      };
      analysesRef.current[id] = built;
      setAnalysis(built);
      setWf(DEFAULT_WF);

      const statusKey: CaseStatusKey =
        screening.state === "not_tomato" || screening.state === "not_sure" ? "collecting" : "diagnosis";
      const title = screening.topName ? screening.topName[lang] : S.notSure;
      setSavedCases((cs) => [{ id, title, status: statusKey, topKey: screening.topKey, createdAt: built.createdAt }, ...cs].slice(0, 12));

      if (notifPerm === "granted") {
        try {
          new Notification("AgroVision", { body: lang === "ar" ? "التقرير جاهز" : "Your screening report is ready" });
        } catch {
          /* notifications may require a service worker */
        }
      }
      setStage("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStage("error");
    }
  }

  function selectCase(id: string) {
    const a = analysesRef.current[id];
    if (a) {
      setAnalysis(a);
      setWf(DEFAULT_WF);
      setStage("done");
    }
  }

  const exportCases = useMemo(() => {
    if (!analysis) return [];
    const entry = analysis.screening.topKey ? diseaseByKey(analysis.screening.topKey) : null;
    return generateAreaCases({
      mode: wf.mode,
      severity: severityFromExtent(analysis.extent),
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
    });
  }, [analysis, wf.mode, wf.farmerPrice, wf.farmerArea, analysis?.marketPrice]);

  const busy = stage !== "idle" && stage !== "done" && stage !== "error";
  const ctx = analysis ? { analysis, lang, wf, set: setWfKey } : null;

  return (
    <div dir={lang === "ar" ? "rtl" : "ltr"} className="min-h-screen text-emerald-50">
      {/* Immersive 3D Welcome Splash Screen */}
      {introVisible && (
        <LeafSplash lang={lang} onComplete={dismissIntro} />
      )}

      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-white/10 bg-[#061a15]/90 px-4 py-3 backdrop-blur">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-400/20 text-emerald-300"><Leaf size={20} /></span>
        <div className="leading-tight">
          <strong className="text-base">{S.brand}</strong>
          <div className="text-[11px] text-emerald-200/50">{S.brandTag}</div>
        </div>
        {analysis && (
          <span className="ms-2 hidden items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-emerald-200/70 sm:flex">
            <CloudSun size={13} /> {analysis.weather.tempC}°C · {analysis.weather.condition[lang]}
            <ProvenanceBadge p={analysis.weather.provenance} lang={lang} />
          </span>
        )}
        {pwa.canInstall && (
          <button
            onClick={() => void pwa.promptInstall()}
            className="ms-auto flex items-center gap-1.5 rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-3 py-1.5 text-sm text-emerald-200 hover:bg-emerald-400/20"
            title={lang === "ar" ? "تثبيت التطبيق على جهازك للعمل بدون نت" : "Install the app for offline use"}
          >
            <ArrowDownToLine size={16} /> {lang === "ar" ? "تثبيت" : "Install"}
          </button>
        )}
        <button onClick={() => setLang(lang === "ar" ? "en" : "ar")} className={`${pwa.canInstall ? "" : "ms-auto"} flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-sm hover:border-emerald-400/40`}>
          <Languages size={16} /> {S.toggleTo}
        </button>
      </header>

      {pwa.updateReady && (
        <div className="flex items-center justify-center gap-3 border-b border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-100">
          <RefreshCw size={15} />
          <span>{lang === "ar" ? "في تحديث جديد جاهز." : "A new version is ready."}</span>
          <button
            onClick={pwa.applyUpdate}
            className="rounded-lg bg-emerald-400 px-3 py-1 text-xs font-bold text-emerald-950 hover:bg-emerald-300"
          >
            {lang === "ar" ? "تحديث الآن" : "Update now"}
          </button>
        </div>
      )}

      <main className={`mx-auto max-w-6xl px-4 py-5 immersive-layout-active ${isSidebarOpen ? "blur-content" : ""}`}>
        {/* Permissions + crop-fixed + capture */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 sm:p-6">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/15 px-3 py-1 text-sm font-semibold text-emerald-200"><Leaf size={14} /> {S.cropFixed}</span>
            <span className="text-[11px] text-emerald-200/50">{S.cropFixedNote}</span>
          </div>

          <div className="mb-4 flex flex-wrap gap-2">
            <button onClick={requestLocation} disabled={locPerm === "requesting"} className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs hover:border-emerald-400/40">
              <MapPin size={14} />
              {locPerm === "granted" ? S.locationReady : locPerm === "requesting" ? S.locationRequesting : locPerm === "denied" ? S.locationDenied : S.useLocation}
            </button>
            <button onClick={requestNotifications} className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs hover:border-emerald-400/40">
              {notifPerm === "granted" ? <BellRing size={14} /> : <Bell size={14} />}
              {notifPerm === "granted" ? S.remindersEnabled : notifPerm === "denied" ? S.remindersDenied : S.enableReminders}
            </button>
          </div>
          <p className="mb-3 text-[11px] text-emerald-200/40">{S.gpsExplain}</p>

          <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-center">
            <div>
              <h1 className="text-xl font-bold sm:text-2xl">{S.onePhotoHint}</h1>
              <p className="mt-1 text-sm text-emerald-200/60">{S.privacyNote}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <label className="flex cursor-pointer items-center gap-2 rounded-xl bg-emerald-400 px-5 py-3 text-base font-bold text-emerald-950 hover:bg-emerald-300">
                  <Camera size={20} /> {S.takePhoto}
                  <input type="file" accept="image/*" capture="environment" onChange={onFile} hidden />
                </label>
                <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-base font-semibold hover:border-emerald-400/40">
                  <Upload size={20} /> {S.uploadPhoto}
                  <input type="file" accept="image/*" onChange={onFile} hidden />
                </label>
              </div>
            </div>
            {analysis?.previewUrl && <img src={analysis.previewUrl} alt={lang === "ar" ? "صورة ورقة الطماطم المرفوعة" : "Uploaded tomato leaf photo"} className="h-28 w-28 rounded-xl object-cover sm:h-32 sm:w-32" />}
          </div>

          {busy && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.06] px-3 py-2 text-sm text-emerald-200">
              <LoaderCircle size={16} className="animate-spin" /> {STAGE_LABEL[stage][lang]}
            </div>
          )}
          {error && (
            <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {STAGE_LABEL.error[lang]}: {error}
            </div>
          )}
        </section>

        {/* Screening verdict */}
        {analysis && (
          <section className="mt-4 rounded-2xl border border-white/10 bg-gradient-to-br from-emerald-400/[0.08] to-transparent p-4 sm:p-5">
            <VerdictBlock analysis={analysis} lang={lang} />
          </section>
        )}

        {/* Body: phases */}
        {analysis && ctx && (
          <div className="mt-4 flex flex-col gap-4">
            <Phase1Diagnosis {...ctx} />
            <Phase2Protect {...ctx} />
            <Phase3Confirm {...ctx} />
            <Phase4Treatment {...ctx} />
            <Phase5Economics {...ctx} />
            <Phase6ActionPlan {...ctx} />
          </div>
        )}

        {!analysis && !busy && (
          <section className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-8 text-center">
            <Cpu size={28} className="mx-auto text-emerald-300/50" />
            <p className="mt-2 text-sm text-emerald-200/60">{lang === "ar" ? "حِط صورة ورقة طماطم عشان نبدأ الفحص على جهازك." : "Add a tomato leaf photo to start the on-device check."}</p>
          </section>
        )}

        {/* Saved cases + Downloads + Egypt Sources / Provenance Grid */}
        {(savedCases.length > 0 || analysis) && (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {/* Left Column: History & Downloads */}
            <div className="flex flex-col gap-4">
              {/* History */}
              {savedCases.length > 0 && (
                <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <h2 className="mb-3 flex items-center gap-1.5 text-sm font-bold text-emerald-100">
                    <FolderOpen size={16} /> {S.savedCases}
                  </h2>
                  <ul className="space-y-1.5">
                    {savedCases.map((c) => (
                      <li key={c.id}>
                        <button
                          onClick={() => selectCase(c.id)}
                          className={`flex w-full items-center justify-between gap-2 rounded-lg border px-2.5 py-1.5 text-start hover:border-emerald-400/30 transition cursor-pointer ${
                            analysis?.id === c.id
                              ? "border-emerald-400 bg-emerald-400/10"
                              : "border-white/10 bg-black/20"
                          }`}
                        >
                          <span className="truncate text-xs text-emerald-50">{c.title}</span>
                          <StatusChip status={c.status} lang={lang} />
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Downloads */}
              {analysis && (
                <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="mb-2 flex items-center gap-1.5 text-sm font-bold text-emerald-100">
                    <Download size={16} /> {S.downloads}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => void exportPdf(analysis, exportCases, lang, wf)}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-2 py-2 text-xs text-emerald-100 hover:border-emerald-400/40 cursor-pointer"
                    >
                      <FileText size={14} /> PDF
                    </button>
                    <button
                      onClick={() => exportCsv(analysis, exportCases, lang)}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-2 py-2 text-xs text-emerald-100 hover:border-emerald-400/40 cursor-pointer"
                    >
                      <FileText size={14} /> CSV
                    </button>
                  </div>
                </section>
              )}
            </div>

            {/* Right Column: Egypt Sources & Provenance */}
            <div className="flex flex-col gap-4">
              {/* Egypt sources */}
              <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="mb-2 text-sm font-bold text-emerald-100">{S.egyptSources}</p>
                <ul className="space-y-2">
                  {EGYPT_SOURCES.map((src) => (
                    <li key={src.url + src.title.en} className="text-[11px]">
                      <a href={src.url} target="_blank" rel="noreferrer" className="font-medium text-sky-300 underline">
                        {src.title[lang]}
                      </a>
                      <p className="text-emerald-200/40">
                        {src.organization[lang]} — {src.purpose[lang]}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>

              {/* Provenance info panel */}
              <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="mb-2 flex items-center gap-1.5 text-sm font-bold text-emerald-100">
                  <BadgeCheck size={16} /> {S.provenanceTitle}
                </p>
                <div className="space-y-1.5">
                  {(Object.keys(PROVENANCE_LABEL) as Provenance[]).map((p) => (
                    <div key={p} className="flex items-start gap-2">
                      <ProvenanceBadge p={p} lang={lang} />
                      <span className="text-[11px] text-emerald-200/50">{PROVENANCE_HINT[p][lang]}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        )}

        <footer className="mt-6 border-t border-white/10 pt-4 text-center text-[11px] text-emerald-200/40">
          {lang === "ar"
            ? "AgroVision مصر · إشارة فرز تساعد المهندس الزراعي وما بتغنيش عنه. >٩٠٪ دقة أعلى (هدف تدريب معملي)، النتيجة على الصور الحقيقية أقل."
            : "AgroVision Egypt · A screening signal that supports — never replaces — an agronomist. >90% top-1 is a lab training target, not real-field accuracy."}
        </footer>
      </main>

      {/* Floating Leaf Button to toggle Sidebar */}
      {!introVisible && (
        <button
          onClick={() => setIsSidebarOpen((prev) => !prev)}
          className="floating-leaf-btn"
          title={lang === "ar" ? "المساعد الذكي" : "AI Assistant"}
          aria-label={lang === "ar" ? "فتح مساعد المحصول" : "Open the crop assistant"}
          aria-expanded={isSidebarOpen}
          aria-controls="crop-assistant-drawer"
        >
          <Leaf size={20} className="animate-[spin_10s_linear_infinite]" />
          <span className="text-sm font-bold">{lang === "ar" ? "مساعد المحصول" : "Crop Assistant"}</span>
        </button>
      )}

      {/* Sidebar Drawer */}
      <div className={`sidebar-backdrop ${isSidebarOpen ? "show" : ""}`} onClick={() => setIsSidebarOpen(false)} aria-hidden="true" />
      <aside
        id="crop-assistant-drawer"
        className={`sidebar-drawer ${isSidebarOpen ? "open" : ""}`}
        dir={lang === "ar" ? "rtl" : "ltr"}
        role="dialog"
        aria-modal="true"
        aria-label={lang === "ar" ? "مساعد حالة المحصول" : "Crop Case Assistant"}
        aria-hidden={!isSidebarOpen}
      >
        <div className="flex h-full flex-col p-4 gap-4 overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-400/20 text-emerald-300">
                <Leaf size={16} />
              </span>
              <strong className="text-sm text-emerald-50">{lang === "ar" ? "مساعد حالة المحصول" : "Crop Case Assistant"}</strong>
            </div>
            <button onClick={() => setIsSidebarOpen(false)} className="rounded-lg border border-white/15 bg-white/5 p-1.5 hover:bg-white/10 text-emerald-100 cursor-pointer">
              <X size={16} />
            </button>
          </div>
          <Sidebar
            analysis={analysis}
            lang={lang}
          />
        </div>
      </aside>
    </div>
  );
}

function VerdictBlock({ analysis, lang }: { analysis: AppAnalysis; lang: Lang }) {
  const S = STRINGS[lang];
  const s = analysis.screening;
  const pct = Math.round(s.displayConfidence * 100);

  if (s.state === "not_tomato") {
    return (
      <div>
        <p className="text-lg font-bold text-amber-200">{S.leafGateWarn}</p>
        <p className="mt-1 text-sm text-emerald-200/60">{S.retakeTips}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <CertaintyChip band={s.certainty} lang={lang} />
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-300">{S.notConfirmed}</span>
        <span className="text-[11px] text-emerald-200/50">{S.engine}: {analysis.local.engine} · {S.checkTime}: {analysis.local.checkMs}ms · {S.memoryUsed}: {analysis.local.modelSizeMb}MB</span>
      </div>
      <p className="mt-2 text-xl font-bold text-emerald-50">
        {s.topName
          ? lang === "ar"
            ? `الأرجح (فرز): ${s.topName.ar} (${pct}٪) — ${S.notConfirmed}`
            : `Most likely (screening): ${s.topName.en} (${pct}%) — ${S.notConfirmed}`
          : S.notSure}
      </p>
      <p className="mt-1 text-sm text-emerald-200/70">
        {lang === "ar" ? "ابدأ الحماية، وأكّد قبل أي رش." : "Start protection, and confirm before any spraying."}
      </p>

      {/* Supporting signals */}
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <SignalCard label={S.infectionExtent} value={`${analysis.extent.extentPct}%`} note={`${S.discoloration} ${analysis.extent.discolorationPct}% · ${S.yellowPixels} ${analysis.extent.yellowPct}% · ${S.darkPixels} ${analysis.extent.darkPct}%`} hint={S.infectionExtentNote} />
        <SignalCard label={S.weatherPressure} value={`${analysis.pressure.score}/100 (${analysis.pressure.level})`} note={analysis.pressure.reason[lang]} hint={S.weatherPressureNote} />
        <SignalCard label={S.aiSecondOpinion} value={s.agreement === "agree" ? "✓" : s.agreement === "ai_offline" ? "—" : "≈"} note={analysis.aiVisibleSigns || (s.agreement === "ai_offline" ? S.aiOffline : S.aiCaveat)} hint={S.aiCaveat} />
      </div>

      <ul className="mt-3 space-y-1 text-[11px] text-emerald-200/45">
        {s.notes.slice(0, 4).map((n, i) => (
          <li key={i}>• {n[lang]}</li>
        ))}
      </ul>
    </div>
  );
}

function SignalCard({ label, value, note, hint }: { label: string; value: string; note: string; hint: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3" title={hint}>
      <p className="text-[11px] text-emerald-200/50">{label}</p>
      <p className="mt-0.5 text-lg font-bold text-emerald-50">{value}</p>
      <p className="mt-0.5 text-[11px] text-emerald-200/40">{note}</p>
    </div>
  );
}

function StatusChip({ status, lang }: { status: SavedCase["status"]; lang: Lang }) {
  const S = STRINGS[lang];
  const map = {
    collecting: { t: S.status_collecting, c: "text-amber-300 border-amber-500/30 bg-amber-500/5" },
    needs_expert: { t: S.status_needs_expert, c: "text-rose-300 border-rose-500/30 bg-rose-500/5" },
    diagnosis: { t: S.status_diagnosis, c: "text-sky-300 border-sky-500/30 bg-sky-500/5" },
    economics: { t: S.status_economics, c: "text-violet-300 border-violet-500/30 bg-violet-500/5" },
    report: { t: S.status_report, c: "text-emerald-300 border-emerald-500/30 bg-emerald-500/5" },
  } as const;
  return <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[9px] ${map[status].c}`}>{map[status].t}</span>;
}

