import { defineConfig, devices } from "@playwright/test";

/**
 * A small number of critical-flow smoke tests, not a full browser test
 * suite. Starts the real Django API and the real Vite dev server, no
 * mocked network layer.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "../.venv/bin/python manage.py migrate --no-input && ../.venv/bin/python manage.py runserver 8000",
      cwd: "../server",
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 5173",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
