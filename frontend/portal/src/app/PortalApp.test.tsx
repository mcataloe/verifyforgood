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

    if (url.endsWith("/v1/organizations")) {
      const body = JSON.parse(String(init?.body ?? "{}"));
      const normalizedSlug =
        String(body.slug || body.name || "")
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-+|-+$/g, "") || "new-organization";
      return new Response(
        JSON.stringify(
          buildEnvelope({
            account_id: "org_123",
            membership: {
              role: "admin",
              status: "active",
              user_id: "user_jamie_admin",
            },
            organization_id: "org_123",
            organization_name: body.name ?? "Verify For Good Org",
            slug: normalizedSlug,
            workspace_id: "org_123",
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

    if (url.endsWith("/v1/organization/settings")) {
      const headers = new Headers(init?.headers);
      return new Response(
        JSON.stringify(
          buildEnvelope({
            account_id: headers.get("X-Portal-Account-Id") ?? "acct_portal_pending",
            billing: {
              allowOverage: false,
              monthlyRequestCap: null,
            },
            source: "default",
            updated_at: "2026-03-27T00:00:00Z",
            workspace_id:
              headers.get("X-Portal-Workspace-Id") ?? "ws_portal_pending",
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

    if (url.includes("/v1/nonprofits/search")) {
      return new Response(
        JSON.stringify(
          buildEnvelope({
            items: [
              {
                active: true,
                ein: "12-3456789",
                irs_status: "active",
                name: "Helping Hands Foundation",
                state: "IL",
                subsection: "03",
                tax_period: "202412",
              },
            ],
            pagination: {
              next_cursor: null,
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

    if (url.includes("/v1/nonprofit/123456789/filings")) {
      return new Response(
        JSON.stringify(
          buildEnvelope({
            ein: "123456789",
            filings: [
              {
                filing_date: "2025-05-01",
                form_type: "990",
                parse_status: "parsed",
                tax_year: "2024",
              },
            ],
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

    if (url.includes("/v1/nonprofit/123456789")) {
      return new Response(
        JSON.stringify(
          buildEnvelope({
            filing_summary: {
              filing_date: "2025-05-01",
              form_type: "990",
              parse_status: "parsed",
              tax_year: "2024",
            },
            integration_evaluation: {
              integrations: [
                {
                  attempted: false,
                  availability_status: "tenant_disabled",
                  integration_id: "candid",
                  label: "Candid",
                },
              ],
            },
            model: {
              source: "irs_eo_bmf_athena",
              version: "1.0.0",
            },
            organization: {
              ein: "12-3456789",
              name: "Helping Hands Foundation",
            },
            queryExecutionId: "qry_123",
            source_record: {
              subsection: "03",
              tax_period: "202412",
            },
            verification: {
              entity_type: "public_charity",
              irs_status: "active",
              ntee_category: "Human services",
              recent_990_on_file: true,
              state: "IL",
              tax_deductible: "yes",
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

    expect(
      await screen.findByRole("heading", { name: "Create your first organization" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Organization name")).toBeTruthy();
  });

  it("allows the registration flow and redirects into organization onboarding", async () => {
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

    expect(
      await screen.findByRole("heading", { name: "Create your first organization" }),
    ).toBeTruthy();
  });

  it("creates an organization during onboarding and redirects to the dashboard", async () => {
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
    await screen.findByRole("heading", {
      name: "Create your first organization",
    });
    fireEvent.change(screen.getByLabelText("Organization name"), {
      target: { value: "Verify For Good Org" },
    });
    fireEvent.change(screen.getByLabelText("Slug"), {
      target: { value: "verify-for-good-org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create organization" }));

    expect(
      await screen.findByRole("heading", {
        name: "Verification dashboard",
      }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Recent verifications" }),
    ).toBeTruthy();
    expect(screen.getByText("Verifications this month")).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
  });

  it("redirects authenticated users with stored active org state away from public auth routes", async () => {
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
    window.localStorage.setItem(
      "verifyforgood.portal.organization.active",
      JSON.stringify({
        account_id: "org_123",
        membership: {
          role: "admin",
          status: "active",
          user_id: "user_jamie_admin",
        },
        organization_id: "org_123",
        organization_name: "Verify For Good Org",
        slug: "verify-for-good-org",
        workspace_id: "org_123",
      }),
    );
    window.location.hash = "#/register";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Verification dashboard" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
  });

  it("gates authenticated users with pending org context to onboarding", async () => {
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
    window.location.hash = "#/usage-billing";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Create your first organization" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/onboarding/organization");
  });

  it("redirects customer admins without admin membership away from admin-only routes", async () => {
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
    window.localStorage.setItem(
      "verifyforgood.portal.organization.active",
      JSON.stringify({
        account_id: "org_123",
        membership: {
          role: "user",
          status: "active",
          user_id: "user_jamie_admin",
        },
        organization_id: "org_123",
        organization_name: "Verify For Good Org",
        slug: "verify-for-good-org",
        workspace_id: "org_123",
      }),
    );
    window.location.hash = "#/usage-billing?nav=customer-admin-usage";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Verification dashboard" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard?nav=customer-admin-home");
  });

  it("renders the tenant-aware nonprofit search on the workspace route", async () => {
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
    window.localStorage.setItem(
      "verifyforgood.portal.organization.active",
      JSON.stringify({
        account_id: "org_123",
        membership: {
          role: "admin",
          status: "active",
          user_id: "user_jamie_admin",
        },
        organization_id: "org_123",
        organization_name: "Verify For Good Org",
        slug: "verify-for-good-org",
        workspace_id: "org_123",
      }),
    );
    window.location.hash = "#/workspace";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Nonprofit search workspace" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Nonprofit verification search" }),
    ).toBeTruthy();
  });
});
