import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import { PortalOrganizationProvider } from "./PortalOrganizationProvider";
import { usePortalOrganization } from "./usePortalOrganization";

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
} as const;

function OrganizationProbe() {
  const organization = usePortalOrganization();

  return (
    <div>
      <p>Status: {organization.status}</p>
      <p>Name: {organization.activeOrganization.organization_name}</p>
      <p>Workspace: {organization.activeOrganization.workspace_id}</p>
      <p>Account: {organization.activeOrganization.account_id}</p>
    </div>
  );
}

describe("PortalOrganizationProvider", () => {
  it("makes the active organization context available across the portal tree", async () => {
    const session = {
      ...createMockPortalSession(),
      auth_method: "portal_browser_session" as const,
      organization_name: "Stored Organization Context",
    };
    const organizationLoader = vi.fn(async () => ({
      account_id: "acct_stored",
      billing_allow_overage: false,
      billing_monthly_request_cap: 800,
      organization_name: "Stored Organization Context",
      scope_source: "backend_settings" as const,
      settings_source: "stored" as const,
      updated_at: "2026-03-21T00:00:00Z",
      workspace_id: "ws_stored",
    }));

    render(
      <PortalOrganizationProvider
        organizationLoader={organizationLoader}
        runtimeConfig={runtimeConfig}
        session={session}
      >
        <OrganizationProbe />
      </PortalOrganizationProvider>,
    );

    expect(await screen.findByText("Status: ready")).toBeTruthy();
    expect(screen.getByText("Name: Stored Organization Context")).toBeTruthy();
    expect(screen.getByText("Workspace: ws_stored")).toBeTruthy();
    expect(screen.getByText("Account: acct_stored")).toBeTruthy();
  });
});
