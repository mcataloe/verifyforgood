import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PortalRegisterPage } from "./PortalRegisterPage";

describe("PortalRegisterPage", () => {
  it("renders registration inputs and disabled provider placeholders", () => {
    renderRegisterPage();

    expect(screen.getByLabelText("Full name")).toBeTruthy();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Create account" })).toBeTruthy();
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
  });

  it("submits the typed registration contract", () => {
    const onRegister = vi.fn(async () => undefined);
    renderRegisterPage(onRegister);

    fireEvent.change(screen.getByLabelText("Full name"), {
      target: { value: "Jamie Admin" },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie.admin@example.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "top-secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(onRegister).toHaveBeenCalledWith({
      email: "jamie.admin@example.org",
      full_name: "Jamie Admin",
      password: "top-secret-password",
    });
  });

  it("shows validation before registration when required fields are empty", () => {
    const onRegister = vi.fn(async () => undefined);
    renderRegisterPage(onRegister);

    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(screen.getByRole("alert").textContent).toContain(
      "Enter an email and password to create your account.",
    );
    expect(onRegister).not.toHaveBeenCalled();
  });
});

function renderRegisterPage(onRegister = vi.fn(async () => undefined)) {
  return render(
    <PortalRegisterPage
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
        oauthToken: "/v1/oauth/token",
        organizationSettings: "/v1/organization/settings",
      }}
      isBusy={false}
      onRegister={onRegister}
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
