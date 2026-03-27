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

function buildEnvelope<TData>(data: TData) {
  return {
    api_release: "2026-03-27",
    api_version: "v1",
    data,
    deprecation: {
      recommended_version: null,
      status: "active",
      sunset_date: null,
    },
    errors: [],
    meta: {},
    plan: "public",
    request_id: "req_portal_test",
  };
}

function buildFetchMock() {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url.endsWith("/v1/auth/login")) {
      const body = JSON.parse(String(init?.body ?? "{}"));
      return new Response(
        JSON.stringify(
          buildEnvelope({
            access_token: "token_login",
            token_type: "Bearer",
            user: {
              email: body.email ?? "jamie.admin@example.org",
              full_name: "Jamie Admin",
              user_id: "user_jamie_admin",
            },
          }),
        ),
        {
          headers: {
            "Content-Type": "application/json",
          },
          status: 200,
        },
      );
    }

    if (url.endsWith("/v1/auth/register")) {
      const body = JSON.parse(String(init?.body ?? "{}"));
      return new Response(
        JSON.stringify(
          buildEnvelope({
            access_token: "token_register",
            token_type: "Bearer",
            user: {
              email: body.email ?? "jamie.admin@example.org",
              full_name: body.full_name ?? "Jamie Admin",
              user_id: "user_jamie_admin",
            },
          }),
        ),
        {
          headers: {
            "Content-Type": "application/json",
          },
          status: 201,
        },
      );
    }

    if (url.endsWith("/v1/auth/me")) {
      return new Response(
        JSON.stringify(
          buildEnvelope({
            user: {
              email: "jamie.admin@example.org",
              full_name: "Jamie Admin",
              user_id: "user_jamie_admin",
            },
          }),
        ),
        {
          headers: {
            "Content-Type": "application/json",
          },
          status: 200,
        },
      );
    }

    if (url.endsWith("/v1/organization/settings")) {
      return new Response(
        JSON.stringify(
          buildEnvelope({
            account_id: "acct_portal_pending",
            billing: {
              allowOverage: false,
              monthlyRequestCap: null,
            },
            source: "default",
            updated_at: "2026-03-27T00:00:00Z",
            workspace_id: "ws_portal_pending",
          }),
        ),
        {
          headers: {
            "Content-Type": "application/json",
          },
          status: 200,
        },
      );
    }

    if (url.endsWith("/v1/organization/billing/subscription")) {
      return new Response(
        JSON.stringify(
          buildEnvelope({
            billing_status: "trialing",
            current_period_end_at: null,
            effective_access_plan: "growth",
            pending_downgrade: null,
            plan: "growth",
            subscription_status: "trialing",
            trial: {
              ends_at: "2026-04-10T00:00:00Z",
              is_active: true,
              started_at: "2026-03-20T00:00:00Z",
            },
          }),
        ),
        {
          headers: {
            "Content-Type": "application/json",
          },
          status: 200,
        },
      );
    }

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
    globalThis.fetch = buildFetchMock();
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

  it("allows the login flow and restores the protected route", async () => {
    render(<App />);

    await screen.findByRole("heading", {
      name: "Sign in to the customer portal",
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "top-secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByLabelText("Request usage meter")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Log out/i })).toBeTruthy();
  });

  it("allows the registration flow and restores the protected route", async () => {
    render(<App />);

    await screen.findByRole("heading", {
      name: "Sign in to the customer portal",
    });
    fireEvent.click(screen.getByRole("link", { name: "Create account" }));

    expect(
      await screen.findByRole("heading", {
        name: "Create your customer portal account",
      }),
    ).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Full name"), {
      target: { value: "Jamie Admin" },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "top-secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByLabelText("Request usage meter")).toBeTruthy();
  });

  it("renders the nonprofit search dashboard on the default protected route after login", async () => {
    window.location.hash = "#/dashboard";

    render(<App />);

    await screen.findByRole("heading", {
      name: "Sign in to the customer portal",
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "top-secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      await screen.findByRole("heading", {
        name: "Verification dashboard",
      }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Recent verifications" }),
    ).toBeTruthy();
    expect(screen.getByText("Verifications this month")).toBeTruthy();
  });

  it("redirects authenticated users away from public auth routes", async () => {
    window.localStorage.setItem(
      "verifyforgood.portal.auth.session",
      JSON.stringify({
        access_token: "persisted_token",
        token_type: "Bearer",
        user: {
          email: "jamie.admin@example.org",
          full_name: "Jamie Admin",
          user_id: "user_jamie_admin",
        },
      }),
    );
    window.location.hash = "#/register";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Verification dashboard" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
  });
});
