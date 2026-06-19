import { ChangeEvent, MouseEvent as ReactMouseEvent, useMemo, useRef, useState } from "react";
import { AlertTriangle, Bell, BellRing, ClipboardCheck, CloudSun, Download, Gauge, Languages, Leaf, ListChecks, LoaderCircle, LocateFixed, MapPin, Upload, Zap } from "lucide-react";
import { api } from "./api";
import { Assistant } from "./components/Assistant";
import { CaseWorkspace } from "./components/CaseWorkspace";
import { FeatureCard } from "./components/FeatureCard";
import { copy } from "./i18n";
import type { Analysis, FusedState } from "./types";

type DevicePermissionState = "idle" | "requesting" | "granted" | "denied" | "unsupported" | "error";

function weatherCodeToCondition(code: number): string {
  if (code === 0) return "clear sky";
  if (code <= 3) return "partly cloudy";
  if (code <= 48) return "fog";
  if (code <= 55) return "drizzle";
  if (code <= 67) return "rain";
  if (code <= 77) return "snow";
  if (code <= 82) return "rain showers";
  if (code <= 99) return "thunderstorm";
  return "cloudy";
}

function symptomsFromAnalysis(analysis: Analysis): string[] {
  const symptomFeatures = new Set(["leaf_yellowing", "dark_spots", "water_stress", "infection_extent"]);
  return Array.from(new Set(
    analysis.results
      .filter((result) => symptomFeatures.has(result.feature) && result.score > 0)
      .map((result) => result.title)
      .filter(Boolean)
  )).slice(0, 8);
}

// One uploaded photo -> one honest headline that tells the farmer which phase they
// are at, derived only from the fused diagnosis state (no extra request).
function phaseHeadline(state: FusedState, arabic: boolean): { phase: string; text: string; tone: "good" | "warn" } {
  switch (state) {
    case "confident":
      return {
        phase: arabic ? "المرحلة ١ — التشخيص جاهز" : "Phase 1 — Diagnosis ready",
        text: arabic
          ? "اتعرف على المرض الأرجح. شوف الخطة الكاملة بالأسفل وأكّد الأعراض قبل العلاج."
          : "The likely disease is identified. See the full action plan below and confirm the symptoms before treating.",
        tone: "good",
      };
    case "screening":
      return {
        phase: arabic ? "المرحلة ١ — فرز مبدئي" : "Phase 1 — Screening",
        text: arabic
          ? "لقينا المرض الأرجح بس مش مؤكد ١٠٠٪. ابدأ خطوات الوقاية وأكّد قبل أي رش."
          : "We found the most likely disease but it is not fully confirmed. Start the protection steps and confirm before any spraying.",
        tone: "warn",
      };
    case "not_tomato":
      return {
        phase: arabic ? "أعد التصوير" : "Retake the photo",
        text: arabic
          ? "الصورة ممكن ما تكونش ورقة طماطم واضحة. صوّر ورقة طماطم من قريب وفي إضاءة كويسة."
          : "This may not be a clear tomato leaf. Retake a close tomato-leaf photo in good light.",
        tone: "warn",
      };
    default:
      return {
        phase: arabic ? "جمع الأدلة" : "Collecting evidence",
        text: arabic
          ? "لسه مش كفاية لتشخيص موثوق. صوّر الورقة من قريب والنبات كله وجاوب على الأسئلة بالأسفل."
          : "Not enough yet for a reliable diagnosis. Retake a close leaf photo plus a whole-plant photo and answer the questions below.",
        tone: "warn",
      };
  }
}

export default function App() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [arabic, setArabic] = useState(false);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState("");
  const crop = "tomato"; // AgroVision focuses on tomato.
  const [initialCaseId, setInitialCaseId] = useState<string | null>(null);
  const [mountCaseWorkspace, setMountCaseWorkspace] = useState(false);
  const [geoCoords, setGeoCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [liveWeather, setLiveWeather] = useState<{ temp_c: number; condition: string; wind_kph: number } | null>(null);
  const [locationPermission, setLocationPermission] = useState<DevicePermissionState>("idle");
  const [notificationPermission, setNotificationPermission] = useState<DevicePermissionState>(() => {
    if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
    return window.Notification.permission === "default" ? "idle" : window.Notification.permission;
  });

  const t = copy[arabic ? "ar" : "en"];
  const heroRef = useRef<HTMLElement>(null);

  function requestLocation() {
    if (!("geolocation" in navigator)) {
      setLocationPermission("unsupported");
      return;
    }
    setLocationPermission("requesting");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const { latitude: lat, longitude: lng } = coords;
        setGeoCoords({ lat, lng });
        setLocationPermission("granted");
        fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto`
        )
          .then((r) => r.json())
          .then((data) => {
            const c = data.current;
            setLiveWeather({
              temp_c: Math.round(c.temperature_2m as number),
              wind_kph: Math.round(c.wind_speed_10m as number),
              condition: weatherCodeToCondition(c.weather_code as number),
            });
          })
          .catch(() => {});
      },
      (reason) => setLocationPermission(reason.code === reason.PERMISSION_DENIED ? "denied" : "error"),
      { enableHighAccuracy: true, timeout: 12_000, maximumAge: 5 * 60_000 }
    );
  }

  async function requestNotifications() {
    if (!("Notification" in window)) {
      setNotificationPermission("unsupported");
      return;
    }
    setNotificationPermission("requesting");
    const permission = await window.Notification.requestPermission();
    setNotificationPermission(permission === "default" ? "idle" : permission);
  }

  function notifyCaseReady(location: string) {
    if (!("Notification" in window) || window.Notification.permission !== "granted") return;
    try {
      new window.Notification("AgroVision case ready", {
        body: `The crop photo and action plan were saved for ${location || "your tomato case"}.`,
      });
    } catch {
      // Some browsers require notifications to be created by a service worker.
    }
  }

  function heroParallax(event: ReactMouseEvent<HTMLElement>) {
    const el = heroRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--px", ((event.clientX - rect.left) / rect.width - 0.5).toFixed(3));
    el.style.setProperty("--py", ((event.clientY - rect.top) / rect.height - 0.5).toFixed(3));
  }

  function resetHero() {
    const el = heroRef.current;
    if (!el) return;
    el.style.setProperty("--px", "0");
    el.style.setProperty("--py", "0");
  }

  const realResultCount = useMemo(
    () => analysis?.results.filter((item) => item.level !== "sample-data").length || 0,
    [analysis]
  );

  function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const url = URL.createObjectURL(file);
      setPreview((old) => {
        if (old) URL.revokeObjectURL(old);
        return url;
      });
    } catch {
      /* object URLs are unavailable in some test environments */
    }
    void analyzeAndBuild(file);
  }

  // One photo drives everything: the fused diagnosis, then the full 6-phase plan —
  // reusing the SAME diagnosis so the slow vision model only runs once.
  async function analyzeAndBuild(file: File) {
    setLoading(true);
    setError("");
    try {
      const result = await api.analyze(file, crop, geoCoords?.lat, geoCoords?.lng);
      setAnalysis(result);
      await buildCaseFromAnalysis(result);
    } catch (reason) {
      if (reason instanceof TypeError) {
        setError("Cannot reach backend — make sure the FastAPI server is running on port 8765");
      } else {
        setError(reason instanceof Error ? reason.message : "Analysis failed");
      }
    } finally {
      setLoading(false);
    }
  }

  async function buildCaseFromAnalysis(result: Analysis) {
    setMountCaseWorkspace(true);
    setBuilding(true);
    try {
      const newCase = await api.createCase({
        crop: "tomato",
        location: geoCoords
          ? `Current device GPS ${geoCoords.lat.toFixed(5)}, ${geoCoords.lng.toFixed(5)}`
          : "",
        symptoms: symptomsFromAnalysis(result),
      });
      if (geoCoords) {
        await api.addCaseObservations(
          newCase.case_id,
          {
            device_latitude: Number(geoCoords.lat.toFixed(6)),
            device_longitude: Number(geoCoords.lng.toFixed(6)),
            location_capture_method:
              "Current device GPS at analysis time; not verified as the photo capture location.",
          },
          "device_sensor"
        );
      }
      await api.addCaseObservations(
        newCase.case_id,
        {
          analysis_processing_ms: result.processing_ms,
          analysis_peak_memory_mb: Number(result.peak_memory_mb.toFixed(2)),
          analysis_provider: result.provider,
          analysis_results_count: result.results.length,
          ...(result.fused_state ? { analysis_fused_state: result.fused_state } : {})
        },
        "image_model"
      );
      if (result.image_measurements && Object.keys(result.image_measurements).length > 0) {
        await api.addCaseObservations(
          newCase.case_id,
          result.image_measurements,
          "image_measurement"
        );
      }
      const diseaseCard = result.results.find((item) => item.feature === "disease");
      const candidates = result.diagnosis_candidates ?? [];
      if (candidates.length) {
        await api.setCaseDiagnosis(newCase.case_id, {
          candidates,
          evidence: diseaseCard?.evidence ?? [],
          missing_info: diseaseCard?.limitation ? [diseaseCard.limitation] : [],
        });
      }
      setInitialCaseId(newCase.case_id);
      notifyCaseReady(newCase.location);
    } catch (reason) {
      // Non-fatal: the photo result still shows even if the deeper plan fails to build.
      setError(reason instanceof Error ? reason.message : "Could not build the full action plan");
    } finally {
      setBuilding(false);
    }
  }

  const headline = analysis ? phaseHeadline((analysis.fused_state ?? "") as FusedState, arabic) : null;

  return (
    <div className="app-shell" dir={arabic ? "rtl" : "ltr"}>
      <div className="aurora" aria-hidden="true">
        <span className="orb orb-1" />
        <span className="orb orb-2" />
        <span className="orb orb-3" />
      </div>
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><Leaf size={22} /></span>
          <div><strong>AgroVision</strong><small>{t.brandTag}</small></div>
        </div>
        {liveWeather && (
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#9bb8ab", background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)", borderRadius: "8px", padding: "5px 10px", flexShrink: 0 }}>
            <CloudSun size={14} />
            <span>{liveWeather.temp_c}°C · {liveWeather.condition} · {liveWeather.wind_kph} km/h</span>
            <MapPin size={12} style={{ color: "#b9ec61" }} aria-label="Live GPS" />
          </div>
        )}
        <button className="ghost-button" onClick={() => setArabic((value) => !value)}>
          <Languages size={17} /> {arabic ? "English" : "العربية"}
        </button>
      </header>
      <section className="device-permissions" aria-label="Device permissions">
        <div>
          <strong>{arabic ? "خدمات الجهاز" : "Device services"}</strong>
          <span>
            {arabic
              ? "استخدم الموقع لملء بيانات الحالة، وفعل الإشعارات للمتابعة."
              : "GPS is used only after permission and records the device position at analysis time, not an unverified photo capture location. Enable browser reminders separately."}
          </span>
        </div>
        <button type="button" className="ghost-button" onClick={requestLocation} disabled={locationPermission === "requesting"}>
          {locationPermission === "granted" ? <MapPin size={16} /> : <LocateFixed size={16} />}
          {locationPermission === "granted"
            ? (arabic ? "الموقع جاهز" : "Location ready")
            : locationPermission === "requesting"
            ? (arabic ? "جاري طلب الموقع" : "Requesting location")
            : locationPermission === "denied"
            ? (arabic ? "الموقع مرفوض" : "Location denied")
            : locationPermission === "unsupported" || locationPermission === "error"
            ? (arabic ? "الموقع غير متاح" : "Location unavailable")
            : (arabic ? "استخدم موقعي" : "Use my location")}
        </button>
        <button type="button" className="ghost-button" onClick={() => void requestNotifications()} disabled={notificationPermission === "requesting"}>
          {notificationPermission === "granted" ? <BellRing size={16} /> : <Bell size={16} />}
          {notificationPermission === "granted"
            ? (arabic ? "الإشعارات مفعلة" : "Reminders enabled")
            : notificationPermission === "requesting"
            ? (arabic ? "جاري طلب الإذن" : "Requesting permission")
            : notificationPermission === "denied"
            ? (arabic ? "الإشعارات مرفوضة" : "Notifications denied")
            : notificationPermission === "unsupported"
            ? (arabic ? "الإشعارات غير متاحة" : "Notifications unavailable")
            : (arabic ? "فعل التذكيرات" : "Enable reminders")}
        </button>
      </section>

      {/* ── Single photo-driven flow ── */}
      <main id="photo-section">
        <section className="hero" ref={heroRef} onMouseMove={heroParallax} onMouseLeave={resetHero}>
          <div className="hero-copy">
            <p className="kicker"><span /> {t.kicker}</p>
            <h1>{t.heroTitle}</h1>
            <p>{t.heroBody}</p>
            <div className="hero-actions">
              <div className="crop-chip" aria-label={arabic ? "المحصول" : "Crop"}>
                <Leaf size={15} /> {arabic ? "طماطم" : "Tomato"}
              </div>
              <label className="primary-button">
                <Upload size={18} /> {t.analyzeImage}
                <input type="file" accept="image/*" capture="environment" onChange={upload} hidden />
              </label>
            </div>
            {error && <p className="error-message">{error}</p>}
          </div>
          <div className="hero-panel">
            {preview ? (
              <img src={preview} alt={analysis?.filename || "Field image"} className="hero-img" />
            ) : (
              <div className="hero-placeholder">
                <span className="hero-scan" />
                <Leaf size={38} />
                <p>{t.previewHint}</p>
              </div>
            )}
            {preview && (
              <div className="map-overlay">
                <span>{analysis?.filename ?? t.previewIdle}</span>
                <strong>{t.previewReady}</strong>
              </div>
            )}
          </div>
        </section>

        {loading && <div className="loading-panel"><LoaderCircle className="spin" /> {t.processingLocally}</div>}

        {analysis ? (
          <>
            {headline && (
              <section
                className="phase-headline"
                style={{
                  display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px 14px",
                  margin: "18px 0", padding: "14px 18px", borderRadius: "14px",
                  border: `1px solid ${headline.tone === "good" ? "rgba(185,236,97,.35)" : "rgba(240,200,105,.35)"}`,
                  background: headline.tone === "good" ? "rgba(185,236,97,.07)" : "rgba(240,200,105,.07)",
                }}
              >
                <ListChecks size={18} style={{ color: headline.tone === "good" ? "#b9ec61" : "#f0c869", flexShrink: 0 }} />
                <strong style={{ color: headline.tone === "good" ? "#cdf58a" : "#f3d489" }}>{headline.phase}</strong>
                <span style={{ color: "#9bb8ab", fontSize: "13px", flex: "1 1 280px" }}>{headline.text}</span>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={() => document.getElementById("case-section")?.scrollIntoView?.({ behavior: "smooth" })}
                >
                  {building ? <LoaderCircle size={15} className="spin" /> : <ListChecks size={15} />}
                  {arabic ? "الخطة الكاملة" : "Full action plan"}
                </button>
              </section>
            )}

            <section className="status-row">
              <div><Gauge /><span>{t.processing}</span><strong>{analysis.processing_ms} ms</strong></div>
              <div><Leaf /><span>{t.realResults}</span><strong>{realResultCount} / {analysis.results.length}</strong></div>
              <div><Zap /><span>{t.runtime}</span><strong>{analysis.provider}</strong></div>
              <div><Gauge /><span>{t.processMemory}</span><strong>{analysis.peak_memory_mb} MB</strong></div>
            </section>

            {analysis.alerts.length > 0 && (
              <section className="alerts">
                <div className="section-heading"><div><p className="eyebrow">{t.safetyReview}</p><h2>{t.actionableAlerts}</h2></div></div>
                {analysis.alerts.map((alert) => <p key={alert.en}><AlertTriangle size={18} /> {arabic ? alert.ar : alert.en}</p>)}
              </section>
            )}

            <section className="results-section">
              <div className="section-heading">
                <div><p className="eyebrow">{t.analysisSuite}</p><h2>{analysis.filename}</h2></div>
                <div className="report-actions">
                  <a href={api.reportUrl(analysis.analysis_id, "pdf")}><Download size={16} /> PDF</a>
                  <a href={api.reportUrl(analysis.analysis_id, "csv")}><Download size={16} /> CSV</a>
                </div>
              </div>
              <div className="feature-grid">
                {analysis.results.map((result) => <FeatureCard key={result.feature} result={result} arabic={arabic} />)}
              </div>
            </section>

            {analysis.recommendations.length > 0 && (
              <section className="recommendations">
                <div className="section-heading"><div><p className="eyebrow">{t.nextSteps}</p><h2>{t.recommendedSteps}</h2></div></div>
                <ul>
                  {analysis.recommendations.map((step) => (
                    <li key={step.en}><ClipboardCheck size={16} /> {arabic ? step.ar : step.en}</li>
                  ))}
                </ul>
              </section>
            )}
          </>
        ) : (
          <section className="empty-state">
            <p className="eyebrow">{t.readyEyebrow}</p>
            <h2>{t.readyTitle}</h2>
            <p>{t.readyBody}</p>
          </section>
        )}
      </main>

      {/* ── Full 6-phase action plan, auto-built from the same photo ── */}
      <div id="case-section">
        {mountCaseWorkspace && (
          <CaseWorkspace
            arabic={arabic}
            initialCaseId={initialCaseId}
            onClearInitialCaseId={() => setInitialCaseId(null)}
            geoCoords={geoCoords}
            previewUrl={preview}
          />
        )}
      </div>

      <footer><span>{t.footer}</span></footer>
      <Assistant analysisId={analysis?.analysis_id} arabic={arabic} quickQuestions={analysis?.assistant_questions} />
    </div>
  );
}
