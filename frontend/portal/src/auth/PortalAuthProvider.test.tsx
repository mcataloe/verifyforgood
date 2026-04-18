import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PortalAuthProvider } from "./PortalAuthProvider";
import { usePortalAuth } from "./usePortalAuth";
import type { PortalAuthClient } from "./portalAuthClient";

describe("PortalAuthProvider", () => {
  it("clears the busy flag after a failed login attempt", async () => {
    const authClient: PortalAuthClient = {
      getSession: vi.fn(async () => null),
      login: vi.fn(async () => {
        throw new Error("Invalid email or password");
      }),
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
