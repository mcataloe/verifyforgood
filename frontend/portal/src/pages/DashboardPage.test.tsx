import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import { DashboardPage } from "./DashboardPage";

describe("DashboardPage", () => {
  it("renders the dashboard prototype sections with placeholder content", () => {
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
    expect(screen.getByLabelText("Verification trend chart placeholder")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Alerts" })).toBeTruthy();
    expect(screen.getByText("American National Red Cross")).toBeTruthy();
  });
});
