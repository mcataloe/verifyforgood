import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { PortalToastProvider } from "../components/feedback";
import { PortalSignInPage } from "./PortalSignInPage";

describe("PortalSignInPage", () => {
  it("renders a focused login form without the explanatory panel", () => {
    renderSignInPage();

    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeTruthy();
    expect(
      screen
        .getByRole("button", { name: "Google available soon" })
        .hasAttribute("disabled"),
    ).toBe(true);
    expect(
      screen
        .getByRole("button", { name: "Microsoft available soon" })
        .hasAttribute("disabled"),
    ).toBe(true);
    expect(
      screen.queryByText("Secure Access for Verification Operations"),
    ).toBeNull();
    expect(screen.queryByText("Requested area")).toBeNull();
    expect(screen.queryByText("We'll Take You There")).toBeNull();
    expect(screen.queryByText("Login endpoint")).toBeNull();
    expect(screen.queryByText("Session restore")).toBeNull();
    expect(screen.queryByText(/auth boundary/i)).toBeNull();
  });

  it("submits the typed login contract", () => {
    const onLogin = vi.fn(async () => undefined);
    renderSignInPage(onLogin);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "top-secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(onLogin).toHaveBeenCalledWith({
      email: "jamie.admin@example.org",
      password: "top-secret-password",
    });
  });

  it("shows validation before login when required fields are empty", () => {
    const onLogin = vi.fn(async () => undefined);
    renderSignInPage(onLogin);

    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      screen.getByText("Enter both email and password to continue."),
    ).toBeTruthy();
    expect(screen.getByText("Sign-in details required")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain(
      "Enter both email and password to continue.",
    );
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("renders backend error messages returned from the login action", async () => {
    const onLogin = vi.fn(async () => {
      throw new Error("Invalid email or password");
    });
    renderSignInPage(onLogin);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong-pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByText("Invalid email or password"),
    ).toBeTruthy();
  });

  it("dismisses the sign-in toast when the user updates the form", async () => {
    const onLogin = vi.fn(async () => {
      throw new Error("Invalid email or password");
    });
    renderSignInPage(onLogin);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong-pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByText("Invalid email or password"),
    ).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "corrected-pass" },
    });

    expect(screen.queryByText("Invalid email or password")).toBeNull();
  });
});

function renderSignInPage(onLogin = vi.fn(async () => undefined)) {
  return render(
    <VerifyForGoodMantineProvider defaultColorScheme="light">
      <PortalToastProvider>
        <PortalSignInPage
          endpoints={{
            authLogin: "/v1/auth/login",
            authMe: "/v1/auth/me",
            authRegister: "/v1/auth/register",
            billingCheckout: "/v1/organization/billing/checkout-session",
            billingPlanChange: "/v1/organization/billing/plan-change",
            billingPortal: "/v1/organization/billing/portal-session",
            billingSubscription: "/v1/organization/billing/subscription",
            nonprofitFilings: "/v1/nonprofit/{ein}/filings",
            nonprofitLookup: "/v1/nonprofit/{ein}",
            nonprofitSearch: "/v1/nonprofits/search",
            organizationCreate: "/v1/organizations",
            organizationDeleteCurrent: "/v1/organizations/current",
            oauthToken: "/v1/oauth/token",
            organizationSettings: "/v1/organization/settings",
          }}
          isBusy={false}
          onLogin={onLogin}
          requestedRoute={{
            access: "protected",
            description: "Dashboard overview route.",
            hash: "#/dashboard",
            key: "dashboard",
            label: "Dashboard",
          }}
        />
      </PortalToastProvider>
    </VerifyForGoodMantineProvider>,
  );
}
