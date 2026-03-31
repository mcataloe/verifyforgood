import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PortalDetailSection, PortalDetailView } from "./PortalDetailView";

describe("PortalDetailView", () => {
  it("keeps sibling sections in one shared detail layout with inserted dividers", () => {
    render(
      <PortalDetailView eyebrow="Profile" intro="Shared intro" title="Detail title">
        <PortalDetailSection title="Overview">Alpha</PortalDetailSection>
        <PortalDetailSection title="Sources">Beta</PortalDetailSection>
        <PortalDetailSection title="Activity">Gamma</PortalDetailSection>
      </PortalDetailView>,
    );

    const layout = screen.getByTestId("detail-page-layout");
    const sections = layout.querySelectorAll(".portal-detail-layout__section");

    expect(screen.getByRole("heading", { name: "Detail title" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Sources" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Activity" })).toBeTruthy();
    expect(sections).toHaveLength(3);
    expect(sections[0]?.textContent).toContain("Alpha");
    expect(sections[1]?.textContent).toContain("Beta");
    expect(sections[2]?.textContent).toContain("Gamma");
    expect(screen.getAllByTestId("section-divider")).toHaveLength(2);
    expect(layout.querySelector(".portal-page-grid")).toBeNull();
    expect(screen.queryByRole("tablist")).toBeNull();
  });
});
