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
    expect(screen.getByTestId("detail-page-layout")).toBeTruthy();
    expect(screen.getByTestId("detail-page-layout-content")).toBeTruthy();
    expect(screen.getAllByTestId("section-divider")).toHaveLength(2);

    const content = screen.getByTestId("detail-page-layout-content");
    const firstSection = screen.getByRole("heading", { name: "First" }).closest("section");
    const secondSection = screen.getByRole("heading", { name: "Second" }).closest("section");
    const thirdSection = screen.getByRole("heading", { name: "Third" }).closest("section");
    const dividers = screen.getAllByTestId("section-divider");
    const orderedChildren = Array.from(content.children);

    expect(orderedChildren).toStrictEqual([
      firstSection,
      dividers[0],
      secondSection,
      dividers[1],
      thirdSection,
    ]);
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
