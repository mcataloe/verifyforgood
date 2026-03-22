import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  Card,
  DataTable,
  PageHeader,
  SectionContainer,
  StatusBadge,
  VerifyForGoodMantineProvider,
} from "./index";

describe("core ui primitives", () => {
  it("renders shared primitives inside the Mantine provider", () => {
    render(
      <VerifyForGoodMantineProvider>
        <SectionContainer
          description="Shared layout and data primitives."
          eyebrow="Workspace"
          title="Organizations"
        >
          <PageHeader
            description="Monitor verification outcomes."
            title="Verification queue"
          />
          <Card
            description="Summary of current nonprofit review state."
            title="Status"
          >
            <StatusBadge status="verified" />
          </Card>
          <DataTable
            columns={[
              {
                key: "name",
                header: "Organization",
                render: (row) => row.name,
              },
              {
                key: "status",
                header: "Status",
                render: (row) => <StatusBadge status={row.status} />,
              },
            ]}
            rows={[{ name: "American National Red Cross", status: "pending" as const }]}
          />
        </SectionContainer>
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByRole("heading", { name: "Organizations" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Verification queue" })).toBeTruthy();
    expect(screen.getByText("American National Red Cross")).toBeTruthy();
    expect(screen.getByText("Pending")).toBeTruthy();
    expect(screen.getByText("Verified")).toBeTruthy();
  });
});
