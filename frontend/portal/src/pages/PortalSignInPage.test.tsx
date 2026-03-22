import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PortalSignInPage } from "./PortalSignInPage";

describe("PortalSignInPage", () => {
  it("renders email/password and Google/Microsoft entry controls", () => {
    renderSignInPage();

    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Continue with Google" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Continue with Microsoft" }),
    ).toBeTruthy();
    expect(screen.getByText("Requested area")).toBeTruthy();
  });

  it("submits email/password through the typed sign-in contract", async () => {
    const onSignIn = vi.fn(async () => undefined);
    renderSignInPage(onSignIn);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "top-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(onSignIn).toHaveBeenCalledWith({
      email: "jamie.admin@example.org",
      method: "password",
      password: "top-secret",
    });
  });

  it("shows validation before password sign-in when required fields are empty", () => {
    const onSignIn = vi.fn(async () => undefined);
    renderSignInPage(onSignIn);

    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("alert").textContent).toContain(
      "Enter both email and password to continue.",
    );
    expect(onSignIn).not.toHaveBeenCalled();
  });

  it("supports mocked OAuth entry buttons without requiring password fields", () => {
    const onSignIn = vi.fn(async () => undefined);
    renderSignInPage(onSignIn);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Continue with Google" }),
    );

    expect(onSignIn).toHaveBeenCalledWith({
      email: "jamie.admin@example.org",
      method: "google",
    });

    const onMicrosoftSignIn = vi.fn(async () => undefined);
    cleanup();
    renderSignInPage(onMicrosoftSignIn);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Continue with Microsoft" }),
    );

    expect(onMicrosoftSignIn).toHaveBeenCalledWith({
      email: "jamie.admin@example.org",
      method: "microsoft",
    });
  });
});

function renderSignInPage(onSignIn = vi.fn(async () => undefined)) {
  return render(
    <PortalSignInPage
      endpoints={{
        billingCheckout: "/v1/organization/billing/checkout-session",
        billingPlanChange: "/v1/organization/billing/plan-change",
        billingPortal: "/v1/organization/billing/portal-session",
        billingSubscription: "/v1/organization/billing/subscription",
        nonprofitFilings: "/v1/nonprofit/{ein}/filings",
        nonprofitLookup: "/v1/nonprofit/{ein}",
        nonprofitSearch: "/v1/nonprofits/search",
        oauthToken: "/v1/oauth/token",
        organizationSettings: "/v1/organization/settings",
      }}
      isBusy={false}
      onSignIn={onSignIn}
      requestedRoute={{
        access: "protected",
        description: "Dashboard overview route.",
        hash: "#/dashboard",
        key: "dashboard",
        label: "Dashboard",
      }}
    />,
  );
}
