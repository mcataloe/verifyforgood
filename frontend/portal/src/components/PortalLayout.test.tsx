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
  description:
    "Customer portal for nonprofit review and account administration.",
  surface: "portal",
  title: "VerifyForGood Portal",
};

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
  environment: "test",
} as const;

describe("PortalLayout", () => {
  it("renders the customer-admin information architecture", () => {
    renderPortalLayout({ currentRoute: resolvePortalRoute("#/billing") });

    expect(screen.getAllByText("Workspace").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Account").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Search Nonprofits\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^API Keys\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Billing\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Usage\b/i })).toBeTruthy();

    fireEvent.click(getSidebarBranchButton("Support") as HTMLElement);
    expect(
      screen.getByRole("link", { name: /^Contact Support\b/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Feedback\b/i }),
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /account menu/i }));
    expect(screen.getByText("Alex Operator")).toBeTruthy();
    expect(screen.getByTestId("portal-user-menu-sign-out")).toBeTruthy();
  });

  it("hides admin-only navigation for user memberships", () => {
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

    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Search Nonprofits\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Usage\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^API Keys\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Settings\b/i })).toBeNull();
  });

  it("maps customer-user navigation to task routes and account menu", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      },
    });

    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Search Nonprofits\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Automation\b/i })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /account menu/i }));
    expect(screen.getByTestId("portal-user-menu-edit-profile")).toBeTruthy();
    expect(screen.getByTestId("portal-user-menu-sign-out")).toBeTruthy();
  });

  it("gives developers the canonical platform navigation", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.developer],
      },
    });

    expect(screen.getByText("Build")).toBeTruthy();
    expect(screen.getByText("Controls")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Search Nonprofits\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Plans\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Usage\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^System\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
  });

  it("maps portal admins to operations and account tasks", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.portalAdmin],
      },
    });

    expect(screen.getByText("Operations")).toBeTruthy();
    expect(screen.getByText("Account")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /^Search Nonprofits\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Billing\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Usage\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
  });

  it("renders plan-gated API keys as locked for lower-tier admins", () => {
    renderPortalLayout({
      session: { ...createMockPortalSession(), plan: "free" },
    });

    const lockedApiItem = screen.getByRole("button", { name: /^API Keys\b/i });
    expect(screen.queryByRole("link", { name: /^API Keys\b/i })).toBeNull();
    expect(
      lockedApiItem.getAttribute("aria-disabled") === "true" ||
        lockedApiItem.getAttribute("data-disabled") !== null,
    ).toBe(true);
  });

  it("marks canonical billing navigation active", () => {
    renderPortalLayout({ currentRoute: resolvePortalRoute("#/billing") });
    expect(
      screen
        .getByRole("link", { name: /^Billing\b/i })
        .getAttribute("aria-current"),
    ).toBe("page");
  });

  it("marks nonprofit search active for a detail route", () => {
    renderPortalLayout({
      currentRoute: resolvePortalRoute("#/organizations/123456789/sources"),
    });
    expect(
      screen
        .getByRole("link", { name: /^Search Nonprofits\b/i })
        .getAttribute("aria-current"),
    ).toBe("page");
  });
});

function renderPortalLayout({
  applyOrganization = vi.fn(() => session),
  availableOrganizations,
  currentRoute = resolvePortalRoute("#/dashboard"),
  onOpenOrganizationOnboarding = vi.fn(),
  session = createMockPortalSession(),
}: {
  applyOrganization?: ReturnType<typeof vi.fn>;
  availableOrganizations?: ReturnType<typeof createOrganizationRecord>[];
  currentRoute?: PortalRouteDefinition;
  onOpenOrganizationOnboarding?: ReturnType<typeof vi.fn>;
  session?: ReturnType<typeof createMockPortalSession>;
}) {
  window.location.hash = currentRoute.hash;

  render(
    <PortalAuthContext.Provider
      value={{
        accessToken: "test_token",
        applyOrganization,
        availableOrganizations: availableOrganizations ?? [
          createOrganizationRecord({
            organization_id: session.workspace_id,
            organization_name: session.organization_name,
            slug: "verifyforgood-demo-workspace",
            account_id: session.account_id,
            membership: session.organization_membership ?? {
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
        refreshSession: vi.fn(async () => session),
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
    workspace_id:
      overrides.workspace_id ?? overrides.organization_id ?? "org_primary",
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
