import { fireEvent, render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it, vi } from "vitest";
import { PortalOrganizationOnboardingPage } from "./PortalOrganizationOnboardingPage";

describe("PortalOrganizationOnboardingPage", () => {
  it("renders the organization setup modal with the required form fields", () => {
    renderPage();

    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Create Your Organization" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Organization name")).toBeTruthy();
    expect(screen.getByLabelText("Slug")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Create Organization" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Close organization setup" }),
    ).toBeTruthy();
    expect(screen.queryByText("Backend contract")).toBeNull();
  });

  it("does not close on outside click or escape, and closes from the X button", () => {
    const onClose = vi.fn();
    renderPage(undefined, onClose);

    const overlay = document.body.querySelector(".mantine-Modal-overlay");
    if (!overlay) {
      throw new Error("Expected modal overlay");
    }

    fireEvent.mouseDown(overlay);
    fireEvent.click(overlay);
    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).not.toHaveBeenCalled();

    fireEvent.click(
      screen.getByRole("button", { name: "Close organization setup" }),
    );

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("blocks submission when organization name is empty", () => {
    const onCreateOrganization = vi.fn(async () => undefined);
    renderPage(onCreateOrganization);

    fireEvent.click(screen.getByRole("button", { name: "Create Organization" }));

    expect(screen.getByRole("alert").textContent).toContain(
      "Enter an organization name to continue.",
    );
    expect(onCreateOrganization).not.toHaveBeenCalled();
  });

  it("auto-generates the slug from the organization name", () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Organization name"), {
      target: { value: "Verify For Good Org" },
    });

    expect((screen.getByLabelText("Slug") as HTMLInputElement).value).toBe(
      "verify-for-good-org",
    );
  });

  it("submits the typed organization create contract", () => {
    const onCreateOrganization = vi.fn(async () => undefined);
    renderPage(onCreateOrganization);

    fireEvent.change(screen.getByLabelText("Organization name"), {
      target: { value: "Verify For Good Org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Organization" }));

    expect(onCreateOrganization).toHaveBeenCalledWith({
      name: "Verify For Good Org",
      slug: "verify-for-good-org",
    });
  });

  it("shows backend errors inline", async () => {
    const onCreateOrganization = vi.fn(async () => {
      throw new Error("Organization slug is already in use");
    });
    renderPage(onCreateOrganization);

    fireEvent.change(screen.getByLabelText("Organization name"), {
      target: { value: "Verify For Good Org" },
    });
    fireEvent.change(screen.getByLabelText("Slug"), {
      target: { value: "Verify For Good Org !!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Organization" }));

    expect(
      await screen.findByText("Organization slug is already in use"),
    ).toBeTruthy();
  });
});

function renderPage(
  onCreateOrganization = vi.fn(async () => undefined),
  onClose = vi.fn(),
) {
  return render(
    <VerifyForGoodMantineProvider defaultColorScheme="light">
      <PortalOrganizationOnboardingPage
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
        onClose={onClose}
        onCreateOrganization={onCreateOrganization}
      />
    </VerifyForGoodMantineProvider>,
  );
}
