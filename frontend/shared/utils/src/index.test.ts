import { describe, expect, it } from "vitest";
import { formatSurfaceLabel } from "./index";

describe("shared utility helpers", () => {
  it("formats frontend surface labels consistently", () => {
    expect(formatSurfaceLabel("marketing")).toBe("Marketing app");
    expect(formatSurfaceLabel("portal")).toBe("Customer portal");
    expect(formatSurfaceLabel("docs")).toBe("Documentation app");
  });
});
