import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PortalDetailSection, PortalDetailView } from "./PortalDetailView";

describe("PortalDetailView", () => {
  it("wraps sibling sections in the shared stacked detail layout", () => {
    render(
      <PortalDetailView intro="Shared intro" title="Detail title">
        <PortalDetailSection title="Overview">Alpha</PortalDetailSection>
        <PortalDetailSection title="Sources">Beta</PortalDetailSection>
        <PortalDetailSection title="Activity">Gamma</PortalDetailSection>
      </PortalDetailView>,
    );

    expect(screen.getByTestId("detail-page-layout")).toBeTruthy();
    expect(screen.getByTestId("detail-page-layout-content")).toBeTruthy();
    expect(screen.getAllByTestId("section-divider")).toHaveLength(2);
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Sources" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Activity" })).toBeTruthy();
  });
});
