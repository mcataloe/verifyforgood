import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "../App";

describe("DocsSite", () => {
  beforeEach(() => {
    window.location.hash = "#/api-usage";
  });

  it("renders the docs shell for a content-focused route", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "VerifyForGood documentation shell",
      }),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "API Usage" })).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "API onboarding" }),
    ).toBeTruthy();
  });
});
