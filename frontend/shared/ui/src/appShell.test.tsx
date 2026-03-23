import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import {
  VerifyForGoodAppShell,
  VerifyForGoodMantineProvider,
  normalizeVerifyForGoodAppShellNavigationSections,
  type VerifyForGoodAppShellNavSection,
  type VerifyForGoodResolvedNavigationSection,
} from "./index";

const sectionedNavigation: VerifyForGoodAppShellNavSection[] = [
  {
    key: "core",
    label: "Core",
    helpText: "Primary product views.",
    items: [
      {
        key: "dashboard",
        label: "Dashboard",
        href: "#/dashboard",
        helpText:
          "High-level product activity and recent verification signals.",
      },
      {
        key: "organizations",
        label: "Organizations",
        helpText: "Browse organization review and credential management views.",
        children: [
          {
            key: "org-directory",
            label: "Directory",
            href: "#/organizations",
          },
          {
            key: "org-credentials",
            label: "Credentials",
            href: "#/organizations/credentials",
          },
        ],
      },
    ],
  },
  {
    key: "admin",
    label: "Admin",
    items: [
      {
        key: "billing",
        label: "Billing",
        href: "#/billing",
      },
    ],
  },
];

const lockedResolvedNavigation: VerifyForGoodResolvedNavigationSection[] = [
  {
    key: "operations",
    label: "Operations",
    items: [
      {
        key: "workspace",
        label: "Workspace",
        href: "#/workspace",
        visibilityState: "visible",
      },
      {
        key: "api",
        label: "API",
        helpText:
          "Self-serve API credentials and token access. Available on Growth and higher plans.",
        visibilityState: "locked",
      },
    ],
  },
];

describe("VerifyForGoodAppShell", () => {
  it("renders distinct sidebar header, navigation content, and footer regions", () => {
    renderAppShell({
      sidebarFooter: <div>Footer slot</div>,
    });

    expect(screen.getByTestId("vf-app-shell-sidebar-header")).toBeTruthy();
    expect(screen.getByTestId("vf-app-shell-sidebar-content")).toBeTruthy();
    expect(screen.getByTestId("vf-app-shell-sidebar-footer")).toBeTruthy();
    expect(screen.getByText("Footer slot")).toBeTruthy();
    expect(screen.getAllByText("Shared Shell").length).toBeGreaterThan(0);
  });

  it("renders the default footer profile block without sidebar theme controls", () => {
    renderAppShell({
      sidebarFooter: undefined,
    });

    expect(screen.getByText("Shared application shell")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Auto" })).toBeNull();
  });

  it("renders grouped navigation sections without forcing nested items open", () => {
    renderAppShell({
      navigationSections: sectionedNavigation,
    });

    expect(screen.getByText("Core")).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Dashboard\b/i })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /^Organizations\b/i }),
    ).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Directory" })).toBeNull();
  });

  it("supports nested expand and collapse behavior", () => {
    renderAppShell({
      navigationSections: sectionedNavigation,
    });

    const organizationsButton = screen.getByRole("button", {
      name: /^Organizations\b/i,
    });

    fireEvent.click(organizationsButton);
    expect(organizationsButton.className).toContain(
      "vf-app-shell-nav__item--expanded",
    );
    expect(screen.getByRole("link", { name: "Directory" }).className).toContain(
      "vf-app-shell-nav__item--child",
    );
    expect(
      screen.getByRole("link", { name: "Credentials" }).className,
    ).toContain("vf-app-shell-nav__item--child");

    fireEvent.click(organizationsButton);
    expect(organizationsButton.className).not.toContain(
      "vf-app-shell-nav__item--expanded",
    );
    expect(screen.queryByRole("link", { name: "Directory" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Credentials" })).toBeNull();
  });

  it("marks the active child and parent states", () => {
    renderAppShell({
      activeNavigationKey: "org-credentials",
      navigationSections: sectionedNavigation,
    });

    expect(
      screen
        .getByRole("button", { name: /^Organizations\b/i })
        .getAttribute("data-active"),
    ).toBe("true");
    expect(
      screen
        .getByRole("link", { name: "Credentials" })
        .getAttribute("aria-current"),
    ).toBe("page");
  });

  it("emits navigation click events for nested items", () => {
    const onNavigationChange = vi.fn();

    renderAppShell({
      navigationSections: sectionedNavigation,
      onNavigationChange,
    });
    fireEvent.click(screen.getByRole("button", { name: /^Organizations\b/i }));
    fireEvent.click(screen.getByRole("link", { name: "Credentials" }));

    expect(onNavigationChange).toHaveBeenCalledWith(
      expect.objectContaining({
        key: "org-credentials",
        label: "Credentials",
      }),
    );
  });

  it("keeps filtered parents usable when only one child remains visible", () => {
    renderAppShell({
      navigationSections: [
        {
          key: "review",
          label: "Review",
          items: [
            {
              key: "organizations",
              label: "Organizations",
              children: [
                {
                  key: "org-profile",
                  label: "Profile",
                  href: "#/organizations/profile",
                },
              ],
            },
          ],
        },
      ],
    });

    expect(
      screen.getByRole("button", { name: /^Organizations\b/i }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: "Profile" })).toBeTruthy();
  });

  it("keeps top-level help text on aria metadata instead of inline copy", () => {
    renderAppShell({
      navigationSections: sectionedNavigation,
    });

    const dashboardLink = screen.getByRole("link", { name: /^Dashboard\b/i });

    expect(dashboardLink.getAttribute("aria-describedby")).toContain(
      "dashboard-navigation-help",
    );
  });

  it("does not render a tooltip for links without help text", () => {
    renderAppShell({
      navigationSections: sectionedNavigation,
    });

    vi.useFakeTimers();
    fireEvent.mouseEnter(screen.getByRole("link", { name: /^Billing\b/i }));
    vi.advanceTimersByTime(150);
    expect(screen.queryByRole("tooltip")).toBeNull();
    vi.useRealTimers();
  });

  it("renders locked items as disabled buttons with a visible unavailable state", () => {
    renderAppShell({
      navigationSections: lockedResolvedNavigation,
    });

    const lockedItem = screen.getByRole("button", { name: /^API\b/i });
    const isUnavailable =
      lockedItem.getAttribute("aria-disabled") === "true" ||
      lockedItem.getAttribute("data-disabled") !== null;

    expect(isUnavailable).toBe(true);
    expect(screen.getByText("Locked")).toBeTruthy();
  });

  it("does not emit navigation events for locked items", () => {
    const onNavigationChange = vi.fn();

    renderAppShell({
      navigationSections: lockedResolvedNavigation,
      onNavigationChange,
    });

    fireEvent.click(screen.getByRole("button", { name: /^API\b/i }));

    expect(onNavigationChange).not.toHaveBeenCalled();
  });

  it("keeps locked item help text behind aria metadata", () => {
    renderAppShell({
      navigationSections: lockedResolvedNavigation,
    });

    const apiButton = screen.getByRole("button", { name: /^API\b/i });

    expect(apiButton.getAttribute("aria-describedby")).toContain(
      "api-navigation-help",
    );
  });

  it("skips empty sections so the sidebar stays stable after filtering", () => {
    renderAppShell({
      navigationSections: [
        {
          key: "empty",
          label: "Empty",
          items: [],
        },
        {
          key: "core",
          label: "Core",
          items: [
            {
              key: "dashboard",
              label: "Dashboard",
              href: "#/dashboard",
            },
          ],
        },
      ],
    });

    expect(screen.queryByText("Empty")).toBeNull();
    expect(screen.getByText("Core")).toBeTruthy();
  });

  it("normalizes flat navigation into a default section for compatibility", () => {
    const normalizedSections = normalizeVerifyForGoodAppShellNavigationSections(
      {
        navigation: [
          {
            key: "settings",
            label: "Settings",
            href: "#/settings",
          },
        ],
      },
    );

    expect(normalizedSections).toEqual([
      {
        key: "navigation",
        label: "Navigation",
        helpText: "Primary application destinations.",
        items: [
          {
            key: "settings",
            label: "Settings",
            href: "#/settings",
          },
        ],
      },
    ]);
  });

  it("renders the compatibility navigation prop through a default section", () => {
    renderAppShell({
      navigation: [
        {
          key: "settings",
          label: "Settings",
          href: "#/settings",
        },
      ],
      navigationSections: undefined,
    });

    expect(screen.getAllByText("Navigation").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Settings" })).toBeTruthy();
  });

  it("renders a custom sidebar summary block when provided", () => {
    renderAppShell({
      sidebarSummary: <div>Custom summary</div>,
    });

    expect(screen.getByText("Custom summary")).toBeTruthy();
  });
});

function renderAppShell(
  props: Partial<ComponentProps<typeof VerifyForGoodAppShell>>,
) {
  const resolvedProps =
    "navigation" in props || "navigationSections" in props
      ? props
      : {
          navigationSections: sectionedNavigation,
          ...props,
        };

  render(
    <VerifyForGoodMantineProvider>
      <VerifyForGoodAppShell appName="Shared Shell" {...resolvedProps}>
        <div>Shell content</div>
      </VerifyForGoodAppShell>
    </VerifyForGoodMantineProvider>,
  );
}
