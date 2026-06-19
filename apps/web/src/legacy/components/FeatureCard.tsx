import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  Bot,
  Bug,
  ChevronDown,
  CloudSun,
  Droplets,
  FlaskConical,
  Leaf,
  MapPinned,
  Sprout,
  Stethoscope,
  TrendingUp,
  Wheat,
  X
} from "lucide-react";
import type { FeatureResult } from "../types";
import { copy } from "../i18n";
import { Badge } from "./Badge";

const icons = {
  disease: Bug,
  infection_extent: Activity,
  resistant_varieties: Sprout,
  vegetation: Leaf,
  weeds: Sprout,
  plant_count: Wheat,
  water_stress: Droplets,
  nutrients: FlaskConical,
  pests: Activity,
  suitability: MapPinned,
  yield: TrendingUp,
  weather: CloudSun,
  assistant: Bot
};

export function FeatureCard({ result, arabic }: { result: FeatureResult; arabic: boolean }) {
  const t = copy[arabic ? "ar" : "en"];
  const [open, setOpen] = useState(false);
  const cardRef = useRef<HTMLElement>(null);
  const Icon = icons[result.feature as keyof typeof icons] || Leaf;
  const info = result.feature === "disease" ? null : result.disease_info;

  // Gentle tilt only — the old 13deg rotation + 26px translateZ pop made the card
  // content shift under the cursor, which felt "difficult" and made the toggle hard
  // to click. A small 5deg lean with no Z-pop keeps it smooth and readable.
  function tilt(event: ReactMouseEvent<HTMLElement>) {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;
    el.style.setProperty("--ry", `${(px - 0.5) * 5}deg`);
    el.style.setProperty("--rx", `${(0.5 - py) * 5}deg`);
    el.style.setProperty("--tz", "0px");
    el.style.setProperty("--gx", `${px * 100}%`);
    el.style.setProperty("--gy", `${py * 100}%`);
  }

  function reset() {
    const el = cardRef.current;
    if (!el) return;
    el.style.setProperty("--ry", "0deg");
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--tz", "0px");
  }

  const name = info && (arabic ? info.name_ar : info.name_en);
  const crop = info && (arabic ? info.crop_ar : info.crop_en);
  const summary = info && (arabic ? info.summary_ar : info.summary_en);
  const symptoms = info ? (arabic ? info.symptoms_ar : info.symptoms_en) : [];
  const management = info ? (arabic ? info.management_ar : info.management_en) : [];

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <article className="feature-card" ref={cardRef} onMouseMove={tilt} onMouseLeave={reset}>
      <span className="card-glare" aria-hidden="true" />
      <div className="feature-top">
        <div className="feature-icon"><Icon size={19} /></div>
        <Badge level={result.level} feature={result.feature} arabic={arabic} />
      </div>
      <div>
        <p className="eyebrow">{arabic ? result.title_ar : result.title}</p>
        <h3>{arabic ? result.value_ar : result.value}</h3>
      </div>
      {result.feature !== "resistant_varieties" && (
        <>
          <div className="meter" aria-label={`${result.title} score`}>
            <span style={{ width: `${Math.max(result.score * 100, 3)}%` }} />
          </div>
          <div className="confidence">
            <span>{result.feature === "disease" ? t.matchScore : t.confidence}</span>
            <strong>{Math.round(result.confidence * 100)}%</strong>
          </div>
        </>
      )}

      {result.feature !== "disease" && result.evidence.length > 0 && (
        <ul className="evidence-list">
          {result.evidence.slice(0, 3).map((line) => <li key={line}>{line}</li>)}
        </ul>
      )}

      {info && (
        <div className="disease-block">
          <button type="button" className="disease-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
            <Stethoscope size={14} /> {t.aboutDisease}
            <ChevronDown size={14} className={open ? "chev open" : "chev"} />
          </button>
        </div>
      )}

      {result.limitation && <p className="limitation">{result.limitation}</p>}

      {open && info && createPortal(
        <div className="disease-modal-backdrop" role="presentation" onClick={() => setOpen(false)}>
          <section className="disease-modal" role="dialog" aria-modal="true" aria-labelledby="disease-detail-title" onClick={(event) => event.stopPropagation()}>
            <header>
              <div>
                <p className="eyebrow">{t.aboutDisease}</p>
                <h2 id="disease-detail-title">{name}</h2>
                {crop && <p className="disease-crop">{t.cropLabel}: {crop}</p>}
              </div>
              <button type="button" onClick={() => setOpen(false)} aria-label={t.closeChat}><X size={19} /></button>
            </header>
            <div className="disease-modal-body">
              <section className="diagnosis-summary">
                <p>{summary}</p>
                <strong>{arabic ? result.value_ar : result.value}</strong>
              </section>
              {symptoms.length > 0 && (
                <section>
                  <p className="disease-label">{t.symptoms}</p>
                  <ul>{symptoms.map((line) => <li key={line}>{line}</li>)}</ul>
                </section>
              )}
              {management.length > 0 && (
                <section>
                  <p className="disease-label">{t.management}</p>
                  <ul>{management.map((line) => <li key={line}>{line}</li>)}</ul>
                </section>
              )}
              <p className="disease-disclaimer">{t.diseaseDisclaimer}</p>
            </div>
          </section>
        </div>,
        document.body
      )}
    </article>
  );
}
