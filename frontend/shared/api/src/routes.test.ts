import { describe, expect, it } from "vitest";
import { apiEndpoints } from "./endpoints";
import {
  buildApiPath,
  buildApiUrl,
  normalizeRouteKey,
  resolvePathTemplate,
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

  it("resolves endpoint descriptors with path params and query params", () => {
    expect(
      buildApiPath(apiEndpoints.nonprofits.lookup, "v1", {
        pathParams: {
          ein: "13-1234567",
        },
      }),
    ).toBe("/v1/nonprofit/13-1234567");

    expect(
      buildApiPath(apiEndpoints.nonprofits.detail, "v1", {
        pathParams: {
          ein: "13-1234567",
        },
      }),
    ).toBe("/v1/nonprofits/13-1234567");

    expect(
      buildApiUrl(apiEndpoints.nonprofits.sources, {
        apiBaseUrl: "https://api.verifyforgood.test/",
        apiVersion: "v1",
      }),
    ).toBe("https://api.verifyforgood.test/v1/nonprofits/{ein}/sources");

    expect(
      buildApiUrl(
        apiEndpoints.nonprofits.search,
        {
          apiBaseUrl: "https://api.verifyforgood.test/",
          apiVersion: "v1",
        },
        {
          query: {
            ein: "13-1234567",
            limit: 5,
            source: ["irs", "state"],
          },
        },
      ),
    ).toBe(
      "https://api.verifyforgood.test/v1/nonprofits/search?ein=13-1234567&limit=5&source=irs&source=state",
    );
  });

  it("throws when unresolved params are required for request paths", () => {
    expect(() =>
      resolvePathTemplate("/nonprofit/{ein}", undefined, {
        preserveUnresolved: false,
      }),
    ).toThrow("Missing API path parameter: ein");
  });
});
