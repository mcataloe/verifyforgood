import { fireEvent, render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PortalEndpoints } from "../app/portalEndpoints";
import { createMockPortalSession } from "../app/portalSession";
import type { PortalUsageBillingController } from "../billing/usePortalUsageBilling";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import type { PortalBudgetSettingsController } from "../settings/usePortalBudgetSettings";
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
  oauthToken: "/v1/oauth/token",
  organizationSettings: "/v1/organization/settings",
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

    renderWithOrganization(
      <SettingsPage
        budgetController={budgetController}
        endpoints={endpoints}
        session={createMockPortalSession()}
        usageController={usageController}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Usage budget controls" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Profile & preferences" }),
    ).toBeTruthy();
    expect(screen.getByText("Portal Test Org")).toBeTruthy();
    expect(screen.getByText("acct_portal_test")).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByText("Alex Operator")).toBeTruthy();
    expect(screen.getByText("alex.operator@example.org")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Auto" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Light" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Dark" })).toBeTruthy();
    expect(screen.getByDisplayValue("800")).toBeTruthy();
    expect(screen.getByText("Budget controls saved.")).toBeTruthy();
    expect(screen.getByText("240 / 800")).toBeTruthy();
    expect(
      screen.getByText(/560 requests remain before the hard stop is reached./i),
    ).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Monthly usage cap"), {
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
        /This limit has been reached, but requests can continue because hard-stop enforcement is disabled./i,
      ),
    ).toBeTruthy();
    expect(screen.getByText("Overage allowed")).toBeTruthy();
  });

  it("persists the appearance preference through the existing theme storage key", () => {
    renderWithOrganization(
      <SettingsPage
        endpoints={endpoints}
        session={createMockPortalSession()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Dark" }));

    expect(window.localStorage.getItem("verifyforgood-color-scheme")).toBe(
      "dark",
    );
    expect(
      screen.getByText(/Current selection:/i).textContent,
    ).toContain("Dark");
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
      organization_name: "Portal Test Org",
      scope_source: "backend_settings",
      settings_source: "stored",
      updated_at: "2026-03-21T00:00:00Z",
      workspace_id: "ws_portal_test",
    },
    apiClient: {} as PortalOrganizationContextValue["apiClient"],
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
    <PortalOrganizationContext.Provider value={value}>
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        {element}
      </VerifyForGoodMantineProvider>
    </PortalOrganizationContext.Provider>,
  );
}
