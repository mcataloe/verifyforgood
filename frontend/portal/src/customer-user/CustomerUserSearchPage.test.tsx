import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { CustomerUserSearchPage } from "./CustomerUserSearchPage";

describe("CustomerUserSearchPage", () => {
  it("renders the EIN search pane with sortable location columns and detail drill-in", () => {
    const { container } = render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <CustomerUserSearchPage pane="search-ein" />
      </VerifyForGoodMantineProvider>,
    );

    fireEvent.change(screen.getByLabelText("EIN"), {
      target: { value: "13-1635294" },
    });
    fireEvent.click(screen.getByRole("button", { name: "By EIN" }));

    expect(
      screen.getAllByText("American National Red Cross").length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Sort by City" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sort by State" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sort by Zip" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "View details" }));

    expect(
      screen.getByRole("heading", { name: "American National Red Cross" }),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Filings" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Compliance" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Sources" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Activity" })).toBeTruthy();
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(
      container.querySelectorAll(".portal-detail-layout__divider").length,
    ).toBeGreaterThanOrEqual(2);
  });

  it("renders the address search pane with address, city, state, and zip fields", () => {
    const { container } = render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <CustomerUserSearchPage pane="search-address" />
      </VerifyForGoodMantineProvider>,
    );

    fireEvent.change(screen.getByLabelText("City"), {
      target: { value: "Chicago" },
    });
    fireEvent.change(screen.getByLabelText("State"), {
      target: { value: "IL" },
    });
    fireEvent.click(screen.getByRole("button", { name: "By Address" }));

    expect(screen.getByLabelText("Address")).toBeTruthy();
    expect(screen.getByLabelText("Zip")).toBeTruthy();
    expect(screen.getAllByText("Feeding America").length).toBeGreaterThan(0);
    expect(container.querySelector(".portal-form--two-column")).toBeNull();
  });
});
