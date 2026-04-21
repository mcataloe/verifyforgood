import { fireEvent, render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it } from "vitest";
import { PortalToastProvider, usePortalToast } from "./PortalToastProvider";

describe("PortalToastProvider", () => {
  it("dismisses a toast when the close button is clicked", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <PortalToastProvider>
          <ToastHarness />
        </PortalToastProvider>
      </VerifyForGoodMantineProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Show toast" }));

    expect(screen.getByText("Close me")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));

    expect(screen.queryByText("Close me")).toBeNull();
  });
});

function ToastHarness() {
  const { showToast } = usePortalToast();

  return (
    <button
      onClick={() => {
        showToast({
          id: "toast-test",
          message: "Close me",
          title: "Toast title",
          tone: "error",
        });
      }}
      type="button"
    >
      Show toast
    </button>
  );
}
