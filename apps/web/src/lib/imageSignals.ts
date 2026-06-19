// ─────────────────────────────────────────────────────────────────────────────
// Pixel HEURISTICS (clearly NOT machine learning). Three jobs:
//   1. Quality gate  — resolution, Laplacian-variance blur, brightness (soft warn).
//   2. Infection extent — HSV pixel split into discoloration / yellow / dark, a
//      ROUGH visual estimate, never a segmentation or a biological severity.
//   3. Green coverage — feeds the tomato-leaf gate in screening.ts.
//
// Everything here is deterministic canvas maths over the pixels. Thresholds are
// labelled heuristics and only ever produce soft warnings; they never block.
// ─────────────────────────────────────────────────────────────────────────────

export interface QualityReport {
  width: number;
  height: number;
  shortEdge: number;
  resolutionOk: boolean;
  /** Variance of the Laplacian — lower means blurrier (heuristic). */
  blurVariance: number;
  blurry: boolean;
  /** Mean luminance 0..255. */
  brightness: number;
  tooDark: boolean;
  tooBright: boolean;
  ok: boolean;
}

export interface InfectionExtent {
  /** Share of plant-ish pixels that look discoloured/yellow/dark (0..100). */
  extentPct: number;
  discolorationPct: number;
  yellowPct: number;
  darkPct: number;
  greenPct: number;
}

const MIN_SHORT_EDGE = 256;
const BLUR_VARIANCE_MIN = 60; // heuristic; below this we suggest a retake
const DARK_MAX = 50;
const BRIGHT_MAX = 225;

/** Draw a source into ImageData, scaled so the longest edge is <= maxSide. */
function toImageData(source: CanvasImageSource, w: number, h: number, maxSide: number): ImageData {
  const scale = Math.min(1, maxSide / Math.max(w, h));
  const dw = Math.max(1, Math.round(w * scale));
  const dh = Math.max(1, Math.round(h * scale));
  const canvas = document.createElement("canvas");
  canvas.width = dw;
  canvas.height = dh;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("2D canvas context unavailable");
  ctx.drawImage(source, 0, 0, dw, dh);
  return ctx.getImageData(0, 0, dw, dh);
}

export function assessQuality(source: CanvasImageSource, width: number, height: number): QualityReport {
  const img = toImageData(source, width, height, 384);
  const { data, width: dw, height: dh } = img;
  const n = dw * dh;

  // Grayscale + mean brightness.
  const gray = new Float32Array(n);
  let sum = 0;
  for (let i = 0; i < n; i++) {
    const b = i * 4;
    const g = 0.299 * data[b] + 0.587 * data[b + 1] + 0.114 * data[b + 2];
    gray[i] = g;
    sum += g;
  }
  const brightness = sum / n;

  // Laplacian (3×3) variance over the interior.
  let lapSum = 0;
  let lapSqSum = 0;
  let count = 0;
  for (let y = 1; y < dh - 1; y++) {
    for (let x = 1; x < dw - 1; x++) {
      const i = y * dw + x;
      const lap = 4 * gray[i] - gray[i - 1] - gray[i + 1] - gray[i - dw] - gray[i + dw];
      lapSum += lap;
      lapSqSum += lap * lap;
      count++;
    }
  }
  const mean = count ? lapSum / count : 0;
  const blurVariance = count ? lapSqSum / count - mean * mean : 0;

  const shortEdge = Math.min(width, height);
  const resolutionOk = shortEdge >= MIN_SHORT_EDGE;
  const blurry = blurVariance < BLUR_VARIANCE_MIN;
  const tooDark = brightness < DARK_MAX;
  const tooBright = brightness > BRIGHT_MAX;

  return {
    width,
    height,
    shortEdge,
    resolutionOk,
    blurVariance: Math.round(blurVariance),
    blurry,
    brightness: Math.round(brightness),
    tooDark,
    tooBright,
    ok: resolutionOk && !blurry && !tooDark && !tooBright,
  };
}

function rgbToHsv(r: number, g: number, b: number): [number, number, number] {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  let h = 0;
  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60;
    if (h < 0) h += 360;
  }
  const s = max === 0 ? 0 : d / max;
  return [h, s, max];
}

export function infectionExtent(source: CanvasImageSource, width: number, height: number): InfectionExtent {
  const img = toImageData(source, width, height, 224);
  const { data, width: dw, height: dh } = img;
  const n = dw * dh;

  const pixelClass = new Uint8Array(n);
  const leafAnchor = new Uint8Array(n);
  let green = 0;
  let yellow = 0;
  let dark = 0;
  let brown = 0; // discoloration / necrosis
  let plantish = 0;

  for (let i = 0; i < n; i++) {
    const b = i * 4;
    const r = data[b];
    const g = data[b + 1];
    const bl = data[b + 2];
    const [h, s, v] = rgbToHsv(r, g, bl);

    // Background guard: near-white / very desaturated bright pixels are skipped.
    // Dark pixels are only counted later when connected to confirmed leaf colors;
    // this prevents tabletop shadows from inflating disease extent.
    const isBackground = (v > 0.92 && s < 0.12) || (s < 0.08 && v > 0.55);

    const greenDominant = g >= r * 0.72 && g >= bl * 0.78;
    const isGreen = h >= 55 && h <= 175 && s > 0.15 && v > 0.16 && greenDominant;
    const isYellow = h >= 35 && h < 68 && s > 0.25 && v > 0.34;
    const isBrown = !isGreen && !isYellow && s > 0.2 && v >= 0.16 && v <= 0.74 && (h < 38 || h > 300);
    const isDarkLeafish = v < 0.24 && s > 0.1 && ((h >= 45 && h <= 180) || (h <= 45 && g >= bl * 0.85));

    if (isGreen) {
      pixelClass[i] = 1;
      leafAnchor[i] = 1;
    } else if (isYellow) {
      pixelClass[i] = 2;
      leafAnchor[i] = 1;
    } else if (isBrown) {
      pixelClass[i] = 3;
      leafAnchor[i] = 1;
    } else if (!isBackground && isDarkLeafish) {
      pixelClass[i] = 4;
    }
  }

  const hasLeafAnchorNearby = (idx: number) => {
    const x = idx % dw;
    const y = Math.floor(idx / dw);
    for (let yy = Math.max(0, y - 2); yy <= Math.min(dh - 1, y + 2); yy++) {
      for (let xx = Math.max(0, x - 2); xx <= Math.min(dw - 1, x + 2); xx++) {
        if (leafAnchor[yy * dw + xx]) return true;
      }
    }
    return false;
  };

  for (let i = 0; i < n; i++) {
    if (pixelClass[i] === 1) {
      green++;
      plantish++;
    } else if (pixelClass[i] === 2) {
      yellow++;
      plantish++;
    } else if (pixelClass[i] === 3) {
      brown++;
      plantish++;
    } else if (pixelClass[i] === 4 && hasLeafAnchorNearby(i)) {
      dark++;
      plantish++;
    }
  }

  const pct = (x: number, base: number) => (base > 0 ? Math.round((x / base) * 1000) / 10 : 0);
  const affected = brown + yellow + dark;
  return {
    extentPct: pct(affected, plantish),
    discolorationPct: pct(brown, plantish),
    yellowPct: pct(yellow, plantish),
    darkPct: pct(dark, plantish),
    greenPct: pct(green, n),
  };
}
