import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  Card,
  DataTable,
  DetailFieldList,
  DetailStack,
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
          <DetailStack
            description="Readable embedded detail body content."
            title="Organization details"
          >
            <DetailFieldList
              items={[
                {
                  key: "ein",
                  label: "EIN",
                  value: "12-3456789",
                },
                {
                  key: "source",
                  label: "Execution",
                  value:
                    "mock_123456789_this_is_a_long_identifier_for_wrapping",
                  detail:
                    "Long identifiers should stay readable inside the list.",
                },
              ]}
            />
          </DetailStack>
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
            rows={[
              {
                name: "American National Red Cross",
                status: "pending" as const,
              },
            ]}
          />
        </SectionContainer>
      </VerifyForGoodMantineProvider>,
    );

    expect(screen.getByRole("heading", { name: "Organizations" })).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Verification queue" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Organization details" }),
    ).toBeTruthy();
    expect(screen.getByText("American National Red Cross")).toBeTruthy();
    expect(screen.getByText("12-3456789")).toBeTruthy();
    expect(
      screen.getByText("mock_123456789_this_is_a_long_identifier_for_wrapping"),
    ).toBeTruthy();
    expect(screen.getByText("Pending review")).toBeTruthy();
    expect(screen.getByText("Evidence complete")).toBeTruthy();
    expect(document.querySelector(".vf-detail-field-list")).toBeTruthy();
    expect(document.querySelector(".vf-detail-stack")).toBeTruthy();
  });
});
