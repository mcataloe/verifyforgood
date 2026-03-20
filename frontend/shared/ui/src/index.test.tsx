import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Panel, ThemeRoot } from "./index";

describe("shared ui primitives", () => {
  it("renders shared panel content inside the shared theme root", () => {
    render(
      <ThemeRoot>
        <Panel
          title="Shared panel"
          subtitle="Reusable across frontend surfaces."
        >
          <p>Layout primitives stay generic.</p>
        </Panel>
      </ThemeRoot>,
    );

    expect(screen.getByRole("heading", { name: "Shared panel" })).toBeTruthy();
    expect(screen.getByText(/Layout primitives stay generic\./i)).toBeTruthy();
  });
});
