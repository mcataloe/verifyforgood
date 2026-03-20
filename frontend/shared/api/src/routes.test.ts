import { describe, expect, it } from "vitest";
import {
  buildApiUrl,
  normalizeRouteKey,
  stripVersionPrefix,
  versionPath,
} from "./routes";

describe("shared api route helpers", () => {
  it("normalizes versioned paths and route keys", () => {
    expect(versionPath("/organization/settings", "v1")).toBe(
      "/v1/organization/settings",
    );
    expect(stripVersionPrefix("/v1/organization/settings", "v1")).toBe(
      "/organization/settings",
    );
    expect(normalizeRouteKey("get organization/settings", "v1")).toBe(
      "GET /v1/organization/settings",
    );
  });

  it("builds absolute API urls when a base url is configured", () => {
    expect(
      buildApiUrl("/organization/settings", {
        apiBaseUrl: "https://api.verifyforgood.test/",
        apiVersion: "v1",
      }),
    ).toBe("https://api.verifyforgood.test/v1/organization/settings");
  });
});
