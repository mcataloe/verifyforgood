import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import {
  VerifyForGoodAppShell,
  VerifyForGoodMantineProvider,
  normalizeVerifyForGoodAppShellNavigationSections,
  type VerifyForGoodAppShellNavSection,
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
      },
      {
        key: "organizations",
        label: "Organizations",
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

describe("VerifyForGoodAppShell", () => {
  it("renders grouped navigation sections and nested items", () => {
    renderAppShell({
      navigationSections: sectionedNavigation,
    });

    expect(screen.getByText("Core")).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeTruthy();
    expect(screen.getByText("Directory")).toBeTruthy();
    expect(screen.getByText("Credentials")).toBeTruthy();
  });

  it("marks the active navigation item", () => {
    renderAppShell({
      activeNavigationKey: "org-credentials",
      navigationSections: sectionedNavigation,
    });

    expect(
      screen.getByRole("link", { name: "Credentials" }).getAttribute("aria-current"),
    ).toBe("page");
  });

  it("emits navigation click events for nested items", () => {
    const onNavigationChange = vi.fn();

    renderAppShell({
      navigationSections: sectionedNavigation,
      onNavigationChange,
    });
    fireEvent.click(screen.getByRole("link", { name: "Credentials" }));

    expect(onNavigationChange).toHaveBeenCalledWith(
      expect.objectContaining({
        key: "org-credentials",
        label: "Credentials",
      }),
    );
  });

  it("normalizes flat navigation into a default section for compatibility", () => {
    const normalizedSections = normalizeVerifyForGoodAppShellNavigationSections({
      navigation: [
        {
          key: "settings",
          label: "Settings",
          href: "#/settings",
        },
      ],
    });

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
      <VerifyForGoodAppShell
        appName="Shared Shell"
        {...resolvedProps}
      >
        <div>Shell content</div>
      </VerifyForGoodAppShell>
    </VerifyForGoodMantineProvider>,
  );
}
