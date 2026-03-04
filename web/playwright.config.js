import { defineConfig } from "@playwright/test";
import process from "node:process";

const isCI = Boolean(process.env.CI);
const ciWorkers = Number(process.env.PLAYWRIGHT_WORKERS || 2);

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  workers: isCI ? ciWorkers : undefined,
  retries: isCI ? 1 : 0,
  expect: {
    timeout: 5_000,
  },
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !isCI,
    timeout: 120_000,
  },
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
