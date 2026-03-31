import { Modal } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VerifyForGoodMantineProvider } from "./index";

describe("modal behavior defaults", () => {
  it("requires explicit dismissal for standard modals", () => {
    const onClose = vi.fn();

    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <Modal onClose={onClose} opened title="Example modal">
          <p>Modal body</p>
        </Modal>
      </VerifyForGoodMantineProvider>,
    );

    const overlay = document.body.querySelector(".mantine-Modal-overlay");
    if (!overlay) {
      throw new Error("Expected modal overlay");
    }

    fireEvent.mouseDown(overlay);
    fireEvent.click(overlay);
    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).not.toHaveBeenCalled();

    const closeButton = document.body.querySelector(".mantine-Modal-close");
    if (!(closeButton instanceof HTMLElement)) {
      throw new Error("Expected modal close button");
    }

    fireEvent.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
