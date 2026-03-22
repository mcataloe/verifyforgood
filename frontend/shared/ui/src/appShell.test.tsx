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
  it("renders grouped navigation sections without forcing nested items open", () => {
    renderAppShell({
      navigationSections: sectionedNavigation,
    });

    expect(screen.getByText("Core")).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /^Organizations/ }),
    ).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Directory" })).toBeNull();
  });

  it("supports nested expand and collapse behavior", () => {
    renderAppShell({
      navigationSections: sectionedNavigation,
    });

    fireEvent.click(screen.getByRole("button", { name: /^Organizations/ }));
    expect(screen.getByRole("link", { name: "Directory" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Credentials" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /^Organizations/ }));
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
        .getByRole("button", { name: /^Organizations/ })
        .getAttribute("data-active"),
    ).toBe("true");
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
    fireEvent.click(screen.getByRole("button", { name: /^Organizations/ }));
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
      screen.getByRole("button", { name: /^Organizations/ }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: "Profile" })).toBeTruthy();
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
