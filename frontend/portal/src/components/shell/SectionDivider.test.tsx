import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SectionDivider } from "./SectionDivider";

describe("SectionDivider", () => {
  it("renders the shared presentational section separator", () => {
    render(<SectionDivider />);

    const divider = screen.getByTestId("section-divider");

    expect(divider.tagName).toBe("HR");
    expect(divider.getAttribute("role")).toBe("presentation");
    expect(divider.getAttribute("aria-hidden")).toBe("true");
  });
});
