import { render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it } from "vitest";
import { PortalHomePage } from "./PortalHomePage";

describe("PortalHomePage", () => {
  it("renders the public portal CTA hierarchy", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <PortalHomePage
          requestedRoute={{
            access: "protected",
            description: "Dashboard overview route.",
            hash: "#/dashboard",
            key: "dashboard",
            label: "Dashboard",
          }}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByText("Sign In to Manage Your Organization"),
    ).toBeTruthy();
    const cta = screen.getByTestId("public-home-auth-cta");
    expect(cta).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign In" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Create Account" })).toBeTruthy();
    expect(cta.textContent).toContain("Sign In");
    expect(cta.textContent).toContain("Create Account");
    expect(
      screen.getByText(
        "Your account is always authenticated before organization setup.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText("Portal scope")).toBeNull();
  });
});
