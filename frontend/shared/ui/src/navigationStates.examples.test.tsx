import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NavigationStatesExamples } from "./components/NavigationStates.examples";

describe("NavigationStatesExamples", () => {
  it("switches between role and plan scenarios", () => {
    render(<NavigationStatesExamples />);

    expect(screen.getByRole("link", { name: "API" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Billing" })).toBeNull();

    fireEvent.click(screen.getByRole("tab", { name: "Customer Admin" }));
    expect(screen.getByRole("link", { name: "Billing" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Customer User" }));
    expect(screen.queryByRole("link", { name: "Billing" })).toBeNull();
    expect(screen.queryByRole("link", { name: "API" })).toBeNull();
  });

  it("shows locked API state for the free-plan admin scenario", () => {
    render(<NavigationStatesExamples />);

    fireEvent.click(screen.getByRole("tab", { name: "Locked API" }));

    const lockedApi = screen.getByRole("button", { name: /^API\b/i });
    const isUnavailable =
      lockedApi.getAttribute("aria-disabled") === "true" ||
      lockedApi.getAttribute("data-disabled") !== null;

    expect(isUnavailable).toBe(true);
    expect(screen.getByText("Locked")).toBeTruthy();
  });
});
