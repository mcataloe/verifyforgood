import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import { DashboardPage } from "./DashboardPage";

describe("DashboardPage", () => {
  it("renders the dashboard sections with customer-facing copy", () => {
    render(
      <DashboardPage
        runtimeConfig={{
          apiBaseUrl: "https://dev.charitystatusapi.com",
          apiVersion: "v1",
          environment: "development",
        }}
        session={createMockPortalSession()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Verification dashboard" }),
    ).toBeTruthy();
    expect(screen.getByText("Verifications this month")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Recent verifications" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Verification trend chart")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Alerts" })).toBeTruthy();
    expect(screen.getByText("American National Red Cross")).toBeTruthy();
    expect(screen.getByTestId("dashboard-content-layout")).toBeTruthy();
    expect(screen.queryByText(/development environment/i)).toBeNull();
    expect(screen.queryByText(/placeholder/i)).toBeNull();
  });

  it("renders a dedicated main/sidebar dashboard layout with shrink-safe containers", () => {
    const { container } = render(
      <DashboardPage
        runtimeConfig={{
          apiBaseUrl: "https://dev.charitystatusapi.com",
          apiVersion: "v1",
          environment: "development",
        }}
        session={createMockPortalSession()}
      />,
    );

    const contentLayout = screen.getByTestId("dashboard-content-layout");
    const mainColumn = screen.getByTestId("dashboard-main-column");
    const sidebarColumn = screen.getByTestId("dashboard-sidebar-column");

    expect(contentLayout.className).toContain("portal-dashboard__content");
    expect(mainColumn.className).toContain("portal-dashboard__main");
    expect(sidebarColumn.className).toContain("portal-dashboard__sidebar");
    expect(
      container.querySelector(".portal-authenticated-container.portal-dashboard"),
    ).toBeTruthy();
    expect(
      screen.getByLabelText("Verification trend chart").className,
    ).toContain("portal-dashboard__chart-placeholder");
  });
});
