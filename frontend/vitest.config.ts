import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: [
      "docs/src/**/*.test.{ts,tsx}",
      "marketing/src/**/*.test.{ts,tsx}",
      "portal/src/**/*.test.{ts,tsx}",
      "shared/*/src/**/*.test.{ts,tsx}",
    ],
    setupFiles: ["./vitest.setup.ts"],
  },
});
