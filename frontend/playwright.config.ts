import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testIgnore: process.env.VISUAL_CAPTURE ? undefined : "**/visual-capture.spec.ts",
  timeout: 60_000,
  workers: 1,
  expect: { timeout: 20_000 },
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: "cd .. && AGENT_ENABLED=true ADME_MOCK_MODE=true AGENT_DB_PATH=/tmp/adme-agent-e2e.sqlite3 ADME_DATA_DIR=/tmp/adme-e2e .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
    },
    {
      command: "npm run dev -- --webpack --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: true,
    },
  ],
});
