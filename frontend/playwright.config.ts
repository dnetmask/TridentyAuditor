import { defineConfig, devices } from "@playwright/test";

// E2E de los flujos críticos (Fase Q). Corre contra un stack YA levantado:
//   - CI: docker compose (imagen única API+SPA) en http://localhost:8001
//   - local: BASE_URL=http://localhost:5173 con Vite + uvicorn, por ejemplo
// Variables:
//   BASE_URL                  dónde vive la app (default: 8001, el compose)
//   E2E_SUPER_EMAIL/_PASSWORD credenciales del Super Admin de pruebas
//   PLAYWRIGHT_CHROMIUM_PATH  binario de Chromium alternativo (sandboxes)
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["github"]] : [["list"]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8001",
    trace: "retain-on-failure",
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
