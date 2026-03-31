import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PortalHomePage } from "./PortalHomePage";

describe("PortalHomePage", () => {
  it("renders the public portal CTA hierarchy", () => {
    render(
      <PortalHomePage
        requestedRoute={{
          access: "protected",
          description: "Dashboard overview route.",
          hash: "#/dashboard",
          key: "dashboard",
          label: "Dashboard",
        }}
      />,
    );

    expect(
      screen.getByText("Sign in to manage your organization"),
    ).toBeTruthy();
    expect(screen.getByTestId("public-home-auth-cta")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Create account" })).toBeTruthy();
    expect(
      screen.getByText("Your account is always authenticated before organization setup."),
    ).toBeTruthy();
    expect(screen.queryByText("Portal scope")).toBeNull();
  });
});
