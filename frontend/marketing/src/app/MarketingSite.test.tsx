import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "../App";

describe("MarketingSite", () => {
  beforeEach(() => {
    window.location.hash = "#/developers";
  });

  it("renders the marketing shell for a public-facing route", () => {
    render(<App />);

    expect(screen.getByRole("link", { name: /VerifyForGood/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Developers" })).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Developer onboarding" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Switch to dark mode" }),
    ).toBeTruthy();
  });
});
