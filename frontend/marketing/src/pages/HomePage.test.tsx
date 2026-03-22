import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
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
      <VerifyForGoodMantineProvider>
        <HomePage
          endpoints={endpoints as Parameters<typeof HomePage>[0]["endpoints"]}
          runtimeConfig={
            runtimeConfig as Parameters<typeof HomePage>[0]["runtimeConfig"]
          }
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByRole("heading", {
        name: "Compliance-grade verification without noisy workflows",
      }),
    ).toBeTruthy();
    expect(
      screen.getByText(
        /Value-forward onboarding keeps usage and upgrade decisions explicit/i,
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(/Grantmaking teams/i),
    ).toBeTruthy();
  });
});
