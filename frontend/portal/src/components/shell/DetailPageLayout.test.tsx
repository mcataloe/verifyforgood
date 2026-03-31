import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DetailPageLayout } from "./DetailPageLayout";
import { SectionBlock } from "./SectionBlock";
import { SectionDivider } from "./SectionDivider";

describe("DetailPageLayout", () => {
  it("renders stacked sections in document order with dividers", () => {
    const { container } = render(
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
    expect(
      container.querySelector(".portal-authenticated-container.portal-detail-layout"),
    ).toBeTruthy();
    expect(
      container.querySelectorAll(".portal-detail-layout__divider"),
    ).toHaveLength(2);
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
