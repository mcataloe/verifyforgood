import { Stack, Text } from "@mantine/core";
import { Card } from "./Card";
import { DataTable } from "./DataTable";
import { PageHeader } from "./PageHeader";
import { SectionContainer } from "./SectionContainer";
import { StatusBadge } from "./StatusBadge";

const sampleRows = [
  {
    ein: "53-0196605",
    name: "American National Red Cross",
    status: "verified" as const,
  },
  {
    ein: "98-6001029",
    name: "International Committee of the Red Cross",
    status: "pending" as const,
  },
];

/**
 * Storybook-style example composition for the shared application primitives.
 */
export function CorePrimitivesExamples() {
  return (
    <Stack gap="xl">
      <PageHeader
        eyebrow="Examples"
        title="Core UI primitives"
        description="Shared building blocks for dashboard and operations surfaces."
      />

      <SectionContainer
        title="Verification overview"
        description="Example composition using the shared SectionContainer and Card primitives."
      >
        <Card
          title="Verification status"
          description="Recent nonprofit checks and current workflow state."
        >
          <Stack gap="sm">
            <StatusBadge status="verified" />
            <StatusBadge status="pending" />
            <StatusBadge status="flagged" />
            <StatusBadge status="inactive" />
          </Stack>
        </Card>

        <DataTable
          columns={[
            {
              key: "name",
              header: "Organization",
              render: (row) => row.name,
            },
            {
              key: "ein",
              header: "EIN",
              render: (row) => row.ein,
            },
            {
              key: "status",
              header: "Status",
              render: (row) => <StatusBadge status={row.status} />,
            },
          ]}
          rows={sampleRows}
        />

        <Text c="dimmed" fz="sm">
          These examples are intended to be copied into future story files or app
          surfaces as the design system expands.
        </Text>
      </SectionContainer>
    </Stack>
  );
}
