import { render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it } from "vitest";
import { PortalPageShell } from "./PortalPageShell";

describe("PortalPageShell", () => {
  it("applies the authenticated portal width container", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <PortalPageShell
          description="Shell description"
          eyebrow="Portal"
          title="Shell title"
        >
          <div>Body</div>
        </PortalPageShell>
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByRole("heading", { name: "Shell title" })).toBeTruthy();
    const container = screen.getByTestId("portal-page-container");
    expect(container.className).toContain("portal-authenticated-container");
    expect(container.className).toContain("portal-page-shell");
  });
});
