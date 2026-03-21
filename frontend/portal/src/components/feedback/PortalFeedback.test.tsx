import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  PortalEmptyState,
  PortalErrorState,
  PortalLoadingState,
  PortalNotice,
} from "./index";

describe("portal feedback components", () => {
  it("renders reusable loading, error, and empty states", () => {
    const retry = vi.fn();

    render(
      <>
        <PortalLoadingState
          subtitle="Waiting on a response."
          title="Loading records"
        >
          <p>Loading data now.</p>
        </PortalLoadingState>
        <PortalErrorState
          actionLabel="Retry"
          message="The request failed."
          onAction={retry}
          subtitle="The API call did not succeed."
          title="Request failed"
        />
        <PortalEmptyState
          subtitle="No records matched the current filter."
          title="No results"
        >
          <p>Change the current input and try again.</p>
        </PortalEmptyState>
        <PortalNotice title="Heads up" tone="warning">
          <p>Warning notice.</p>
        </PortalNotice>
      </>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      screen.getByRole("heading", { name: "Loading records" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Request failed" }),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "No results" })).toBeTruthy();
    expect(screen.getByText("Warning notice.")).toBeTruthy();
    expect(retry).toHaveBeenCalled();
  });
});
