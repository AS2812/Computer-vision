import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure"
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run --project ../../services/api uvicorn app.main:app --app-dir ../../services/api --host 127.0.0.1 --port 8011",
      url: "http://127.0.0.1:8011/health",
      reuseExistingServer: false,
      env: {
        CORS_ORIGINS: "http://127.0.0.1:5174",
        SUPABASE_URL: "",
        SUPABASE_SERVICE_ROLE_KEY: "",
        EXTERNAL_LLM_API_KEY: ""
      }
    },
    {
      command: "pnpm dev --host 127.0.0.1 --port 5174",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      env: {
        VITE_API_URL: "http://127.0.0.1:8011"
      }
    }
  ]
});
