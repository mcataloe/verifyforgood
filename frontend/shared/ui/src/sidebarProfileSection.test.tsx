import { fireEvent, render, screen } from "@testing-library/react";
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

  it("renders theme controls when explicitly enabled", () => {
    render(
      <VerifyForGoodMantineProvider>
        <SidebarProfileSection
          primaryLabel="Acme Relief Fund"
          showThemeControls
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByRole("button", { name: "Auto" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Light" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Dark" })).toBeTruthy();
  });

  it("updates the selected theme mode when controls are pressed", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <SidebarProfileSection
          primaryLabel="Acme Relief Fund"
          showThemeControls
        />
      </VerifyForGoodMantineProvider>,
    );

    const autoButton = screen.getByRole("button", { name: "Auto" });
    const lightButton = screen.getByRole("button", { name: "Light" });
    const darkButton = screen.getByRole("button", { name: "Dark" });

    expect(lightButton.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(darkButton);
    expect(darkButton.getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(autoButton);
    expect(autoButton.getAttribute("aria-pressed")).toBe("true");
    expect(lightButton.getAttribute("aria-pressed")).toBe("false");
  });

  it("omits optional metadata cleanly when it is not provided", () => {
    render(
      <VerifyForGoodMantineProvider>
        <SidebarProfileSection
          primaryLabel="Acme Relief Fund"
          showThemeControls={false}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByText("Acme Relief Fund")).toBeTruthy();
    expect(screen.queryByText("Admin")).toBeNull();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
  });
});
