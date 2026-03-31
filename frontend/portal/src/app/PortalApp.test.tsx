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

function readStoredActiveOrganizationForTest() {
  const raw = window.localStorage.getItem(
    "verifyforgood.portal.organization.active",
  );
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function createStoredOrganizationForTest(overrides: Partial<{
  account_id: string;
  membership: {
    role: string;
    status: string;
    user_id: string;
  };
  organization_id: string;
  organization_name: string;
  slug: string;
  workspace_id: string;
}> = {}) {
  return {
    account_id: overrides.account_id ?? "org_123",
    membership: overrides.membership ?? {
      role: "admin",
      status: "active",
      user_id: "user_jamie_admin",
    },
    organization_id: overrides.organization_id ?? "org_123",
    organization_name: overrides.organization_name ?? "Verify For Good Org",
    slug: overrides.slug ?? "verify-for-good-org",
    workspace_id: overrides.workspace_id ?? overrides.organization_id ?? "org_123",
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
      const storedOrganization = readStoredActiveOrganizationForTest();
      return new Response(
        JSON.stringify(
          buildEnvelope({
            organization_context: storedOrganization,
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

    if (url.endsWith("/v1/organization/usage")) {
      return new Response(
        JSON.stringify(
          buildEnvelope({
            metrics: [
              {
                last_updated: "2026-03-28T00:00:00Z",
                metric_type: "api_requests",
                request_count: 84,
              },
              {
                last_updated: "2026-03-28T00:00:00Z",
                metric_type: "nonprofit_lookup_requests",
                request_count: 42,
              },
              {
                last_updated: "2026-03-28T00:00:00Z",
                metric_type: "search_requests",
                request_count: 19,
              },
            ],
            period_label: "March 2026",
            period_month: "2026-03",
            plan_limit_context: {
              allow_overage: false,
              monthly_requests_limit: 10000,
              policy_source: "organization_settings",
            },
            totals: {
              api_requests: 84,
              enrichment_requests: 0,
              filing_lookup_requests: 0,
              nonprofit_lookup_requests: 42,
              search_requests: 19,
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

    if (url.includes("/v1/organization/activity")) {
      const parsed = new URL(url, "https://portal.test");
      const cursor = parsed.searchParams.get("cursor");
      return new Response(
        JSON.stringify(
          buildEnvelope(
            cursor
              ? {
                  has_more: false,
                  items: [
                    {
                      activity_id: "activity_older",
                      actor: {
                        display_name: "Jamie Admin",
                        email: "j***@example.org",
                        user_id: "user_jamie_admin",
                      },
                      category: "api_keys",
                      description: "Created API key Older Key.",
                      event_type: "api_key_creation",
                      metadata: {
                        display_name: "Older Key",
                        key_id: "key_older",
                        status: "active",
                      },
                      occurred_at: "2026-03-27T12:00:00Z",
                      target: {
                        display_name: null,
                        email: null,
                        user_id: null,
                      },
                      title: "API key created",
                    },
                  ],
                  next_cursor: null,
                }
              : {
                  has_more: true,
                  items: [
                    {
                      activity_id: "activity_1",
                      actor: {
                        display_name: "Jamie Admin",
                        email: "j***@example.org",
                        user_id: "user_jamie_admin",
                      },
                      category: "organization_settings",
                      description:
                        "Updated organization settings: display_name, contact_email.",
                      event_type: "organization_settings_update",
                      metadata: {
                        changed_fields: ["display_name", "contact_email"],
                        changed_sections: [],
                      },
                      occurred_at: "2026-03-28T12:00:00Z",
                      target: {
                        display_name: "Verify For Good Org",
                        email: null,
                        user_id: null,
                      },
                      title: "Organization settings updated",
                    },
                  ],
                  next_cursor: "cursor_activity_2",
                },
          ),
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

  it("shows the public portal home on an empty hash", async () => {
    window.location.hash = "";

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Customer portal entry",
      }),
    ).toBeTruthy();
    expect(screen.getByTestId("public-home-auth-cta")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Create account" })).toBeTruthy();
    expect(window.location.hash).toBe("#/");
  });

  it("falls back to the public portal home on an unknown hash", async () => {
    window.location.hash = "#/missing";

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Customer portal entry",
      }),
    ).toBeTruthy();
    expect(screen.getByTestId("public-home-auth-cta")).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Create your first organization" }),
    ).toBeNull();
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
    expect(screen.queryByText("Login endpoint")).toBeNull();
  });

  it("allows the login flow and enters the portal shell for zero-org users", async () => {
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

    expect(await screen.findByRole("heading", { name: "Organization activity" })).toBeTruthy();
    expect(screen.getByTestId("portal-page-container")).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();
    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();
    expect(screen.getByLabelText("Organization name")).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Complete setup" }),
    ).toBeNull();
  });

  it("allows the registration flow and enters the portal shell for zero-org users", async () => {
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

    expect(await screen.findByRole("heading", { name: "Organization activity" })).toBeTruthy();
    expect(screen.getByTestId("portal-page-container")).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();
  });

  it("restores the remembered protected route after login when org context exists", async () => {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/v1/auth/me")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              organization_context: createStoredOrganizationForTest(),
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

      return buildFetchMock()(input, init);
    }) as typeof fetch;

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

    expect(await screen.findByRole("heading", { name: "Billing" })).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Subscription visibility" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/billing");
    expect(screen.queryByTestId("organization-onboarding-page")).toBeNull();
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
    await screen.findByTestId("organization-onboarding-page");
    fireEvent.change(screen.getByLabelText("Organization name"), {
      target: { value: "Verify For Good Org" },
    });
    fireEvent.change(screen.getByLabelText("Slug"), {
      target: { value: "verify-for-good-org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create organization" }));

    expect(
      await screen.findByRole("heading", {
        name: "Organization activity",
      }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Recent organization activity" }),
    ).toBeTruthy();
    expect(screen.getByText("Organization settings updated")).toBeTruthy();
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
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
  });

  it("routes authenticated users from the public home to the dashboard when org context exists", async () => {
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
    window.location.hash = "#/";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
  });

  it("never shows organization onboarding before authentication", async () => {
    window.location.hash = "#/";

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Customer portal entry",
      }),
    ).toBeTruthy();
    expect(screen.getByTestId("public-home-auth-cta")).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Create your first organization" }),
    ).toBeNull();
    expect(screen.queryByTestId("organization-onboarding-page")).toBeNull();
  });

  it("keeps unknown hashes on the public home before authentication", async () => {
    window.location.hash = "#/missing";

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Customer portal entry",
      }),
    ).toBeTruthy();
    expect(screen.queryByTestId("organization-onboarding-page")).toBeNull();
    expect(window.location.hash).toBe("#/missing");
  });

  it("restores existing organization context from backend auth data without local org storage", async () => {
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
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/v1/auth/me")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              organization_context: {
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
              },
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

      return buildFetchMock()(input, init);
    }) as typeof fetch;
    window.location.hash = "#/register";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
    expect(
      window.localStorage.getItem("verifyforgood.portal.organization.active"),
    ).toContain("\"organization_name\":\"Verify For Good Org\"");
  });

  it("routes authenticated users with pending org context into the portal shell", async () => {
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
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(screen.getByTestId("portal-page-container")).toBeTruthy();
    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Create your first organization" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Complete setup" }),
    ).toBeNull();
    expect(window.location.hash).toBe("#/dashboard?nav=customer-admin-home");
  });

  it("does not dismiss organization setup on overlay click and allows explicit close and reopen from the portal shell", async () => {
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
    window.location.hash = "#/dashboard";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(await screen.findByTestId("organization-onboarding-page")).toBeTruthy();

    const overlay = document.body.querySelector(".mantine-Modal-overlay");
    if (!overlay) {
      throw new Error("Expected modal overlay");
    }

    fireEvent.mouseDown(overlay);
    fireEvent.click(overlay);

    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();

    fireEvent.click(
      screen.getByRole("button", { name: "Close organization setup" }),
    );

    expect(screen.queryByTestId("organization-onboarding-page")).toBeNull();
    expect(screen.getByTestId("pending-organization-callout")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Open organization setup" }),
    ).toBeTruthy();

    fireEvent.click(
      screen.getByRole("button", { name: "Open organization setup" }),
    );

    expect(await screen.findByTestId("organization-onboarding-page")).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
  });

  it("redirects authenticated onboarding-route access into the dashboard shell", async () => {
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
    window.location.hash = "#/onboarding/organization";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
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
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/dashboard");
  });

  it("renders the nonprofit search experience on the dedicated search route", async () => {
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
    window.location.hash = "#/search";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Nonprofit search" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Nonprofit verification search" }),
    ).toBeTruthy();
  });

  it("redirects the legacy workspace route to the dedicated search route", async () => {
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
      await screen.findByRole("heading", { name: "Nonprofit search" }),
    ).toBeTruthy();
    expect(window.location.hash).toBe("#/search");
  });

  it("renders the billing management experience on the dedicated billing route", async () => {
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
    window.location.hash = "#/billing";

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Billing",
      }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Subscription visibility" }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Enabled capabilities" }),
    ).toBeTruthy();
  });

  it("redirects the legacy usage-billing route to the dedicated billing route", async () => {
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
    window.location.hash = "#/usage-billing";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Billing" })).toBeTruthy();
    expect(window.location.hash).toBe("#/billing");
  });

  it("switches organizations from the authenticated shell without leaving the current route", async () => {
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
      JSON.stringify(
        createStoredOrganizationForTest({
          organization_id: "org_primary",
          organization_name: "Primary Org",
          slug: "primary-org",
          workspace_id: "org_primary",
          account_id: "org_primary",
        }),
      ),
    );
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/v1/auth/me")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              available_organizations: [
                createStoredOrganizationForTest({
                  organization_id: "org_primary",
                  organization_name: "Primary Org",
                  slug: "primary-org",
                  workspace_id: "org_primary",
                  account_id: "org_primary",
                }),
                createStoredOrganizationForTest({
                  organization_id: "org_secondary",
                  organization_name: "Secondary Org",
                  slug: "secondary-org",
                  workspace_id: "org_secondary",
                  account_id: "org_secondary",
                  membership: {
                    role: "user",
                    status: "active",
                    user_id: "user_jamie_admin",
                  },
                }),
              ],
              organization_context: createStoredOrganizationForTest({
                organization_id: "org_primary",
                organization_name: "Primary Org",
                slug: "primary-org",
                workspace_id: "org_primary",
                account_id: "org_primary",
              }),
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

      return buildFetchMock()(input, init);
    }) as typeof fetch;
    window.location.hash = "#/search";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Nonprofit search" }),
    ).toBeTruthy();
    expect(screen.getAllByText("Primary Org").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId("portal-organization-switcher"));
    fireEvent.click(screen.getByTestId("portal-organization-option-secondary-org"));

    expect(
      (await screen.findByTestId("portal-organization-switcher")).textContent,
    ).toContain("Secondary Org");
    expect(window.location.hash).toBe("#/search");
    expect(
      window.localStorage.getItem("verifyforgood.portal.organization.active"),
    ).toContain("\"organization_id\":\"org_secondary\"");
  });

  it("renders customer-admin home as an activity-first surface", async () => {
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
    window.location.hash = "#/dashboard?nav=customer-admin-home";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Organization activity" }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", {
        name: "Recent organization activity",
      }),
    ).toBeTruthy();
    expect(
      screen.getByText("Organization settings updated"),
    ).toBeTruthy();
    expect(screen.getAllByText("Jamie Admin").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", { name: "Load more activity" }),
    ).toBeTruthy();
  });

  it("keeps billing and usage as distinct route surfaces", async () => {
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
    window.location.hash = "#/billing";

    const { rerender } = render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Billing",
      }),
    ).toBeTruthy();

    window.location.hash = "#/usage";
    fireEvent(window, new HashChangeEvent("hashchange"));
    rerender(<App />);

    expect(
      await screen.findByRole("heading", { name: "Usage" }),
    ).toBeTruthy();
  });
});
