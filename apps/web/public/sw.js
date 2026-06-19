/* AgroVision service worker — offline-first for the on-device tomato checkup.
 *
 * The app's promise is "checked on your device". This SW makes that real: after
 * the first successful load the app shell, the ~9 MB PlantVillage ONNX model and
 * the onnxruntime-web wasm runtime are all served from cache, so a farmer with no
 * signal can still open the app and run a screening — and repeat loads are instant.
 *
 * Dynamic, privacy- or freshness-sensitive calls are NEVER cached and pass straight
 * to the network: the Supabase AI gateway / assistant (*.supabase.co), Open-Meteo
 * weather, market-price lookups, and anything that is not a GET. Bump VERSION to
 * invalidate every cache on the next deploy.
 */

const VERSION = "agrovision-v2-online-assistant";
const SHELL_CACHE = `${VERSION}-shell`;
const ASSET_CACHE = `${VERSION}-assets`;
const MODEL_CACHE = `${VERSION}-model`;
const RUNTIME_CACHE = `${VERSION}-ort`;
const KEEP = [SHELL_CACHE, ASSET_CACHE, MODEL_CACHE, RUNTIME_CACHE];

// onnxruntime-web loads its wasm glue + binaries from this version-matched CDN
// (see src/lib/onnx.ts). Caching those responses is what lets inference run offline.
const ORT_CDN = "https://cdn.jsdelivr.net/npm/onnxruntime-web";

self.addEventListener("install", (event) => {
  // Pre-cache the navigation entry so an offline reload always has a shell to show.
  event.waitUntil(
    caches.open(SHELL_CACHE).then((c) => c.add("/index.html")).catch(() => {}),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => !KEEP.includes(k)).map((k) => caches.delete(k)));
      await self.clients.claim();
    })(),
  );
});

// The page posts this when the user accepts an update; we then take over so the
// `controllerchange` listener on the page can reload into the new version.
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

const isModel = (url) => url.pathname.startsWith("/models/");
const isStaticAsset = (url) =>
  /\.(?:js|mjs|css|woff2?|ttf|otf|svg|png|webp|ico|json|wasm)$/.test(url.pathname);

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  // `opaque` covers the cross-origin ORT runtime; cache it so it works offline.
  if (res && (res.ok || res.type === "opaque")) cache.put(request, res.clone()).catch(() => {});
  return res;
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  const network = fetch(request)
    .then((res) => {
      if (res && res.ok) cache.put(request, res.clone()).catch(() => {});
      return res;
    })
    .catch(() => hit);
  return hit || network;
}

async function networkFirstNavigation(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put("/index.html", res.clone()).catch(() => {});
    return res;
  } catch {
    return (await cache.match("/index.html")) || (await cache.match(request)) || Response.error();
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Cross-origin: only the onnxruntime-web wasm runtime is cached. Everything else
  // (Supabase gateway/assistant, Open-Meteo, market prices, analytics) is left
  // entirely to the network so dynamic data is never stale or wrongly persisted.
  if (url.origin !== self.location.origin) {
    if (request.url.startsWith(ORT_CDN)) {
      event.respondWith(cacheFirst(request, RUNTIME_CACHE));
    }
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
    return;
  }
  if (isModel(url)) {
    event.respondWith(cacheFirst(request, MODEL_CACHE)); // immutable, big → cache once
    return;
  }
  if (isStaticAsset(url)) {
    event.respondWith(staleWhileRevalidate(request, ASSET_CACHE));
  }
});
