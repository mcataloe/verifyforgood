import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { PortalAuthContext } from "../auth/usePortalAuth";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { PortalSupportDeliveryMode } from "../settings/portalSupport";
import type { PortalSupportController } from "../settings/usePortalSupport";
import { SupportPage } from "./SupportPage";

describe("SupportPage", () => {
  it("renders contact support separately from issue reporting", () => {
    const supportController = createSupportController();

    renderWithOrganization(
      <SupportPage
        pane="support-contact"
        supportController={supportController}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Support" }),
    ).toBeTruthy();
    expect(screen.getAllByRole("heading", { name: "Contact Support" })).toHaveLength(1);
    expect(screen.getByText("support@verifyforgood.com")).toBeTruthy();
    expect(screen.queryByText("Portal Test Org")).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "Report An Issue" }),
    ).toBeNull();
  });

  it("renders report issue separately and includes the recommendation category", () => {
    const supportController = createSupportController();

    renderWithOrganization(
      <SupportPage
        pane="support-report-issue"
        supportController={supportController}
      />,
    );

    expect(screen.getAllByRole("heading", { name: "Report An Issue" })).toHaveLength(1);
    expect(
      screen.getByRole("option", { name: "Recommendation" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Contact Support" }),
    ).toBeNull();
  });

  it("validates support requests before submission", () => {
    const submit = vi.fn(async () => {});
    const supportController = createSupportController({ submit });

    renderWithOrganization(
      <SupportPage
        pane="support-report-issue"
        supportController={supportController}
      />,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "Watchers" }), {
      target: { value: "invalid-email" },
    });
    fireEvent.keyDown(screen.getByRole("textbox", { name: "Watchers" }), {
      key: "Enter",
    });
    fireEvent.change(screen.getByLabelText("Subject"), {
      target: { value: "Hi" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "short" },
    });

    expect(
      screen.getByText("Subject must be at least 3 characters."),
    ).toBeTruthy();
    expect(
      screen
        .getByRole("button", { name: "Send support request" })
        .hasAttribute("disabled"),
    ).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Send support request" }));
    expect(submit).not.toHaveBeenCalled();
  });

  it("submits support requests and records the support route in context", async () => {
    const submit = vi.fn(async () => {});
    const supportController = createSupportController({
      clearReceipt: vi.fn(),
      receipt: {
        delivery_mode: PortalSupportDeliveryMode.RecordedAndEmailed,
        status: "received",
        submitted_at: "2026-03-29T14:15:00Z",
        support_email: "support@verifyforgood.com",
        support_request_id: "support_req_123",
      },
      submit,
    });
    window.location.hash = "#/support?nav=customer-admin-support-report-issue";

    renderWithOrganization(
      <SupportPage
        pane="support-report-issue"
        supportController={supportController}
      />,
    );

    fireEvent.change(screen.getByLabelText("Category"), {
      target: { value: "recommendation" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Watchers" }), {
      target: { value: "reviewer@example.org" },
    });
    fireEvent.keyDown(screen.getByRole("textbox", { name: "Watchers" }), {
      key: "Enter",
    });
    fireEvent.change(screen.getByLabelText("Subject"), {
      target: { value: "Feature idea" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: {
        value: "Please add a recommendation workflow for future customer requests.",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send support request" }));

    await waitFor(() => {
      expect(submit).toHaveBeenCalledTimes(1);
    });
    expect(submit).toHaveBeenCalledWith({
      category: "recommendation",
      context: {
        current_route_hash: "#/support?nav=customer-admin-support-report-issue",
        user_agent: window.navigator.userAgent,
      },
      description:
        "Please add a recommendation workflow for future customer requests.",
      subject: "Feature idea",
      watchers: ["reviewer@example.org"],
    });
    expect(screen.getByText(/Support request sent/i)).toBeTruthy();
    expect(screen.queryByText(/support_req_123/i)).toBeNull();
  });
});

function renderWithOrganization(
  element: ReactNode,
  overrides: Partial<PortalOrganizationContextValue> = {},
) {
  const value: PortalOrganizationContextValue = {
    activeOrganization: {
      account_id: "acct_portal_test",
      billing_allow_overage: false,
      billing_monthly_request_cap: 800,
      contact_email: "ops@example.org",
      created_at: "2026-03-20T00:00:00Z",
      organization_id: "org_portal_test",
      organization_name: "Portal Test Org",
      organization_updated_at: "2026-03-21T00:00:00Z",
      scope_source: "backend_settings",
      settings_source: "stored",
      slug: "portal-test-org",
      updated_at: "2026-03-21T00:00:00Z",
      workspace_id: "ws_portal_test",
    },
    apiClient: {
      delete: vi.fn(async () => ({})),
      get: vi.fn(async () => ({})),
      patch: vi.fn(async () => ({})),
      post: vi.fn(async () => ({})),
      put: vi.fn(async () => ({})),
    } as unknown as PortalOrganizationContextValue["apiClient"],
    currentMembership: {
      role: "admin",
      status: "active",
      user_id: "user_verifyforgood_demo",
    },
    isTenantReady: true,
    members: [],
    membersStatus: "ready",
    refresh: async () => {},
    refreshMembers: async () => [],
    selectionStatus: "active",
    setMembers: () => {},
    setActiveOrganization: () => {},
    status: "ready",
    ...overrides,
  };

  return render(
    <PortalAuthContext.Provider
      value={{
        accessToken: "test_token",
        applyOrganization: vi.fn(),
        availableOrganizations: [],
        isBusy: false,
        login: vi.fn(async () => null as never),
        register: vi.fn(async () => null as never),
        removeOrganization: vi.fn(() => null as never),
        session: null,
        signOut: vi.fn(async () => {}),
        status: "authenticated",
      }}
    >
      <PortalOrganizationContext.Provider value={value}>
        <VerifyForGoodMantineProvider defaultColorScheme="light">
          {element}
        </VerifyForGoodMantineProvider>
      </PortalOrganizationContext.Provider>
    </PortalAuthContext.Provider>,
  );
}

function createSupportController(
  overrides: Partial<PortalSupportController> = {},
): PortalSupportController {
  return {
    clearReceipt: vi.fn(),
    context: {
      account_context: {
        account_id: "acct_portal_test",
        contact_email: "ops@example.org",
        current_plan: "growth",
        membership_role: "admin",
        organization_id: "org_portal_test",
        organization_name: "Portal Test Org",
        workspace_id: "ws_portal_test",
      },
      issue_reporting: {
        delivery_mode: PortalSupportDeliveryMode.RecordedAndEmailed,
        honesty_notice:
          "Support requests are recorded and emailed for follow-up. There is not yet a customer-visible ticket thread.",
        urgent_contact_notice:
          "Urgent issues should still go through the listed support email.",
      },
      product_links: {
        api_access_hash: "#/api-access?nav=customer-admin-api",
        billing_hash: "#/billing?nav=customer-admin-billing",
        homepage_url: "https://verifyforgood.com",
        usage_hash: "#/usage?nav=customer-admin-usage",
      },
      support_contact: {
        brand_name: "VerifyForGood",
        homepage_url: "https://verifyforgood.com",
        support_email: "support@verifyforgood.com",
        support_mailto: "mailto:support@verifyforgood.com",
      },
    },
    error: null,
    isLoading: false,
    isSubmitting: false,
    receipt: null,
    reload: vi.fn(async () => {}),
    submit: vi.fn(async () => {}),
    ...overrides,
  };
}
