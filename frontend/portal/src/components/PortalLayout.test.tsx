import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  VerifyForGoodMantineProvider,
  type VerifyForGoodThemeMode,
} from "@charity-status/shared-ui";
import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAppInfo,
} from "@charity-status/shared-types";
import { createMockPortalSession } from "../app/portalSession";
import { PortalAuthContext } from "../auth/usePortalAuth";
import {
  portalProtectedRoutes,
  resolvePortalRoute,
  type PortalRouteDefinition,
} from "../app/portalRoutes";
import { PortalLayout } from "./PortalLayout";
import { PortalOrganizationContext } from "../organization/usePortalOrganization";

const app: FrontendAppInfo = {
  audience:
    "Authenticated customers managing verification workflows and account settings.",
  description: "Application shell for future authenticated product slices.",
  surface: "portal",
  title: "Customer portal shell",
};

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
  environment: "test",
} as const;

describe("PortalLayout", () => {
  it("renders the customer-admin information architecture", () => {
    renderPortalLayout({
      currentRoute: resolvePortalRoute("#/billing"),
    });

    expect(getSidebarBranchButton("Organization")).toBeTruthy();
    expect(getSidebarBranchButton("Account")).toBeTruthy();
    expect(getSidebarBranchButton("Support & Help")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^API Keys\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Billing\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Usage\b/i })).toBeTruthy();

    fireEvent.click(getSidebarBranchButton("Support & Help") as HTMLElement);
    expect(screen.getByRole("link", { name: /^Contact Support\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Report An Issue\b/i })).toBeTruthy();

    expect(screen.getByText("Alex Operator")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Log out/i })).toBeTruthy();
    expect(screen.getByTestId("portal-organization-switcher")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
    expect(screen.getByRole("link", { name: /Open profile/i })).toBeTruthy();
  });

  it("keeps the active organization child visible under the organization branch", () => {
    renderPortalLayout({
      currentRoute: resolvePortalRoute("#/dashboard"),
    });

    expect(getSidebarBranchButton("Organization")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Home\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Search\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
  });

  it("shows a multi-organization switcher in the header for users with more than one org", async () => {
    renderPortalLayout({
      availableOrganizations: [
        createOrganizationRecord({
          organization_id: "org_primary",
          organization_name: "Primary Org",
          slug: "primary-org",
        }),
        createOrganizationRecord({
          organization_id: "org_secondary",
          organization_name: "Secondary Org",
          slug: "secondary-org",
          membership: { role: "user", status: "active", user_id: "user_verifyforgood_demo" },
        }),
      ],
      session: {
        ...createMockPortalSession(),
        account_id: "org_primary",
        organization_name: "Primary Org",
        workspace_id: "org_primary",
      },
    });

    const switcher = screen.getByTestId("portal-organization-switcher");
    expect(switcher.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(switcher);

    expect(screen.getByText("Switch organization")).toBeTruthy();
    expect(switcher.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getAllByText("Primary Org").length).toBeGreaterThan(0);
    expect(screen.getByText("Secondary Org")).toBeTruthy();
    expect(screen.getByText("Current")).toBeTruthy();
    expect(screen.getByText("Create Organization")).toBeTruthy();
  });

  it("shows the organization dropdown when at least one accessible organization is available", async () => {
    renderPortalLayout();

    fireEvent.click(screen.getByTestId("portal-organization-switcher"));

    expect(screen.getByText("Switch organization")).toBeTruthy();
    expect(screen.getAllByText("VerifyForGood Demo Workspace").length).toBeGreaterThan(0);
    expect(screen.getByText("Current")).toBeTruthy();
    expect(screen.getByText("Create Organization")).toBeTruthy();
  });

  it("keeps the organization dropdown available when onboarding is still pending", async () => {
    renderPortalLayout({
      availableOrganizations: [],
      session: {
        ...createMockPortalSession(),
        organization_context_status: "pending",
        organization_membership: null,
        organization_name: "Organization setup pending",
      },
    });

    fireEvent.click(screen.getByTestId("portal-organization-switcher"));

    expect(screen.getByText("No organizations available yet")).toBeTruthy();
    expect(screen.getByText("Create Organization")).toBeTruthy();
  });

  it("switches active organization through the shared auth seam", () => {
    const applyOrganization = vi.fn();

    renderPortalLayout({
      applyOrganization,
      availableOrganizations: [
        createOrganizationRecord({
          organization_id: "org_primary",
          organization_name: "Primary Org",
          slug: "primary-org",
        }),
        createOrganizationRecord({
          organization_id: "org_secondary",
          organization_name: "Secondary Org",
          slug: "secondary-org",
        }),
      ],
      session: {
        ...createMockPortalSession(),
        account_id: "org_primary",
        organization_name: "Primary Org",
        workspace_id: "org_primary",
      },
    });

    fireEvent.click(screen.getByTestId("portal-organization-switcher"));
    fireEvent.click(screen.getByTestId("portal-organization-option-secondary-org"));

    expect(applyOrganization).toHaveBeenCalledWith(
      expect.objectContaining({
        organization_id: "org_secondary",
        organization_name: "Secondary Org",
      }),
    );
  });

  it("opens organization creation from the header switcher menu", async () => {
    const onOpenOrganizationOnboarding = vi.fn();

    renderPortalLayout({
      onOpenOrganizationOnboarding,
    });

    fireEvent.click(screen.getByTestId("portal-organization-switcher"));
    const createOrganizationLabel = screen.getByText("Create Organization");
    const createOrganizationButton =
      createOrganizationLabel.closest("button");
    if (!createOrganizationButton) {
      throw new Error("Expected create organization button");
    }
    fireEvent.click(createOrganizationButton);

    expect(onOpenOrganizationOnboarding).toHaveBeenCalledTimes(1);
  });

  it("hides admin-only navigation items when the current membership role is user", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        organization_membership: {
          role: "user",
          status: "active",
          user_id: "user_verifyforgood_demo",
        },
      },
    });

    expect(screen.getByRole("link", { name: /^Home\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Search\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /^Account\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Usage\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^API Keys\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Settings\b/i })).toBeNull();
  });

  it("keeps account navigation visible but locked while organization setup is pending", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        organization_context_status: "pending",
        organization_membership: null,
        organization_name: "Organization setup pending",
      },
    });

    const organizationBranch = getSidebarBranchButton("Organization");
    const accountBranch = getSidebarBranchButton("Account");
    const supportBranch = getSidebarBranchButton("Support & Help");
    expect(organizationBranch).toBeTruthy();
    expect(accountBranch).toBeTruthy();
    expect(supportBranch).toBeTruthy();
    fireEvent.click(accountBranch as HTMLElement);
    const billingButton = screen.getByRole("button", { name: /^Billing\b/i });
    const usageButton = screen.getByRole("button", { name: /^Usage\b/i });
    const apiKeysButton = screen.getByRole("button", { name: /^API Keys\b/i });
    const settingsButton = screen.getByRole("button", { name: /^Settings\b/i });
    const isUnavailable = (element: HTMLElement) =>
      element.getAttribute("aria-disabled") === "true" ||
      element.getAttribute("data-disabled") !== null ||
      element.hasAttribute("disabled");
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
    expect(isUnavailable(billingButton)).toBe(true);
    expect(isUnavailable(usageButton)).toBe(true);
    expect(isUnavailable(apiKeysButton)).toBe(true);
    expect(isUnavailable(settingsButton)).toBe(true);

    fireEvent.click(supportBranch as HTMLElement);
    const contactSupportButton = screen.getByRole("button", {
      name: /^Contact Support\b/i,
    });
    const reportIssueButton = screen.getByRole("button", {
      name: /^Report An Issue\b/i,
    });
    expect(isUnavailable(contactSupportButton)).toBe(true);
    expect(isUnavailable(reportIssueButton)).toBe(true);
  });

  it("maps customer-user navigation to dashboard, search, automation, and footer profile access", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      },
    });

    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Search\b/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Automation\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Open profile/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Log out/i })).toBeTruthy();
    expect(screen.queryByText("Account acct_verifyforgood_demo")).toBeNull();
    expect(screen.queryByRole("link", { name: /^Team\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^API\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Settings\b/i })).toBeNull();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
  });

  it("gives developers the platform-oriented navigation structure", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.developer],
      },
    });

    expect(screen.getByText("Build")).toBeTruthy();
    expect(screen.getByText("Controls")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Overview\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Tenants\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Plans\b/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Feature Flags\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Audit\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^System\b/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /^Settings\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
  });

  it("maps portal admins to customer and subscription operations", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.portalAdmin],
      },
    });

    expect(screen.getByText("Operations")).toBeTruthy();
    expect(screen.getByText("Revenue")).toBeTruthy();
    expect(screen.getByText("Configure")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Customers\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Support\b/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Subscriptions\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Reports\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /^API\b/i })).toBeNull();
    expect(screen.getByRole("button", { name: /Log out/i })).toBeTruthy();
  });

  it("renders discoverable plan-gated items as locked for lower-tier admins", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        plan: "free",
      },
    });

    fireEvent.click(screen.getByRole("button", { name: /^Account\b/i }));
    const lockedApiItem = screen.getByRole("button", { name: /^API Keys\b/i });
    const isUnavailable =
      lockedApiItem.getAttribute("aria-disabled") === "true" ||
      lockedApiItem.getAttribute("data-disabled") !== null;

    expect(screen.queryByRole("link", { name: /^API Keys\b/i })).toBeNull();
    expect(isUnavailable).toBe(true);
    expect(
      screen.getByText("Create and manage API keys for your organization."),
    ).toBeTruthy();
  });

  it("marks the active portal navigation item based on the current route", () => {
    renderPortalLayout({
      currentRoute: resolvePortalRoute("#/billing"),
    });

    expect(
      screen
        .getByRole("link", { name: /^Billing\b/i })
        .getAttribute("aria-current"),
    ).toBe("page");
  });

  it("resolves active navigation from the current hash alias when multiple items share one route surface", () => {
    renderPortalLayout({
      currentHash: "#/usage",
      currentRoute: resolvePortalRoute("#/usage"),
    });

    expect(
      screen
        .getByRole("link", { name: /^Usage\b/i })
        .getAttribute("aria-current"),
    ).toBe("page");
    expect(
      screen
        .getByRole("link", { name: /^Billing\b/i })
        .getAttribute("aria-current"),
    ).toBeNull();
  });

});

function renderPortalLayout({
  applyOrganization = vi.fn(),
  availableOrganizations,
  currentHash,
  currentRoute = resolvePortalRoute("#/dashboard"),
  onOpenOrganizationOnboarding = vi.fn(),
  session = createMockPortalSession(),
}: {
  applyOrganization?: ReturnType<typeof vi.fn>;
  availableOrganizations?: Array<{
    account_id: string;
    membership: { role: string; status: string; user_id: string };
    organization_id: string;
    organization_name: string;
    slug: string;
    workspace_id: string;
  }>;
  currentHash?: string;
  currentRoute?: PortalRouteDefinition;
  onOpenOrganizationOnboarding?: ReturnType<typeof vi.fn>;
  session?: ReturnType<typeof createMockPortalSession>;
} = {}) {
  window.location.hash = currentHash ?? currentRoute.hash;

  render(
    <PortalAuthContext.Provider
      value={{
        accessToken: "test_token",
        applyOrganization,
        availableOrganizations:
          availableOrganizations ??
          [
            createOrganizationRecord({
              organization_id: session.workspace_id,
              organization_name: session.organization_name,
              slug: "verifyforgood-demo-workspace",
              account_id: session.account_id,
              membership:
                session.organization_membership ?? {
                  role: "admin",
                  status: "active",
                  user_id: session.user.subject_id,
                },
              workspace_id: session.workspace_id,
            }),
          ],
        isBusy: false,
        login: vi.fn(async () => session),
        removeOrganization: vi.fn(() => session),
        register: vi.fn(async () => session),
        session,
        signOut: vi.fn(async () => {}),
        status: "authenticated",
      }}
    >
      <PortalOrganizationContext.Provider
        value={{
          activeOrganization: {
            account_id: session.account_id,
            billing_allow_overage: true,
            billing_monthly_request_cap: 10_000,
            organization_id: session.workspace_id,
            organization_name: session.organization_name,
            scope_source: "session_mock",
            settings_source: "mock",
            slug: "verifyforgood-demo-workspace",
            updated_at: session.issued_at,
            workspace_id: session.workspace_id,
          },
          apiClient: {
            delete: vi.fn(),
            get: vi.fn(),
            patch: vi.fn(),
            post: vi.fn(),
            requestData: vi.fn(),
            requestEnvelope: vi.fn(),
            put: vi.fn(),
          } as never,
          currentMembership: session.organization_membership,
          isTenantReady: true,
          members: [],
          membersStatus: "ready",
          refresh: vi.fn(async () => {}),
          refreshMembers: vi.fn(async () => []),
          selectionStatus: "active",
          setMembers: vi.fn(),
          setActiveOrganization: vi.fn(),
          status: "ready",
        }}
      >
        <VerifyForGoodMantineProvider
          defaultColorScheme={"light" as VerifyForGoodThemeMode}
        >
          <PortalLayout
            app={app}
            currentRoute={currentRoute}
            onOpenOrganizationOnboarding={onOpenOrganizationOnboarding}
            onSignOut={vi.fn(async () => {})}
            routes={portalProtectedRoutes}
            runtimeConfig={runtimeConfig}
            session={session}
          >
            <div>Portal content</div>
          </PortalLayout>
        </VerifyForGoodMantineProvider>
      </PortalOrganizationContext.Provider>
    </PortalAuthContext.Provider>,
  );
}

function createOrganizationRecord(
  overrides: Partial<{
    account_id: string;
    membership: { role: string; status: string; user_id: string };
    organization_id: string;
    organization_name: string;
    slug: string;
    workspace_id: string;
  }>,
) {
  return {
    account_id: overrides.account_id ?? "org_primary",
    membership: overrides.membership ?? {
      role: "admin",
      status: "active",
      user_id: "user_verifyforgood_demo",
    },
    organization_id: overrides.organization_id ?? "org_primary",
    organization_name: overrides.organization_name ?? "Primary Org",
    slug: overrides.slug ?? "primary-org",
    workspace_id: overrides.workspace_id ?? overrides.organization_id ?? "org_primary",
  };
}

function getSidebarBranchButton(label: string) {
  return (
    screen
      .getAllByRole("button", { name: new RegExp(`^${label}\\b`, "i") })
      .find((element) =>
        element.className.includes("vf-app-shell-nav__item--branch"),
      ) ?? null
  );
}
