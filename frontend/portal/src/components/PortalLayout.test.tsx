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
  audience: "Authenticated customers managing verification workflows and account settings.",
  description: "Customer portal for nonprofit review and account administration.",
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
    expect(screen.getByRole("link", { name: /^Home\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Organizations\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^API Keys\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Billing\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Usage\b/i })).toBeTruthy();
    expect(screen.getByText("Alex Operator")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Log out/i })).toBeTruthy();
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

    expect(screen.getByRole("link", { name: /^Home\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Organizations\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Team\b/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Usage\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^API Keys\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Settings\b/i })).toBeNull();
  });

  it("maps customer-user navigation to task routes and footer profile", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      },
    });

    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Organizations\b/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Automation\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Profile/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Log out/i })).toBeTruthy();
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
    expect(screen.getByRole("link", { name: /^Overview\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Organizations\b/i })).toBeTruthy();
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
    expect(screen.getByRole("link", { name: /^Organizations\b/i })).toBeTruthy();
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

  it("marks organizations active for a detail route", () => {
    renderPortalLayout({
      currentRoute: resolvePortalRoute(
        "#/organizations/123456789/sources",
      ),
    });
    expect(
      screen
        .getByRole("link", { name: /^Organizations\b/i })
        .getAttribute("aria-current"),
    ).toBe("page");
  });
});

function renderPortalLayout({
  currentRoute = resolvePortalRoute("#/dashboard"),
  session = createMockPortalSession(),
}: {
  currentRoute?: PortalRouteDefinition;
  session?: ReturnType<typeof createMockPortalSession>;
}) {
  window.location.hash = currentRoute.hash;

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
