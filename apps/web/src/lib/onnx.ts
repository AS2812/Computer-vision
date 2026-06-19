// ─────────────────────────────────────────────────────────────────────────────
// In-browser tomato disease inference ("Checked on your device").
//
// Runs the PlantVillage MobileNetV2 ONNX model with onnxruntime-web, fully on
// device. It replicates the server's `mobilenet_pv` preprocessing EXACTLY (see
// services/api/app/model_runtime.py) — get this wrong and predictions are noise:
//   1. resize the SHORTEST edge to 256 (bilinear),
//   2. center-crop 224×224,
//   3. scale 1/255, then normalize (x − 0.5) / 0.5  →  [-1, 1],
//   4. NCHW layout, float32.
//
// The model has 38 PlantVillage classes. We softmax all 38, then CROP-CONDITION
// to the 10 tomato classes (indices 28–37): the tomato mass and the top-2 tomato
// margin feed the tomato-leaf gate. Confidence is the RENORMALISED tomato top-1 —
// an uncalibrated visual-match value, never a probability the diagnosis is right.
// ─────────────────────────────────────────────────────────────────────────────

import * as ort from "onnxruntime-web";
import type { Bi } from "../data/diseases";
import { HEALTHY, TOMATO_DISEASES } from "../data/diseases";

// Where ORT loads its wasm runtime from. onnxruntime-web's package `exports` map
// blocks deep `./dist/*` imports (so we can't `?url` the wasm), and self-hosting it
// from /public makes ORT import its `.mjs` glue from /public — which Vite refuses to
// transform in dev. Pointing wasmPaths at the version-matched CDN is the robust path:
// a full URL Vite leaves alone, served with the correct MIME + CORS, working in dev
// AND build. The MODEL and INFERENCE still run ON DEVICE; only the wasm runtime
// (HTTP-cached after the first load) comes from the CDN. Keep ORT_VERSION in sync
// with the pinned onnxruntime-web in package.json.
const ORT_VERSION = "1.26.0";
ort.env.wasm.numThreads = 1; // single-threaded: no COOP/COEP / SharedArrayBuffer needed
ort.env.wasm.wasmPaths = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;

const MODEL_URL = "/models/plant_disease_mobilenetv2.onnx";
const LABELS_URL = "/models/plant_disease_mobilenetv2.labels.json";
const INPUT_SIZE = 224;
const RESIZE_SHORT = 256;

export interface LocalCandidate {
  key: string; // knowledge-base key (e.g. "tomato_late_blight", "healthy")
  rawLabel: string;
  name: Bi;
  /** Renormalised tomato probability (0..1). Uncalibrated visual match. */
  prob: number;
}

export interface LocalInference {
  /** All 10 tomato classes (incl. healthy), sorted by probability desc. */
  candidates: LocalCandidate[];
  top3: LocalCandidate[];
  /** Sum of the raw 38-way softmax over the tomato classes (crop/leaf gate). */
  tomatoMass: number;
  /** Top-1 minus top-2 tomato probability, as a fraction (separation/margin). */
  topMargin: number;
  engine: string;
  checkMs: number;
  modelSizeMb: number;
  /** JS heap delta around inference when the browser exposes it (Chromium). */
  heapUsedMb: number | null;
  modelFile: string;
}

// rawLabel -> knowledge-base entry, across the 10 tomato classes + healthy.
const RAW_TO_ENTRY = new Map(
  [...TOMATO_DISEASES, HEALTHY].map((d) => [d.rawLabel, d]),
);

let sessionPromise: Promise<{ session: ort.InferenceSession; labels: string[]; sizeMb: number }> | null = null;

async function getSession() {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      const [modelBuf, labels] = await Promise.all([
        fetch(MODEL_URL).then((r) => {
          if (!r.ok) throw new Error(`model fetch failed: ${r.status}`);
          return r.arrayBuffer();
        }),
        fetch(LABELS_URL).then((r) => r.json() as Promise<string[]>),
      ]);
      const session = await ort.InferenceSession.create(new Uint8Array(modelBuf), {
        executionProviders: ["wasm"],
        graphOptimizationLevel: "all",
      });
      return { session, labels, sizeMb: modelBuf.byteLength / (1024 * 1024) };
    })();
  }
  return sessionPromise;
}

/** Warm the model in the background so the first real check is fast. */
export function warmupModel(): void {
  void getSession().catch(() => {
    // Surfaced later on the real call; warmup failures are non-fatal.
  });
}

function numericSoftmax(logits: Float32Array): Float64Array {
  let max = -Infinity;
  for (const v of logits) if (v > max) max = v;
  const out = new Float64Array(logits.length);
  let sum = 0;
  for (let i = 0; i < logits.length; i++) {
    const e = Math.exp(logits[i] - max);
    out[i] = e;
    sum += e;
  }
  for (let i = 0; i < out.length; i++) out[i] /= sum;
  return out;
}

// mobilenet_pv preprocessing on a drawable source -> NCHW float32 tensor data.
function preprocess(source: CanvasImageSource, w: number, h: number): Float32Array {
  const scale = RESIZE_SHORT / Math.min(w, h);
  const rw = Math.round(w * scale);
  const rh = Math.round(h * scale);

  const canvas = document.createElement("canvas");
  canvas.width = rw;
  canvas.height = rh;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("2D canvas context unavailable");
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(source, 0, 0, rw, rh);

  const left = Math.floor((rw - INPUT_SIZE) / 2);
  const top = Math.floor((rh - INPUT_SIZE) / 2);
  const { data } = ctx.getImageData(left, top, INPUT_SIZE, INPUT_SIZE);

  const area = INPUT_SIZE * INPUT_SIZE;
  const tensor = new Float32Array(3 * area);
  for (let p = 0; p < area; p++) {
    const base = p * 4;
    // (x/255 - 0.5) / 0.5  ==  x/127.5 - 1
    tensor[p] = data[base] / 127.5 - 1; // R -> channel 0
    tensor[area + p] = data[base + 1] / 127.5 - 1; // G -> channel 1
    tensor[2 * area + p] = data[base + 2] / 127.5 - 1; // B -> channel 2
  }
  return tensor;
}

function dimsOf(source: CanvasImageSource): { w: number; h: number } {
  if (source instanceof HTMLImageElement) return { w: source.naturalWidth, h: source.naturalHeight };
  if (typeof ImageBitmap !== "undefined" && source instanceof ImageBitmap) return { w: source.width, h: source.height };
  if (source instanceof HTMLCanvasElement) return { w: source.width, h: source.height };
  const anySrc = source as { width?: number; height?: number };
  return { w: anySrc.width ?? 0, h: anySrc.height ?? 0 };
}

function heapMb(): number | null {
  const mem = (performance as unknown as { memory?: { usedJSHeapSize: number } }).memory;
  return mem ? mem.usedJSHeapSize / (1024 * 1024) : null;
}

/**
 * Run the on-device tomato classifier on a drawable image source.
 * @throws if the model or wasm runtime cannot be loaded.
 */
export async function runLocalInference(source: CanvasImageSource): Promise<LocalInference> {
  const { session, labels, sizeMb } = await getSession();
  const { w, h } = dimsOf(source);
  if (!w || !h) throw new Error("image has no dimensions");

  const heapBefore = heapMb();
  const started = performance.now();

  const inputData = preprocess(source, w, h);
  const feeds: Record<string, ort.Tensor> = {
    [session.inputNames[0]]: new ort.Tensor("float32", inputData, [1, 3, INPUT_SIZE, INPUT_SIZE]),
  };
  const results = await session.run(feeds);
  const logits = results[session.outputNames[0]].data as Float32Array;
  const probs = numericSoftmax(logits);

  const checkMs = performance.now() - started;
  const heapAfter = heapMb();

  // Crop-condition to tomato classes.
  const tomatoIdx: number[] = [];
  for (let i = 0; i < labels.length; i++) if (labels[i].startsWith("Tomato___")) tomatoIdx.push(i);
  const tomatoMass = tomatoIdx.reduce((s, i) => s + probs[i], 0);

  const candidates: LocalCandidate[] = tomatoIdx
    .map((i) => {
      const entry = RAW_TO_ENTRY.get(labels[i]);
      return {
        key: entry?.key ?? labels[i],
        rawLabel: labels[i],
        name: entry?.name ?? { en: labels[i], ar: labels[i] },
        prob: tomatoMass > 0 ? probs[i] / tomatoMass : 0,
      };
    })
    .sort((a, b) => b.prob - a.prob);

  const topMargin = candidates.length > 1 ? candidates[0].prob - candidates[1].prob : candidates[0]?.prob ?? 0;

  return {
    candidates,
    top3: candidates.slice(0, 3),
    tomatoMass,
    topMargin,
    engine: "onnxruntime-web · wasm (CPU, on-device)",
    checkMs: Math.round(checkMs),
    modelSizeMb: Math.round(sizeMb * 100) / 100,
    heapUsedMb: heapBefore != null && heapAfter != null ? Math.max(0, Math.round((heapAfter - heapBefore) * 100) / 100) : null,
    modelFile: "plant_disease_mobilenetv2.onnx",
  };
}

/** Load a File/Blob into a drawable ImageBitmap (with an <img> fallback). */
export async function sourceFromFile(file: Blob): Promise<CanvasImageSource> {
  if (typeof createImageBitmap === "function") {
    try {
      return await createImageBitmap(file);
    } catch {
      // fall through to the <img> path
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.decoding = "async";
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("image decode failed"));
      img.src = url;
    });
    return img;
  } finally {
    // The bitmap/image keeps the decoded pixels; revoke after a tick.
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  }
}
