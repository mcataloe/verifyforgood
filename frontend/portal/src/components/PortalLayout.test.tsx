import { render, screen } from "@testing-library/react";
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
      currentRoute: resolvePortalRoute("#/usage-billing"),
    });

    expect(screen.getAllByText("Workspace").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Account").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /^Home\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^API\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Billing\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Usage\b/i })).toBeTruthy();
    expect(screen.getByText("Alex Operator")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Log out/i })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
    expect(
      screen.getByRole("link", { name: /Profile & preferences/i }),
    ).toBeTruthy();
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
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Usage\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^API\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Settings\b/i })).toBeNull();
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

    const lockedApiItem = screen.getByRole("button", { name: /^API\b/i });
    const isUnavailable =
      lockedApiItem.getAttribute("aria-disabled") === "true" ||
      lockedApiItem.getAttribute("data-disabled") !== null;

    expect(screen.queryByRole("link", { name: /^API\b/i })).toBeNull();
    expect(isUnavailable).toBe(true);
    expect(
      screen.getByText("Self-serve API credentials and token access."),
    ).toBeTruthy();
  });

  it("marks the active portal navigation item based on the current route", () => {
    renderPortalLayout({
      currentRoute: resolvePortalRoute("#/usage-billing"),
    });

    expect(
      screen
        .getByRole("link", { name: /^Billing\b/i })
        .getAttribute("aria-current"),
    ).toBe("page");
  });

  it("resolves active navigation from the current hash alias when multiple items share one route surface", () => {
    renderPortalLayout({
      currentHash: "#/usage-billing?nav=customer-admin-usage",
      currentRoute: resolvePortalRoute(
        "#/usage-billing?nav=customer-admin-usage",
      ),
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
  currentHash,
  currentRoute = resolvePortalRoute("#/dashboard"),
  session = createMockPortalSession(),
}: {
  currentHash?: string;
  currentRoute?: PortalRouteDefinition;
  session?: ReturnType<typeof createMockPortalSession>;
}) {
  window.location.hash = currentHash ?? currentRoute.hash;

  render(
    <PortalOrganizationContext.Provider
      value={{
        activeOrganization: {
          account_id: session.account_id,
          billing_allow_overage: true,
          billing_monthly_request_cap: 10_000,
          organization_name: session.organization_name,
          scope_source: "session_mock",
          settings_source: "mock",
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
          onSignOut={vi.fn(async () => {})}
          routes={portalProtectedRoutes}
          runtimeConfig={runtimeConfig}
          session={session}
        >
          <div>Portal content</div>
        </PortalLayout>
      </VerifyForGoodMantineProvider>
    </PortalOrganizationContext.Provider>,
  );
}
