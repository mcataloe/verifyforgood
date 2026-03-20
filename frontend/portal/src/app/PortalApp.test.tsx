import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "../App";

function createStorageMock(): Storage {
  const store = new Map<string, string>();

  return {
    clear() {
      store.clear();
    },
    getItem(key) {
      return store.get(key) ?? null;
    },
    key(index) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key) {
      store.delete(key);
    },
    setItem(key, value) {
      store.set(key, value);
    },
  };
}

describe("PortalApp", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    window.location.hash = "#/usage-billing";
  });

  it("redirects unauthenticated access to the sign-in boundary", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Sign in to the customer portal",
      }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Usage & Billing" }),
    ).toBeNull();
    expect(screen.getByText(/Requested area/i)).toBeTruthy();
  });

  it("allows the mock sign-in flow and restores the protected route", async () => {
    render(<App />);

    await screen.findByRole("heading", {
      name: "Sign in to the customer portal",
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Continue with demo session" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Customer portal shell" }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Usage & Billing" }),
    ).toBeTruthy();
    expect(screen.getByText(/Usage and billing IA/i)).toBeTruthy();
  });
});
