import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  VerifyForGoodMantineProvider,
  type VerifyForGoodThemeMode,
} from "@charity-status/shared-ui";
import { FRONTEND_ACCESS_ROLE, type FrontendAppInfo } from "@charity-status/shared-types";
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
  it("renders grouped schema-driven navigation for admin-capable sessions", () => {
    renderPortalLayout({
      currentRoute: resolvePortalRoute("#/usage-billing"),
    });

    expect(screen.getByText("Review")).toBeTruthy();
    expect(screen.getByText("Operations")).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Workspace\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^API\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Billing\b/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Settings\b/i })).toBeTruthy();
  });

  it("filters admin-oriented navigation items for customer users", () => {
    renderPortalLayout({
      session: {
        ...createMockPortalSession(),
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      },
    });

    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /^Workspace\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^API\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Billing\b/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Settings\b/i })).toBeNull();
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
      screen.getByText(
        "Self-serve API credentials and token access. Available on Growth and higher plans.",
      ),
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
});

function renderPortalLayout({
  currentRoute = resolvePortalRoute("#/dashboard"),
  session = createMockPortalSession(),
}: {
  currentRoute?: PortalRouteDefinition;
  session?: ReturnType<typeof createMockPortalSession>;
}) {
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
          del: vi.fn(),
          get: vi.fn(),
          post: vi.fn(),
          put: vi.fn(),
        } as never,
        refresh: vi.fn(async () => {}),
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
