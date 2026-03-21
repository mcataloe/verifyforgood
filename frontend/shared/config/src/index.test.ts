import { describe, expect, it } from "vitest";
import {
  normalizeApiVersion,
  normalizeBaseUrl,
  readRuntimeConfig,
  resolveFrontendEnvironment,
} from "./index";

describe("shared runtime config helpers", () => {
  it("normalizes api version and base url values", () => {
    expect(normalizeApiVersion("/v1/")).toBe("v1");
    expect(normalizeBaseUrl("https://api.verifyforgood.test/")).toBe(
      "https://api.verifyforgood.test",
    );
  });

  it("maps explicit environment and mode values into shared runtime config", () => {
    expect(resolveFrontendEnvironment("prod", "development")).toBe(
      "production",
    );
    expect(
      readRuntimeConfig({
        MODE: "test",
        VITE_API_BASE_URL: "https://api.verifyforgood.test/",
        VITE_API_VERSION: "/v1/",
      }),
    ).toEqual({
      environment: "test",
      apiBaseUrl: "https://api.verifyforgood.test",
      apiVersion: "v1",
    });
  });
});
