import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import { PortalAuthContext } from "../auth/usePortalAuth";
import { PortalOrganizationContext } from "../organization/usePortalOrganization";
import { PortalChatDrawer } from "./PortalChatDrawer";

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
  environment: "test",
} as const;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PortalChatDrawer", () => {
  it("hides conversations when the server-resolved organization does not match the portal selection", async () => {
    const fetchMock = vi.fn(async () =>
      chatResponse({
        conversations: [
          {
            conversation_id: 1,
            user_id: 10,
            organization_id: 2,
            title: "Other organization",
            created_at: "2026-09-05T10:00:00Z",
            updated_at: "2026-09-05T10:00:00Z",
          },
        ],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(chatTree("1"));
    fireEvent.click(screen.getByRole("button", { name: "Open Chat" }));

    expect(await screen.findByText("Organization context changed")).toBeTruthy();
    expect(screen.queryByText("Other organization")).toBeNull();
  });

  it("discards an in-flight response after the selected organization changes", async () => {
    let resolveFetch: ((response: Response) => void) | undefined;
    const pendingResponse = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    const fetchMock = vi.fn(() => pendingResponse);
    vi.stubGlobal("fetch", fetchMock);

    const rendered = render(chatTree("1"));
    fireEvent.click(screen.getByRole("button", { name: "Open Chat" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);

    rendered.rerender(chatTree("2"));

    await act(async () => {
      resolveFetch?.(
        chatResponse({
          conversations: [
            {
              conversation_id: 7,
              user_id: 10,
              organization_id: 1,
              title: "Stale organization history",
              created_at: "2026-09-05T10:00:00Z",
              updated_at: "2026-09-05T10:00:00Z",
            },
          ],
        }),
      );
      await pendingResponse;
    });

    await waitFor(() => {
      expect(screen.queryByText("Stale organization history")).toBeNull();
      expect(screen.queryByText("Running local Chat pipeline…")).toBeNull();
    });
  });
});

function chatTree(organizationId: string) {
  const session = {
    ...createMockPortalSession(),
    account_id: organizationId,
    workspace_id: organizationId,
    organization_name: `Organization ${organizationId}`,
  };

  return (
    <PortalAuthContext.Provider
      value={{
        accessToken: "test_token",
        applyOrganization: vi.fn(() => session),
        availableOrganizations: [],
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
            account_id: organizationId,
            billing_allow_overage: true,
            billing_monthly_request_cap: 10_000,
            organization_id: organizationId,
            organization_name: `Organization ${organizationId}`,
            scope_source: "session_mock",
            settings_source: "mock",
            slug: `organization-${organizationId}`,
            updated_at: session.issued_at,
            workspace_id: organizationId,
          },
          apiClient: {
            delete: vi.fn(),
            get: vi.fn(),
            patch: vi.fn(),
            post: vi.fn(),
            put: vi.fn(),
            requestData: vi.fn(),
            requestEnvelope: vi.fn(),
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
        <VerifyForGoodMantineProvider defaultColorScheme="light">
          <PortalChatDrawer runtimeConfig={runtimeConfig} session={session} />
        </VerifyForGoodMantineProvider>
      </PortalOrganizationContext.Provider>
    </PortalAuthContext.Provider>
  );
}

function chatResponse(data: unknown) {
  return new Response(
    JSON.stringify({
      api_version: "v1",
      api_release: "test",
      request_id: "req_chat_test",
      deprecation: { status: "active" },
      plan: "growth",
      data,
      meta: {},
      errors: [],
    }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    },
  );
}
