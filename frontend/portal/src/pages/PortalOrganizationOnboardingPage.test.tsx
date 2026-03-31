import { fireEvent, render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it, vi } from "vitest";
import { PortalOrganizationOnboardingPage } from "./PortalOrganizationOnboardingPage";

describe("PortalOrganizationOnboardingPage", () => {
  it("renders organization name and slug fields", () => {
    const { container } = renderPage();

    expect(screen.getByTestId("organization-onboarding-page")).toBeTruthy();
    expect(screen.getByLabelText("Organization name")).toBeTruthy();
    expect(screen.getByLabelText("Slug")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Setup flow" })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Create organization" }),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Continue" })).toBeNull();
    expect(container.querySelector(".portal-page-grid")).toBeNull();
    expect(screen.getAllByTestId("section-divider")).toHaveLength(2);
  });

  it("blocks submission when organization name is empty", () => {
    const onCreateOrganization = vi.fn(async () => undefined);
    renderPage(onCreateOrganization);

    fireEvent.click(screen.getByRole("button", { name: "Create organization" }));

    expect(screen.getByRole("alert").textContent).toContain(
      "Enter an organization name to continue.",
    );
    expect(onCreateOrganization).not.toHaveBeenCalled();
  });

  it("submits the typed organization create contract", () => {
    const onCreateOrganization = vi.fn(async () => undefined);
    renderPage(onCreateOrganization);

    fireEvent.change(screen.getByLabelText("Organization name"), {
      target: { value: "Verify For Good Org" },
    });
    fireEvent.change(screen.getByLabelText("Slug"), {
      target: { value: "verify-for-good-org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create organization" }));

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
      target: { value: "verify-for-good-org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create organization" }));

    expect(
      await screen.findByText("Organization slug is already in use"),
    ).toBeTruthy();
  });
});

function renderPage(
  onCreateOrganization = vi.fn(async () => undefined),
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
          oauthToken: "/v1/oauth/token",
          organizationSettings: "/v1/organization/settings",
        }}
        isBusy={false}
        onCreateOrganization={onCreateOrganization}
      />
    </VerifyForGoodMantineProvider>,
  );
}
