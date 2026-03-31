import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DetailPageLayout } from "./DetailPageLayout";
import { SectionBlock } from "./SectionBlock";
import { SectionDivider } from "./SectionDivider";

describe("DetailPageLayout", () => {
  it("renders stacked sections in document order with dividers", () => {
    render(
      <DetailPageLayout eyebrow="Profile" intro="Intro copy" title="Profile">
        <SectionBlock title="First">Alpha</SectionBlock>
        <SectionDivider />
        <SectionBlock title="Second">Beta</SectionBlock>
        <SectionDivider />
        <SectionBlock title="Third">Gamma</SectionBlock>
      </DetailPageLayout>,
    );

    expect(screen.getByRole("heading", { name: "Profile" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "First" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Second" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Third" })).toBeTruthy();
    const layout = screen.getByTestId("detail-page-layout");
    const content = layout.querySelector(".portal-detail-layout__content");
    const sections = content?.querySelectorAll(".portal-detail-layout__section");

    expect(layout.className).toContain("portal-authenticated-container");
    expect(layout.className).toContain("portal-detail-layout");
    expect(content).toBeTruthy();
    expect(sections).toHaveLength(3);
    expect(sections?.[0]?.textContent).toContain("Alpha");
    expect(sections?.[1]?.textContent).toContain("Beta");
    expect(sections?.[2]?.textContent).toContain("Gamma");
    expect(screen.getAllByTestId("section-divider")).toHaveLength(2);
  });

  it("supports custom header content", () => {
    render(
      <DetailPageLayout
        header={
          <header>
            <h1>Custom header</h1>
          </header>
        }
      >
        <SectionBlock title="Only section">Body</SectionBlock>
      </DetailPageLayout>,
    );

    expect(screen.getByRole("heading", { name: "Custom header" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Only section" })).toBeTruthy();
  });
});
