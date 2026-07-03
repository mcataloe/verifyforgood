import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { createMockPortalSession } from "../app/portalSession";
import { PortalDashboardPage } from "./PortalDashboardPage";

describe("PortalDashboardPage", () => {
  it("renders Home as a task landing page without nonprofit search history", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <PortalDashboardPage
          audience="customer_admin"
          runtimeConfig={{
            apiBaseUrl: "https://api.verifyforgood.test",
            apiVersion: "v1",
            environment: "test",
          }}
          session={createMockPortalSession()}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByRole("heading", { name: "Home" })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "Open organizations" }),
    ).toHaveAttribute("href", "#/organizations");
    expect(screen.getByRole("link", { name: "Open team" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open settings" })).toBeTruthy();
    expect(screen.queryByText("Organization Activity")).toBeNull();
    expect(screen.queryByText("Recent searches")).toBeNull();
  });
});
