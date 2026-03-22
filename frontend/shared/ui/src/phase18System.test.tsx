import { Button, Text } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  CallToAction,
  DataTable,
  EntityDetailLayout,
  FeatureGrid,
  OnboardingLayout,
  VerifyForGoodMantineProvider,
  type DataTableColumn,
} from "./index";

type TableRow = {
  filingYear: string;
  name: string;
  state: string;
  status: string;
};

describe("phase 18 shared foundations", () => {
  it("renders entity detail, onboarding, marketing, and interactive table patterns", () => {
    const rows: TableRow[] = [
      {
        filingYear: "2024",
        name: "Helping Hands Foundation",
        state: "IL",
        status: "verified",
      },
      {
        filingYear: "2023",
        name: "Future Scholars Fund",
        state: "CA",
        status: "pending",
      },
    ];
    const columns: DataTableColumn<TableRow>[] = [
      {
        key: "name",
        header: "Organization",
        sortable: true,
        render: (row) => row.name,
        sortValue: (row) => row.name,
      },
      {
        key: "state",
        header: "State",
        sortable: true,
        render: (row) => row.state,
        sortValue: (row) => row.state,
      },
    ];

    render(
      <VerifyForGoodMantineProvider>
        <EntityDetailLayout
          description="Shared review layout for organization detail screens."
          ein="12-3456789"
          name="Helping Hands Foundation"
          status="verified"
          summaryItems={[
            { key: "irs", label: "IRS status", value: "Active" },
            { key: "filing", label: "Most recent filing", value: "2024" },
            { key: "classification", label: "Classification", value: "Human services" },
            { key: "risk", label: "Risk indicators", value: "2 flags" },
          ]}
          tabs={[
            { key: "overview", label: "Overview", content: <Text>Overview tab</Text> },
            { key: "filings", label: "Filings", content: <Text>Filings tab</Text> },
          ]}
        />
        <DataTable
          columns={columns}
          filterDefinitions={[
            {
              key: "state",
              label: "State",
              options: [
                { label: "Illinois", value: "IL" },
                { label: "California", value: "CA" },
              ],
              getValue: (row) => row.state,
            },
          ]}
          getSearchText={(row) => `${row.name} ${row.filingYear}`}
          rows={rows}
        />
        <OnboardingLayout
          steps={[
            {
              key: "welcome",
              label: "Welcome",
              status: "complete",
              description: "Review workspace setup.",
              action: <Button variant="subtle">Review</Button>,
            },
            {
              key: "verification",
              label: "Create first verification",
              status: "current",
              description: "Run the first verification request.",
            },
          ]}
          title="Onboarding"
        />
        <FeatureGrid
          items={[
            { title: "Verification", description: "Review nonprofit status." },
          ]}
        />
        <CallToAction
          actions={<Button>Start free</Button>}
          description="Keep setup lightweight and predictable."
          title="Move from evaluation to rollout"
        />
      </VerifyForGoodMantineProvider>,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "Search rows" }), {
      target: { value: "Future" },
    });

    expect(screen.getByRole("heading", { name: "Helping Hands Foundation" })).toBeTruthy();
    expect(screen.getByRole("table", { name: "Data table" })).toBeTruthy();
    expect(screen.getByText("Future Scholars Fund")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Onboarding" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Verification" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Move from evaluation to rollout" })).toBeTruthy();
  });
});
