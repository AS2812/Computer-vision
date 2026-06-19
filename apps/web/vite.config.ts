import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // onnxruntime-web ships its own wasm + .mjs glue and resolves them at runtime;
  // pre-bundling breaks that resolution, so let Vite serve it unbundled in dev.
  optimizeDeps: { exclude: ["onnxruntime-web"] },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    exclude: ["src/legacy/**", "node_modules/**", "dist/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      exclude: [
        "src/main.tsx",
        "src/types.ts",
        "src/appTypes.ts",
        "src/App.tsx",
        "src/components/**",
        "src/data/i18n.ts",
        "src/lib/exports.ts",
        "src/lib/onnx.ts",
        "src/lib/weather.ts",
        "src/lib/imageSignals.ts",
        "src/lib/analyzeClient.ts",
        "src/lib/market.ts",
        "src/lib/supabase.ts",
        "src/lib/treatments.ts",
        "src/lib/cropBot.ts",
        "src/lib/apiBase.ts",
        "src/lib/pwa.ts",
        "public/**",
        "src/legacy/**",
        "vite.config.*",
        "playwright.config.ts",
        "e2e/**",
        "dist/**"
      ],
      thresholds: { lines: 80, functions: 60, statements: 80, branches: 65 }
    }
  }
});
