import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";

function createStorageMock(): Storage {
  const store = new Map<string, string>();

  return {
    clear() {
      store.clear();
    },
    getItem(key) {
      return store.get(key) ?? null;
    },
    key(index) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key) {
      store.delete(key);
    },
    setItem(key, value) {
      store.set(key, value);
    },
  };
}

describe("PortalApp", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/v1/plans")) {
        return new Response(
          JSON.stringify({
            api_release: "2026-03-21",
            api_version: "v1",
            data: {
              plans: [
                {
                  display_name: "Free",
                  feature_availability: {
                    batch_verification: false,
                    benchmarking: false,
                    financial_trends: false,
                    monitoring: false,
                    organization_settings: false,
                    risk_flags: false,
                    state_registry: false,
                    verification: true,
                  },
                  included_usage: {
                    batch_items: 0,
                    monthly_requests: 250,
                    requests_per_minute: 10,
                  },
                  per_request_pricing: {
                    amount_usd_micros: 5000,
                    currency_code: "USD",
                    unit: "request",
                  },
                  plan_code: "free",
                },
                {
                  display_name: "Growth",
                  feature_availability: {
                    batch_verification: true,
                    benchmarking: true,
                    financial_trends: true,
                    monitoring: false,
                    organization_settings: false,
                    risk_flags: true,
                    state_registry: false,
                    verification: true,
                  },
                  included_usage: {
                    batch_items: 100,
                    monthly_requests: 10000,
                    requests_per_minute: 120,
                  },
                  per_request_pricing: {
                    amount_usd_micros: 3000,
                    currency_code: "USD",
                    unit: "request",
                  },
                  plan_code: "growth",
                },
              ],
            },
            deprecation: {
              recommended_version: null,
              status: "active",
              sunset_date: null,
            },
            errors: [],
            meta: {},
            plan: "public",
            request_id: "req_portal_test",
          }),
          {
            headers: {
              "Content-Type": "application/json",
            },
            status: 200,
          },
        );
      }

      return new Response("Not Found", {
        status: 404,
      });
    }) as typeof fetch;
    window.location.hash = "#/usage-billing";
  });

  it("redirects unauthenticated access to the sign-in boundary", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Sign in to the customer portal",
      }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Usage & Billing" }),
    ).toBeNull();
    expect(screen.getByText(/Requested area/i)).toBeTruthy();
  });

  it("allows the mock sign-in flow and restores the protected route", async () => {
    render(<App />);

    await screen.findByRole("heading", {
      name: "Sign in to the customer portal",
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Continue with demo session" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Customer portal shell" }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Usage & Billing" }),
    ).toBeTruthy();
    expect(screen.getByText(/Org: VerifyForGood Demo Workspace/i)).toBeTruthy();
    expect(screen.getByText(/Usage and billing state/i)).toBeTruthy();
    expect(screen.getByLabelText("Request usage meter")).toBeTruthy();
  });

  it("renders the nonprofit search dashboard on the default protected route", async () => {
    window.location.hash = "#/dashboard";

    render(<App />);

    await screen.findByRole("heading", {
      name: "Sign in to the customer portal",
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Continue with demo session" }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Nonprofit verification search",
      }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("button", { name: "Search nonprofit" }),
    ).toBeTruthy();
  });
});
