import { fireEvent, render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
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
      <VerifyForGoodMantineProvider defaultColorScheme="light">
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
        </>
      </VerifyForGoodMantineProvider>,
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

  it("dismisses a notice from the shared feedback template", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <PortalNotice title="Heads up" tone="warning">
          <p>Dismiss me.</p>
        </PortalNotice>
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByText("Dismiss me.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Dismiss Heads up" }));

    expect(screen.queryByText("Dismiss me.")).toBeNull();
  });
});
