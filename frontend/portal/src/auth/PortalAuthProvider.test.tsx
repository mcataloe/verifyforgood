import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PortalAuthProvider } from "./PortalAuthProvider";
import { usePortalAuth } from "./usePortalAuth";
import type { PortalAuthClient } from "./portalAuthClient";
import { createMockPortalSession } from "../app/portalSession";

describe("PortalAuthProvider", () => {
  it("clears the busy flag after a failed login attempt", async () => {
    const authClient: PortalAuthClient = {
      getSession: vi.fn(async () => null),
      login: vi.fn(async () => {
        throw new Error("Invalid email or password");
      }),
      refreshSession: vi.fn(async () => null),
      register: vi.fn(async () => {
        throw new Error("Registration failed");
      }),
      signOut: vi.fn(async () => {}),
    };

    render(
      <PortalAuthProvider
        authClient={authClient}
        runtimeConfig={{ apiBaseUrl: "http://localhost:8000", apiVersion: "v1" }}
      >
        <TestHarness />
      </PortalAuthProvider>,
    );

    await screen.findByText("idle");
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByText("idle")).toBeTruthy();
    });
  });

  it("refreshes the active session without duplicating concurrent refreshes", async () => {
    const initialSession = createMockPortalSession();
    const refreshedSession = {
      ...initialSession,
      organization_membership: {
        role: "user",
        status: "active",
        user_id: initialSession.user.subject_id,
      },
      organization_name: "Updated Organization",
    };
    const refreshSession = vi.fn(async () => ({
      accessToken: "refreshed_token",
      availableOrganizations: [],
      session: refreshedSession,
    }));
    const authClient: PortalAuthClient = {
      getSession: vi.fn(async () => ({
        accessToken: "initial_token",
        availableOrganizations: [],
        session: initialSession,
      })),
      login: vi.fn(async () => {
        throw new Error("Not used");
      }),
      refreshSession,
      register: vi.fn(async () => {
        throw new Error("Not used");
      }),
      signOut: vi.fn(async () => {}),
    };

    render(
      <PortalAuthProvider
        authClient={authClient}
        runtimeConfig={{ apiBaseUrl: "http://localhost:8000", apiVersion: "v1" }}
      >
        <RefreshHarness />
      </PortalAuthProvider>,
    );

    await screen.findByText("VerifyForGood Demo Workspace");
    fireEvent.click(screen.getByRole("button", { name: "Refresh twice" }));

    expect(await screen.findByText("Updated Organization")).toBeTruthy();
    expect(await screen.findByText("user")).toBeTruthy();
    expect(refreshSession).toHaveBeenCalledTimes(1);
  });
});

function TestHarness() {
  const auth = usePortalAuth();

  return (
    <div>
      <span>{auth.isBusy ? "busy" : "idle"}</span>
      <button
        onClick={() => {
          void auth.login({
            email: "jamie.admin@example.org",
            password: "wrong-pass",
          }).catch(() => {});
        }}
        type="button"
      >
        Login
      </button>
    </div>
  );
}

function RefreshHarness() {
  const auth = usePortalAuth();

  return (
    <div>
      <span>{auth.session?.organization_name ?? "none"}</span>
      <span>{auth.session?.organization_membership?.role ?? "no-role"}</span>
      <button
        onClick={() => {
          void Promise.all([
            auth.refreshSession().catch(() => null),
            auth.refreshSession().catch(() => null),
          ]);
        }}
        type="button"
      >
        Refresh twice
      </button>
    </div>
  );
}
