import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SidebarProfileSection, VerifyForGoodMantineProvider } from "./index";

describe("SidebarProfileSection", () => {
  it("renders organization, account, and access context without theme controls by default", () => {
    render(
      <VerifyForGoodMantineProvider>
        <SidebarProfileSection
          accessLabel="Admin"
          eyebrow="Customer context"
          primaryLabel="Acme Relief Fund"
          secondaryLabel="Account acct_12345"
          tertiaryLabel="Riley Admin"
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByText("Acme Relief Fund")).toBeTruthy();
    expect(screen.getByText("Account acct_12345")).toBeTruthy();
    expect(screen.getByText("Riley Admin")).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
  });

  it("omits optional metadata cleanly when it is not provided", () => {
    render(
      <VerifyForGoodMantineProvider>
        <SidebarProfileSection primaryLabel="Acme Relief Fund" />
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByText("Acme Relief Fund")).toBeTruthy();
    expect(screen.queryByText("Admin")).toBeNull();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
  });

  it("renders an optional footer destination without reintroducing theme controls", () => {
    render(
      <VerifyForGoodMantineProvider>
        <SidebarProfileSection
          ariaLabel="Profile & preferences"
          href="#/settings"
          primaryLabel="Acme Relief Fund"
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByRole("link", { name: "Profile & preferences" }),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
  });
});
