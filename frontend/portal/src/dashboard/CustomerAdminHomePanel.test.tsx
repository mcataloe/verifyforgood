import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it, vi } from "vitest";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { CustomerAdminHomePanel } from "./CustomerAdminHomePanel";

function resolveMockPath(path: unknown) {
  if (typeof path === "string") {
    return path;
  }
  if (typeof path === "object" && path !== null && "path" in path) {
    return String((path as { path?: unknown }).path ?? "");
  }
  return String(path);
}

describe("CustomerAdminHomePanel", () => {
  it("renders sanitized activity rows and supports cursor-driven load more", async () => {
    const get = vi
      .fn()
      .mockResolvedValueOnce({
        has_more: true,
        items: [
          {
            activity_id: "activity_1",
            actor: {
              display_name: "Jamie Admin",
              email: "j***@example.org",
              user_id: "user_admin",
            },
            category: "invitations",
            description: "Sent an invitation to i***@example.org.",
            event_type: "invitation_creation",
            metadata: {
              email: "i***@example.org",
              role: "user",
            },
            occurred_at: "2026-03-29T12:00:00Z",
            target: {
              display_name: null,
              email: "i***@example.org",
              user_id: null,
            },
            title: "Invitation sent",
          },
        ],
        next_cursor: "cursor_2",
      })
      .mockResolvedValueOnce({
        has_more: false,
        items: [
          {
            activity_id: "activity_2",
            actor: {
              display_name: "Jamie Admin",
              email: "j***@example.org",
              user_id: "user_admin",
            },
            category: "api_keys",
            description: "Created API key Primary Key.",
            event_type: "api_key_creation",
            metadata: {
              display_name: "Primary Key",
              key_id: "key_123",
              status: "active",
            },
            occurred_at: "2026-03-28T12:00:00Z",
            target: {
              display_name: null,
              email: null,
              user_id: null,
            },
            title: "API key created",
          },
        ],
        next_cursor: null,
      });

    renderWithOrganization({
      apiClient: {
        delete: vi.fn(),
        get,
        patch: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        requestData: vi.fn(),
        requestEnvelope: vi.fn(),
      } as unknown as PortalOrganizationContextValue["apiClient"],
    });

    expect(
      await screen.findByRole("heading", { name: "Recent organization activity" }),
    ).toBeTruthy();
    expect(screen.getByText("Invitation sent")).toBeTruthy();
    expect(screen.getByText("Jamie Admin")).toBeTruthy();
    expect(screen.getByText("i***@example.org")).toBeTruthy();
    expect(screen.queryByText(/invtok_/i)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Load more activity" }));

    await waitFor(() => {
      expect(screen.getByText("API key created")).toBeTruthy();
    });
    expect(get).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ path: "/organization/activity" }),
      expect.objectContaining({ query: { limit: 20 } }),
    );
    expect(get).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ path: "/organization/activity" }),
      expect.objectContaining({ query: { cursor: "cursor_2", limit: 20 } }),
    );
  });

  it("shows a read-only notice for non-admin memberships", () => {
    renderWithOrganization({
      currentMembership: {
        role: "user",
        status: "active",
        user_id: "user_admin",
      },
    });

    expect(screen.getByText("Activity visibility unavailable")).toBeTruthy();
    expect(
      screen.getByText(/Organization activity is visible only to active organization admins/i),
    ).toBeTruthy();
  });
});

function renderWithOrganization(
  overrides: Partial<PortalOrganizationContextValue> = {},
) {
  const value: PortalOrganizationContextValue = {
    activeOrganization: {
      account_id: "acct_portal_test",
      billing_allow_overage: false,
      billing_monthly_request_cap: 800,
      organization_id: "org_123",
      organization_name: "Portal Test Org",
      scope_source: "backend_settings",
      settings_source: "stored",
      updated_at: "2026-03-21T00:00:00Z",
      workspace_id: "ws_portal_test",
    },
    apiClient: {
      delete: vi.fn(),
      get: vi.fn(async (path: unknown) => {
        if (resolveMockPath(path).includes("/organization/activity")) {
          return {
            has_more: false,
            items: [],
            next_cursor: null,
          };
        }
        return {};
      }),
      patch: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      requestData: vi.fn(),
      requestEnvelope: vi.fn(),
    } as unknown as PortalOrganizationContextValue["apiClient"],
    currentMembership: {
      role: "admin",
      status: "active",
      user_id: "user_admin",
    },
    isTenantReady: true,
    members: [],
    membersStatus: "ready",
    refresh: vi.fn(async () => {}),
    refreshMembers: vi.fn(async () => []),
    selectionStatus: "active",
    setActiveOrganization: vi.fn(),
    setMembers: vi.fn(),
    status: "ready",
    ...overrides,
  };

  return render(
    <PortalOrganizationContext.Provider value={value}>
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <CustomerAdminHomePanel />
      </VerifyForGoodMantineProvider>
    </PortalOrganizationContext.Provider>,
  );
}
