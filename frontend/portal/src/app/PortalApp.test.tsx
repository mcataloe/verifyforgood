import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "../App";

describe("PortalApp", () => {
  beforeEach(() => {
    window.location.hash = "#/usage-billing";
  });

  it("renders the portal shell for an authenticated product area", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Customer portal shell" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Usage & Billing" }),
    ).toBeTruthy();
    expect(screen.getByText(/Usage and billing IA/i)).toBeTruthy();
  });
});
