import { Button, Text } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  VerifyForGoodMantineProvider,
} from "./index";

describe("feedback states", () => {
  it("renders loading, empty, and error state primitives", () => {
    render(
      <VerifyForGoodMantineProvider>
        <LoadingSkeleton
          description="Preparing the latest records."
          title="Loading organizations"
          variant="table"
        />
        <EmptyState
          action={<Button variant="light">Create API key</Button>}
          preset="api-keys"
        />
        <ErrorState
          action={<Button variant="light">Retry</Button>}
          description={<Text>The request could not be completed.</Text>}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByText("No API keys created")).toBeTruthy();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
  });
});
