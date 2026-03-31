import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StackedDetailSections } from "./StackedDetailSections";

describe("StackedDetailSections", () => {
  it("renders children in document flow with separators between sections", () => {
    const { container } = render(
      <StackedDetailSections>
        <div>First section</div>
        <div>Second section</div>
        <div>Third section</div>
      </StackedDetailSections>,
    );

    expect(screen.getByText("First section")).toBeTruthy();
    expect(screen.getByText("Second section")).toBeTruthy();
    expect(screen.getByText("Third section")).toBeTruthy();
    expect(
      container.querySelectorAll(".portal-stacked-sections__divider"),
    ).toHaveLength(2);
  });

  it("supports semantic section wrappers when requested", () => {
    const { container } = render(
      <StackedDetailSections
        sectionWrapper={({ section, index }) => (
          <section aria-label={`section-${index + 1}`}>{section}</section>
        )}
      >
        <article>Section A</article>
        <article>Section B</article>
      </StackedDetailSections>,
    );

    expect(screen.getByLabelText("section-1")).toBeTruthy();
    expect(screen.getByLabelText("section-2")).toBeTruthy();
    expect(container.querySelectorAll("section")).toHaveLength(2);
  });
});
