import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ThemeRoot } from "@charity-status/shared-ui";
import { HomePage } from "./HomePage";

const endpoints = {
  nonprofitSearch: "/v1/nonprofits/search",
  nonprofitVerify: "/v1/nonprofits/verify",
} as const;

const runtimeConfig = {
  environment: "test",
} as const;

describe("HomePage", () => {
  it("keeps free-tier and trial messaging clear and non-intrusive", () => {
    render(
      <ThemeRoot>
        <HomePage
          endpoints={endpoints as Parameters<typeof HomePage>[0]["endpoints"]}
          runtimeConfig={
            runtimeConfig as Parameters<typeof HomePage>[0]["runtimeConfig"]
          }
        />
      </ThemeRoot>,
    );

    expect(screen.getByRole("heading", { name: "Start on free" })).toBeTruthy();
    expect(
      screen.getByText(
        "Value-forward onboarding without urgency or surprise billing.",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        /Paid enrollment stays separate so teams move up only when the additional capacity is useful./i,
      ),
    ).toBeTruthy();
  });
});
