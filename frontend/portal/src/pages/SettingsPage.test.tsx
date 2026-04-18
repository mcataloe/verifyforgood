import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PortalEndpoints } from "../app/portalEndpoints";
import { createMockPortalSession } from "../app/portalSession";
import { PortalAuthContext } from "../auth/usePortalAuth";
import type { PortalUsageBillingController } from "../billing/usePortalUsageBilling";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import type { PortalBudgetSettingsController } from "../settings/usePortalBudgetSettings";
import type { PortalOrganizationProfileSettingsController } from "../settings/usePortalOrganizationProfileSettings";
import type { PortalOrganizationDeletionController } from "../settings/usePortalOrganizationDeletion";
import { SettingsPage } from "./SettingsPage";

const endpoints: PortalEndpoints = {
  authLogin: "/v1/auth/login",
  authMe: "/v1/auth/me",
  authRegister: "/v1/auth/register",
  billingCheckout: "/v1/organization/billing/checkout-session",
  billingPlanChange: "/v1/organization/billing/plan-change",
  billingPortal: "/v1/organization/billing/portal-session",
  billingSubscription: "/v1/organization/billing/subscription",
  nonprofitFilings: "/v1/nonprofit/{ein}/filings",
  nonprofitLookup: "/v1/nonprofit/{ein}",
  nonprofitSearch: "/v1/nonprofits/search",
  organizationCreate: "/v1/organizations",
  organizationDeleteCurrent: "/v1/organizations/current",
  oauthToken: "/v1/oauth/token",
  organizationSettings: "/v1/organization/settings",
  organizationSupport: "/v1/organization/support",
  organizationSupportRequests: "/v1/organization/support-requests",
};

describe("SettingsPage", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
  });

  it("renders budget controls and persists the configured state", () => {
    const save = vi.fn(async () => {});
    const organizationProfileController: PortalOrganizationProfileSettingsController = {
      clearNotice: vi.fn(),
      error: null,
      isLoading: false,
      isSaving: false,
      notice: "Organization profile saved.",
      save: vi.fn(async () => {}),
      settings: {
        contactEmail: "ops@example.org",
        displayName: "Portal Test Org",
        slug: "portal-test-org",
        updatedAt: "2026-03-21T00:00:00Z",
      },
    };
    const budgetController: PortalBudgetSettingsController = {
      clearNotice: vi.fn(),
      error: null,
      isLoading: false,
      isSaving: false,
      notice: "Budget controls saved.",
      save,
      settings: {
        allowOverage: false,
        monthlyRequestCap: 800,
        updatedAt: "2026-03-21T00:00:00Z",
      },
    };
    const usageController: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload: vi.fn(async () => {}),
      snapshot: {
        billingStatus: "active",
        budgetStatus: {
          allowOverage: false,
          label: "Hard stop enabled at the monthly request limit",
          policySource: "organization_settings",
        },
        effectiveAccessPlan: "growth",
        notice: null,
        pendingChangeType: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
        usage: {
          limit: 10000,
          periodLabel: "Current month",
          remaining: 9760,
          source: "mock_plan_baseline",
          used: 240,
          usagePercent: 2,
        },
      },
    };

    const { container } = renderWithOrganization(
      <SettingsPage
        budgetController={budgetController}
        endpoints={endpoints}
        organizationProfileController={organizationProfileController}
        session={createMockPortalSession()}
        usageController={usageController}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Usage budget controls" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Workspace settings" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Organization Profile" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Plan & access" }),
    ).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByText("Growth")).toBeTruthy();
    expect(screen.getByDisplayValue("Portal Test Org")).toBeTruthy();
    expect(screen.getByDisplayValue("portal-test-org")).toBeTruthy();
    expect(screen.getByDisplayValue("ops@example.org")).toBeTruthy();
    expect(screen.getByDisplayValue("800")).toBeTruthy();
    expect(screen.getByText("Budget controls saved.")).toBeTruthy();
    expect(screen.getByText("Organization profile saved.")).toBeTruthy();
    expect(screen.queryByText("Current backend anchor")).toBeNull();
    expect(screen.queryByText("Settings source")).toBeNull();
    expect(screen.getByTestId("detail-page-layout")).toBeTruthy();
    expect(container.querySelector(".portal-page-grid")).toBeNull();
    expect(screen.getAllByTestId("section-divider")).toHaveLength(3);
    expect(
      screen.queryByRole("heading", { name: "Organization details" }),
    ).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "Support & Help" }),
    ).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "Limit visualization" }),
    ).toBeNull();

    fireEvent.change(screen.getByLabelText("Organization request cap"), {
      target: { value: "950" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Save budget controls" }),
    );

    expect(save).toHaveBeenCalledWith({
      allowOverage: false,
      monthlyRequestCap: 950,
    });
  });

  it("explains overage clearly when hard-stop enforcement is disabled", () => {
    const budgetController: PortalBudgetSettingsController = {
      clearNotice: vi.fn(),
      error: null,
      isLoading: false,
      isSaving: false,
      notice: null,
      save: vi.fn(async () => {}),
      settings: {
        allowOverage: true,
        monthlyRequestCap: 500,
        updatedAt: null,
      },
    };
    const usageController: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload: vi.fn(async () => {}),
      snapshot: {
        billingStatus: "active",
        budgetStatus: {
          allowOverage: true,
          label: "Overage allowed beyond included usage",
          policySource: "organization_settings",
        },
        effectiveAccessPlan: "growth",
        notice: null,
        pendingChangeType: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "growth",
        renewalDate: null,
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
        usage: {
          limit: 10000,
          periodLabel: "Current month",
          remaining: 9400,
          source: "mock_plan_baseline",
          used: 600,
          usagePercent: 6,
        },
      },
    };

    renderWithOrganization(
      <SettingsPage
        budgetController={budgetController}
        endpoints={endpoints}
        session={createMockPortalSession()}
        usageController={usageController}
      />,
    );

    expect(
      screen.getByText(
        /Requests can continue beyond 500 if needed, so this cap acts as a budget target while overage remains enabled./i,
      ),
    ).toBeTruthy();
  });

  it("keeps user appearance controls off the organization settings page", () => {
    renderWithOrganization(
      <SettingsPage
        endpoints={endpoints}
        session={createMockPortalSession()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Light" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Dark" })).toBeNull();
    expect(
      window.localStorage.getItem("verifyforgood-color-scheme"),
    ).toBeNull();
  });

  it("submits organization profile updates through the shared settings surface", () => {
    const save = vi.fn(async () => {});
    const organizationProfileController: PortalOrganizationProfileSettingsController = {
      clearNotice: vi.fn(),
      error: null,
      isLoading: false,
      isSaving: false,
      notice: null,
      save,
      settings: {
        contactEmail: "ops@example.org",
        displayName: "Portal Test Org",
        slug: "portal-test-org",
        updatedAt: "2026-03-21T00:00:00Z",
      },
    };

    renderWithOrganization(
      <SettingsPage
        endpoints={endpoints}
        organizationProfileController={organizationProfileController}
        session={createMockPortalSession()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Display name"), {
      target: { value: "Updated Portal Org" },
    });
    fireEvent.change(screen.getByLabelText("Slug"), {
      target: { value: "updated-portal-org" },
    });
    fireEvent.change(screen.getByLabelText("Contact email"), {
      target: { value: "support@example.org" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Save organization profile" }),
    );

    expect(save).toHaveBeenCalledWith({
      contactEmail: "support@example.org",
      displayName: "Updated Portal Org",
      slug: "updated-portal-org",
    });
  });

  it("keeps the profile save action visually actionable after a successful save", () => {
    const organizationProfileController: PortalOrganizationProfileSettingsController = {
      clearNotice: vi.fn(),
      error: null,
      isLoading: false,
      isSaving: false,
      notice: "Organization profile saved.",
      save: vi.fn(async () => {}),
      settings: {
        contactEmail: "ops@example.org",
        displayName: "Portal Test Org",
        slug: "portal-test-org",
        updatedAt: "2026-03-21T00:00:00Z",
      },
    };

    renderWithOrganization(
      <SettingsPage
        endpoints={endpoints}
        organizationProfileController={organizationProfileController}
        session={createMockPortalSession()}
      />,
    );

    const saveButton = screen.getByRole("button", {
      name: "Organization profile saved",
    }) as HTMLButtonElement;

    expect(saveButton.disabled).toBe(false);
  });

  it("requires an exact slug match before deleting an organization", async () => {
    const deleteOrganization = vi.fn(
      async (_input: { slug: string }) => {},
    );
    const deletionController: PortalOrganizationDeletionController = {
      deleteOrganization: vi.fn(async ({ slug }) => {
        await deleteOrganization({ slug });
        return true;
      }),
      error: null,
      isDeleting: false,
      organizationName: "Portal Test Org",
      organizationSlug: "portal-test-org",
    };

    renderWithOrganization(
      <SettingsPage
        deletionController={deletionController}
        endpoints={endpoints}
        session={createMockPortalSession()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete organization" }));

    expect(screen.getAllByRole("heading", { name: "Delete organization" }).length).toBeGreaterThan(0);
    const modal = await screen.findByRole("dialog");
    const slugInput = await screen.findByLabelText("Organization slug");
    expect(document.body.textContent).toContain(
      "This action will be recorded as performed by",
    );
    expect(document.body.textContent).toContain("portal-test-org");
    const confirmDeleteButton = within(modal).getByRole("button", {
      name: "Delete organization",
    });

    expect((confirmDeleteButton as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(slugInput, {
      target: { value: "wrong-slug" },
    });
    expect((confirmDeleteButton as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(slugInput, {
      target: { value: "portal-test-org" },
    });
    fireEvent.click(confirmDeleteButton);

    await waitFor(() => {
      expect(deleteOrganization).toHaveBeenCalledWith({
        slug: "portal-test-org",
      });
    });
  });

});

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

function renderWithOrganization(element: ReactNode) {
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
      get: vi.fn(async () => ({
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
          delivery_mode: "recorded_only",
          honesty_notice:
            "Support requests are recorded for follow-up. There is not yet a customer-visible ticket thread.",
          urgent_contact_notice:
            "Urgent issues should still go through the listed support email.",
        },
        product_links: {
          api_access_hash: "#/api-access?nav=customer-admin-api",
          billing_hash: "#/usage-billing?nav=customer-admin-billing",
          homepage_url: "https://verifyforgood.com",
          usage_hash: "#/usage-billing?nav=customer-admin-usage",
        },
        support_contact: {
          brand_name: "VerifyForGood",
          homepage_url: "https://verifyforgood.com",
          support_email: "support@verifyforgood.com",
          support_mailto: "mailto:support@verifyforgood.com",
        },
      })),
      patch: vi.fn(async () => ({})),
      post: vi.fn(async () => ({
        delivery_mode: "recorded_only",
        status: "received",
        submitted_at: "2026-03-29T14:15:00Z",
        support_email: "support@verifyforgood.com",
        support_request_id: "support_req_default",
      })),
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
  };

  return render(
    <PortalAuthContext.Provider
      value={{
        accessToken: "test_token",
        applyOrganization: vi.fn(),
        availableOrganizations: [
          {
            account_id: "acct_portal_test",
            membership: {
              role: "admin",
              status: "active",
              user_id: "user_verifyforgood_demo",
            },
            organization_id: "org_portal_test",
            organization_name: "Portal Test Org",
            slug: "portal-test-org",
            workspace_id: "ws_portal_test",
          },
        ],
        isBusy: false,
        login: vi.fn(async () => createMockPortalSession()),
        register: vi.fn(async () => createMockPortalSession()),
        removeOrganization: vi.fn(() => createMockPortalSession()),
        session: createMockPortalSession(),
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

