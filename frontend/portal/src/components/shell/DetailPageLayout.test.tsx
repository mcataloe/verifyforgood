import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DetailPageLayout, SectionBlock, SectionDivider } from "./DetailPageLayout";

describe("DetailPageLayout", () => {
  it("stacks sections and inserts dividers between siblings", () => {
    const { container } = render(
      <DetailPageLayout>
        <SectionBlock>
          <div>Section one</div>
        </SectionBlock>
        <SectionBlock>
          <div>Section two</div>
        </SectionBlock>
        <SectionBlock>
          <div>Section three</div>
        </SectionBlock>
      </DetailPageLayout>,
    );

    expect(screen.getByText("Section one")).toBeTruthy();
    expect(screen.getByText("Section two")).toBeTruthy();
    expect(screen.getByText("Section three")).toBeTruthy();
    expect(container.querySelectorAll(".portal-stacked-sections__divider")).toHaveLength(2);
  });

  it("exposes a dedicated divider primitive for explicit composition", () => {
    const { container } = render(<SectionDivider />);

    expect(container.querySelector(".portal-stacked-sections__divider")).toBeTruthy();
  });
});
