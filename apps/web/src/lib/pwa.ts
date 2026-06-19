// ─────────────────────────────────────────────────────────────────────────────
// PWA wiring: registers the offline-first service worker (production only — the
// dev server stays SW-free so Vite HMR is never intercepted), captures the
// install prompt, and surfaces "an update is ready". The actual caching strategy
// lives in /public/sw.js; this hook is just the page-side controller.
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback, useEffect, useRef, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

// Captured at module scope because `beforeinstallprompt` can fire before React
// mounts; the hook reads it on first run.
let deferredInstall: BeforeInstallPromptEvent | null = null;

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredInstall = e as BeforeInstallPromptEvent;
  });
}

export interface PwaState {
  /** A browser install prompt is available (Chromium-family). */
  canInstall: boolean;
  /** A new service-worker version is waiting to take over. */
  updateReady: boolean;
  /** Show the native install prompt. */
  promptInstall: () => Promise<void>;
  /** Activate the waiting SW and reload into the new version. */
  applyUpdate: () => void;
}

export function usePwa(): PwaState {
  const [canInstall, setCanInstall] = useState(deferredInstall !== null);
  const [updateReady, setUpdateReady] = useState(false);
  const waitingRef = useRef<ServiceWorker | null>(null);

  useEffect(() => {
    const onBeforeInstall = (e: Event) => {
      e.preventDefault();
      deferredInstall = e as BeforeInstallPromptEvent;
      setCanInstall(true);
    };
    const onInstalled = () => {
      deferredInstall = null;
      setCanInstall(false);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);

    if (!("serviceWorker" in navigator) || !import.meta.env.PROD) {
      return () => {
        window.removeEventListener("beforeinstallprompt", onBeforeInstall);
        window.removeEventListener("appinstalled", onInstalled);
      };
    }

    const markWaiting = (sw: ServiceWorker) => {
      waitingRef.current = sw;
      setUpdateReady(true);
    };

    navigator.serviceWorker
      .register("/sw.js")
      .then((reg) => {
        if (reg.waiting && navigator.serviceWorker.controller) markWaiting(reg.waiting);
        reg.addEventListener("updatefound", () => {
          const sw = reg.installing;
          if (!sw) return;
          sw.addEventListener("statechange", () => {
            // A new worker finished installing while one already controls the page.
            if (sw.state === "installed" && navigator.serviceWorker.controller) markWaiting(sw);
          });
        });
      })
      .catch(() => {
        /* offline support is best-effort; failure leaves the app fully functional */
      });

    let refreshing = false;
    const onControllerChange = () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);

    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    if (!deferredInstall) return;
    await deferredInstall.prompt();
    await deferredInstall.userChoice;
    deferredInstall = null;
    setCanInstall(false);
  }, []);

  const applyUpdate = useCallback(() => {
    waitingRef.current?.postMessage("SKIP_WAITING");
    // `controllerchange` (registered above) reloads the page into the new version.
  }, []);

  return { canInstall, updateReady, promptInstall, applyUpdate };
}
