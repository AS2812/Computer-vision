import { expect, test } from "@playwright/test";
import path from "node:path";

const TOMATO_PHOTO = path.resolve("../../tests/fixtures/healthy_synthetic_field.png");

test("analyzes one photo, shows the auto-detected phase, keeps chat above the footer, and switches to Arabic", async ({ page }) => {
  await page.goto("/");
  await page.locator('#photo-section input[type="file"]').setInputFiles(TOMATO_PHOTO);
  await expect(page.getByRole("heading", { name: "healthy_synthetic_field.png" })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".feature-card")).toHaveCount(4);
  await expect(page.locator(".phase-headline")).toBeVisible();
  await expect(page.getByText("24°C, partly cloudy, wind 9 km/h")).toBeVisible();
  await expect(page.getByText("Treatment options — best first")).toHaveCount(0);

  await page.locator("footer").scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: "Ask AI" }).click();
  await expect(page.locator(".chat-drawer")).toHaveClass(/open/);
  await expect(page.locator("body")).toHaveCSS("overflow", "hidden");
  await page.getByRole("button", { name: "Close" }).click();
  await expect(page.locator("body")).not.toHaveCSS("overflow", "hidden");

  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page.getByText("اعرف زرعك تعبان من إيه من صورة واحدة.")).toBeVisible();
});

test("auto-builds a resumable tomato case from one photo with reports and phase navigation", async ({ page }) => {
  await page.goto("/");
  const createResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/v1/cases") && response.request().method() === "POST"
  );
  await page.locator('#photo-section input[type="file"]').setInputFiles(TOMATO_PHOTO);
  expect((await createResponse).ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Crop case workspace" })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("API route not found")).toHaveCount(0);
  await expect(page.locator(".case-active-head")).toBeVisible();
  // The full 6-phase plan is available from the same photo.
  await expect(page.getByRole("button", { name: /Phase 4/ })).toBeVisible();

  const pdfHref = await page.locator('a[href*="/report.pdf"]').first().getAttribute("href");
  expect(pdfHref).toContain("/api/v1/cases/");
  expect(pdfHref).toContain("/report.pdf");
});

test("requests device permissions and prefills the auto-built case with device GPS", async ({ page, context }) => {
  test.setTimeout(90_000);
  await context.grantPermissions(["geolocation"], { origin: "http://127.0.0.1:5174" });
  await context.setGeolocation({ latitude: 31.211, longitude: 29.96 });
  await context.addInitScript(() => {
    let permission: NotificationPermission = "default";
    class TestNotification {
      static get permission() {
        return permission;
      }
      static async requestPermission() {
        permission = "granted";
        return permission;
      }
      constructor(_title: string, _options?: NotificationOptions) {}
    }
    Object.defineProperty(window, "Notification", { configurable: true, value: TestNotification });
  });
  await page.route("https://api.open-meteo.com/**", async (route) => {
    await route.fulfill({ json: { current: { temperature_2m: 27, weather_code: 2, wind_speed_10m: 15 } } });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Use my location" }).click();
  await expect(page.getByRole("button", { name: "Location ready" })).toBeVisible();
  const enableReminders = page.getByRole("button", { name: "Enable reminders" });
  if (await enableReminders.count()) await enableReminders.click();
  await expect(page.getByRole("button", { name: "Reminders enabled" })).toBeVisible();

  await page.locator('#photo-section input[type="file"]').setInputFiles(TOMATO_PHOTO);
  await expect(page.getByRole("heading", { name: "Crop case workspace" })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("API route not found")).toHaveCount(0);
  await expect(page.locator(".case-active-head h2")).toContainText("GPS 31.21100, 29.96000");

  const pdfHref = await page.locator('a[href*="/report.pdf"]').first().getAttribute("href");
  expect(pdfHref).toContain("/report.pdf");
});
